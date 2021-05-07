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
import bpy
import bgl

from bmesh import from_edit_mesh
from bpy.types import Panel, Operator, SpaceView3D
from bpy.app.handlers import persistent
from mathutils import Vector, Matrix

from .measureit_arch_geometry import clear_batches, update_text, \
    get_view, draw3d_loop, get_rv3d


draw_instanced = True

# ------------------------------------------------------
# Handler to detect new Blend load
#
# ------------------------------------------------------


@persistent
def load_handler(dummy):
    ShowHideViewportButton.handle_remove(None, bpy.context)


# ------------------------------------------------------
# Handler to detect save Blend
# Clear not used measured
#
# ------------------------------------------------------

@persistent
def save_handler(dummy):
    cleanScene = True
    if cleanScene:
        # Check all Scenes for phantom objects
        # Necessary because the pointer properties on Dimensions and annotations
        # count as an ID user and prevent the object from being removed normally
        print("MeasureIt_ARCH: Cleaning Phantom Objects")
        objlist = []
        clear_batches()
        for scene in bpy.data.scenes:
            for obj in scene.objects:
                objlist.append(obj.name)

        for obj in bpy.context.blend_data.objects:
            if obj.name in objlist or obj is None:
                pass
            else:
                print(str(obj.name) + ' Data Removed')
                if 'DimensionGenerator' in obj:
                    dimgen = obj.DimensionGenerator[0]
                    if 'alignedDimensions' in dimgen:
                        for alignedDim in obj.DimensionGenerator[0].alignedDimensions:
                            obj.DimensionGenerator[0].alignedDimensions.remove(
                                0)
                            obj.DimensionGenerator[0].measureit_arch_num = 0
                    if 'angleDimensions' in dimgen:
                        for angleDim in obj.DimensionGenerator[0].angleDimensions:
                            obj.DimensionGenerator[0].angleDimensions.remove(0)
                            obj.DimensionGenerator[0].measureit_arch_num = 0
                    if 'axisDimensions' in dimgen:
                        for axisDim in obj.DimensionGenerator[0].axisDimensions:
                            obj.DimensionGenerator[0].axisDimensions.remove(0)
                            obj.DimensionGenerator[0].measureit_arch_num = 0
                    if 'boundsDimensions' in dimgen:
                        for boundsDim in obj.DimensionGenerator[0].boundsDimensions:
                            obj.DimensionGenerator[0].boundsDimensions.remove(0)
                            obj.DimensionGenerator[0].measureit_arch_num = 0
                    if 'wrappedDimensions' in dimgen:
                        for wrapper in obj.DimensionGenerator[0].wrappedDimensions:
                            obj.DimensionGenerator[0].wrappedDimensions.remove(
                                0)
                if 'AnnotationGenerator' in obj:
                    for annotation in obj.AnnotationGenerator[0].annotations:
                        obj.AnnotationGenerator[0].annotations.remove(0)
                        obj.AnnotationGenerator[0].num_annotations = 0


bpy.app.handlers.load_post.append(load_handler)
bpy.app.handlers.save_pre.append(save_handler)


# Rough Attempts to add a m-ARCH tab to the properties panel navigation bar
# Not solved yet (not entirely sure its possible), but kept for future reference.

# class MeasureIt_nav_button(Panel):
#    bl_space_type = 'PROPERTIES'
#    bl_region_type = 'NAVIGATION_BAR'
#    bl_label = "Navigation Bar"
#    bl_options = {'HIDE_HEADER'}

#    def draw(self, context):
#        layout = self.layout
#        layout.scale_x = 1.4
#        layout.scale_y = 1.4
#        layout.operator("measureit_arch.addaligneddimensionbutton", text="Aligned", icon="DRIVER_DISTANCE")


