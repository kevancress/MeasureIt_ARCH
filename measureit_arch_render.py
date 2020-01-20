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
# support routines for render measures in final image
# Author: Antonio Vazquez (antonioya), Kevan Cress
#
# ----------------------------------------------------------

import bpy

import bgl
import gpu

import blf
from os import path, remove
from sys import exc_info

import bpy_extras.image_utils as img_utils

import bpy_extras.object_utils as object_utils
# noinspection PyUnresolvedReferences
from bpy_extras import view3d_utils
from math import ceil

from gpu_extras.presets import draw_texture_2d
from bgl import *
import numpy as np
import bmesh
from .measureit_arch_geometry import *
from .measureit_arch_main import draw_main, draw_main_3d
from bpy.props import IntProperty
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D

# ------------------------------------------------------------------
# Define panel class for render functions.
# ------------------------------------------------------------------
class MeasureitArchRenderPanel(Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"
    bl_options = {'HIDE_HEADER'}
    bl_label = "MeasureIt-ARCH Render"

    #bl_idname = "measureit_arch_render_panel"
    #bl_label = "MeasureIt-ARCH Render"
    #bl_space_type = 'PROPERTIES'
    #bl_region_type = "WINDOW"
    #bl_context = "render"

    # ------------------------------
    # Draw UI
    # ------------------------------
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        scene = context.scene

        # Render settings
        col = layout.column()
        col.label(text="MeasureIt-ARCH Render")
        col = layout.column(align=True)
        col.scale_y = 1.5
        col.operator("measureit_arch.rendersegmentbutton", icon='RENDER_STILL', text= "MeasureIt-ARCH Image")
        col.operator("measureit_arch.render_anim", icon='RENDER_ANIMATION', text= "MeasureIt-ARCH Animation")
        col = layout.column()

        col.prop(scene, "measureit_arch_render", text="Save Render to Output")
        #col.prop(scene, "measureit_arch_use_depth_clipping")

# -------------------------------------------------------------
# Defines button for render option
#
# -------------------------------------------------------------

class RenderSegmentButton(Operator):
    bl_idname = "measureit_arch.rendersegmentbutton"
    bl_label = "Render"
    bl_description = "Create a render image with measures. Use UV/Image editor to view image generated"
    bl_category = 'MeasureitArch'
    tag: IntProperty()

    # ------------------------------
    # Execute button action
    # ------------------------------
    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def execute(self, context):
        scene = context.scene
        msg = "New image created with measures. Open it in UV/image editor"
        camera_msg = "Unable to render. No camera found"
        # -----------------------------
        # Check camera
        # -----------------------------
        if scene.camera is None:
            self.report({'ERROR'}, camera_msg)
            return {'FINISHED'}
        # -----------------------------
        # Use default render
        # -----------------------------

        print("MeasureIt-ARCH: Rendering image")
        #bpy.ops.render.render()
        if render_main(self, context) is True:
            self.report({'INFO'}, msg)

        
        return {'FINISHED'}

    # ---------------------
    # Set cameraView
    # ---------------------
    # noinspection PyMethodMayBeStatic
    def set_camera_view(self):
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces[0].region_3d.view_perspective = 'CAMERA'

    # -------------------------------------
    # Set only render status
    # -------------------------------------
    # noinspection PyMethodMayBeStatic
    def set_only_render(self, status):
        screen = bpy.context.screen

        v3d = False
        s = None
        # get spaceview_3d in current screen
        for a in screen.areas:
            if a.type == 'VIEW_3D':
                for s in a.spaces:
                    if s.type == 'VIEW_3D':
                        v3d = s
                        break

        if v3d is not False:
            s.show_only_render = status

class MeasureitRenderAnim(bpy.types.Operator):
    """Operator which runs its self from a timer"""
    bl_idname = "measureit_arch.render_anim"
    bl_label = "Render Measureit-ARCH animation"

    _timer = None
    _updating = False
    view3d = None 

    def modal(self, context, event):
        scene = context.scene
        wm = context.window_manager
        
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}
            
        if event.type == 'TIMER' and not self._updating:
            self._updating=True
            if scene.frame_current <= scene.frame_end:
                scene.frame_set(scene.frame_current)
                self.view3d.tag_redraw()      
                print("MeasureIt-ARCH: Rendering frame: " + str(scene.frame_current))
                render_main(self, context, True)
                self._updating = False
                scene.frame_current += 1
            else:
                self.cancel(context)
                return {'CANCELLED'}

        self.view3d.tag_redraw() 
        return {'PASS_THROUGH'}
                
    def execute(self, context):
        scene = context.scene
        msg = "New image created with measures. Open it in UV/image editor"
        camera_msg = "Unable to render. No camera found"
        # -----------------------------
        # Check camera
        # -----------------------------
        if scene.camera is None:
            self.report({'ERROR'}, camera_msg)
            return {'FINISHED'}

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                self.view3d = area
        
        if self.view3d == None:
            self.report({'ERROR'}, 'A 3D Viewport must be open to render MeasureIt-ARCH Animations')
            self.cancel(context)
            return {'CANCELLED'}

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        scene.frame_current = scene.frame_start
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        return {'CANCELLED'}


