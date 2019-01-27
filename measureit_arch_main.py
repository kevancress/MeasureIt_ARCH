# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

# ----------------------------------------------------------
# File: measureit_arch_main.py
# Main panel for different MeasureitArch general actions
# Author: Antonio Vazquez (antonioya), Kevan Cress
#
# ----------------------------------------------------------
# noinspection PyUnresolvedReferences
import bpy
import bmesh
from bmesh import from_edit_mesh
# noinspection PyUnresolvedReferences
import bgl
import gpu
from gpu_extras.batch import batch_for_shader

from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, BoolProperty, StringProperty, \
                      FloatProperty, EnumProperty
from bpy.app.handlers import persistent
# noinspection PyUnresolvedReferences
from .measureit_arch_geometry import *
from .measureit_arch_render import *

import gpu
from gpu_extras.batch import batch_for_shader

coords = [(100, 100, 1), (200, 400, 0), (-2, -1, 3), (0, 1, 1)]
shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
batch = batch_for_shader(shader, 'LINES', {"pos": coords})

# ------------------------------------------------------
# Handler to detect new Blend load
#
# ------------------------------------------------------
# noinspection PyUnusedLocal
@persistent
def load_handler(dummy):
    RunHintDisplayButton.handle_remove(None, bpy.context)


# ------------------------------------------------------
# Handler to detect save Blend
# Clear not used measured
#
# ------------------------------------------------------
# noinspection PyUnusedLocal
@persistent
def save_handler(dummy):
    # noinspection PyBroadException
    try:
        print("MeasureIt-ARCH: Cleaning data")
        objlist = bpy.context.scene.objects
        for myobj in objlist:
            if 'MeasureGenerator' in myobj:
                mp = myobj.MeasureGenerator[0]
                x = 0
                for ms in mp.measureit_arch_segments:
                    ms.name = "segment_" + str(x)
                    x += 1
                    if ms.glfree is True:
                        idx = mp.measureit_arch_segments.find(ms.name)
                        if idx > -1:
                            print("MeasureIt-ARCH: Removed segment not used")
                            mp.measureit_arch_segments.remove(idx)

                # reset size
                mp.measureit_arch_num = len(mp.measureit_arch_segments)
    except:
        pass


bpy.app.handlers.load_post.append(load_handler)
bpy.app.handlers.save_pre.append(save_handler)


# ------------------------------------------------------------------
# Define property group class for measureit_arch faces index
# ------------------------------------------------------------------
class MeasureitArchIndex(PropertyGroup):
    glidx = IntProperty(name="index",
                        description="vertex index")


# Register
bpy.utils.register_class(MeasureitArchIndex)


# ------------------------------------------------------------------
# Define property group class for measureit_arch faces
# ------------------------------------------------------------------
class MeasureitArchFaces(PropertyGroup):
    glface = IntProperty(name="glface",
                         description="Face number")
    # Array of index
    measureit_arch_index: CollectionProperty(type=MeasureitArchIndex)


# Register
bpy.utils.register_class(MeasureitArchFaces)


# ------------------------------------------------------------------
# Define property group class for measureit_arch data
# ------------------------------------------------------------------
class MeasureitArchProperties(PropertyGroup):
    style: IntProperty(name="style",
                        description="Dimension Style to use",
                        min = 0)
    gltype: IntProperty(name="gltype",
                         description="Measure type (1-Segment, 2-Label, etc..)", default=1)
    glpointa: IntProperty(name="glpointa",
                           description="Hidden property for opengl")
    glpointb: IntProperty(name="glpointb",
                           description="Hidden property for opengl")
    glpointc: IntProperty(name="glpointc",
                           description="Hidden property for opengl")
    glcolor: FloatVectorProperty(name="glcolor",
                                  description="Color for the measure",
                                  default=(0.173, 0.545, 1.0, 1.0),
                                  min=0.1,
                                  max=1,
                                  subtype='COLOR',
                                  size=4)
    glview: BoolProperty(name="glview",
                          description="Measure visible/hide",
                          default=True)
    glspace: FloatProperty(name='glspace', min=-100, max=100, default=0.1,
                            precision=3,
                            description='Distance to display measure')
    glwidth: IntProperty(name='glwidth', min=1, max=20, default=1,
                          description='line width')
    glfree: BoolProperty(name="glfree",
                          description="This measure is free and can be deleted",
                          default=False)
    gltxt: StringProperty(name="gltxt", maxlen=256,
                           description="Short description (use | for line break)")
    gladvance: BoolProperty(name="gladvance",
                             description="Advanced options as line width or position",
                             default=False)
    gldefault: BoolProperty(name="gldefault",
                             description="Display measure in position calculated by default",
                             default=True)
    glnormalx: FloatProperty(name="glnormalx",
                              description="Change orientation in X axis",
                              default=1, min=-1, max=1, precision=2)
    glnormaly: FloatProperty(name="glnormaly",
                              description="Change orientation in Y axis",
                              default=0, min=-1, max=1, precision=2)
    glnormalz: FloatProperty(name="glnormalz",
                              description="Change orientation in Z axis",
                              default=0, min=-1, max=1, precision=2)
    glfont_size: IntProperty(name="Text Size",
                              description="Text size",
                              default=14, min=6, max=150)
    glfont_align: EnumProperty(items=(('L', "Left align", ""),
                                       ('C', "Center align", ""),
                                       ('R', "Right align", "")),
                                name="align Font",
                                description="Set Font alignment")
    glfont_rotat: IntProperty(name='Rotate', min=0, max=360, default=0,
                                description="Text rotation in degrees")
    gllink: StringProperty(name="gllink",
                            description="linked object for linked measures")
    glocwarning: BoolProperty(name="glocwarning",
                               description="Display a warning if some axis is not used in distance",
                               default=True)
    glocx: BoolProperty(name="glocx",
                         description="Include changes in X axis for calculating the distance",
                         default=True)
    glocy: BoolProperty(name="glocy",
                         description="Include changes in Y axis for calculating the distance",
                         default=True)
    glocz: BoolProperty(name="glocz",
                         description="Include changes in Z axis for calculating the distance",
                         default=True)
    glfontx: IntProperty(name="glfontx",
                          description="Change font position in X axis",
                          default=0, min=-3000, max=3000)
    glfonty: IntProperty(name="glfonty",
                          description="Change font position in Y axis",
                          default=0, min=-3000, max=3000)
    gldist: BoolProperty(name="gldist",
                          description="Display distance for this measure",
                          default=True)
    glnames: BoolProperty(name="glnames",
                           description="Display text for this measure",
                           default=True)
    gltot: EnumProperty(items=(('99', "-", "Select a group for sum"),
                                ('0', "A", ""),
                                ('1', "B", ""),
                                ('2', "C", ""),
                                ('3', "D", ""),
                                ('4', "E", ""),
                                ('5', "F", ""),
                                ('6', "G", ""),
                                ('7', "H", ""),
                                ('8', "I", ""),
                                ('9', "J", ""),
                                ('10', "K", ""),
                                ('11', "L", ""),
                                ('12', "M", ""),
                                ('13', "N", ""),
                                ('14', "O", ""),
                                ('15', "P", ""),
                                ('16', "Q", ""),
                                ('17', "R", ""),
                                ('18', "S", ""),
                                ('19', "T", ""),
                                ('20', "U", ""),
                                ('21', "V", ""),
                                ('22', "W", ""),
                                ('23', "X", ""),
                                ('24', "Y", ""),
                                ('25', "Z", "")),
                         name="Sum in Group",
                         description="Add segment length in selected group")
    glorto: EnumProperty(items=(('99', "None", ""),
                                 ('0', "A", "Point A must use selected point B location"),
                                 ('1', "B", "Point B must use selected point A location")),
                          name="Orthogonal",
                          description="Display point selected as orthogonal (select axis to copy)")
    glorto_x: BoolProperty(name="ox",
                            description="Copy X location",
                            default=False)
    glorto_y: BoolProperty(name="oy",
                            description="Copy Y location",
                            default=False)
    glorto_z: BoolProperty(name="oz",
                            description="Copy Z location",
                            default=False)
    glarrow_a: EnumProperty(items=(('99', "--", "No arrow"),
                                    ('1', "Line", "The point of the arrow are lines"),
                                    ('2', "Triangle", "The point of the arrow is triangle"),
                                    ('3', "TShape", "The point of the arrow is a T")),
                             name="A end",
                             description="Add arrows to point A")
    glarrow_b: EnumProperty(items=(('99', "--", "No arrow"),
                                    ('1', "Line", "The point of the arrow are lines"),
                                    ('2', "Triangle", "The point of the arrow is triangle"),
                                    ('3', "TShape", "The point of the arrow is a T")),
                             name="B end",
                             description="Add arrows to point B")
    glarrow_s: IntProperty(name="Size",
                            description="Arrow size",
                            default=15, min=6, max=500)

    glarc_full: BoolProperty(name="arcfull",
                              description="Create full circunference",
                              default=False)
    glarc_extrad: BoolProperty(name="arcextrad",
                                description="Adapt radio lengh to arc line",
                                default=True)
    glarc_rad: BoolProperty(name="arc rad",
                             description="Show arc radius",
                             default=True)
    glarc_len: BoolProperty(name="arc len",
                             description="Show arc length",
                             default=True)
    glarc_ang: BoolProperty(name="arc ang",
                             description="Show arc angle",
                             default=True)

    glarc_a: EnumProperty(items=(('99', "--", "No arrow"),
                                  ('1', "Line", "The point of the arrow are lines"),
                                  ('2', "Triangle", "The point of the arrow is triangle"),
                                  ('3', "TShape", "The point of the arrow is a T")),
                           name="Ar end",
                           description="Add arrows to point A")
    glarc_b: EnumProperty(items=(('99', "--", "No arrow"),
                                  ('1', "Line", "The point of the arrow are lines"),
                                  ('2', "Triangle", "The point of the arrow is triangle"),
                                  ('3', "TShape", "The point of the arrow is a T")),
                           name="Br end",
                           description="Add arrows to point B")
    glarc_s: IntProperty(name="Size",
                          description="Arrow size",
                          default=15, min=6, max=500)
    glarc_txradio: StringProperty(name="txradio",
                                   description="Text for radius", default="r=")
    glarc_txlen: StringProperty(name="txlen",
                                 description="Text for length", default="L=")
    glarc_txang: StringProperty(name="txang",
                                 description="Text for angle", default="A=")
    glcolorarea: FloatVectorProperty(name="glcolorarea",
                                      description="Color for the measure of area",
                                      default=(0.1, 0.1, 0.1, 1.0),
                                      min=0.1,
                                      max=1,
                                      subtype='COLOR',
                                      size=4)

    # Array of faces
    measureit_arch_faces: CollectionProperty(type=MeasureitArchFaces)


