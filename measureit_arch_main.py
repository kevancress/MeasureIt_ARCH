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

from bpy.types import Panel, Operator, SpaceView3D
from bpy.app.handlers import persistent
from mathutils import Vector, Matrix

from .measureit_arch_geometry import clear_batches, update_text, draw3d_loop, preview_dual
from .measureit_arch_utils import get_view, get_rv3d
from .gitcommit import prev_commit,date


@persistent
def load_handler(dummy):
    """ Handler called when a Blender file is loaded """
    ShowHideViewportButton.handle_remove(None, bpy.context)


@persistent
def save_handler(dummy):
    """ Handler called when a Blender file is saved """
    # Clear not used measured
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
                    dimgen = obj.DimensionGenerator
                    if 'alignedDimensions' in dimgen:
                        for alignedDim in obj.DimensionGenerator.alignedDimensions:
                            obj.DimensionGenerator.alignedDimensions.remove(0)
                            obj.DimensionGenerator.measureit_arch_num = 0
                    if 'angleDimensions' in dimgen:
                        for angleDim in obj.DimensionGenerator.angleDimensions:
                            obj.DimensionGenerator.angleDimensions.remove(0)
                            obj.DimensionGenerator.measureit_arch_num = 0
                    if 'axisDimensions' in dimgen:
                        for axisDim in obj.DimensionGenerator.axisDimensions:
                            obj.DimensionGenerator.axisDimensions.remove(0)
                            obj.DimensionGenerator.measureit_arch_num = 0
                    if 'boundsDimensions' in dimgen:
                        for boundsDim in obj.DimensionGenerator.boundsDimensions:
                            obj.DimensionGenerator.boundsDimensions.remove(0)
                            obj.DimensionGenerator.measureit_arch_num = 0
                    if 'wrappedDimensions' in dimgen:
                        for wrapper in obj.DimensionGenerator.wrappedDimensions:
                            obj.DimensionGenerator.wrappedDimensions.remove(0)
                if 'AnnotationGenerator' in obj:
                    for annotation in obj.AnnotationGenerator.annotations:
                        obj.AnnotationGenerator.annotations.remove(0)
                        obj.AnnotationGenerator.num_annotations = 0



# Rough Attempts to add a m-ARCH tab to the properties panel navigation bar
# Not solved yet (not entirely sure its possible), but kept for future reference.

#class MeasureIt_nav_button(Panel):
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
    bl_label = "MeasureIt_ARCH v0.5.0(dev-{})".format(prev_commit)
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
        row.prop(sceneProps, 'highlight_selected', text="", icon='VIS_SEL_11')
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
        col.operator("measureit_arch.adddynamiclinebutton",
            text="Dynamic Line Group", icon="MESH_CUBE")

        col.operator("measureit_arch.addlinebutton",
                     text="Line Group by Selection", icon="MESH_CUBE")
        
        # Dynamic line  group is fast enough to replace this now
        #op = col.operator("measureit_arch.addlinebyproperty",
        #                  text="Line Group by Crease", icon="MESH_CUBE")
        #op.calledFromGroup = False


       
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




class SCENE_PT_Panel(bpy.types.Panel):
    """ Main (scene) properties panel """
    bl_idname = "SCENE_PT_Panel"
    bl_label = "MeasureIt_ARCH"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        sceneProps = context.scene.MeasureItArchProps
        col.prop(sceneProps,"project_name")
        col.prop(sceneProps,"project_address")
        col.prop(sceneProps,"project_number")
        pass


class SCENE_PT_MARCH_Settings(Panel):
    """ Settings panel """
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
        col.prop(sceneProps, 'depth_samples')
        col.prop(sceneProps, 'hide_units')
        col.prop(sceneProps, 'hide_titleblock')
        col.prop(sceneProps, 'hide_linework')
        col.prop(sceneProps, "eval_mods")
        col.prop(sceneProps, "use_text_autoplacement")
        col.prop(sceneProps, 'use_default_res', text="Use Default Resolution (3D View)")
        col.prop(sceneProps, 'default_resolution', text="Default Resolution")
        col.prop(sceneProps, 'keep_freestyle_svg', text="Keep Freestyle SVG")
        col.prop(sceneProps, 'show_dxf_props', text="Show DXF Options")
        col.prop(sceneProps, 'use_cad_col')

        col = layout.column(align=True, heading='Debug')
        col.prop(sceneProps, "measureit_arch_debug_text")
        col.prop(sceneProps, "show_text_cards")

        col = layout.column(align=True, heading='Experimental')
        col.prop(sceneProps, "enable_experimental")

        if sceneProps.enable_experimental:
            col.prop(sceneProps, "instance_dims")
        # col.prop(sceneProps, "debug_flip_text")

        col.label(text = "MeasureIt_ARCH Version Info:")
        col.label(text = "Prev Commit Hash: {}".format(prev_commit))
        col.label(text = "Prev Commit Date: {}".format(date))