# ------------------------------------------------------------------
# Define panel class for main functions.
# ------------------------------------------------------------------
class MEASUREIT_PT_main_panel(Panel):
    bl_idname = "MEASUREIT_PT_main_panel"
    bl_label = "MeasureIt_ARCH v0.4.7(git)"
    bl_space_type = 'VIEW_3D'
    bl_region_type = "UI"
    bl_category = 'MeasureIt_ARCH'

    # ------------------------------
    # Draw UI
    # ------------------------------
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        hasGen = False

        StyleGen = scene.StyleGenerator
        hasGen = True

        # ------------------------------
        # Display Buttons
        # ------------------------------

        box = layout.box()
        box.label(text="Show/Hide MeasureIt_ARCH")
        row = box.row(align=True)

        if not context.window_manager.measureit_arch_run_opengl:
            icon = 'PLAY'
            txt = 'Show'
        else:
            icon = 'PAUSE'
            txt = 'Hide'

        sceneProps = scene.MeasureItArchProps
        row.operator("measureit_arch.runopenglbutton", text=txt, icon=icon,)
        row.prop(sceneProps, "show_all", text="", icon='GHOST_ENABLED')
        #row.prop(sceneProps, 'highlight_selected', text="", icon='VIS_SEL_11')
        row.prop(sceneProps, "show_gizmos", text="", icon='GIZMO')

        # ------------------------------
        # Tool Buttons
        # ------------------------------
        layout.label(text="Tools")
        # Tools
        box = layout.box()
        box.label(text="Add Dimensions")

        col = box.column(align=True)
        col.operator("measureit_arch.addaligneddimensionbutton",
                     text="Aligned", icon="DRIVER_DISTANCE")
        split = col.split(factor=0.7, align=True)
        split.operator("measureit_arch.addaxisdimensionbutton",
                       text="Axis", icon="TRACKING_FORWARDS_SINGLE")
        split.prop(sceneProps, 'measureit_arch_dim_axis', text="")

        split = col.split(factor=0.7, align=True)
        split.operator("measureit_arch.addboundingdimensionbutton",
                       text="Bounds", icon="SHADING_BBOX")
        row = split.row(align=True)
        row.prop(sceneProps, 'bound_x', text="X", toggle=1)
        row.prop(sceneProps, 'bound_y', text="Y", toggle=1)
        row.prop(sceneProps, 'bound_z', text="Z", toggle=1)

        col = box.column(align=True)
        col.operator("measureit_arch.addanglebutton", text="Angle",
                     icon="DRIVER_ROTATIONAL_DIFFERENCE")
        col.operator("measureit_arch.addarcbutton",
                     text="Arc", icon="MOD_THICKNESS")

        col = box.column(align=True)
        col.operator("measureit_arch.addareabutton",
                     text="Area", icon="MESH_GRID")

        col = box.column(align=True)
        if hasGen:
            col.prop_search(sceneProps, 'default_dimension_style',
                            StyleGen, 'alignedDimensions', text="", icon='COLOR')
        col.prop(sceneProps, 'viewPlane', text='')

        # ------------------------------
        # Linework Tools
        # ------------------------------

        box = layout.box()
        box.label(text="Add Lines")

        col = box.column(align=True)
        col.operator("measureit_arch.addlinebutton",
                     text="Line Group", icon="MESH_CUBE")
        col.operator("measureit_arch.adddynamiclinebutton",
                     text="Dynamic Line Group", icon="MESH_CUBE")
        op = col.operator("measureit_arch.addlinebyproperty",
                          text="Line Group by Crease", icon="MESH_CUBE")
        op.calledFromGroup = False

        col = box.column(align=True)
        if hasGen:
            col.prop_search(sceneProps, 'default_line_style',
                            StyleGen, 'line_groups', text="", icon='COLOR')

        # ------------------------------
        # Annotation Tools
        # ------------------------------
        box = layout.box()
        box.label(text="Add Annotations")

        col = box.column(align=True)
        col.operator("measureit_arch.addannotationbutton",
                     text="Annotation", icon="FONT_DATA")

        col = box.column(align=True)
        if hasGen:
            col.prop_search(sceneProps, 'default_annotation_style',
                            StyleGen, 'annotations', text="", icon='COLOR')