# Register
bpy.utils.register_class(MeasureitArchProperties)


# ------------------------------------------------------------------
# Define object class (container of segments)
# MeasureitArch
# ------------------------------------------------------------------
class MeasureContainer(PropertyGroup):
    measureit_arch_num = IntProperty(name='Number of measures', min=0, max=1000, default=0,
                                description='Number total of measureit_arch elements')
    # Array of segments
    measureit_arch_segments = CollectionProperty(type=MeasureitArchProperties)


bpy.utils.register_class(MeasureContainer)
Object.MeasureGenerator = CollectionProperty(type=MeasureContainer)

# ------------------------------------------------------------------
# Define property group class for individual line Data
# ------------------------------------------------------------------
class SingleLineProperties(PropertyGroup):
    pointA: IntProperty(name = "pointA",
                        description = "first vertex index of the line")
                        
    pointB: IntProperty(name = "pointB",
                        description = "Second vertex index of the line")

bpy.utils.register_class(SingleLineProperties)

# ------------------------------------------------------------------
# Define property group class for line data
# ------------------------------------------------------------------

class LineProperties(PropertyGroup):
    lineStyle: IntProperty(name="lineStyle",
                        description="Dimension Style to use",
                        min = 0)
    
    lineColor: FloatVectorProperty(name="lineColor",
                        description="Color for Lines",
                        default=(0.1, 0.1, 0.1, 1.0),
                        min=0.0,
                        max=1,
                        subtype='COLOR',
                        size=4) 

    lineWeight: IntProperty(name="lineWeight",
                        description="Lineweight",
                        min = 1,
                        max = 10)

    lineVis: BoolProperty(name="lineVis",
                        description="Line show/hide",
                        default=True)

    lineFree: BoolProperty(name="lineFree",
                        description="This line is free and can be deleted",
                        default=False)

    numLines: IntProperty(name="numLines",
                        description="Number Of Single Lines")

    lineDrawHidden: BoolProperty(name= "lineDrawHidden",
                        description= "Draw Hidden Lines",
                        default= False)
    
    lineSettings: BoolProperty(name= "lineSettings",
                        description= "Show Line Settings",
                        default=False)

    lineHiddenColor: FloatVectorProperty(name="lineHiddenColor",
                        description="Color for Hidden Lines",
                        default=(0.2, 0.2, 0.2, 1.0),
                        min=0.0,
                        max=1,
                        subtype='COLOR',
                        size=4) 

    lineHiddenWeight: IntProperty(name="lineHiddenWeight",
                        description="Hidden Line Lineweight",
                        default= 1,
                        min = 0,
                        max = 10)
    
    lineHiddenDashScale: IntProperty(name="lineHiddenDashScale",
                        description="Hidden Line Dash Scale",
                        default= 10,
                        min = 0)

    isOutline: BoolProperty(name= "isOutline",
                        description= "Line Group Is For Drawing Outlines",
                        default=False)
    #collection of indicies                        
    singleLine: CollectionProperty(type=SingleLineProperties)

# Register
bpy.utils.register_class(LineProperties)



