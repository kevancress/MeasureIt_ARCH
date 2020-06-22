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
import bmesh
from bmesh import from_edit_mesh
import bgl
import gpu
import time
import math
from gpu_extras.batch import batch_for_shader

from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, BoolProperty, StringProperty, \
                      FloatProperty, EnumProperty
from bpy.app.handlers import persistent
from .measureit_arch_geometry import clear_batches, draw_annotation, draw_arcDimension, draw_areaDimension, \
                        draw_alignedDimension, draw_line_group, draw_angleDimension, update_text, draw_axisDimension, draw_boundsDimension, \
                        get_mesh_vertices, printTime, draw_sheet_views

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
        print("Measureit-ARCH: Cleaning Phantom Objects")
        objlist = []
        clear_batches()
        for scene in bpy.data.scenes:
            for obj in scene.objects:
                objlist.append(obj.name)

        for obj in bpy.context.blend_data.objects:
            if obj.name in objlist or obj is None:
                pass
            else:
                print (str(obj.name) + ' Data Removed')
                if 'DimensionGenerator' in obj:
                    dimgen = obj.DimensionGenerator[0]
                    if 'alignedDimensions' in dimgen:
                        for alignedDim in obj.DimensionGenerator[0].alignedDimensions:
                            obj.DimensionGenerator[0].alignedDimensions.remove(0)
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
                            obj.DimensionGenerator[0].wrappedDimensions.remove(0)
                if 'AnnotationGenerator' in obj:
                    for annotation in obj.AnnotationGenerator[0].annotations:
                        obj.AnnotationGenerator[0].annotations.remove(0)
                        obj.AnnotationGenerator[0].num_annotations = 0

bpy.app.handlers.load_post.append(load_handler)
bpy.app.handlers.save_pre.append(save_handler)





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
class MeasureitArchMainPanel(Panel):
    bl_idname = "MEASUREIT_PT_main_panel"
    bl_label = "MeasureIt ARCH V0.4.1(Dev)"
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

        StyleGen = scene.StyleGenerator
        hasGen = True

       
        # ------------------------------
        # Display Buttons
        # ------------------------------
       
        box = layout.box()
        box.label(text="Show/Hide Measure-It")
        row = box.row(align=True)
        
        if context.window_manager.measureit_arch_run_opengl is False:
            icon = 'PLAY'
            txt = 'Show'
        else:
            icon = "PAUSE"
            txt = 'Hide'

        sceneProps = scene.MeasureItArchProps
        row.operator("measureit_arch.runopenglbutton", text=txt, icon=icon ,)
        row.prop(scene, "measureit_arch_gl_ghost", text="", icon='GHOST_ENABLED')
        row.prop(sceneProps, "show_gizmos", text="", icon='GIZMO')


        # ------------------------------
        # Tool Buttons
        # ------------------------------
        layout.label(text="Tools")
        # Tools
        box = layout.box()
        box.label(text="Add Dimensions")

        col = box.column(align=True)
        col.operator("measureit_arch.addaligneddimensionbutton", text="Aligned", icon="DRIVER_DISTANCE")
        split = col.split(factor=0.7,align=True)
        split.operator("measureit_arch.addaxisdimensionbutton", text="Axis", icon="TRACKING_FORWARDS_SINGLE")
        split.prop(scene,'measureit_arch_dim_axis',text="")

        split = col.split(factor=0.7,align=True)
        split.operator("measureit_arch.addboundingdimensionbutton", text="Bounds", icon="SHADING_BBOX")
        row = split.row(align=True)
        row.prop(scene,'measureit_arch_bound_x',text="X", toggle = 1)
        row.prop(scene,'measureit_arch_bound_y',text="Y", toggle = 1)
        row.prop(scene,'measureit_arch_bound_z',text="Z", toggle = 1)

        col = box.column(align=True)
        col.operator("measureit_arch.addanglebutton", text="Angle", icon="DRIVER_ROTATIONAL_DIFFERENCE")
        col.operator("measureit_arch.addarcbutton", text="Arc", icon="MOD_THICKNESS")

        col = box.column(align=True)
        col.operator("measureit_arch.addareabutton", text="Area", icon="MESH_GRID")

        col = box.column(align=True)
        if hasGen:
            col.prop_search(scene,'measureit_arch_default_dimension_style', StyleGen,'alignedDimensions',text="", icon='COLOR')
        col.prop(scene,'viewPlane',text='')


        # ------------------------------
        # Linework Tools
        # ------------------------------
    
        box = layout.box()
        box.label(text="Add Lines")

        col = box.column(align=True)
        col.operator("measureit_arch.addlinebutton", text="Line Group", icon="MESH_CUBE")
        op = col.operator("measureit_arch.addlinebyproperty", text="Line Group by Crease", icon="MESH_CUBE")
        op.calledFromGroup = False

        col = box.column(align=True)
        if hasGen:
            col.prop_search(scene,'measureit_arch_default_line_style', StyleGen,'line_groups',text="", icon='COLOR')

        # ------------------------------
        # Annotation Tools
        # ------------------------------
        box = layout.box()
        box.label(text="Add Annotations")
        
        col = box.column(align=True)
        col.operator("measureit_arch.addannotationbutton", text="Annotation", icon="FONT_DATA")

        col = box.column(align=True)
        if hasGen:
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