# ------------------------------------------------------------------
# New Panel to group Object Properties
# ------------------------------------------------------------------


class OBJECT_PT_Panel(Panel):
    """Creates a Panel in the Object properties window"""
    bl_idname = 'OBJECT_PT_Panel'
    bl_label = "MeasureIt_ARCH"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        pass


bpy.utils.register_class(OBJECT_PT_Panel)


# ------------------------------------------------------------------
# New Panel to group Scene Properties
# ------------------------------------------------------------------
class SCENE_PT_Panel(bpy.types.Panel):
    """Main Properties Panel"""
    bl_idname = "SCENE_PT_Panel"
    bl_label = "MeasureIt_ARCH"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'

    def draw(self, context):
        pass


bpy.utils.register_class(SCENE_PT_Panel)


# MeasureIt_ARCH settings
class SCENE_PT_MARCH_Settings(Panel):
    bl_parent_id = 'SCENE_PT_Panel'
    bl_idname = "SCENE_PT_MARCH_Settings"
    bl_label = "Settings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon='SETTINGS')

    # -----------------------------------------------------
    # Draw (create UI interface)
    # -----------------------------------------------------
    # noinspection PyUnusedLocal
    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        scene = context.scene
        sceneProps = scene.MeasureItArchProps

        col = layout.column(align=True, heading='Settings')
        # col.prop(sceneProps, 'show_dim_text',) I Dont Know why this would be usefull
        col.prop(sceneProps, 'hide_units')
        col.prop(sceneProps, "eval_mods")
        col.prop(sceneProps, "use_text_autoplacement")
        col.prop(sceneProps, 'default_resolution', text="Default Resolution")
        col.prop(sceneProps, 'keep_freestyle_svg', text="Keep Freestyle SVG")

        col = layout.column(align=True, heading='Debug')
        col.prop(sceneProps, "measureit_arch_debug_text")
        col.prop(sceneProps, "show_text_cards")

        col = layout.column(align=True, heading='Experimental')
        col.prop(sceneProps, "enable_experimental")

        if sceneProps.enable_experimental:
            col.prop(sceneProps, "instance_dims")
        #col.prop(sceneProps, "debug_flip_text")


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
            ShowHideViewportButton._handle3d = SpaceView3D.draw_handler_add(
                draw_callback_3d, (self, context), 'WINDOW', 'POST_VIEW')
            context.window_manager.measureit_arch_run_opengl = True

    # ------------------------------------
    # Disable gl drawing removing handler
    # ------------------------------------
    # noinspection PyUnusedLocal
    @staticmethod
    def handle_remove(self, context):
        if ShowHideViewportButton._handle is not None:
            SpaceView3D.draw_handler_remove(
                ShowHideViewportButton._handle, 'WINDOW')
            SpaceView3D.draw_handler_remove(
                ShowHideViewportButton._handle3d, 'WINDOW')
        ShowHideViewportButton._handle = None
        context.window_manager.measureit_arch_run_opengl = False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            if not context.window_manager.measureit_arch_run_opengl:
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
# Handle all 2d draw routines (Text Updating mostly)
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
    sceneProps = scene.MeasureItArchProps

    # Get visible collections
    viewLayer = bpy.context.view_layer

    # Display selected or all
    if not sceneProps.show_all:
        objlist = context.selected_objects
    else:
        objlist = context.view_layer.objects

    # Enable GL drawing
    bgl.glEnable(bgl.GL_BLEND)
    # ---------------------------------------
    # Generate all OpenGL calls for measures
    # ---------------------------------------
    text_update_loop(context, objlist)

    view = get_view()
    if view is not None and view.titleBlock != "":
        camera = view.camera
        titleblockScene = bpy.data.scenes[view.titleBlock]
        objlist = titleblockScene.objects
        text_update_loop(context, objlist)

    # Reset Style & Scene Update Flags
    StyleGen = context.scene.StyleGenerator
    dimStyles = StyleGen.alignedDimensions
    annoStyles = StyleGen.annotations
    for style in annoStyles:
        style.text_updated = False
    for style in dimStyles:
        style.text_updated = False

    sceneProps = scene.MeasureItArchProps
    sceneProps.text_updated = False


