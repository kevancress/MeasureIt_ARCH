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
from .measureit_arch_geometry import draw_annotation, draw_alignedDimension, draw_line_group, update_text, draw_vertices, draw_object, draw_edges


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
    ShowHideViewportButton.handle_remove(None, bpy.context)


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
            if 'DimensionGenerator' in myobj:
                mp = myobj.DimensionGenerator[0]
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
# Define UI class
# show/Hide Dimensions
# ------------------------------------------------------------------
class MeasureitArchShowHidePanel(Panel):
    bl_idname = "measureit_arch.showhidepanel"
    bl_label = "Show/Hide MeasureIt"
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
    bl_label = "Add Drawing Element"
    bl_space_type = 'VIEW_3D'
    bl_region_type = "UI"
    bl_category = 'MeasureIt-ARCH'

    # ------------------------------
    # Draw UI
    # ------------------------------
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        hasGen = False
        if 'StyleGenerator' in scene:
            StyleGen = scene.StyleGenerator[0]
            hasGen = True
        # ------------------------------
        # Tool Buttons
        # ------------------------------

        # Tools
        box = layout.box()
        box.label(text="Add Dimensions")

        col = box.column(align=True)
        col.operator("measureit_arch.addaligneddimensionbutton", text="Aligned", icon="DRIVER_DISTANCE")
        col.operator("measureit_arch.addanglebutton", text="Angle", icon="LINCURVE")
        #col.operator("measureit_arch.addarcbutton", text="Arc", icon="DRIVER_ROTATIONAL_DIFFERENCE")
        col.operator("measureit_arch.addlinkbutton", text="Link", icon="PIVOT_MEDIAN")
        #col = box.column()
        #col.operator("measureit_arch.addareabutton", text="Area", icon="MESH_GRID")

        col = box.column(align=True)
        col.prop_search(scene,'measureit_arch_default_dimension_style', StyleGen,'alignedDimensions',text="", icon='COLOR')
        col.prop(scene,'viewPlane',text='')


        # ------------------------------
        # Linework Tools
        # ------------------------------
    
        box = layout.box()
        box.label(text="Add Lines")

        col = box.column(align=True)
        col.operator("measureit_arch.addlinebutton", text="Line", icon="MESH_CUBE")
        op = col.operator("measureit_arch.addlinebyproperty", text="Line by Prop", icon="MESH_CUBE")
        op.calledFromGroup = False

        col = box.column(align=True)
        col.prop_search(scene,'measureit_arch_default_line_style', StyleGen,'line_groups',text="", icon='COLOR')

        # ------------------------------
        # Annotation Tools
        # ------------------------------
        box = layout.box()
        box.label(text="Add Annotations")
        
        col = box.column(align=True)
        col.operator("measureit_arch.addnotebutton", text="Note", icon="EMPTY_DATA")
        col.operator("measureit_arch.addannotationbutton", text="Annotation", icon="FONT_DATA")

        col = box.column(align=True)
        col.prop_search(scene,'measureit_arch_default_annotation_style', StyleGen,'annotations',text="", icon='COLOR')
        # ------------------------------
        # Debug data
        # ------------------------------
        debug = False
        if debug:
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



# -------------------------------------------------------------
# Defines button that enables/disables Viewport Display
#
# -------------------------------------------------------------
class ShowHideViewportButton(Operator):
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
        if ShowHideViewportButton._handle is None:
            ShowHideViewportButton._handle = SpaceView3D.draw_handler_add(draw_callback_px, (self, context),
                                                                        'WINDOW',
                                                                        'POST_PIXEL')
            ShowHideViewportButton._handle3d = SpaceView3D.draw_handler_add(draw_callback_3d, (self,context), 'WINDOW', 'POST_VIEW')
            context.window_manager.measureit_arch_run_opengl = True

    # ------------------------------------
    # Disable gl drawing removing handler
    # ------------------------------------
    # noinspection PyUnusedLocal
    @staticmethod
    def handle_remove(self, context):
        if ShowHideViewportButton._handle is not None:
            SpaceView3D.draw_handler_remove(ShowHideViewportButton._handle, 'WINDOW')
            SpaceView3D.draw_handler_remove(ShowHideViewportButton._handle3d, 'WINDOW')
        ShowHideViewportButton._handle = None
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
        if myobj.visible_get() is True:
            if 'DimensionGenerator' in myobj:
                measureGen = myobj.DimensionGenerator[0]
                for linDim in measureGen.alignedDimensions:
                    
                    linDimProps = linDim
                    if linDim.uses_style:
                        for linDimStyle in context.scene.StyleGenerator[0].alignedDimensions:
                            if linDimStyle.name == linDim.style:
                                linDimProps= linDimStyle

                    update_text(textobj=linDim,props=linDimProps,context=context)
                     
            if 'AnnotationGenerator' in myobj:
                annotationGen = myobj.AnnotationGenerator[0]
                for idx in range(0, annotationGen.num_annotations):
                    annotation = annotationGen.annotations[idx]

                    annotationProps = annotation
                    if annotation.uses_style:
                        for annotationStyle in context.scene.StyleGenerator[0].annotations:
                            if annotationStyle.name == annotation.style:
                                annotationProps= annotationStyle

                    update_text(textobj=annotation,props=annotationProps,context=context)
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
    # Generate all OpenGL calls
    # ---------------------------------------
    for myobj in objlist:
        if myobj.visible_get() is True:
            if 'LineGenerator' in myobj:
                lineGen = myobj.LineGenerator[0]
                draw_line_group(context,myobj,lineGen)
            
            if 'AnnotationGenerator' in myobj:
                annotationGen = myobj.AnnotationGenerator[0]
                draw_annotation(context,myobj,annotationGen)

            if 'DimensionGenerator' in myobj:
                measureGen = myobj.DimensionGenerator[0]
                for linDim in measureGen.alignedDimensions:
                    if linDim.visible is True:
                        draw_alignedDimension(context, myobj, measureGen,linDim)
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

