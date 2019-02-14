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


# ----------------------------------------------------------
# File: measureit_arch_dimensions.py
# Main panel for different MeasureitArch general actions
# Author: Antonio Vazquez (antonioya), Kevan Cress
#
# ----------------------------------------------------------
import bpy
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, BoolProperty, StringProperty, \
                      FloatProperty, EnumProperty, PointerProperty
from .measureit_arch_main import *
from .measureit_arch_baseclass import BaseWithText

# ------------------------------------------------------------------
# Define property group class for measureit_arch faces index
# ------------------------------------------------------------------
class MeasureitArchIndex(PropertyGroup):
    glidx = IntProperty(name="index",
                        description="vertex index")

bpy.utils.register_class(MeasureitArchIndex)

# ------------------------------------------------------------------
# Define property group class for measureit_arch faces
# ------------------------------------------------------------------
class MeasureitArchFaces(PropertyGroup):
    glface = IntProperty(name="glface",
                         description="Face number")
    # Array of index
    measureit_arch_index: CollectionProperty(type=MeasureitArchIndex)

bpy.utils.register_class(MeasureitArchFaces)

class LinearDimensionProperties(BaseWithText,PropertyGroup):
    dimPointA: IntProperty(name='dimPointA',
                    description="Dimension Start Vertex Index")

    dimPointB: IntProperty(name='dimPointB',
                    description="Dimension End Vertex Index")

    dimOffset: FloatProperty(name='Dimension Offset',
                    description='Offset for Dimension',
                    default= (0.1))
    
    dimVisibleInView: PointerProperty(type= bpy.types.Camera)

    dimFlip: BoolProperty(name='Flip Dimension',
                    description= 'Flip The Dimension Normal',
                    default=False)

    dimViewPlane: EnumProperty(
                    items=(('99', "None", "None",'EMPTY_AXIS',0),
                           ('XY', "XY Plane", "Optimize Dimension for XY Plane (Plan)",'AXIS_TOP',1),
                           ('YZ', "YZ Plane", "Optimize Dimension for YZ Plane (Elevation)",'AXIS_FRONT',2),
                           ('XZ', "XZ Plane", "Optimize Dimension for XZ Plane (Elevation)",'AXIS_SIDE',3)),
                    name="B end",
                    description="Add arrows to point A")   

    dimEndcapA: EnumProperty(
                    items=(('99', "--", "No arrow"),
                           ('1', "Line", "The point of the arrow are lines"),
                           ('2', "Triangle", "The point of the arrow is triangle"),
                           ('3', "TShape", "The point of the arrow is a T")),
                    name="A end",
                    description="Add arrows to point A")
    
    dimEndcapB: EnumProperty(
                    items=(('99', "--", "No arrow"),
                           ('1', "Line", "The point of the arrow are lines"),
                           ('2', "Triangle", "The point of the arrow is triangle"),
                           ('3', "TShape", "The point of the arrow is a T")),
                    name="B end",
                    description="Add arrows to point A")                    

    dimEndcapSize: IntProperty(name="dimEndcapSize",
                    description="Arrow size",
                    default=15, min=6, max=500)

    dimRotation:FloatProperty(name='annotationOffset',
                            description='Rotation for Annotation',
                            default= 0.0,
                            subtype='ANGLE')

bpy.utils.register_class(LinearDimensionProperties)

# ------------------------------------------------------------------
# LEGACY Define property group class for measureit_arch data
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
    linearDimensions = CollectionProperty(type=LinearDimensionProperties)

bpy.utils.register_class(MeasureContainer)
Object.MeasureGenerator = CollectionProperty(type=MeasureContainer)