# -------------------------------------------------------------
# Render image main entry point
#
# -------------------------------------------------------------
def render_main(self, context, animation=False):

    # Save old info
    scene = context.scene
    scene.measureit_arch_is_render_draw = True
    bgl.glEnable(bgl.GL_MULTISAMPLE)
    settings = bpy.context.scene.render.image_settings
    depth = settings.color_depth
    settings.color_depth = '16'

    
    clipdepth = context.scene.camera.data.clip_end
    path = scene.render.filepath
    objlist = context.view_layer.objects

    # --------------------
    # Get resolution
    # --------------------

    render_scale = scene.render.resolution_percentage / 100
    width = int(scene.render.resolution_x * render_scale)
    height = int(scene.render.resolution_y * render_scale)


    # --------------------------------------
    # Draw all lines in Offsecreen
    # --------------------------------------
    offscreen = gpu.types.GPUOffScreen(width, height)
    
    view_matrix = Matrix([
        [2 / width, 0, 0, -1],
        [0, 2 / height, 0, -1],
        [0, 0, 1, 0],
        [0, 0, 0, 1]])

    view_matrix_3d = scene.camera.matrix_world.inverted()
    projection_matrix = scene.camera.calc_matrix_camera(context.view_layer.depsgraph, x=width, y=height)
    
    with offscreen.bind():
        # Clear Depth Buffer, set Clear Depth to Cameras Clip Distance
        bgl.glClear(bgl.GL_DEPTH_BUFFER_BIT)
        bgl.glClearDepth(clipdepth)
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        bgl.glDepthFunc(bgl.GL_LESS)  

        gpu.matrix.reset()
        gpu.matrix.load_matrix(view_matrix_3d)
        gpu.matrix.load_projection_matrix(projection_matrix)

        draw_scene(self, context, projection_matrix) 

        
        # Clear Color Keep on depth info
        bgl.glClear(bgl.GL_COLOR_BUFFER_BIT)

        # -----------------------------
        # Loop to draw all objects
        # -----------------------------
        for myobj in objlist:
            if myobj.visible_get() is True:
                mat = myobj.matrix_world
                if 'DimensionGenerator' in myobj:
                    measureGen = myobj.DimensionGenerator[0]
                    if 'alignedDimensions' in measureGen:
                        for linDim in measureGen.alignedDimensions:
                            draw_alignedDimension(context, myobj, measureGen,linDim,mat)
                    if 'angleDimensions' in measureGen:
                        for dim in measureGen.angleDimensions:
                            draw_angleDimension(context, myobj, measureGen,dim,mat)
                    if 'axisDimensions' in measureGen:
                        for dim in measureGen.axisDimensions:
                            draw_axisDimension(context, myobj, measureGen,dim,mat)

                if 'LineGenerator' in myobj:
                    # Set 3D Projection Martix
                    gpu.matrix.reset()
                    gpu.matrix.load_matrix(view_matrix_3d)
                    gpu.matrix.load_projection_matrix(projection_matrix)

                    # Draw Line Groups
                    op = myobj.LineGenerator[0]
                    draw_line_group(context, myobj, op, mat)
             
                if 'AnnotationGenerator' in myobj:
                    # Set 3D Projection Martix
                    gpu.matrix.reset()
                    gpu.matrix.load_matrix(view_matrix_3d)
                    gpu.matrix.load_projection_matrix(projection_matrix)

                    # Draw Line Groups
                    op = myobj.AnnotationGenerator[0]
                    draw_annotation(context, myobj, op, mat)                
       
        # Draw Instance 
        deps = bpy.context.view_layer.depsgraph
        for obj_int in deps.object_instances:
            if obj_int.is_instance:
                myobj = obj_int.object
                mat = obj_int.matrix_world

                if 'LineGenerator' in myobj:
                    lineGen = myobj.LineGenerator[0]
                    draw_line_group(context,myobj,lineGen,mat)
                
                if scene.measureit_arch_inst_dims:
                    if 'AnnotationGenerator' in myobj:
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
        
        # -----------------------------
        # Draw a rectangle frame
        # -----------------------------
        if scene.measureit_arch_rf is True:
            rfcolor = scene.measureit_arch_rf_color
            rfborder = scene.measureit_arch_rf_border
            rfline = scene.measureit_arch_rf_line

            bgl.glLineWidth(rfline)
            x1 = rfborder
            x2 = width - rfborder
            y1 = int(ceil(rfborder / (width / height)))
            y2 = height - y1
            draw_rectangle((x1, y1), (x2, y2))

        buffer = bgl.Buffer(bgl.GL_BYTE, width * height * 4)
        bgl.glReadBuffer(bgl.GL_COLOR_ATTACHMENT0)
        bgl.glReadPixels(0, 0, width, height, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, buffer)
    offscreen.free()

    
    # -----------------------------
    # Create image
    # -----------------------------
    image_name = "measureit_arch_output"
    if image_name not in bpy.data.images:
        bpy.data.images.new(image_name, width, height)

    image = bpy.data.images[image_name]
    image.scale(width, height)
    image.pixels = [v / 255 for v in buffer]

    # Saves image
    if image is not None and (scene.measureit_arch_render is True or animation is True):
        ren_path = bpy.context.scene.render.filepath
        filename = "mit_frame"
        ftxt = "%04d" % scene.frame_current
        outpath = (ren_path + filename + ftxt + ".png")
        save_image(self, outpath, image)

    # restore default value
    settings.color_depth = depth
    scene.measureit_arch_is_render_draw = False