# ------------------------------------------------------------------
# Define object class (container of lines)
# MeasureitArch
# ------------------------------------------------------------------
class LineContainer(PropertyGroup):
    line_num: IntProperty(name='Number of Line Groups', min=0, max=1000, default=0,
                                description='Number total of line groups')
    # Array of segments
    line_groups: CollectionProperty(type=LineProperties)


bpy.utils.register_class(LineContainer)
Object.LineGenerator = CollectionProperty(type=LineContainer)


# ------------------------------------------------------------------
# Define UI class
# show/Hide Dimensions
# ------------------------------------------------------------------
class MeasureitArchShowHidePanel(Panel):
    bl_idname = "measureit_arch.showhidepanel"
    bl_label = "Show/Hide Dimensions"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MeasureIt-ARCH'

    # -----------------------------------------------------
    # Draw (create UI interface)
    # -----------------------------------------------------
    # noinspection PyUnusedLocal
    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        # ------------------------------
        # Display Buttons
        # ------------------------------
        row = box.row(align=True)
        
        if context.window_manager.measureit_arch_run_opengl is False:
            icon = 'PLAY'
            txt = 'Show'
        else:
            icon = "PAUSE"
            txt = 'Hide'

        row.operator("measureit_arch.runopenglbutton", text=txt, icon=icon ,)
        row.prop(scene, "measureit_arch_gl_ghost", text="", icon='GHOST_ENABLED')


# ------------------------------------------------------------------
# Define panel class for main functions.
# ------------------------------------------------------------------
class MeasureitArchMainPanel(Panel):
    bl_idname = "MEASUREIT_PT_main_panel"
    bl_label = "Add Dimension"
    bl_space_type = 'VIEW_3D'
    bl_region_type = "UI"
    bl_category = 'MeasureIt-ARCH'

    # ------------------------------
    # Draw UI
    # ------------------------------
    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # ------------------------------
        # Tool Buttons
        # ------------------------------

        # Tools
        box = layout.box()
        box.label(text="Add Measures")
        row = box.row()
        row.operator("measureit_arch.addsegmentbutton", text="Segment", icon="ALIGN_CENTER")
        row = box.row()
        row.prop(scene, "measureit_arch_sum", text="Sum")

        # To origin
        row = box.row()
        split = row.split(align=True)
        op = split.operator("measureit_arch.addsegmentortobutton", text="X", icon="ALIGN_CENTER")
        op.tag = 0  # saves internal data
        op = split.operator("measureit_arch.addsegmentortobutton", text="Y", icon="ALIGN_CENTER")
        op.tag = 1  # saves internal data
        op = split.operator("measureit_arch.addsegmentortobutton", text="Z", icon="ALIGN_CENTER")
        op.tag = 2  # saves internal data

        row = box.row()
        row.operator("measureit_arch.addanglebutton", text="Angle", icon="LINCURVE")
        row = box.row()
        row.operator("measureit_arch.addarcbutton", text="Arc", icon="DRIVER_ROTATIONAL_DIFFERENCE")

        row = box.row()
        row.operator("measureit_arch.addlabelbutton", text="Label", icon="FONT_DATA")
        row = box.row()
        row.operator("measureit_arch.addnotebutton", text="Annotation", icon="FILE_NEW")

        row = box.row()
        row.operator("measureit_arch.addlinkbutton", text="Link", icon="PIVOT_MEDIAN")
        row = box.row()
        row.operator("measureit_arch.addoriginbutton", text="Origin", icon="PIVOT_CURSOR")

        row = box.row()
        row.operator("measureit_arch.addareabutton", text="Area", icon="MESH_GRID")
        
        # ------------------------------
        # Linework Tools
        # ------------------------------
    
        box = layout.box()
        box.label(text="Add Lines")
        row = box.row()
        row.operator("measureit_arch.addlinebutton", text="Line", icon="ALIGN_CENTER")

        # ------------------------------
        # Debug data
        # ------------------------------
        box = layout.box()
        row = box.row(align=False)
        if scene.measureit_arch_debug is False:
            row.prop(scene, "measureit_arch_debug", icon="TRIA_RIGHT",
                     text="Mesh Debug", emboss=False)
        else:
            row.prop(scene, "measureit_arch_debug", icon="TRIA_DOWN",
                     text="Mesh Debug", emboss=False)

            row = box.row()
            split = row.split(factor=0.10, align=True)
            split.prop(scene, 'measureit_arch_debug_obj_color', text="")
            split.prop(scene, "measureit_arch_debug_objects", icon="OBJECT_DATA")
            split.prop(scene, "measureit_arch_debug_object_loc", icon="EMPTY_DATA")

            row = box.row()
            split = row.split(factor=0.10, align=True)
            split.prop(scene, 'measureit_arch_debug_vert_color', text="")
            split.prop(scene, "measureit_arch_debug_vertices", icon="VERTEXSEL")
            split.prop(scene, "measureit_arch_debug_vert_loc", icon="EMPTY_DATA")
            if scene.measureit_arch_debug_vert_loc is True:
                split.prop(scene, 'measureit_arch_debug_vert_loc_toggle', text="")

            row = box.row()
            split = row.split(factor=0.10, align=True)
            split.prop(scene, 'measureit_arch_debug_edge_color', text="")
            split = split.split(factor=0.5, align=True)
            split.prop(scene, "measureit_arch_debug_edges", icon="EDGESEL")

            row = box.row()
            split = row.split(factor=0.10, align=True)
            split.prop(scene, 'measureit_arch_debug_face_color', text="")
            split = split.split(factor=0.5, align=True)
            split.prop(scene, "measureit_arch_debug_faces", icon="FACESEL")

            row = box.row()
            split = row.split(factor=0.10, align=True)
            split.prop(scene, 'measureit_arch_debug_norm_color', text="")
            if scene.measureit_arch_debug_normals is False:
                split = split.split(factor=0.50, align=True)
                split.prop(scene, "measureit_arch_debug_normals", icon="DRIVER_TRANSFORM")
            else:
                split = split.split(factor=0.5, align=True)
                split.prop(scene, "measureit_arch_debug_normals", icon="DRIVER_TRANSFORM")
                split.prop(scene, "measureit_arch_debug_normal_size")
                row = box.row()
                split = row.split(factor=0.10, align=True)
                split.separator()
                split.prop(scene, "measureit_arch_debug_normal_details")
                split.prop(scene, 'measureit_arch_debug_width', text="Thickness")

            row = box.row(align=True)
            row.prop(scene, "measureit_arch_debug_select", icon="GHOST_ENABLED")
            row.prop(scene, 'measureit_arch_debug_font', text="Font")
            row.prop(scene, 'measureit_arch_debug_precision', text="Precision")


# ------------------------------------------------------------------
# Define panel class for conf functions.
# ------------------------------------------------------------------