class MeasureitArchDimensionsPanel(Panel):
    bl_idname = "obj_dimensions"
    bl_label = "Dimensions"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    
    @classmethod
    def poll(cls, context):
        if 'MeasureGenerator' in bpy.context.object:
            return True
        else:
            return False

    
    def draw(self, context):
         scene = context.scene
         if context.object is not None:
            if 'MeasureGenerator' in context.object:
                layout = self.layout
                layout.use_property_split = True
                layout.use_property_decorate = False
                # -----------------
                # loop
                # -----------------
                
                measureGen = context.object.MeasureGenerator[0]
                row = layout.row(align = True)
                exp = row.operator("measureit_arch.expandcollapseallpropbutton", text="Expand All", icon="ADD")
                exp.state = True
                exp.is_style = False
                exp.item_type = 'D'

                clp = row.operator("measureit_arch.expandcollapseallpropbutton", text="Collapse All", icon="REMOVE")
                clp.state = False
                clp.is_style = False
                exp.item_type = 'D'
                
                idx = 0
                for seg in measureGen.measureit_arch_segments:
                    if seg.glfree is False:
                        add_item(layout, idx, seg)
                    idx += 1
                
                idx = 0
                for linDim in measureGen.linearDimensions:
                    add_linearDimension_item(layout,idx, linDim)
                    idx += 1

                col = layout.column()
                delOp = col.operator("measureit_arch.deleteallitemsbutton", text="Delete All Dimensions", icon="X")
                delOp.is_style = False
                delOp.item_type = linDim.itemType
                
def add_item(layout, idx, segment):
    scene = bpy.context.scene
    if segment.gladvance is True:
        box = layout.box()
        row = box.row(align=True)
    else:
        row = layout.row(align=True)


    if segment.glview is True:
        icon = "VISIBLE_IPO_ON"
    else:
        icon = "VISIBLE_IPO_OFF"

    row.prop(segment, 'glview', text="", toggle=True, icon=icon)
    row.prop(segment, 'gladvance', text="", toggle=True, icon="PREFERENCES")
    row.prop(segment, 'style', text="")
    row.prop(segment, 'gltxt', text="")
    op = row.operator("measureit_arch.deletesegmentbutton", text="", icon="X")
    # send index and type to operator
    op.tag = idx  
    op.itemType = 'segment'

    if segment.gladvance is True:

        col = box.column()

        if segment.gltype == 20:  # Area special
            
            col.prop(segment, 'glcolorarea', text="Area Color")
            col.prop(segment, 'glcolor', text="Color")
        else:
            col.prop(segment, 'glcolor', text="Color")

        if segment.gltype != 9 and segment.gltype != 10 and segment.gltype != 20:
            col.prop(segment, 'gldefault', text="Automatic position")

            col = box.column(align=True)

            col.prop(segment, 'glspace', text="Distance")
            col.prop(segment, 'glwidth', text="Lineweight")
            if segment.gldefault is False:
                col.prop(segment, 'glnormalx', text="X")
                col.prop(segment, 'glnormaly', text="Y")
                col.prop(segment, 'glnormalz', text="Z")
            
            

        col = box.column(align=True)

        col.prop(segment, 'glfont_size', text="Font Size")
        col.prop(segment, 'glfont_rotat', text="Rotate")
        col.prop(segment, 'glfontx', text="X")
        col.prop(segment, 'glfonty', text="Y")
        col.prop(segment, 'glfont_align', text="Align")

        # Arrows
        if segment.gltype != 9 and segment.gltype != 10 and segment.gltype != 20:
            col = box.column(align=True)

            col.prop(segment, 'glarrow_a', text="Arrow Start ")
            col.prop(segment, 'glarrow_b', text="End ")
            if segment.glarrow_a != '99' or segment.glarrow_b != '99':
                col.prop(segment, 'glarrow_s', text="Size")

        if segment.gltype != 2 and segment.gltype != 10:
            col = box.column(align=True)
            if scene.measureit_arch_gl_show_d is True and segment.gltype != 9 and segment.gltype != 21:
                if segment.gldist is True:
                    icon = "VISIBLE_IPO_ON"
                else:
                    icon = "VISIBLE_IPO_OFF"
                col.prop(segment, 'gldist', text="Distance", toggle=True, icon=icon)
            if scene.measureit_arch_gl_show_n is True:
                if segment.glnames is True:
                    icon = "VISIBLE_IPO_ON"
                else:
                    icon = "VISIBLE_IPO_OFF"
                col.prop(segment, 'glnames', text="Text", toggle=True, icon=icon)
            # sum distances

            col = box.column(align=True)

            if segment.gltype == 1 or segment.gltype == 12 or segment.gltype == 13 or segment.gltype == 14:
                col.prop(segment, 'gltot', text="Sum")

        

        # Loc axis
        if segment.gltype != 2 and segment.gltype != 9 and segment.gltype != 10 \
                and segment.gltype != 11 and segment.gltype != 12 and segment.gltype != 13 \
                and segment.gltype != 14 and segment.gltype != 20:
            row = box.row(align = True)
            row.use_property_split = False
            row.prop(segment, 'glocx', text="X", toggle=True)
            row.prop(segment, 'glocy', text="Y", toggle=True)
            row.prop(segment, 'glocz', text="Z", toggle=True)
            if segment.glocx is False or segment.glocy is False or segment.glocz is False:
                row = box.row()
                if segment.gltype == 1:
                    row.prop(segment, 'glorto', text="Orthogonal")
                row.prop(segment, 'glocwarning', text="Warning")
                # ortogonal (only segments)
                if segment.gltype == 1:
                    if segment.glorto != "99":
                        row = box.row(align=True)
                        row.prop(segment, 'glorto_x', text="X", toggle=True)
                        row.prop(segment, 'glorto_y', text="Y", toggle=True)
                        row.prop(segment, 'glorto_z', text="Z", toggle=True)

        # Arc special
        if segment.gltype == 11:
            row = box.row(align = True)
            row.prop(segment, 'glarc_rad', text="Radius")
            row.prop(segment, 'glarc_len', text="Length")
            row.prop(segment, 'glarc_ang', text="Angle")

            row = box.row(align = True)
            row.prop(segment, 'glarc_txradio', text="")
            row.prop(segment, 'glarc_txlen', text="")
            row.prop(segment, 'glarc_txang', text="")
            row = box.row(align = True)
            row.prop(segment, 'glarc_full', text="Full Circle")
            if segment.glarc_rad is True:
                row.prop(segment, 'glarc_extrad', text="Adapt radio")

            row = box.row(align = True)
            row.prop(segment, 'glarc_a', text="")
            row.prop(segment, 'glarc_b', text="")
            if segment.glarc_a != '99' or segment.glarc_b != '99':
                row.prop(segment, 'glarc_s', text="Size")