def text_update_loop(context, objlist):

    for myobj in objlist:
        if not myobj.hide_get():
            if 'DimensionGenerator' in myobj:
                DimGen = myobj.DimensionGenerator[0]
                for alignedDim in DimGen.alignedDimensions:

                    alignedDimProps = alignedDim
                    if alignedDim.uses_style:
                        for alignedDimStyle in context.scene.StyleGenerator.alignedDimensions:
                            if alignedDimStyle.name == alignedDim.style:
                                alignedDimProps = alignedDimStyle

                    update_text(textobj=alignedDim,
                                props=alignedDimProps, context=context)

                for angleDim in DimGen.angleDimensions:
                    dimProps = angleDim
                    if angleDim.uses_style:
                        for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                            if dimStyle.name == angleDim.style:
                                dimProps = dimStyle
                    update_text(textobj=angleDim,
                                props=dimProps, context=context)

                for axisDim in DimGen.axisDimensions:
                    dimProps = axisDim
                    if axisDim.uses_style:
                        for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                            if dimStyle.name == axisDim.style:
                                dimProps = dimStyle
                    update_text(textobj=axisDim,
                                props=dimProps, context=context)

                for boundsDim in DimGen.boundsDimensions:
                    dimProps = boundsDim
                    if boundsDim.uses_style:
                        for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                            if dimStyle.name == boundsDim.style:
                                dimProps = dimStyle
                    update_text(textobj=boundsDim,
                                props=dimProps, context=context)

                for arcDim in DimGen.arcDimensions:
                    dimProps = arcDim
                    if arcDim.uses_style:
                        for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                            if dimStyle.name == arcDim.style:
                                dimProps = dimStyle
                    update_text(textobj=arcDim, props=dimProps, context=context)

                for areaDim in DimGen.areaDimensions:
                    dimProps = areaDim
                    if areaDim.uses_style:
                        for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                            if dimStyle.name == areaDim.style:
                                dimProps = dimStyle
                    update_text(textobj=areaDim,
                                props=dimProps, context=context)

            if 'AnnotationGenerator' in myobj:
                annotationGen = myobj.AnnotationGenerator[0]
                for annotation in annotationGen.annotations:
                    annotationProps = annotation
                    if annotation.uses_style:
                        for annotationStyle in context.scene.StyleGenerator.annotations:
                            if annotationStyle.name == annotation.style:
                                annotationProps = annotationStyle

                    fields = []
                    notesFlag = False
                    for textField in annotation.textFields:
                        fields.append(textField)
                        if textField.autoFillText and textField.textSource == 'NOTES':
                            notesFlag = True

                    if notesFlag:
                        view = get_view()
                        for textField in view.textFields:
                            fields.append(textField)

                    update_text(textobj=annotation,
                                props=annotationProps, context=context, fields = fields)

                # Draw Instanced Objects

    if draw_instanced:
        deps = bpy.context.view_layer.depsgraph
        for obj_int in deps.object_instances:
            if obj_int.is_instance:
                myobj = obj_int.object

                if 'DimensionGenerator' in myobj:
                    DimGen = myobj.DimensionGenerator[0]
                    for alignedDim in DimGen.alignedDimensions:

                        alignedDimProps = alignedDim
                        if alignedDim.uses_style:
                            for alignedDimStyle in context.scene.StyleGenerator.alignedDimensions:
                                if alignedDimStyle.name == alignedDim.style:
                                    alignedDimProps = alignedDimStyle

                        update_text(textobj=alignedDim,
                                    props=alignedDimProps, context=context)

                    for angleDim in DimGen.angleDimensions:
                        dimProps = angleDim
                        if angleDim.uses_style:
                            for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                                if dimStyle.name == angleDim.style:
                                    dimProps = dimStyle
                        update_text(textobj=angleDim,
                                    props=dimProps, context=context)

                    for axisDim in DimGen.axisDimensions:
                        dimProps = axisDim
                        if axisDim.uses_style:
                            for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                                if dimStyle.name == axisDim.style:
                                    dimProps = dimStyle
                        update_text(textobj=axisDim,
                                    props=dimProps, context=context)

                    for boundsDim in DimGen.boundsDimensions:
                        dimProps = boundsDim
                        if boundsDim.uses_style:
                            for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                                if dimStyle.name == boundsDim.style:
                                    dimProps = dimStyle
                        update_text(textobj=boundsDim,
                                    props=dimProps, context=context)

                    for arcDim in DimGen.arcDimensions:
                        dimProps = arcDim
                        if arcDim.uses_style:
                            for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                                if dimStyle.name == arcDim.style:
                                    dimProps = dimStyle
                        update_text(textobj=arcDim, props=dimProps,
                                    context=context)