# -------------------------------------------------------------
# Defines button that adds a measure segment
#
# -------------------------------------------------------------
class AddSegmentButton(Operator):
    bl_idname = "measureit_arch.addsegmentbutton"
    bl_label = "Add"
    bl_description = "(EDITMODE only) Add a new measure segment between 2 vertices (select 2 vertices or more)"
    bl_category = 'MeasureitArch'

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "MESH":
                if bpy.context.mode == 'EDIT_MESH':
                    return True
                else:
                    return False
            else:
                return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # Add properties
            scene = context.scene
            mainobject = context.object
            mylist = get_smart_selected(mainobject)
            if len(mylist) < 2:  # if not selected linked vertex
                mylist = get_selected_vertex(mainobject)

            if len(mylist) >= 2:
                if 'MeasureGenerator' not in mainobject:
                    mainobject.MeasureGenerator.add()

                mp = mainobject.MeasureGenerator[0]
                for x in range(0, len(mylist) - 1, 2):
                    # -----------------------
                    # Only if not exist
                    # -----------------------
                    if exist_segment(mp, mylist[x], mylist[x + 1]) is False:
                        # Create all array elements
                        for cont in range(len(mp.measureit_arch_segments) - 1, mp.measureit_arch_num):
                            mp.measureit_arch_segments.add()

                        # Set values
                        ms = mp.measureit_arch_segments[mp.measureit_arch_num]
                        ms.gltype = 1
                        ms.style = scene.measureit_arch_default_style
                        ms.glpointa = mylist[x]
                        ms.glpointb = mylist[x + 1]
                        ms.glarrow_a = scene.measureit_arch_glarrow_a
                        ms.glarrow_b = scene.measureit_arch_glarrow_b
                        ms.glarrow_s = scene.measureit_arch_glarrow_s
                        # color
                        ms.glcolor = scene.measureit_arch_default_color
                        # dist
                        ms.glspace = scene.measureit_arch_hint_space
                        # text
                        ms.gltxt = scene.measureit_arch_gl_txt
                        ms.glfont_size = scene.measureit_arch_font_size
                        ms.glfont_align = scene.measureit_arch_font_align
                        ms.glfont_rotat = scene.measureit_arch_font_rotation
                        # Sum group
                        ms.gltot = scene.measureit_arch_sum
                        # Add index
                        mp.measureit_arch_num += 1

                # redraw
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: Select at least two vertices for creating measure segment.")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}


# -------------------------------------------------------------
# Defines button that adds an area measure
#
# -------------------------------------------------------------
class AddAreaButton(Operator):
    bl_idname = "measureit_arch.addareabutton"
    bl_label = "Area"
    bl_description = "(EDITMODE only) Add a new measure for area (select 1 o more faces)"
    bl_category = 'MeasureitArch'

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "MESH":
                if bpy.context.mode == 'EDIT_MESH':
                    return True
                else:
                    return False
            else:
                return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # Add properties
            scene = context.scene
            mainobject = context.object
            mylist = get_selected_faces(mainobject)
            if len(mylist) >= 1:
                if 'MeasureGenerator' not in mainobject:
                    mainobject.MeasureGenerator.add()

                mp = mainobject.MeasureGenerator[0]
                mp.measureit_arch_segments.add()
                ms = mp.measureit_arch_segments[mp.measureit_arch_num]
                ms.gltype = 20

                f = -1
                for face in mylist:
                    # Create array elements
                    ms.measureit_arch_faces.add()
                    f += 1
                    # Set values
                    mf = ms.measureit_arch_faces[f]
                    mf.glface = f
                    i = 0
                    for v in face:
                        mf.measureit_arch_index.add()
                        mi = mf.measureit_arch_index[i]
                        mi.glidx = v
                        i += 1

                # color
                rgb = scene.measureit_arch_default_color
                ms.glcolor = (rgb[0], rgb[1], rgb[2], 0.4)
                # dist
                ms.glspace = scene.measureit_arch_hint_space
                # text
                ms.gltxt = scene.measureit_arch_gl_txt
                ms.glfont_size = scene.measureit_arch_font_size
                ms.glfont_align = scene.measureit_arch_font_align
                ms.glfont_rotat = scene.measureit_arch_font_rotation
                # Sum group
                ms.gltot = scene.measureit_arch_sum
                # Add index
                mp.measureit_arch_num += 1
                # redraw
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: Select at least one face for creating area measure. ")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}


# -------------------------------------------------------------
# Defines button that adds a measure segment to x/y/z origin
#
# -------------------------------------------------------------
class AddSegmentOrtoButton(Operator):
    bl_idname = "measureit_arch.addsegmentortobutton"
    bl_label = "Add"
    bl_description = "(EDITMODE only) Add a new measure segment from vertex to object origin for one " \
                     "axis (select 1 vertex)"
    bl_category = 'MeasureitArch'
    tag = IntProperty()

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "MESH":
                if bpy.context.mode == 'EDIT_MESH':
                    return True
                else:
                    return False
            else:
                return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # Add properties
            scene = context.scene
            mainobject = context.object
            mylist = get_smart_selected(mainobject)
            if len(mylist) < 1:  # if not selected linked vertex
                mylist = get_selected_vertex(mainobject)

            if len(mylist) >= 1:
                if 'MeasureGenerator' not in mainobject:
                    mainobject.MeasureGenerator.add()

                mp = mainobject.MeasureGenerator[0]
                for x in range(0, len(mylist)):
                    # -----------------------
                    # Only if not exist
                    # -----------------------
                    if exist_segment(mp, mylist[x], mylist[x], 12 + int(self.tag)) is False:
                        # Create all array elements
                        for cont in range(len(mp.measureit_arch_segments) - 1, mp.measureit_arch_num):
                            mp.measureit_arch_segments.add()

                        # Set values
                        ms = mp.measureit_arch_segments[mp.measureit_arch_num]
                        ms.gltype = 12 + int(self.tag)
                        ms.glpointa = mylist[x]
                        ms.glpointb = mylist[x]
                        ms.glarrow_a = scene.measureit_arch_glarrow_a
                        ms.glarrow_b = scene.measureit_arch_glarrow_b
                        ms.glarrow_s = scene.measureit_arch_glarrow_s
                        # color
                        ms.glcolor = scene.measureit_arch_default_color
                        # dist
                        ms.glspace = scene.measureit_arch_hint_space
                        # text
                        ms.gltxt = scene.measureit_arch_gl_txt
                        ms.glfont_size = scene.measureit_arch_font_size
                        ms.glfont_align = scene.measureit_arch_font_align
                        ms.glfont_rotat = scene.measureit_arch_font_rotation
                        # Sum group
                        ms.gltot = scene.measureit_arch_sum
                        # Add index
                        mp.measureit_arch_num += 1

                # redraw
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: Select at least one vertex for creating measure segment.")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}