# Measureit-ARCH settings
class SCENE_PT_MARCH_Settings(Panel):
    bl_idname = "SCENE_PT_MARCH_Settings"
    bl_label = "MeasureIt-ARCH Settings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'

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
        
        col = layout.column(align=True)
        #col.prop(scene, 'measureit_arch_gl_show_d', text="Distances", toggle=True, icon="DRIVER_DISTANCE")
        #col.prop(scene, 'measureit_arch_gl_show_n', text="Texts", toggle=True, icon="FONT_DATA")
        
        #col.prop(scene, 'measureit_arch_hide_units', text="Units", toggle=True, icon="DRIVER_DISTANCE")
        
      
        col = layout.column(align = True)
        col.alignment = 'RIGHT'
        col = layout.column()
        col.prop(scene, "measureit_arch_gl_show_d")
        col.prop(scene, "measureit_arch_debug_text")
        col.prop(sceneProps, "eval_mods")
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

    # Get visible collections
    viewLayer = bpy.context.view_layer

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
                DimGen = myobj.DimensionGenerator[0]
                for alignedDim in DimGen.alignedDimensions:
                    
                    alignedDimProps = alignedDim
                    if alignedDim.uses_style:
                        for alignedDimStyle in context.scene.StyleGenerator.alignedDimensions:
                            if alignedDimStyle.name == alignedDim.style:
                                alignedDimProps= alignedDimStyle

                    update_text(textobj=alignedDim,props=alignedDimProps,context=context)
                
                for angleDim in DimGen.angleDimensions: 
                    dimProps = angleDim
                    if angleDim.uses_style:
                        for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                            if dimStyle.name == angleDim.style:
                                dimProps= dimStyle
                    update_text(textobj=angleDim,props=dimProps,context=context)
                
                for axisDim in DimGen.axisDimensions: 
                    dimProps = axisDim
                    if axisDim.uses_style:
                        for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                            if dimStyle.name == axisDim.style:
                                dimProps= dimStyle
                    update_text(textobj=axisDim,props=dimProps,context=context)

                for boundsDim in DimGen.boundsDimensions: 
                    dimProps = boundsDim
                    if boundsDim.uses_style:
                        for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                            if dimStyle.name == boundsDim.style:
                                dimProps= dimStyle
                    update_text(textobj=boundsDim,props=dimProps,context=context)
                
                for arcDim in DimGen.arcDimensions: 
                    dimProps = arcDim
                    if arcDim.uses_style:
                        for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                            if dimStyle.name == arcDim.style:
                                dimProps= dimStyle
                    update_text(textobj=arcDim,props=dimProps,context=context)

                for areaDim in DimGen.areaDimensions: 
                    dimProps = areaDim
                    if areaDim.uses_style:
                        for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                            if dimStyle.name == areaDim.style:
                                dimProps= dimStyle
                    update_text(textobj=areaDim,props=dimProps,context=context)
        
            if 'AnnotationGenerator' in myobj:
                annotationGen = myobj.AnnotationGenerator[0]
                for annotation in annotationGen.annotations:
                    annotationProps = annotation
                    if annotation.uses_style:
                        for annotationStyle in context.scene.StyleGenerator.annotations:
                            if annotationStyle.name == annotation.style:
                                annotationProps = annotationStyle
                    if annotation.annotationTextSource is not '':
                        try:
                            if len(annotation.textFields)>1:
                                annotation.textFields[0].text = annotation.annotationTextSource
                                annotation.textFields[1].text = str(myobj[annotation.annotationTextSource])
                            else:  
                                 annotation.textFields[0].text = str(myobj[annotation.annotationTextSource])

                        except:
                            pr = scene.measureit_arch_gl_precision
                            fmt = "%1." + str(pr) + "f"
                            annotation.text = fmt % myobj[annotation.annotationTextSource]
                    update_text(textobj=annotation,props=annotationProps,context=context)

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
                                    alignedDimProps= alignedDimStyle

                        update_text(textobj=alignedDim,props=alignedDimProps,context=context)
                    
                    for angleDim in DimGen.angleDimensions: 
                        dimProps = angleDim
                        if angleDim.uses_style:
                            for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                                if dimStyle.name == angleDim.style:
                                    dimProps= dimStyle
                        update_text(textobj=angleDim,props=dimProps,context=context)
                    
                    for axisDim in DimGen.axisDimensions: 
                        dimProps = axisDim
                        if axisDim.uses_style:
                            for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                                if dimStyle.name == axisDim.style:
                                    dimProps= dimStyle
                        update_text(textobj=axisDim,props=dimProps,context=context)

                    for boundsDim in DimGen.boundsDimensions: 
                        dimProps = boundsDim
                        if boundsDim.uses_style:
                            for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                                if dimStyle.name == boundsDim.style:
                                    dimProps= dimStyle
                        update_text(textobj=boundsDim,props=dimProps,context=context)
                    
                    for arcDim in DimGen.arcDimensions: 
                        dimProps = arcDim
                        if arcDim.uses_style:
                            for dimStyle in context.scene.StyleGenerator.alignedDimensions:
                                if dimStyle.name == arcDim.style:
                                    dimProps= dimStyle
                        update_text(textobj=arcDim,props=dimProps,context=context)

    # Reset Style Update Flags
    StyleGen = context.scene.StyleGenerator
    dimStyles = StyleGen.alignedDimensions
    annoStyles = StyleGen.annotations
    for style in annoStyles:
        style.text_updated = False
    for style in dimStyles:
        style.text_updated = False