def draw_main_3d(context):

    scene = context.scene
    sceneProps = scene.MeasureItArchProps

    # Display selected or all
    if not sceneProps.show_all:
        objlist = context.selected_objects
    else:
        objlist = context.view_layer.objects

    draw3d_loop(context, objlist)
    # preview_dual(context)

    # Draw TitleBlock
    draw_titleblock(context)


def draw_titleblock(context, svg=None):
    view = get_view()
    rv3d = get_rv3d()
    sceneProps = context.scene.MeasureItArchProps

    if sceneProps.is_vector_draw:
        titleblock = svg.g(id='TitleBlock')

    if view is not None and view.titleBlock != "":
        if not sceneProps.is_render_draw:
            if rv3d.view_perspective != 'CAMERA':
                return

        camera = view.camera

        titleblockScene = bpy.data.scenes[view.titleBlock]

        objlist = titleblockScene.objects

        cameraMat = camera.matrix_world
        offsetVec = Vector((0, 0, -1.1))
        offsetVec *= camera.data.clip_start
        #offsetVec = cameraMat @ offsetVec

        transMat = Matrix.Translation(offsetVec)

        scaleMat = Matrix.Identity(3)
        scaleMat *= (view.model_scale / view.paper_scale)
        scaleMat.resize_4x4()

        extMat = cameraMat @ transMat @ scaleMat
        draw3d_loop(context, objlist, extMat=extMat, svg=svg, multMat=True)


# -------------------------------------------------------------
# Handlers for drawing OpenGl
# -------------------------------------------------------------
def draw_callback_px(self, context):
    draw_main(context)


def draw_callback_3d(self, context):
    draw_main_3d(context)


# -------------------------------------------------------------
# Check if the segment already exist
# LEGACY REMOVED - SHOULD BE RE IMPLIMENTED WITH NEW SYSTEM
# -------------------------------------------------------------
def exist_segment(mp, pointa, pointb, typ=1, pointc=None):
    return False
    pass


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
    bmhistory = bm.select_history
    if len(bmhistory) > 0:
        for v in bmhistory:
            if len(mylist) == 0:
                mylist.extend([v.index])
            else:
                mylist.extend([v.index])
                mylist.extend([v.index])

    if flag:
        bpy.ops.object.editmode_toggle()
    # Back context object
    bpy.context.view_layer.objects.active = oldobj

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

    if flag:
        bpy.ops.object.editmode_toggle()
    # Back context object
    bpy.context.view_layer.objects.active = oldobj

    return mylist


# -------------------------------------------------------------
# Get verticies and their parent object depending on selection type
# -------------------------------------------------------------


# Adds verts to a vertex dictionary to be processed by the add function

