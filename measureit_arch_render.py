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
from bpy.props import IntProperty
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D
# ------------------------------------------------------------------
# Define panel class for render functions.
# ------------------------------------------------------------------
class MeasureitArchRenderPanel(Panel):
    bl_idname = "measureit_arch_render_panel"
    bl_label = "MeasureIt-ARCH Render"
    bl_space_type = 'PROPERTIES'
    bl_region_type = "WINDOW"
    bl_context = "render"

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


        col.operator("measureit_arch.rendersegmentbutton", icon='RENDER_STILL')
        col.prop(scene, "measureit_arch_render_type")

        col.prop(scene, "measureit_arch_render", text="Save render image")
        col.prop(scene, "measureit_arch_use_depth_clipping")
        col.prop(scene, "measureit_arch_rf", text="Border")

        if scene.measureit_arch_rf is True:
            col.prop(scene, "measureit_arch_rf_color", text="Color")
            col.prop(scene, "measureit_arch_rf_border", text="Space")
            col.prop(scene, "measureit_arch_rf_line", text="Width")

# -------------------------------------------------------------
# Defines button for render option
#
# -------------------------------------------------------------


class RenderSegmentButton(Operator):
    bl_idname = "measureit_arch.rendersegmentbutton"
    bl_label = "Render"
    bl_description = "Create a render image with measures. Use UV/Image editor to view image generated"
    bl_category = 'MeasureitArch'
    tag = IntProperty()

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
        if scene.measureit_arch_render_type == "1":
            # noinspection PyBroadException
            try:
                result = bpy.data.images['Render Result']
                bpy.ops.render.render()
            except:
                bpy.ops.render.render()
            print("MeasureIt-ARCH: Using current render image on buffer")
            if render_main(self, context) is True:
                self.report({'INFO'}, msg)

        # -----------------------------
        # OpenGL image
        # -----------------------------
        if scene.measureit_arch_render_type == "2":
            self.set_camera_view()
            self.set_only_render(True)

            print("MeasureIt-ARCH: Rendering opengl image")
            bpy.ops.render.opengl()
            if render_main(self, context) is True:
                self.report({'INFO'}, msg)

            self.set_only_render(False)

        # -----------------------------
        # OpenGL Animation
        # -----------------------------
        if scene.measureit_arch_render_type == "3":
            oldframe = scene.frame_current
            self.set_camera_view()
            self.set_only_render(True)
            flag = False
            # loop frames
            for frm in range(scene.frame_start, scene.frame_end + 1):
                scene.frame_set(frm)
                print("MeasureIt-ARCH: Rendering opengl frame %04d" % frm)
                bpy.ops.render.opengl()
                #flag = render_main(self, context, True)
                #if flag is False:
                #    break

            self.set_only_render(False)
            scene.frame_current = oldframe
            if flag is True:
                self.report({'INFO'}, msg)

        # -----------------------------
        # Image
        # -----------------------------
        if scene.measureit_arch_render_type == "4":
            print("MeasureIt-ARCH: Rendering image")
            bpy.ops.render.render()
            if render_main(self, context) is True:
                self.report({'INFO'}, msg)

        # -----------------------------
        # Animation
        # -----------------------------
        if scene.measureit_arch_render_type == "5":
            oldframe = scene.frame_current
            flag = False
            # loop frames
            for frm in range(scene.frame_start, scene.frame_end + 1):
                scene.frame_set(frm)
                print("MeasureIt-ARCH: Rendering frame: " + str(frm))
                #bpy.ops.render.render()
                render_main(self, context, True)
                #if flag is False:
                #   break

            #scene.frame_current = oldframe
            #if flag is True:
            #    self.report({'INFO'}, msg)

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