# -------------------------------------------------------------
# Defines button that adds an angle measure
#
# -------------------------------------------------------------
class AddAngleButton(Operator):
    bl_idname = "measureit_arch.addanglebutton"
    bl_label = "Angle"
    bl_description = "(EDITMODE only) Add a new angle measure (select 3 vertices, 2nd is angle vertex)"
    bl_category = 'MeasureitArch'

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "MESH":
                if bpy.context.mode == 'EDIT_MESH':
                    return True
                else:
                    return False
            else:
                return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # Add properties
            scene = context.scene
            mainobject = context.object
            mylist = get_selected_vertex_history(mainobject)
            if len(mylist) == 3:
                if 'MeasureGenerator' not in mainobject:
                    mainobject.MeasureGenerator.add()

                mp = mainobject.MeasureGenerator[0]
                # -----------------------
                # Only if not exist
                # -----------------------
                if exist_segment(mp, mylist[0], mylist[1], 9, mylist[2]) is False:
                    # Create all array elements
                    for cont in range(len(mp.measureit_arch_segments) - 1, mp.measureit_arch_num):
                        mp.measureit_arch_segments.add()

                    # Set values
                    ms = mp.measureit_arch_segments[mp.measureit_arch_num]
                    ms.gltype = 9
                    ms.glpointa = mylist[0]
                    ms.glpointb = mylist[1]
                    ms.glpointc = mylist[2]
                    # color
                    ms.glcolor = scene.measureit_arch_default_color
                    # dist
                    ms.glspace = scene.measureit_arch_hint_space
                    # text
                    ms.gltxt = scene.measureit_arch_gl_txt
                    ms.glfont_size = scene.measureit_arch_font_size
                    ms.glfont_align = scene.measureit_arch_font_align
                    ms.glfont_rotat = scene.measureit_arch_font_rotation
                    # Add index
                    mp.measureit_arch_num += 1

                # redraw
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: Select three vertices for creating angle measure")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}


# -------------------------------------------------------------
# Defines button that adds an arc measure
#
# -------------------------------------------------------------
class AddArcButton(Operator):
    bl_idname = "measureit_arch.addarcbutton"
    bl_label = "Angle"
    bl_description = "(EDITMODE only) Add a new arc measure (select 3 vertices of the arc," \
                     " vertices 1st and 3rd are arc extremes)"
    bl_category = 'MeasureitArch'

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "MESH":
                if bpy.context.mode == 'EDIT_MESH':
                    return True
                else:
                    return False
            else:
                return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # Add properties
            scene = context.scene
            mainobject = context.object
            mylist = get_selected_vertex_history(mainobject)
            if len(mylist) == 3:
                if 'MeasureGenerator' not in mainobject:
                    mainobject.MeasureGenerator.add()

                mp = mainobject.MeasureGenerator[0]
                # -----------------------
                # Only if not exist
                # -----------------------
                if exist_segment(mp, mylist[0], mylist[1], 11, mylist[2]) is False:
                    # Create all array elements
                    for cont in range(len(mp.measureit_arch_segments) - 1, mp.measureit_arch_num):
                        mp.measureit_arch_segments.add()

                    # Set values
                    ms = mp.measureit_arch_segments[mp.measureit_arch_num]
                    ms.gltype = 11
                    ms.glpointa = mylist[0]
                    ms.glpointb = mylist[1]
                    ms.glpointc = mylist[2]
                    ms.glarrow_a = scene.measureit_arch_glarrow_a
                    ms.glarrow_b = scene.measureit_arch_glarrow_b
                    ms.glarrow_s = scene.measureit_arch_glarrow_s
                    # color
                    ms.glcolor = scene.measureit_arch_default_color
                    # dist
                    ms.glspace = scene.measureit_arch_hint_space
                    # text
                    ms.gltxt = scene.measureit_arch_gl_txt
                    ms.glfont_size = scene.measureit_arch_font_size
                    ms.glfont_align = scene.measureit_arch_font_align
                    ms.glfont_rotat = scene.measureit_arch_font_rotation
                    # Add index
                    mp.measureit_arch_num += 1

                # redraw
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: Select three vertices for creating arc measure")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}


# -------------------------------------------------------------
# Defines button that adds a label segment
#
# -------------------------------------------------------------
class AddLabelButton(Operator):
    bl_idname = "measureit_arch.addlabelbutton"
    bl_label = "Add"
    bl_description = "(EDITMODE only) Add a new measure label (select 1 vertex)"
    bl_category = 'MeasureitArch'

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "MESH":
                if bpy.context.mode == 'EDIT_MESH':
                    return True
                else:
                    return False
            else:
                return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # Add properties
            scene = context.scene
            mainobject = context.object
            mylist = get_selected_vertex(mainobject)
            if len(mylist) == 1:
                if 'MeasureGenerator' not in mainobject:
                    mainobject.MeasureGenerator.add()

                mp = mainobject.MeasureGenerator[0]
                # -----------------------
                # Only if not exist
                # -----------------------
                if exist_segment(mp, mylist[0], mylist[0], 2) is False:  # Both equal
                    # Create all array elements
                    for cont in range(len(mp.measureit_arch_segments) - 1, mp.measureit_arch_num):
                        mp.measureit_arch_segments.add()

                    # Set values
                    ms = mp.measureit_arch_segments[mp.measureit_arch_num]
                    ms.gltype = 2
                    ms.glpointa = mylist[0]
                    ms.glpointb = mylist[0]  # Equal
                    ms.glarrow_a = scene.measureit_arch_glarrow_a
                    ms.glarrow_b = scene.measureit_arch_glarrow_b
                    ms.glarrow_s = scene.measureit_arch_glarrow_s
                    # color
                    ms.glcolor = scene.measureit_arch_default_color
                    # dist
                    ms.glspace = scene.measureit_arch_hint_space
                    # text
                    ms.gltxt = scene.measureit_arch_gl_txt
                    ms.glfont_size = scene.measureit_arch_font_size
                    ms.glfont_align = scene.measureit_arch_font_align
                    ms.glfont_rotat = scene.measureit_arch_font_rotation
                    # Add index
                    mp.measureit_arch_num += 1

                # redraw
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: Select one vertex for creating measure label")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}