def add_linearDimension_item(layout, idx, linDim):
    scene = bpy.context.scene
    linDim=linDim
    hasGen = False
    if 'StyleGenerator' in scene:
        StyleGen = scene.StyleGenerator[0]
        hasGen = True

    if linDim.settings is True:
        box = layout.box()
        row = box.row(align=True)
    else:
        row = layout.row(align=True)

    useStyleIcon = 'UNLINKED'
    if linDim.uses_style is True:
        useStyleIcon = 'LINKED'

    row.prop(linDim, 'visible', text="", toggle=True, icon='DRIVER_DISTANCE')
    
    if hasGen and not linDim.is_style:
        row.prop(linDim, 'uses_style', text="",toggle=True, icon=useStyleIcon)

    row.prop(linDim, 'settings', text="", toggle=True, icon="PREFERENCES")
    
    if linDim.is_style is False: row.prop(linDim, 'dimFlip',text='',toggle=True, icon='UV_SYNC_SELECT')
    if linDim.uses_style:
        row.prop_search(linDim,'style', StyleGen,'linearDimensions',text="", icon='COLOR')
    else:
        row.prop(linDim,'color',text='')
        row.prop(linDim, 'name', text="")
    
    op = row.operator("measureit_arch.deletepropbutton", text="", icon="X")
    # send index and type to operator
    op.tag = idx
    op.item_type = linDim.itemType
    op.is_style = linDim.is_style

    # advanced Settings
    if linDim.settings is True:
        col = box.column(align=True)
        if linDim.uses_style is False:
            col.template_ID(linDim, "font", open="font.open", unlink="font.unlink")

            col = box.column(align=True)
            col.prop(linDim,'dimViewPlane', text='View Plane')
            col.prop_search(linDim,'dimVisibleInView', bpy.data, 'cameras',text='Visible In View')
            
            col = box.column(align=True)
            col.prop(linDim,'lineWeight',text='Line Weight')
        
        if linDim.is_style is False:
            col.prop(linDim,'dimOffset',text='Offset')
            col.prop(linDim, 'dimRotation', text='Rotation')
        
        col = box.column(align=True)   
        if linDim.uses_style is False:
            col = box.column(align=True)
            col.prop(linDim,'fontSize',text='Font Size')
            col.prop(linDim,'textResolution',text='Resolution')
            col.prop(linDim,'textAlignment',text='Alignment')
            col.prop(linDim,'textPosition',text='Position')
        
        if linDim.is_style is False:
            col.prop(linDim,'textFlippedX',text='Flip Text X')
            col.prop(linDim,'textFlippedY',text='Flip Text Y')


        if linDim.uses_style is False:
            col = box.column(align=True)
            col.prop(linDim,'dimEndcapA', text='Arrow Start')
            col.prop(linDim,'dimEndcapB', text='End')
            col.prop(linDim,'dimEndcapSize', text='Arrow Size')