def draw_main_3d (context):
   
    scene = context.scene
    sceneProps = scene.MeasureItArchProps

    # Display selected or all
    if scene.measureit_arch_gl_ghost is False:
        objlist = context.selected_objects
    else:
        objlist = context.view_layer.objects

    # ---------------------------------------
    # Generate all OpenGL calls
    # ---------------------------------------
    for myobj in objlist:
    
        #Stash Object Vertices for use in Draw functions
          
        if myobj.visible_get() is True:
            mat = myobj.matrix_world
            
            sheetGen = myobj.SheetGenerator
            for sheet_view in sheetGen.sheet_views:
                draw_sheet_views(context,myobj,sheetGen,sheet_view,mat)

            if 'LineGenerator' in myobj and myobj.LineGenerator[0].line_num != 0:
                lineGen = myobj.LineGenerator[0]
                draw_line_group(context,myobj,lineGen,mat)

            if 'AnnotationGenerator' in myobj and myobj.AnnotationGenerator[0].num_annotations != 0:
                annotationGen = myobj.AnnotationGenerator[0]
                draw_annotation(context,myobj,annotationGen,mat)

            if 'DimensionGenerator' in myobj:
                DimGen = myobj.DimensionGenerator[0]
                
                for alignedDim in DimGen.alignedDimensions:
                    draw_alignedDimension(context, myobj, DimGen, alignedDim,mat)

                for angleDim in DimGen.angleDimensions:
                    draw_angleDimension(context, myobj, DimGen, angleDim,mat)

                for axisDim in DimGen.axisDimensions:
                    draw_axisDimension(context,myobj,DimGen,axisDim,mat)
                
                for boundsDim in DimGen.boundsDimensions:
                    draw_boundsDimension(context,myobj,DimGen,boundsDim,mat)
                
                for arcDim in DimGen.arcDimensions:
                    draw_arcDimension(context,myobj,DimGen,arcDim,mat)

                for areaDim in DimGen.areaDimensions:
                    draw_areaDimension(context,myobj,DimGen,areaDim,mat)


    # Draw Instanced Objects

    if draw_instanced:
        deps = bpy.context.view_layer.depsgraph
        for obj_int in deps.object_instances:
            if obj_int.is_instance:
                myobj = obj_int.object
                
                if 'LineGenerator' in myobj or 'AnnotationGenerator' in myobj or 'DimensionGenerator' in myobj:
                    mat = obj_int.matrix_world

                if 'LineGenerator' in myobj and myobj.LineGenerator[0].line_num != 0:
                    lineGen = myobj.LineGenerator[0]
                    draw_line_group(context,myobj,lineGen,mat)
                
                if 'AnnotationGenerator' in myobj and myobj.AnnotationGenerator[0].num_annotations != 0:
                    annotationGen = myobj.AnnotationGenerator[0]
                    draw_annotation(context,myobj,annotationGen,mat)
                    
                if sceneProps.instance_dims:
                    if 'DimensionGenerator' in myobj and myobj.DimensionGenerator[0].measureit_arch_num != 0:
                        DimGen = myobj.DimensionGenerator[0]
                        mat = obj_int.matrix_world
                        for alignedDim in DimGen.alignedDimensions:
                            draw_alignedDimension(context, myobj, DimGen, alignedDim,mat)
                        for angleDim in DimGen.angleDimensions:
                            draw_angleDimension(context, myobj, DimGen, angleDim,mat)
                        for axisDim in DimGen.axisDimensions:
                            draw_axisDimension(context,myobj,DimGen,axisDim,mat)

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
            if len(mylist)==0: mylist.extend([v.index])
            else:
                mylist.extend([v.index])
                mylist.extend([v.index])

    if flag is True:
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
    for face in bm.faces:
        myface = []
        if face.select is True:
            mylist.extend([face.index])

    if flag is True:
        bpy.ops.object.editmode_toggle()
    # Back context object
    bpy.context.view_layer.objects.active = oldobj

    return mylist