# -------------------------------------------------------------
# Defines button that adds a link
#
# -------------------------------------------------------------
class AddLinkButton(Operator):
    bl_idname = "measureit_arch.addlinkbutton"
    bl_label = "Add"
    bl_description = "(OBJECT mode only) Add a new measure between objects (select 2 " \
                     "objects and optionally 1 or 2 vertices)"
    bl_category = 'MeasureitArch'

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "MESH" or o.type == "EMPTY" or o.type == "CAMERA" or o.type == "LAMP":
                if bpy.context.mode == 'OBJECT':
                    return True
                else:
                    return False
            else:
                return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            scene = context.scene
            mainobject = context.object
            # -------------------------------
            # Verify number of objects
            # -------------------------------
            if len(context.selected_objects) != 2:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: Select two objects only, and optionally 1 vertex or 2 vertices "
                            "(one of each object)")
                return {'FINISHED'}
            # Locate other object
            linkobject = None
            for o in context.selected_objects:
                if o.name != mainobject.name:
                    linkobject = o.name
            # Verify destination vertex
            lkobj = bpy.data.objects[linkobject]
            mylinkvertex = get_selected_vertex(lkobj)
            if len(mylinkvertex) > 1:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: The destination object has more than one vertex selected. "
                            "Select only 1 or none")
                return {'FINISHED'}
            # Verify origin vertex
            myobjvertex = get_selected_vertex(mainobject)
            if len(mylinkvertex) > 1:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: The active object has more than one vertex selected. Select only 1 or none")
                return {'FINISHED'}

            # -------------------------------
            # Add properties
            # -------------------------------
            flag = False
            if 'MeasureGenerator' not in mainobject:
                mainobject.MeasureGenerator.add()

            mp = mainobject.MeasureGenerator[0]

            # if exist_segment(mp, mylist[0], mylist[0], 3) is False:
            #     flag = True
            # Create all array elements
            for cont in range(len(mp.measureit_arch_segments) - 1, mp.measureit_arch_num):
                mp.measureit_arch_segments.add()

            # Set values
            ms = mp.measureit_arch_segments[mp.measureit_arch_num]
            # -----------------------
            # Vertex to Vertex
            # -----------------------
            if len(myobjvertex) == 1 and len(mylinkvertex) == 1:
                ms.gltype = 3
                ms.glpointa = myobjvertex[0]
                ms.glpointb = mylinkvertex[0]
                flag = True
            # -----------------------
            # Vertex to Object
            # -----------------------
            if len(myobjvertex) == 1 and len(mylinkvertex) == 0:
                ms.gltype = 4
                ms.glpointa = myobjvertex[0]
                ms.glpointb = 0
                flag = True
            # -----------------------
            # Object to Vertex
            # -----------------------
            if len(myobjvertex) == 0 and len(mylinkvertex) == 1:
                ms.gltype = 5
                ms.glpointa = 0
                ms.glpointb = mylinkvertex[0]
                flag = True
            # -----------------------
            # Object to Object
            # -----------------------
            if len(myobjvertex) == 0 and len(mylinkvertex) == 0:
                ms.gltype = 8
                ms.glpointa = 0
                ms.glpointb = 0  # Equal
                flag = True

            # ------------------
            # only if created
            # ------------------
            if flag is True:
                ms.glarrow_a = scene.measureit_arch_glarrow_a
                ms.glarrow_b = scene.measureit_arch_glarrow_b
                ms.glarrow_s = scene.measureit_arch_glarrow_s
                # color
                ms.glcolor = scene.measureit_arch_default_color
                # dist
                ms.glspace = scene.measureit_arch_hint_space
                # text
                ms.gltxt = scene.measureit_arch_gl_txt
                ms.glfont_size = scene.measureit_arch_font_size
                ms.glfont_align = scene.measureit_arch_font_align
                ms.glfont_rotat = scene.measureit_arch_font_rotation
                # link
                ms.gllink = linkobject
                # Add index
                mp.measureit_arch_num += 1

                # -----------------------
                # Only if not exist
                # -----------------------
                # redraw
                context.area.tag_redraw()
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}


# -------------------------------------------------------------
# Defines button that adds an origin segment
#
# -------------------------------------------------------------
class AddOriginButton(Operator):
    bl_idname = "measureit_arch.addoriginbutton"
    bl_label = "Add"
    bl_description = "(OBJECT mode only) Add a new measure to origin (select object and optionally 1 vertex)"
    bl_category = 'MeasureitArch'

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "MESH" or o.type == "EMPTY" or o.type == "CAMERA" or o.type == "LAMP":
                if bpy.context.mode == 'OBJECT':
                    return True
                else:
                    return False
            else:
                return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # Add properties
            scene = context.scene
            mainobject = context.object
            mylist = get_selected_vertex(mainobject)
            if 'MeasureGenerator' not in mainobject:
                mainobject.MeasureGenerator.add()

            mp = mainobject.MeasureGenerator[0]
            # Create all array elements
            for cont in range(len(mp.measureit_arch_segments) - 1, mp.measureit_arch_num):
                mp.measureit_arch_segments.add()

            # -----------------------
            # Set values
            # -----------------------
            ms = mp.measureit_arch_segments[mp.measureit_arch_num]
            flag = False
            if len(mylist) > 0:
                if len(mylist) == 1:
                    if exist_segment(mp, mylist[0], mylist[0], 6) is False:  # Both equal
                        flag = True
                        # Vertex to origin
                        ms.gltype = 6
                        ms.glpointa = mylist[0]
                        ms.glpointb = mylist[0]
                else:
                    self.report({'ERROR'},
                                "MeasureIt-ARCH: Enter in EDITMODE and select one vertex only for creating "
                                "measure from vertex to origin")
                    return {'FINISHED'}
            else:
                # Object to origin
                if exist_segment(mp, 0, 0, 7) is False:  # Both equal
                    flag = True
                    ms.gltype = 7
                    ms.glpointa = 0
                    ms.glpointb = 0
            # ------------------
            # only if created
            # ------------------
            if flag is True:
                ms.glarrow_a = scene.measureit_arch_glarrow_a
                ms.glarrow_b = scene.measureit_arch_glarrow_b
                ms.glarrow_s = scene.measureit_arch_glarrow_s
                # color
                ms.glcolor = scene.measureit_arch_default_color
                # dist
                ms.glspace = scene.measureit_arch_hint_space
                # text
                ms.gltxt = scene.measureit_arch_gl_txt
                ms.glfont_size = scene.measureit_arch_font_size
                ms.glfont_align = scene.measureit_arch_font_align
                ms.glfont_rotat = scene.measureit_arch_font_rotation
                # Add index
                mp.measureit_arch_num += 1

            # redraw
            context.area.tag_redraw()

            return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}


# -------------------------------------------------------------
# Defines button that deletes a measure segment
#
# -------------------------------------------------------------
class DeleteSegmentButton(Operator):
    bl_idname = "measureit_arch.deletesegmentbutton"
    bl_label = "Delete"
    bl_description = "Delete a measure"
    bl_category = 'MeasureitArch'
    tag= IntProperty()

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):

        # Add properties
        mainobject = context.object
        mp = mainobject.MeasureGenerator[0]
        ms = mp.measureit_arch_segments[self.tag]
        ms.glfree = True
        # Delete element
        mp.measureit_arch_segments.remove(self.tag)
        mp.measureit_arch_num -= 1
        # redraw
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
                    context.area.tag_redraw()
                    return {'FINISHED'}
                
        return {'FINISHED'}



# -------------------------------------------------------------
# Defines button that deletes all measure segments
#
# -------------------------------------------------------------
class DeleteAllSegmentButton(Operator):
    bl_idname = "measureit_arch.deleteallsegmentbutton"
    bl_label = "Delete All Segments?"
    bl_description = "Delete all measures (it cannot be undone)"
    bl_category = 'MeasureitArch'

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        # Add properties
        mainobject = context.object
        mp = mainobject.MeasureGenerator[0]

        while len(mp.measureit_arch_segments) > 0:
            mp.measureit_arch_segments.remove(0)

        # reset size
        mp.measureit_arch_num = len(mp.measureit_arch_segments)
        # redraw

        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
                    context.area.tag_redraw()
                    return {'FINISHED'} 
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