def get_smart_selected(filterObj=None, forceEdges=False, usePairs=True):
    pointList = []
    warningStr = ''

    # Object Mode
    if bpy.context.mode == 'OBJECT':
        objs = bpy.context.selected_objects
        print('In Object Mode')
        idx = 0
        if len(objs) > 2 and usePairs:
            warningStr = "More than 2 objects selected, Order may not be as expected"

        # Sort Objects into Pairs
        idx = 0
        for obj in objs:
            pointData = {}
            pointData['vert'] = 9999999
            pointData['obj'] = obj
            pointList.append(pointData)

            if usePairs:
                try:
                    pointData = {}
                    pointData['vert'] = 9999999
                    pointData['obj'] = objs[idx+1]
                    pointList.append(pointData)
                except IndexError:
                    pass

            idx += 1

    # Edit Mode
    elif bpy.context.mode == 'EDIT_MESH':
        objs = bpy.context.objects_in_mode
        selectionMode = bpy.context.scene.tool_settings.mesh_select_mode

        # For each obj in edit mode
        for obj in objs:
            if filterObj is None or obj.name == filterObj.name:
                bm = from_edit_mesh(obj.data)
                dupFlag = False

                # Ignore force Edges if Selection History exists
                if len(bm.select_history) >= 2:
                    forceEdges = False

                # Vertex Selection
                if selectionMode[0] and not forceEdges:
                    # Get Selected Verts:
                    verts = []
                    # use History if avaialable fall back to basic selection
                    if len(bm.select_history) > 0:
                        for vert in bm.select_history:
                            verts.append(vert)
                    else:
                        for v in obj.data.vertices:
                            if v.select:
                                verts.append(v)

                    # reverse selection history
                    verts.reverse()
                    idx = 0

                    # Flag to add a duplicate if were coming from a different obj
                    if ((len(pointList) % 2) == 1) and usePairs:
                        dupFlag = True

                    # Warning Text for too many verts
                    if len(verts) > 2 and len(objs) > 2:
                        warningStr = "More than 2 Verticies selected across multiple objects \n Order may not be as expected"

                    for vert in verts:
                        pointData = {}
                        pointData['vert'] = vert.index
                        pointData['obj'] = obj
                        pointList.append(pointData)

                        if dupFlag:
                            pointData = {}
                            pointData['vert'] = vert.index
                            pointData['obj'] = obj
                            pointList.append(pointData)
                            dupFlag = False

                        if usePairs:
                            try:
                                pointData = {}
                                pointData['vert'] = verts[idx+1].index
                                pointData['obj'] = obj
                                pointList.append(pointData)

                            except IndexError:
                                pass
                        idx += 1

                # Edge Selection
                elif selectionMode[1] or forceEdges:
                    for e in bm.edges:
                        if e.select:
                            for vert in e.verts:
                                pointData = {}
                                pointData['vert'] = vert.index
                                pointData['obj'] = obj
                                pointList.append(pointData)

        print('In Edit Mode')

    # print(pointList)
    return pointList, warningStr
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
    for face in bm.faces:
        myface = []
        if face.select:
            mylist.extend([face.index])

    if flag:
        bpy.ops.object.editmode_toggle()
    # Back context object
    bpy.context.view_layer.objects.active = oldobj

    return mylist


# MeasureIt_ARCH Unit settings
class SCENE_PT_MARCH_units(Panel):
    bl_parent_id = 'SCENE_PT_unit'
    bl_idname = "SCENE_PT_MARCH_Units"
    bl_label = "MeasureIt_ARCH Unit Settings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon='SNAP_INCREMENT')

    # -----------------------------------------------------
    # Draw (create UI interface)
    # -----------------------------------------------------
    def draw(self, context):
        scene = context.scene
        sceneProps = scene.MeasureItArchProps

        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        scene = context.scene

        col = layout.column()
        col.prop(sceneProps, 'metric_precision', text="Metric Precision")
        col.prop(sceneProps, 'angle_precision', text="Angle Precision")
        col.prop(sceneProps, 'imperial_precision', text="Imperial Precision")

        col = layout.column(align=True)
        col.prop(sceneProps, 'default_scale', text="Default Scale 1:")
