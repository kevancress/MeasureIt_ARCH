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
import os

import blf
from os import path, remove
from sys import exc_info
import svgwrite

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
from .measureit_arch_main import draw_main, draw_main_3d, draw_titleblock
from bpy.props import IntProperty
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D
depthOnlyshader = gpu.types.GPUShader(Base_Shader_3D.vertex_shader, DepthOnlyFrag.fragment_shader)

global svg

# ------------------------------------------------------------------
# Define panel class for render functions.
# ------------------------------------------------------------------
class RENDER_PT_MeasureitArch_Panel(Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"
    bl_options = {'HIDE_HEADER'}
    bl_label = "MeasureIt_ARCH Render"

    #bl_idname = "measureit_arch_render_panel"
    #bl_label = "MeasureIt_ARCH Render"
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
        sceneProps = scene.MeasureItArchProps

        # Render settings
        col = layout.column()
        col.label(text="MeasureIt_ARCH Render")
        col = layout.column(align=True)
        col.scale_y = 1.5
        col.operator("measureit_arch.render_image", icon='RENDER_STILL', text= "MeasureIt_ARCH Image")
        col.operator("measureit_arch.render_anim", icon='RENDER_ANIMATION', text= "MeasureIt_ARCH Animation")
        col.operator("measureit_arch.rendersvgbutton", icon='DOCUMENTS', text= "MeasureIt_ARCH Vector")
        if sceneProps.enable_experimental:
            col = layout.column()
            col.prop(sceneProps, "vector_depthtest", text="Use Vector DepthTest")
        col = layout.column()
        
        col.prop(sceneProps, "embed_scene_render", text="Embed Scene Render")
        #col.prop(sceneProps, "measureit_arch_render", text="Save Render to Output")


# -------------------------------------------------------------
# Defines button for render option
#
# -------------------------------------------------------------

class RenderSegmentButton(Operator):
    bl_idname = "measureit_arch.render_image"
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

        print("MeasureIt_ARCH: Rendering image")
        #bpy.ops.render.render()
        render_result = render_main(self, context)
        #render_result = [True, 0]
        if render_result[0] is True:
            self.report({'INFO'}, msg)
        del render_result

        return {'FINISHED'}


class MeasureitRenderAnim(bpy.types.Operator):
    """Operator which runs its self from a timer"""
    bl_idname = "measureit_arch.render_anim"
    bl_label = "Render MeasureIt_ARCH animation"

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
                print("MeasureIt_ARCH: Rendering frame: " + str(scene.frame_current))
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
            self.report({'ERROR'}, 'A 3D Viewport must be open to render MeasureIt_ARCH Animations')
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


class RenderSvgButton(Operator):
    bl_idname = "measureit_arch.rendersvgbutton"
    bl_label = "Render"
    bl_description = "WARNING: EXPERIMENTAL - Create a Vector Drawing. Saved to Render output path"
    bl_category = 'MeasureitArch'
    tag: IntProperty()

    # ------------------------------
    # Execute button action
    # ------------------------------
    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def execute(self, context):
        scene = context.scene
        msg = "New Svg created with measures. Saved to Output Path"
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

        print("MeasureIt_ARCH: Rendering image")
        #bpy.ops.render.render()
        if render_main_svg(self, context) is True:
            self.report({'INFO'}, msg)

        return {'FINISHED'}



# -------------------------------------------------------------
# Render image main entry point
#
# -------------------------------------------------------------
def render_main(self, context, animation=False):

    scene = context.scene
    sceneProps= scene.MeasureItArchProps
    sceneProps.is_render_draw = True

    clipdepth = context.scene.camera.data.clip_end
    objlist = context.view_layer.objects


    # Get resolution
    render_scale = scene.render.resolution_percentage / 100
    width = int(scene.render.resolution_x * render_scale)
    height = int(scene.render.resolution_y * render_scale)


    # Draw all lines in Offsecreen
    renderoffscreen = gpu.types.GPUOffScreen(width, height)
    
    view_matrix_3d = scene.camera.matrix_world.inverted()
    projection_matrix = scene.camera.calc_matrix_camera(context.view_layer.depsgraph, x=width, y=height)

    set_OpenGL_Settings(True)
    with renderoffscreen.bind():

        # Clear Depth Buffer, set Clear Depth to Cameras Clip Distance
        bgl.glClear(bgl.GL_DEPTH_BUFFER_BIT)
        bgl.glClearDepth(clipdepth) 

        gpu.matrix.reset()
        gpu.matrix.load_matrix(view_matrix_3d)
        gpu.matrix.load_projection_matrix(projection_matrix)


        # Draw Scene for the depth buffer
        draw_scene(self, context, projection_matrix) 

        
        # Clear Color Buffer, we only need the depth info
        bgl.glClearColor(0,0,0,0)
        bgl.glClear(bgl.GL_COLOR_BUFFER_BIT)

        # -----------------------------
        # Loop to draw all objects
        # -----------------------------
        draw3d_loop(context,objlist)
        draw_titleblock(context)
        
        buffer = bgl.Buffer(bgl.GL_BYTE, width * height * 4)
        bgl.glReadBuffer(bgl.GL_COLOR_ATTACHMENT0)
        bgl.glReadPixels(0, 0, width, height, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, buffer)
    

    # -----------------------------
    # Create image
    # -----------------------------
    image_name = "measureit_arch_output"
    if image_name not in bpy.data.images:
        image = bpy.data.images.new(image_name, width, height)

    image = bpy.data.images[image_name]

    image.scale(width, height)
    image.pixels = [v / 255 for v in buffer]

    renderoffscreen.free()
    # Saves image
    if image is not None and animation is True:
        ren_path = bpy.context.scene.render.filepath
        filename = "mit_frame"
        ftxt = "%04d" % scene.frame_current
        outpath = (ren_path + filename + ftxt + '.png')
        save_image(self, outpath, image)

    # restore default value
    set_OpenGL_Settings(False)
    sceneProps.is_render_draw = False
    return True, buffer
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
        settings.color_depth = '16'
        myimage.save_render(filepath)
        print("MeasureIt_ARCH: Image " + filepath + " saved")

        # Restore old info
        settings.file_format = myformat
        settings.color_mode = mode
        settings.color_depth = depth
    except:
        print("Unexpected error:" + str(exc_info()))
        self.report({'ERROR'}, "MeasureIt_ARCH: Unable to save render image")
        return

#--------------------------------------
# Draw Scene Geometry for Depth Buffer
#--------------------------------------

def draw_scene(self, context, projection_matrix):

    set_OpenGL_Settings(True)
    # Get List of Mesh Objects
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

           
            batch = batch_for_shader(depthOnlyshader, 'TRIS', {"pos": vertices}, indices=indices)
            batch.program_set(depthOnlyshader)
            batch.draw()
            obj_eval.to_mesh_clear()
            gpu.shader.unbind()

    #Write to Image for Debug
    debug=False
    if debug:
        scene = context.scene
        render_scale = scene.render.resolution_percentage / 100
        width = int(scene.render.resolution_x * render_scale)
        height = int(scene.render.resolution_y * render_scale)

        buffer = bgl.Buffer(bgl.GL_BYTE, width * height * 4)
        bgl.glReadBuffer(bgl.COLOR_ATTACHMENT0)
        bgl.glReadPixels(0, 0, width, height, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, buffer)

        image_name = "measureit_arch_depth"
        if image_name not in bpy.data.images:
            bpy.data.images.new(image_name, width, height)

        image = bpy.data.images[image_name]
        image.scale(width, height)
        image.pixels = [v / 255 for v in buffer]

    set_OpenGL_Settings(False)

def render_main_svg(self, context, animation=False):

    # Save old info
    scene = context.scene
    sceneProps= scene.MeasureItArchProps
    sceneProps.is_render_draw = True
    sceneProps.is_vector_draw = True

    clipdepth = context.scene.camera.data.clip_end
    path = bpy.path.abspath(scene.render.filepath)
    objlist = context.view_layer.objects

    # --------------------
    # Get resolution
    # --------------------

    render_scale = scene.render.resolution_percentage / 100
    width = int(scene.render.resolution_x * render_scale)
    height = int(scene.render.resolution_y * render_scale)
    
    offscreen = gpu.types.GPUOffScreen(width, height)
    
    view_matrix_3d = scene.camera.matrix_world.inverted()
    projection_matrix = scene.camera.calc_matrix_camera(context.view_layer.depsgraph, x=width, y=height)

    # Render Depth Buffer
    print("Rendering Depth Buffer")
    if sceneProps.vector_depthtest:
        with offscreen.bind():
            # Clear Depth Buffer, set Clear Depth to Cameras Clip Distance
            set_OpenGL_Settings(True)
            bgl.glClear(bgl.GL_DEPTH_BUFFER_BIT)
            bgl.glClearDepth(clipdepth)
            bgl.glEnable(bgl.GL_DEPTH_TEST)
            bgl.glDepthFunc(bgl.GL_LEQUAL)  

            gpu.matrix.reset()
            gpu.matrix.load_matrix(view_matrix_3d)
            gpu.matrix.load_projection_matrix(projection_matrix)

            texture_buffer = bgl.Buffer(bgl.GL_FLOAT, width * height)

            draw_scene(self, context, projection_matrix) 

            bgl.glReadBuffer(bgl.GL_BACK)
            bgl.glReadPixels(0, 0, width, height, bgl.GL_DEPTH_COMPONENT, bgl.GL_FLOAT, texture_buffer)

            if 'depthbuffer' in sceneProps:
                del sceneProps['depthbuffer']
            sceneProps['depthbuffer'] = texture_buffer
        offscreen.free()
        set_OpenGL_Settings(False)

        if False:
            imageName = 'depthBufferTest'
            if not imageName in bpy.data.images:
                bpy.data.images.new(imageName, width, height, alpha=False, float_buffer=True, is_data=True)
            image = bpy.data.images[imageName]

            image.scale(width, height)
            image.pixels = [v for v in texture_buffer]



    # Setup Output Path
    ren_path = path
    filename = "mit_vector"
    ftxt = "%04d" % scene.frame_current
    outpath = (ren_path + filename + ftxt + '.svg')

    view = get_view()

    paperWidth = width / sceneProps.default_resolution
    paperHeight = height / sceneProps.default_resolution

    try:
        if view.res_type == 'res_type_paper':
            paperWidth = round(view.width * 39.370078740196853, 3)
            paperHeight = round(view.height * 39.370078740196853, 3)
    except:
        print('No View Present, using default resolution')

    # Setup basic svg
    svg = svgwrite.Drawing(
            outpath,
            debug=False,
            size=('{}in'.format(paperWidth), '{}in'.format(paperHeight)),
            viewBox=('0 0 {} {}'.format(width,height)),
            id='root',
        )



    if sceneProps.embed_scene_render:
        lastformat = scene.render.image_settings.file_format
        scene.render.image_settings.file_format = 'PNG'
        scene.render.use_file_extension = True
        bpy.ops.render.render(write_still=True)

        image_path = bpy.context.scene.render.filepath
        svg.add(svg.image(
            os.path.basename(image_path + '.png'), **{
            'width': width,
            'height': height
            }
        ))

        scene.render.image_settings.file_format = lastformat
        

    # -----------------------------
    # Loop to draw all objects
    # -----------------------------
    draw3d_loop(context,objlist,svg=svg)
    draw_titleblock(context,svg=svg)

 

    svg.save(pretty=True)
    # restore default value
    sceneProps.is_render_draw = False
    sceneProps.is_vector_draw = False
    return True