class ShowHideViewportButton(Operator):
    """ A button that enables/disables Viewport Display """

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
            ShowHideViewportButton._handle = SpaceView3D.draw_handler_add(
                draw_main, (context,), 'WINDOW', 'POST_PIXEL')
            ShowHideViewportButton._handle3d = SpaceView3D.draw_handler_add(
                draw_main_3d, (context,), 'WINDOW', 'POST_VIEW')
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


def draw_main(context):
    """ Handle all 2D draw routines (Text Updating mostly) """

    region = bpy.context.region
    # Detect if Quadview to get drawing area
    if context.space_data.region_quadviews:
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

    scene = bpy.context.scene
    sceneProps = scene.MeasureItArchProps

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
    if view is not None and view.titleBlock != "" and not sceneProps.hide_titleblock:
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
    scene = bpy.context.scene
    sceneProps = scene.MeasureItArchProps
    for myobj in objlist:
        if not myobj.hide_get():
            if 'DimensionGenerator' in myobj:
                DimGen = myobj.DimensionGenerator
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
                annotationGen = myobj.AnnotationGenerator
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

                    update_text(
                        textobj=annotation, props=annotationProps,
                        context=context, fields=fields)

                # Draw Instanced Objects


    deps = bpy.context.view_layer.depsgraph
    for obj_int in deps.object_instances:
        if obj_int.is_instance:
            myobj = obj_int.object

            annotationGen = myobj.AnnotationGenerator
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

                update_text(
                    textobj=annotation, props=annotationProps,
                    context=context, fields=fields)


            if sceneProps.instance_dims:

                DimGen = myobj.DimensionGenerator
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

    sceneProps.source_scene = scene
    draw3d_loop(context, objlist)
    #preview_dual(context)
    
    # VIEWPORTS
    viewportGen = scene.ViewportGenerator
    for viewport in get_view().viewports:
        draw_viewport(context,viewport=viewport)


    # Draw TitleBlock

    if not sceneProps.hide_titleblock:
        draw_viewport(context)
    
    scene.ViewGenerator.view_changed = False


### Revised version of draw Titleblock, to draw any view in any scene, in paperspace
### A way to use views similar to AutoCAD "viewports" or Rhino "DetailViews"
def draw_viewport(context, viewport=None, svg=None, dxf = None):
    view = get_view()
    rv3d = get_rv3d()
    sceneProps = context.scene.MeasureItArchProps

    if sceneProps.is_vector_draw:
        titleblock = svg.g(id='TitleBlock')

    
    # titleblock call
    if viewport is None:
        if view.titleBlock == "":
            return
        viewportScene = bpy.data.scenes[view.titleBlock]
        viewportView = viewportScene.ViewGenerator.views[0]
        obj = view.camera
        offsetVec = Vector((0, 0, -1.2))
        offsetVec *= obj.data.clip_start

    else: #normal call
        viewportScene = viewport.scene
        viewportView = viewportScene.ViewGenerator.views[viewport.view]
        offsetVec = Vector((0, 0, 0))
        obj = viewport.anchor

    ## Only draw in camera view
    #if not sceneProps.is_render_draw:
    #    if rv3d.view_perspective != 'CAMERA':
    #        return
     
    viewportCamera = viewportView.camera
    viewportMat = viewportCamera.matrix_world.inverted_safe()

    objlist = viewportScene.objects

    anchorObjMat = obj.matrix_world

    transMat = Matrix.Translation(offsetVec)

    scaleMat = Matrix.Identity(3)
    scaleMat *= (view.model_scale / view.paper_scale) / (viewportView.model_scale / viewportView.paper_scale)
    scaleMat.resize_4x4()

    extMat = anchorObjMat @ transMat @ scaleMat @ viewportMat
    sceneProps.source_scene = viewportScene

    if sceneProps.is_render_draw:
            text_update_loop(context, objlist)

    draw3d_loop(context, objlist, extMat=extMat, svg=svg, dxf = dxf, multMat=True, custom_call=True)
    
    # Return Source scene to the current scene
    sceneProps.source_scene = context.scene

def draw_titleblock(context, svg=None, dxf = None):
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
        titleblockView = titleblockScene.ViewGenerator.views[0]

        objlist = titleblockScene.objects

        cameraMat = camera.matrix_world
        offsetVec = Vector((0, 0, -1.2))
        offsetVec *= camera.data.clip_start

        transMat = Matrix.Translation(offsetVec)

        scaleMat = Matrix.Identity(3)
        scaleMat *= (view.model_scale / view.paper_scale)
        scaleMat.resize_4x4()

        extMat = cameraMat @ transMat @ scaleMat
        sceneProps.source_scene = titleblockScene
        if sceneProps.is_render_draw:
             text_update_loop(context, objlist)
        draw3d_loop(context, objlist, extMat=extMat, svg=svg, dxf = dxf, multMat=True, custom_call=True)
        sceneProps.source_scene = context.scene


# -------------------------------------------------------------
# Handlers for drawing OpenGl
# -------------------------------------------------------------
def draw_callback_px(self, context):
    draw_main(context)


def draw_callback_3d(self, context):
    draw_main_3d(context)