# -------------------------------------
# Save image to file
# -------------------------------------
def save_image(self, filepath, myimage):
    # noinspection PyBroadException
    try:

        # Save old info
        settings = bpy.context.scene.render.image_settings
        myformat = settings.file_format
        mode = settings.color_mode
        depth = settings.color_depth

        # Apply new info and save
        settings.file_format = 'PNG'
        settings.color_mode = "RGBA"
        settings.color_depth = '8'
        myimage.save_render(filepath)
        print("MeasureIt-ARCH: Image " + filepath + " saved")

        # Restore old info
        settings.file_format = myformat
        settings.color_mode = mode
        settings.color_depth = depth
    except:
        print("Unexpected error:" + str(exc_info()))
        self.report({'ERROR'}, "MeasureIt-ARCH: Unable to save render image")
        return


#--------------------------------------
# Draw Scene Geometry for Depth Buffer
#--------------------------------------

def draw_scene(self, context, projection_matrix):
    bgl.glEnable(bgl.GL_DEPTH_TEST)
    bgl.glDepthFunc(bgl.GL_LESS)   

    # Get List of Mesh Objects
    objs = []
    deps = bpy.context.view_layer.depsgraph
    for obj_int in deps.object_instances:
        obj = obj_int.object
        if obj.type == 'MESH' and obj.hide_render == False :

            mat = obj_int.matrix_world
            obj_eval = obj.evaluated_get(deps)
            mesh = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=bpy.context.view_layer.depsgraph)
            mesh.calc_loop_triangles()
            tris = mesh.loop_triangles
            vertices = []
            indices = []

            for vert in mesh.vertices:
                # Multipy vertex Position by Object Transform Matrix
                vertices.append(mat @ vert.co)

            for tri in tris:
                indices.append(tri.vertices)      

            #shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
            shader = gpu.types.GPUShader(Base_Shader_3D.vertex_shader, DepthOnlyFrag.fragment_shader)
            batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
            batch.program_set(shader)
            batch.draw()
            gpu.shader.unbind()
            obj_eval.to_mesh_clear()

    #Write to Image for Debug
    debug=False
    if debug:
        scene = context.scene
        render_scale = scene.render.resolution_percentage / 100
        width = int(scene.render.resolution_x * render_scale)
        height = int(scene.render.resolution_y * render_scale)

        buffer = bgl.Buffer(bgl.GL_BYTE, width * height * 4)
        bgl.glReadBuffer(bgl.GL_COLOR_ATTACHMENT0)
        bgl.glReadPixels(0, 0, width, height, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, buffer)

        image_name = "measureit_arch_depth"
        if image_name not in bpy.data.images:
            bpy.data.images.new(image_name, width, height)

        image = bpy.data.images[image_name]
        image.scale(width, height)
        image.pixels = [v / 255 for v in buffer]

    bgl.glDisable(bgl.GL_DEPTH_TEST)