# -------------------------------------------------------------
# Defines button that adds a measure segment
#
# -------------------------------------------------------------
class AddDimensionButton(Operator):
    bl_idname = "measureit_arch.adddimensionbutton"
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
            # get selected

            scene = context.scene
            mainobject = context.object
            mylist = get_smart_selected(mainobject)
            
            if len(mylist) < 2:  # if not selected linked vertex
                mylist = get_selected_vertex(mainobject)

            if len(mylist) >= 2:
                #Check Generators
                if 'MeasureGenerator' not in mainobject:
                    mainobject.MeasureGenerator.add()
                if 'StyleGenerator' not in scene:
                    scene.StyleGenerator.add()

                measureGen = mainobject.MeasureGenerator[0]

                for x in range(0, len(mylist) - 1, 2):
                    if exist_segment(measureGen, mylist[x], mylist[x + 1]) is False:
                        newDimension = measureGen.linearDimensions.add()
                        newDimension.itemType = 'D'
                        
                        # Set values

                        tex_buffer = bgl.Buffer(bgl.GL_INT, 1)
                        bgl.glGenTextures(1, tex_buffer)
                        newDimension['tex_buffer'] = tex_buffer.to_list()

                        newDimension.uses_style = scene.measureit_arch_set_dimension_use_style
                        if newDimension.uses_style: newDimension.style = scene.measureit_arch_default_dimension_style
                        newDimension.dimVisibleInView = scene.camera.data
                        newDimension.dimViewPlane = scene.viewPlane
                        newDimension.dimPointB = mylist[x]
                        newDimension.dimPointA = mylist[x + 1]
                        newDimension.dimEndcapA= scene.measureit_arch_glarrow_a
                        newDimension.dimEndcapB = scene.measureit_arch_glarrow_b
                        newDimension.dimEndcapSize= scene.measureit_arch_glarrow_s
                        # color
                        newDimension.color = scene.measureit_arch_default_color
                        # dist
                        newDimension.dimOffset = 0.2
                        # text
                        newDimension.text = scene.measureit_arch_gl_txt
                        newDimension.fontSize = 7
                        newDimension.textResolution = 72
                        newDimension.textAlignment = 'C'
                        # Sum group
                        measureGen.measureit_arch_num += 1

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
# Defines a new note
#
# -------------------------------------------------------------
class AddNoteButton(Operator):
    bl_idname = "measureit_arch.addnotebutton"
    bl_label = "Note"
    bl_description = "(OBJECT mode only) Add a new note"
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