# -------------------------------------------------------------
# Defines button that deletes all measure segment sums
#
# -------------------------------------------------------------
class DeleteAllSumButton(Operator):
    bl_idname = "measureit_arch.deleteallsumbutton"
    bl_label = "Delete"
    bl_description = "Delete all sum groups"
    bl_category = 'MeasureitArch'
    tag= IntProperty()

    # ------------------------------
    # Execute button action
    # ------------------------------
    # noinspection PyMethodMayBeStatic
    def execute(self, context):
        if context.object is not None:
            if 'MeasureGenerator' in context.object:
                mp = context.object.MeasureGenerator[0]
                for idx in range(0, mp.measureit_arch_num):
                    ms = mp.measureit_arch_segments[idx]
                    ms.gltot = '99'

            return {'FINISHED'}


# -------------------------------------------------------------
# Defines button that expands all measure segments
#
# -------------------------------------------------------------
class ExpandAllSegmentButton(Operator):
    bl_idname = "measureit_arch.expandallsegmentbutton"
    bl_label = "Expand"
    bl_description = "Expand all measure properties"
    bl_category = 'MeasureitArch'
    tag= IntProperty()

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        # Add properties
        mainobject = context.object
        mp = mainobject.MeasureGenerator[0]

        for i in mp.measureit_arch_segments:
            i.gladvance = True

        return {'FINISHED'}
    
# -------------------------------------------------------------
# Defines button that collapses all measure segments
#
# -------------------------------------------------------------
class CollapseAllSegmentButton(Operator):
    bl_idname = "measureit_arch.collapseallsegmentbutton"
    bl_label = "Collapse"
    bl_description = "Collapses all measure properties"
    bl_category = 'MeasureitArch'
    tag= IntProperty()

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        # Add properties
        mainobject = context.object
        mp = mainobject.MeasureGenerator[0]

        for i in mp.measureit_arch_segments:
            i.gladvance = False

        return {'FINISHED'}
    

# -------------------------------------------------------------
# Defines a new note
#
# -------------------------------------------------------------
class AddNoteButton(Operator):
    bl_idname = "measureit_arch.addnotebutton"
    bl_label = "Note"
    bl_description = "(OBJECT mode only) Add a new annotation"
    bl_category = 'MeasureitArch'
    tag= IntProperty()

    # ------------------------------
    # Poll
    # ------------------------------
    # noinspection PyUnusedLocal
    @classmethod
    def poll(cls, context):
        if bpy.context.mode == 'OBJECT':
            return True
        else:
            return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            bpy.ops.object.empty_add(type='PLAIN_AXES')
            myempty = bpy.data.objects[bpy.context.active_object.name]
            myempty.location = bpy.context.scene.cursor_location
            myempty.empty_display_size = 0.01
            myempty.name = "Annotation"
            # Add properties
            scene = context.scene
            mainobject = myempty
            if 'MeasureGenerator' not in mainobject:
                mainobject.MeasureGenerator.add()

            mp = mainobject.MeasureGenerator[0]
            # Create all array elements
            for cont in range(len(mp.measureit_arch_segments) - 1, mp.measureit_arch_num):
                mp.measureit_arch_segments.add()

            # Set values
            ms = mp.measureit_arch_segments[mp.measureit_arch_num]
            ms.gltype = 10
            ms.glpointa = 0
            ms.glpointb = 0  # Equal
            # color
            ms.glcolor = scene.measureit_arch_default_color
            # dist
            ms.glspace = scene.measureit_arch_hint_space
            # text
            ms.gltxt = scene.measureit_arch_gl_txt
            ms.glfont_size = scene.measureit_arch_font_size
            ms.glfont_align = scene.measureit_arch_font_align
            ms.glfont_rotat = scene.measureit_arch_font_rotation
            # Add index
            mp.measureit_arch_num += 1

            # redraw
            context.area.tag_redraw()
            return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}


# -------------------------------------------------------------
# Defines button that enables/disables the tip display
#
# -------------------------------------------------------------
class RunHintDisplayButton(Operator):
    bl_idname = "measureit_arch.runopenglbutton"
    bl_label = "Display hint data manager"
    bl_description = "Main control for enabling or disabling the display of measurements in the viewport"
    bl_category = 'MeasureitArch'

    _handle = None  # keep function handler
    _handle3d = None
    # ----------------------------------
    # Enable gl drawing adding handler
    # ----------------------------------
    @staticmethod
    def handle_add(self, context):
        if RunHintDisplayButton._handle is None:
            RunHintDisplayButton._handle = SpaceView3D.draw_handler_add(draw_callback_px, (self, context),
                                                                        'WINDOW',
                                                                        'POST_PIXEL')
            RunHintDisplayButton._handle3d = SpaceView3D.draw_handler_add(draw_callback_3d, (self,context), 'WINDOW', 'POST_VIEW')
            context.window_manager.measureit_arch_run_opengl = True

    # ------------------------------------
    # Disable gl drawing removing handler
    # ------------------------------------
    # noinspection PyUnusedLocal
    @staticmethod
    def handle_remove(self, context):
        if RunHintDisplayButton._handle is not None:
            SpaceView3D.draw_handler_remove(RunHintDisplayButton._handle, 'WINDOW')
            SpaceView3D.draw_handler_remove(RunHintDisplayButton._handle3d, 'WINDOW')
        RunHintDisplayButton._handle = None
        context.window_manager.measureit_arch_run_opengl = False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            if context.window_manager.measureit_arch_run_opengl is False:
                self.handle_add(self, context)
                context.area.tag_redraw()
            else:
                self.handle_remove(self, context)
                context.area.tag_redraw()

            return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}


class AddLineButton(Operator):
    bl_idname = "measureit_arch.addlinebutton"
    bl_label = "Add"
    bl_description = "(EDITMODE only) Add a new measure segment between 2 vertices (select 2 vertices or more)"
    bl_category = 'MeasureitArch'

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "MESH":
                if bpy.context.mode == 'EDIT_MESH':
                    return True
                else:
                    return False
            else:
                return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # Add properties
            scene = context.scene
            mainobject = context.object
            mylist = get_smart_selected(mainobject)
            if len(mylist) < 2:  # if not selected linked vertex
                mylist = get_selected_vertex(mainobject)

            if len(mylist) >= 2:
                if 'LineGenerator' not in mainobject:
                    mainobject.LineGenerator.add()

                lineGen = mainobject.LineGenerator[0]
                lGroup = lineGen.line_groups.add()

                # Set values
                lGroup.lineStyle = scene.measureit_arch_default_style
                lGroup.lineWidth = 2     
                lGroup.lineColor = scene.measureit_arch_default_color
                
                for x in range (0, len(mylist)-1, 2):
                    sLine = lGroup.singleLine.add()
                    sLine.pointA = mylist[x]
                    sLine.pointB = mylist[x+1]
                    lGroup.numLines +=1

                lineGen.line_num += 1


                # redraw
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: Select at least two vertices for creating measure segment.")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}