# -------------------------------------------------------------
# Render image main entry point
#
# -------------------------------------------------------------
def render_main(self, context, animation=False):

    # Save old info
    bgl.glEnable(bgl.GL_MULTISAMPLE)
    settings = bpy.context.scene.render.image_settings
    depth = settings.color_depth
    settings.color_depth = '16'

    scene = context.scene
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
    projection_matrix = scene.camera.calc_matrix_camera(context.depsgraph, x=width, y=height)

    with offscreen.bind():
        # Clear Depth Buffer, set Clear Depth to Cameras Clip Distance
        bgl.glClearDepth(clipdepth)
        bgl.glClear(bgl.GL_DEPTH_BUFFER_BIT)

        # Draw Scene If Necessary
        if scene.measureit_arch_use_depth_clipping is True:
            draw_scene(self, context, projection_matrix) 
        
        # Clear Color Keep on depth info
        bgl.glClear(bgl.GL_COLOR_BUFFER_BIT)

        # -----------------------------
        # Loop to draw all objects
        # -----------------------------
        for myobj in objlist:
            if myobj.visible_get() is True:
                if 'DimensionGenerator' in myobj:
                    measureGen = myobj.DimensionGenerator[0]
                    for linDim in measureGen.alignedDimensions:
                        draw_alignedDimension(context, myobj, measureGen,linDim)
                    for dim in measureGen.angleDimensions:
                        draw_angleDimension(context, myobj, measureGen,dim)

                if 'LineGenerator' in myobj:
                    # Set 3D Projection Martix
                    gpu.matrix.reset()
                    gpu.matrix.load_matrix(view_matrix_3d)
                    gpu.matrix.load_projection_matrix(projection_matrix)

                    # Draw Line Groups
                    op = myobj.LineGenerator[0]
                    draw_line_group(context, myobj, op)
             
                if 'AnnotationGenerator' in myobj:
                    # Set 3D Projection Martix
                    gpu.matrix.reset()
                    gpu.matrix.load_matrix(view_matrix_3d)
                    gpu.matrix.load_projection_matrix(projection_matrix)

                    # Draw Line Groups
                    op = myobj.AnnotationGenerator[0]
                    draw_annotation(context, myobj, op)                

        # -----------------------------
        # Loop to draw all debug
        # -----------------------------
        if scene.measureit_arch_debug is True:
            selobj = bpy.context.selected_objects
            for myobj in selobj:
                if scene.measureit_arch_debug_objects is True:
                    draw_object(context, myobj, None, None)
                elif scene.measureit_arch_debug_object_loc is True:
                    draw_object(context, myobj, None, None)
                if scene.measureit_arch_debug_vertices is True:
                    draw_vertices(context, myobj, None, None)
                elif scene.measureit_arch_debug_vert_loc is True:
                    draw_vertices(context, myobj, None, None)
                if scene.measureit_arch_debug_edges is True:
                    draw_edges(context, myobj, None, None)
                if scene.measureit_arch_debug_faces is True or scene.measureit_arch_debug_normals is True:
                    draw_faces(context, myobj, None, None)
        
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
    
    # Get List of Mesh Objects
    objs = []
    for obj in context.view_layer.objects:
            if obj.type == 'MESH':
                objs.append(obj)

    # get 3D view matrix
    view_matrix_3d = context.scene.camera.matrix_world.inverted()

    # Get Vertices and Indices of Objects
    for obj in objs:
        mesh = obj.data
        bm = bmesh.new()
        bm.from_object(obj, context.depsgraph, deform=True)
        mesh.calc_loop_triangles()
        vertices = []
        indices = np.empty((len(mesh.loop_triangles), 3), 'i')

        for vert in bm.verts:
            # Multipy vertex Position by Object Transform Matrix
            vertices.append(obj.matrix_world @ vert.co)

        # get Indices
        mesh.loop_triangles.foreach_get(
            "vertices", np.reshape(indices, len(mesh.loop_triangles) * 3))            

        #---------------
        # Draw
        #---------------
        
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        bgl.glDepthFunc(bgl.GL_LESS)   

        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        #shader = gpu.types.GPUShader(Base_Shader_3D.vertex_shader, DepthOnlyFrag.fragment_shader)
        batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)

        gpu.matrix.reset()
        gpu.matrix.load_matrix(view_matrix_3d)
        gpu.matrix.load_projection_matrix(projection_matrix)

        batch.draw(shader)
        bgl.glDisable(bgl.GL_DEPTH_TEST)