# -------------------------------------------------------------
# Handle all draw routines (OpenGL main entry point)
#
# -------------------------------------------------------------
def draw_main(context):
    region = bpy.context.region
    # Detect if Quadview to get drawing area
    if not context.space_data.region_quadviews:
        rv3d = bpy.context.space_data.region_3d
    else:
        # verify area
        if context.area.type != 'VIEW_3D' or context.space_data.type != 'VIEW_3D':
            return
        i = -1
        for region in context.area.regions:
            if region.type == 'WINDOW':
                i += 1
                if context.region.id == region.id:
                    break
        else:
            return

        rv3d = context.space_data.region_quadviews[i]

    scene = bpy.context.scene

    # Get visible collections
    viewLayer = bpy.context.view_layer

    visibleCollections = []

    for collection in viewLayer.layer_collection.children:
       if collection.exclude == False:
            visibleCollections.extend([collection])

    # Display selected or all
    if scene.measureit_arch_gl_ghost is False:
        objlist = context.selected_objects
    else:
        objlist = context.view_layer.objects

    # Enable GL drawing
    bgl.glEnable(bgl.GL_BLEND)
    # ---------------------------------------
    # Generate all OpenGL calls for measures
    # ---------------------------------------
    for myobj in objlist:
        if myobj.hide_viewport is False:
            if 'MeasureGenerator' in myobj:
                
                # verify visible layer
                for collection in visibleCollections:
                    objCollections = []
                    objCollections = myobj.users_collection
                    if objCollections[0].name == collection.collection.name:
                        op = myobj.MeasureGenerator[0]

                        draw_segments(context, myobj, op, region, rv3d)
                        break
                
    # ---------------------------------------
    # Generate all OpenGL calls for debug
    # ---------------------------------------
    if scene.measureit_arch_debug is True:
        selobj = bpy.context.selected_objects
        for myobj in selobj:
            if scene.measureit_arch_debug_objects is True:
                draw_object(context, myobj, region, rv3d)
            elif scene.measureit_arch_debug_object_loc is True:
                draw_object(context, myobj, region, rv3d)
            if scene.measureit_arch_debug_vertices is True:
                draw_vertices(context, myobj, region, rv3d)
            elif scene.measureit_arch_debug_vert_loc is True:
                draw_vertices(context, myobj, region, rv3d)
            if scene.measureit_arch_debug_edges is True:
                draw_edges(context, myobj, region, rv3d)
            if scene.measureit_arch_debug_faces is True or scene.measureit_arch_debug_normals is True:
                draw_faces(context, myobj, region, rv3d)

    # -----------------------
    # restore opengl defaults
    # -----------------------
    #bgl.glLineWidth(1)
    #bgl.glDisable(bgl.GL_BLEND)
    #bgl.glColor4f(0.0, 0.0, 0.0, 1.0)

# -------------------------------------------------------------
# Handler for drawing OpenGl
# -------------------------------------------------------------
# noinspection PyUnusedLocal
def draw_callback_px(self, context):
    draw_main(context)

def draw_callback_3d(self, context):
    draw_main_3d(context)


# -------------------------------------------------------------
# Check if the segment already exist
#
# -------------------------------------------------------------
def exist_segment(mp, pointa, pointb, typ=1, pointc=None):
    #  for ms in mp.measureit_arch_segments[mp.measureit_arch_num]
    for ms in mp.measureit_arch_segments:
        if ms.gltype == typ and ms.glfree is False:
            if typ != 9:
                if ms.glpointa == pointa and ms.glpointb == pointb:
                    return True
                if ms.glpointa == pointb and ms.glpointb == pointa:
                    return True
            else:
                if ms.glpointa == pointa and ms.glpointb == pointb and ms.glpointc == pointc:
                    return True

    return False


# -------------------------------------------------------------
# Get vertex selected
# -------------------------------------------------------------
def get_selected_vertex(myobject):
    mylist = []
    # if not mesh, no vertex
    if myobject.type != "MESH":
        return mylist
    # --------------------
    # meshes
    # --------------------
    oldobj = bpy.context.object
    bpy.context.view_layer.objects.active = myobject
    flag = False
    if myobject.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
        flag = True

    bm = from_edit_mesh(myobject.data)
    tv = len(bm.verts)
    for v in bm.verts:
        if v.select:
            mylist.extend([v.index])

    if flag is True:
        bpy.ops.object.editmode_toggle()
    # Back context object
    bpy.context.view_layer.objects.active = oldobj

    # if select all vertices, then use origin
    if tv == len(mylist):
        return []

    return mylist


# -------------------------------------------------------------
# Get vertex selected
# -------------------------------------------------------------
def get_selected_vertex_history(myobject):
    mylist = []
    # if not mesh, no vertex
    if myobject.type != "MESH":
        return mylist
    # --------------------
    # meshes
    # --------------------
    oldobj = bpy.context.object
    bpy.context.view_layer.objects.active = myobject
    flag = False
    if myobject.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
        flag = True

    bm = from_edit_mesh(myobject.data)
    for v in bm.select_history:
        mylist.extend([v.index])

    if flag is True:
        bpy.ops.object.editmode_toggle()
    # Back context object
    bpy.context.view_layer.objects.active = oldobj

    return mylist


# -------------------------------------------------------------
# Get vertex selected segments
# -------------------------------------------------------------
def get_smart_selected(myobject):
    mylist = []
    # if not mesh, no vertex
    if myobject.type != "MESH":
        return mylist
    # --------------------
    # meshes
    # --------------------
    oldobj = bpy.context.object
    bpy.context.view_layer.objects.active = myobject
    flag = False
    if myobject.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
        flag = True

    bm = from_edit_mesh(myobject.data)
    for e in bm.edges:
        if e.select is True:
            mylist.extend([e.verts[0].index])
            mylist.extend([e.verts[1].index])

    if flag is True:
        bpy.ops.object.editmode_toggle()
    # Back context object
    bpy.context.view_layer.objects.active = oldobj

    return mylist


# -------------------------------------------------------------
# Get vertex selected faces
# -------------------------------------------------------------
def get_selected_faces(myobject):
    mylist = []
    # if not mesh, no vertex
    if myobject.type != "MESH":
        return mylist
    # --------------------
    # meshes
    # --------------------
    oldobj = bpy.context.object
    bpy.context.view_layer.objects.active = myobject
    flag = False
    if myobject.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
        flag = True

    bm = from_edit_mesh(myobject.data)
    for e in bm.faces:
        myface = []
        if e.select is True:
            for i in range(0, len(e.verts)):
                myface.extend([e.verts[i].index])

            mylist.extend([myface])

    if flag is True:
        bpy.ops.object.editmode_toggle()
    # Back context object
    bpy.context.view_layer.objects.active = oldobj

    return mylist

def draw_main_3d (context):

    scene = context.scene

    # Display selected or all
    if scene.measureit_arch_gl_ghost is False:
        objlist = context.selected_objects
    else:
        objlist = context.view_layer.objects

    # Enable GL drawing
    bgl.glEnable(bgl.GL_BLEND)
    # ---------------------------------------
    # Generate all OpenGL calls for measures
    # ---------------------------------------
    for myobj in objlist:
        if myobj.hide_viewport is False:              
            if 'LineGenerator' in myobj:
                lineGen = myobj.LineGenerator[0]
                draw_line_group(context,myobj,lineGen)
