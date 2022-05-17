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

from random import randint
import bgl
import bpy
import gpu
import os
from .measureit_arch_baseclass import recalc_index
import svgwrite
import xml.etree.ElementTree as ET
import time
import ezdxf

from addon_utils import check, paths
from bpy.types import Panel, Operator
from sys import exc_info
from datetime import datetime

from . import svg_shaders
from . import vector_utils
from .measureit_arch_geometry import draw3d_loop, batch_for_shader
from .measureit_arch_main import draw_titleblock
from .measureit_arch_utils import get_view, local_attrs, get_loaded_addons, OpenGL_Settings, Set_Render
from .measureit_arch_units import BU_TO_INCHES
from .shaders import Base_Shader_3D, DepthOnlyFrag


depthOnlyshader = gpu.types.GPUShader(
    Base_Shader_3D.vertex_shader, DepthOnlyFrag.fragment_shader)


class RENDER_PT_MeasureitArch_Panel(Panel):
    """ Panel class for render functions """

    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"
    bl_options = {'HIDE_HEADER'}
    bl_label = "MeasureIt_ARCH Render"

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
        col.operator("measureit_arch.renderimagebutton",
                     icon='RENDER_STILL', text="MeasureIt_ARCH Image")
        col.operator("measureit_arch.renderanimbutton",
                     icon='RENDER_ANIMATION', text="MeasureIt_ARCH Animation")
        col.operator("measureit_arch.rendervectorbutton",
                     icon='DOCUMENTS', text="MeasureIt_ARCH Vector")
        
        if sceneProps.show_dxf_props:
            col.operator("measureit_arch.renderdxfbutton",
                     icon='DOCUMENTS', text="MeasureIt_ARCH to DXF")



        if sceneProps.enable_experimental:
            pass


class RenderImageButton(Operator):
    """ Button for render option """

    bl_idname = "measureit_arch.renderimagebutton"
    bl_label = "Render image"
    bl_description = "Render an image with measures. Use UV/Image editor to view image generated."
    bl_category = 'MeasureitArch'

    def execute(self, context):
        # Check camera
        if not context.scene.camera:
            self.report({'ERROR'}, "Unable to render: no camera found!")
            return {'FINISHED'}

        outpath = render_main(self, context)
        if outpath:
            self.report({'INFO'}, "Image exported to: {}".format(outpath))

        return {'FINISHED'}


class RenderAnimationButton(Operator):
    """ Operator which runs itself from a timer """

    bl_idname = "measureit_arch.renderanimbutton"
    bl_label = "Render animation"
    bl_description = "Render an animation, saved to render output path."
    bl_category = 'MeasureitArch'

    _timer = None
    _updating = False
    view3d = None

    def modal(self, context, event):
        scene = context.scene

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER' and not self._updating:
            self._updating = True
            if scene.frame_current <= scene.frame_end:
                scene.frame_set(scene.frame_current)
                self.view3d.tag_redraw()
                print("MeasureIt_ARCH: Rendering frame: " + str(scene.frame_current))
                render_main(self, context)
                self._updating = False
                scene.frame_current += 1
            else:
                self.cancel(context)
                return {'CANCELLED'}

        self.view3d.tag_redraw()
        return {'PASS_THROUGH'}

    def execute(self, context):
        # Check camera
        if not context.scene.camera:
            self.report({'ERROR'}, "Unable to render: no camera found!")
            return {'FINISHED'}

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                self.view3d = area

        if self.view3d is None:
            self.report(
                {'ERROR'}, 'A 3D Viewport must be open to render MeasureIt_ARCH Animations')
            self.cancel(context)
            return {'CANCELLED'}

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        context.scene.frame_current = context.scene.frame_start
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        return {'CANCELLED'}


class RenderVectorButton(Operator):
    bl_idname = "measureit_arch.rendervectorbutton"
    bl_label = "Render vector"
    bl_description = "Create a SVG drawing, saved to render output path."
    bl_category = 'MeasureitArch'

    def execute(self, context):
        # Check camera
        if not context.scene.camera:
            self.report({'ERROR'}, "Unable to render: no camera found!")
            return {'FINISHED'}

        outpath = render_main_svg(self, context)
        self.report({'INFO'}, "SVG exported to: {}".format(outpath))
        return {'FINISHED'}

class RenderDXFButton(Operator):
    bl_idname = "measureit_arch.renderdxfbutton"
    bl_label = "Render to DFX"
    bl_description = "Create a DXF drawing, saved to render output path."
    bl_category = 'MeasureitArch'

    def execute(self, context):
        # Check camera
        if not context.scene.camera:
            self.report({'ERROR'}, "Unable to render: no camera found!")
            return {'FINISHED'}

        outpath = render_main_dxf(self, context)
        self.report({'INFO'}, "DXF exported to: {}".format(outpath))
        return {'FINISHED'}

def render_main(self, context):
    """ Render image main entry point """

    scene = context.scene
    sceneProps = scene.MeasureItArchProps

    with Set_Render(sceneProps):
        clipdepth = context.scene.camera.data.clip_end
        objlist = context.view_layer.objects

        # Get resolution
        render_scale = scene.render.resolution_percentage / 100
        width = int(scene.render.resolution_x * render_scale)
        height = int(scene.render.resolution_y * render_scale)

        # Draw all lines offscreen
        renderoffscreen = gpu.types.GPUOffScreen(width, height)

        view_matrix_3d = scene.camera.matrix_world.inverted()
        projection_matrix = scene.camera.calc_matrix_camera(
            context.view_layer.depsgraph, x=width, y=height)

        with OpenGL_Settings(None):
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
                bgl.glClearColor(0, 0, 0, 0)
                bgl.glClear(bgl.GL_COLOR_BUFFER_BIT)

                # -----------------------------
                # Loop to draw all objects
                # -----------------------------
                draw3d_loop(context, objlist)
                view = get_view()
                dt = view.vector_depthtest
                view.vector_depthtest = False
                draw_titleblock(context)
                view.vector_depthtest = dt

                buffer = bgl.Buffer(bgl.GL_BYTE, width * height * 4)
                bgl.glReadBuffer(bgl.GL_COLOR_ATTACHMENT0)
                bgl.glReadPixels(0, 0, width, height, bgl.GL_RGBA,
                                bgl.GL_UNSIGNED_BYTE, buffer)

            # Create image
            image_name = "measureit_arch_output"
            if image_name not in bpy.data.images:
                image = bpy.data.images.new(image_name, width, height)

            image = bpy.data.images[image_name]
            image.scale(width, height)
            image.pixels = [v / 255 for v in buffer]

            renderoffscreen.free()

            # Save image
            outpath = None
            if image is not None:
                view = get_view()
                outpath = get_view_outpath(
                    scene, view, "{:04d}.png".format(scene.frame_current))
                save_image(self, outpath, image)

        # Restore default value
        sceneProps.is_render_draw = False
    return outpath


def get_view_outpath(scene, view, suffix):
    if view.output_path:
        filenameStr =  "{}_{}".format(view.view_num, view.name)
        outpath = os.path.join(view.output_path, filenameStr)
    else:
        outpath = scene.render.filepath
    filepath = "{}_{}".format(bpy.path.abspath(outpath), suffix)
    
    dir, filename = os.path.split(filepath)
    if not os.path.exists(dir):
        os.mkdir(dir)

    if view.date_folder:
        today = datetime.now()
        datedir = os.path.join(dir, today.strftime('%Y%m%d'))
        if not os.path.exists(datedir):
            os.mkdir(datedir)
        return os.path.join(datedir, filename)
    return filepath


def save_image(self, filepath, image):
    """ Save image to file """
    try:
        settings = bpy.context.scene.render.image_settings
        with local_attrs(settings, [
                'file_format',
                'color_mode',
                'color_depth']):
            settings.file_format = 'PNG'
            settings.color_mode = 'RGBA'
            settings.color_depth = '16'
            image.save_render(filepath)
            self.report({'INFO'}, "Image exported to: {}".format(filepath))
    except:
        print("Unexpected error:" + str(exc_info()))
        self.report({'ERROR'}, "MeasureIt_ARCH: Unable to save render image")


def draw_scene(self, context, projection_matrix):
    """ Draw Scene Geometry for Depth Buffer """

    with OpenGL_Settings(None):
        # Get List of Mesh Objects
        deps = bpy.context.view_layer.depsgraph
        num_instances = len(deps.object_instances)
        idx = 0
        vertices = []
        indices = []
  
        for obj_int in deps.object_instances:
            idx += 1 
            #print("Rendering Obj {} of {} to Depth Buffer".format(idx,num_instances))
            obj = obj_int.object
            if obj.type == 'MESH' and not(obj.hide_render or obj.display_type == "WIRE" or obj.MeasureItArchProps.ignore_in_depth_test):
                mat = obj_int.matrix_world
                obj_eval = obj.evaluated_get(deps)
                mesh = obj_eval.to_mesh(
                    preserve_all_data_layers=False, depsgraph=bpy.context.view_layer.depsgraph)
                mesh.calc_loop_triangles()
                tris = mesh.loop_triangles
       
                
                vertices = [mat @ vert.co for vert in mesh.vertices]
                indices = [[tri.vertices[0],tri.vertices[1],tri.vertices[2]] for tri in tris]

                #for vert in mesh.vertices:
                    # Multipy vertex Position by Object Transform Matrix
                #    vertices.append(mat @ vert.co)

                #for tri in tris:
                #    indices.append([tri.vertices[0],tri.vertices[1],tri.vertices[2]])

                obj_eval.to_mesh_clear()

            batch = batch_for_shader(depthOnlyshader, 'TRIS', {
                                    "pos": vertices}, indices=indices)
            batch.program_set(depthOnlyshader)
            batch.draw()
            gpu.shader.unbind()

        # Write to Image for Debug
        debug = False
        if debug:
            print("Reading Buffer to Image")
            scene = context.scene
            render_scale = scene.render.resolution_percentage / 100
            width = int(scene.render.resolution_x * render_scale)
            height = int(scene.render.resolution_y * render_scale)

            buffer = bgl.Buffer(bgl.GL_BYTE, width * height * 4)
            bgl.glReadBuffer(bgl.GL_COLOR_ATTACHMENT0)
            bgl.glReadPixels(0, 0, width, height, bgl.GL_RGBA,
                            bgl.GL_UNSIGNED_BYTE, buffer)

            image_name = "measureit_arch_depth"
            if image_name not in bpy.data.images:
                bpy.data.images.new(image_name, width, height)

            image = bpy.data.images[image_name]
            image.scale(width, height)
            image.pixels = [v / 255 for v in buffer]


def render_main_svg(self, context):
    startTime = time.time()
    scene = context.scene
    sceneProps = scene.MeasureItArchProps
    view = get_view()

    with Set_Render(sceneProps, is_vector = True):
        vector_utils.clear_db()
        

        clipdepth = context.scene.camera.data.clip_end
        objlist = context.view_layer.objects

        # Get resolution
        render_scale = scene.render.resolution_percentage / 100
        width = int(scene.render.resolution_x * render_scale)
        height = int(scene.render.resolution_y * render_scale)


        view_matrix_3d = scene.camera.matrix_world.inverted()
        # Render Depth Buffer

        if view.vector_depthtest:
            print("Rendering Depth Buffer")
            offscreen = gpu.types.GPUOffScreen(width, height)
            with offscreen.bind():
                # Clear Depth Buffer, set Clear Depth to Cameras Clip Distance
                deps = context.evaluated_depsgraph_get()
                projection_matrix = scene.camera.calc_matrix_camera(deps, x=width, y=height)
                with OpenGL_Settings(None):
                    bgl.glClear(bgl.GL_DEPTH_BUFFER_BIT)
                    bgl.glClearDepth(clipdepth)
                    bgl.glEnable(bgl.GL_DEPTH_TEST)
                    bgl.glDepthFunc(bgl.GL_LEQUAL)

                    gpu.matrix.reset()
                    gpu.matrix.load_matrix(view_matrix_3d)
                    gpu.matrix.load_projection_matrix(projection_matrix)

                    texture_buffer = bgl.Buffer(bgl.GL_FLOAT, width * height)
                    print("Drawing Scene")
                    draw_scene(self, context, projection_matrix)
                    
                    print("Reading to Buffer")
                    bgl.glReadBuffer(bgl.GL_BACK)
                    bgl.glReadPixels(
                        0, 0, width, height, bgl.GL_DEPTH_COMPONENT, bgl.GL_FLOAT, texture_buffer)

                    if 'depthbuffer' in sceneProps:
                        del sceneProps['depthbuffer']
                    sceneProps['depthbuffer'] = texture_buffer

        vector_utils.set_globals()
            # imageName = 'depthBufferTest'
            # if imageName not in bpy.data.images:
            #     bpy.data.images.new(imageName, width, height,
            #                         alpha=False, float_buffer=True, is_data=True)
            # image = bpy.data.images[imageName]

            # image.scale(width, height)
            # image.pixels = [v for v in texture_buffer]

        # Setup Output Path
        view = get_view()
        outpath = get_view_outpath(
            scene, view, "{:04d}.svg".format(scene.frame_current))

        if view and view.res_type == 'res_type_paper':
            paperWidth = round(view.width * BU_TO_INCHES, 3)
            paperHeight = round(view.height * BU_TO_INCHES, 3)
        else:
            print('No View Present, using default resolution')
            paperWidth = width / sceneProps.default_resolution
            paperHeight = height / sceneProps.default_resolution

        # Setup basic svg
        svg = svgwrite.Drawing(
            outpath,
            debug=False,
            size=('{}in'.format(paperWidth), '{}in'.format(paperHeight)),
            viewBox=('0 0 {} {}'.format(width, height)),
            id='root',
        )

        view = get_view()
        if view.embed_scene_render:
            with local_attrs(scene, [
                    'render.image_settings.file_format',
                    'render.use_file_extension',
                    'render.filepath']):

                image_path = get_view_outpath(
                    scene, view, "{:04d}.svg".format(scene.frame_current))
                scene.render.filepath =  image_path
                scene.render.image_settings.file_format = 'PNG'
                scene.render.use_file_extension = True
                bpy.ops.render.render(write_still=True)

                png_image_path = os.path.basename("{}.png".format(image_path))
                svg.add(svg.image(
                    png_image_path, **{
                        'width': width,
                        'height': height
                    }
                ))


        ## Freestyle Embed
        freestyle_svg_export = 'render_freestyle_svg' in get_loaded_addons()
        if view.embed_freestyle_svg and freestyle_svg_export:
            # If "FreeStyle SVG export" addon is loaded, we render the scene to SVG
            # and embed the output in the final SVG.

            svg_image_path = get_view_outpath(
                scene, view, "{}".format("_freestyle"))

            with local_attrs(scene, [
                    'render.filepath',
                    'render.image_settings.file_format',
                    'render.use_freestyle',
                    'svg_export.use_svg_export',
                    'svg_export.mode']):

                scene.render.use_freestyle = True
                scene.svg_export.use_svg_export = True
                scene.svg_export.mode = 'FRAME'
                scene.render.filepath = svg_image_path
                scene.render.image_settings.file_format = 'PNG'
                scene.render.use_file_extension = True
                bpy.ops.render.render(write_still=False)


                frame = scene.frame_current
                svg_image_path += "{:04d}.svg".format(frame)
                svg_root = ET.parse(svg_image_path).getroot()
                for elem in svg_root:
                    svg.add(SVGWriteElement(elem))

                if (os.path.exists(svg_image_path) and
                    not sceneProps.keep_freestyle_svg):
                    os.remove(svg_image_path)

        ## Greasepencil Embed
        if view.embed_greasepencil_svg:

            image_path = get_view_outpath(
                scene, view, "{:04d}.svg".format(scene.frame_current))
            frame = scene.frame_current
            gp_image_path = image_path + "_Grease_Pencil"

            bpy.ops.wm.gpencil_export_svg(filepath= gp_image_path,
                        check_existing=True,
                        filemode=8,
                        display_type='DEFAULT',
                        sort_method='FILE_SORT_ALPHA',
                        use_fill=True,
                        selected_object_type='VISIBLE',
                        stroke_sample=0,
                        use_normalized_thickness=False,
                        use_clip_camera=True)


            svg_root = ET.parse(gp_image_path).getroot()
            for elem in svg_root:
                svg.add(SVGWriteElement(elem))

            if os.path.exists(gp_image_path):
                os.remove(gp_image_path)

        # -----------------------------
        # Loop to draw all objects
        # -----------------------------
        draw3d_loop(context, objlist, svg=svg)
        draw_titleblock(context, svg=svg)

        svg.save(pretty=True)

        # restore default value
        sceneProps.is_render_draw = False
        sceneProps.is_vector_draw = False

        endTime = time.time()
        print("Time: " + str(endTime - startTime))

    return outpath



def render_main_dxf(self, context):
    print('rendering dxf')
    startTime = time.time()
    scene = context.scene
    sceneProps = scene.MeasureItArchProps
    view = get_view()

    with Set_Render(sceneProps, is_dxf = True):
        vector_utils.clear_db()
        

        clipdepth = context.scene.camera.data.clip_end
        objlist = context.view_layer.objects

        # Get resolution
        render_scale = scene.render.resolution_percentage / 100
        width = int(scene.render.resolution_x * render_scale)
        height = int(scene.render.resolution_y * render_scale)


        view_matrix_3d = scene.camera.matrix_world.inverted()
        # Render Depth Buffer

        if view.vector_depthtest:
            print("Rendering Depth Buffer")
            offscreen = gpu.types.GPUOffScreen(width, height)
            with offscreen.bind():
                # Clear Depth Buffer, set Clear Depth to Cameras Clip Distance
                deps = context.evaluated_depsgraph_get()
                projection_matrix = scene.camera.calc_matrix_camera(deps, x=width, y=height)
                with OpenGL_Settings(None):
                    bgl.glClear(bgl.GL_DEPTH_BUFFER_BIT)
                    bgl.glClearDepth(clipdepth)
                    bgl.glEnable(bgl.GL_DEPTH_TEST)
                    bgl.glDepthFunc(bgl.GL_LEQUAL)

                    gpu.matrix.reset()
                    gpu.matrix.load_matrix(view_matrix_3d)
                    gpu.matrix.load_projection_matrix(projection_matrix)

                    texture_buffer = bgl.Buffer(bgl.GL_FLOAT, width * height)
                    print("Drawing Scene")
                    draw_scene(self, context, projection_matrix)
                    
                    print("Reading to Buffer")
                    bgl.glReadBuffer(bgl.GL_BACK)
                    bgl.glReadPixels(
                        0, 0, width, height, bgl.GL_DEPTH_COMPONENT, bgl.GL_FLOAT, texture_buffer)

                    if 'depthbuffer' in sceneProps:
                        del sceneProps['depthbuffer']
                    sceneProps['depthbuffer'] = texture_buffer

        vector_utils.set_globals()

        # Setup Output Path
        view = get_view()
        outpath = get_view_outpath(
            scene, view, "{:04d}.dxf".format(scene.frame_current))

        if view and view.res_type == 'res_type_paper':
            paperWidth = round(view.width * BU_TO_INCHES, 3)
            paperHeight = round(view.height * BU_TO_INCHES, 3)
        else:
            print('No View Present, using default resolution')
            paperWidth = width / sceneProps.default_resolution
            paperHeight = height / sceneProps.default_resolution

        # Setup basic dxf
        doc = ezdxf.new(dxfversion="AC1032", setup=True, units = 6)
        doc.units = ezdxf.units.M
        doc.header['$LUNITS'] = 2 # For Decimal
        doc.header['$INSUNITS'] = 14 # For Decimeters, I have no idea why this works best for CAD but it does... AutoCADs unit system is a mess
        doc.header['$MEASUREMENT'] = 1 #for Metric

        # Setup Layers based on styles 
        recalc_index(self, context)
        styles = scene.StyleGenerator.wrapper
        
        for style_wrapper in styles:
            name = style_wrapper.name
            type_str = style_wrapper.itemType
            idx = style_wrapper.itemIndex
            
            source_scene = sceneProps.source_scene
            style = eval("source_scene.StyleGenerator.{}[{}]".format(type_str,idx)) 
            cad_col_id = style.cad_col_idx

            if cad_col_id == 256:
                cad_col_id = randint(0,255)

            if "lineDrawDashed" in style and style.lineDrawDashed:
                doc.layers.add(name, color=cad_col_id, linetype="DASHED2")
            else:
                doc.layers.add(name, color=cad_col_id)

        view = get_view()

        # -----------------------------
        # Loop to draw all objects
        # -----------------------------
        draw3d_loop(context, objlist,dxf=doc)
        #draw_titleblock(context, dxf = doc)

        doc.saveas(outpath)

        # restore default value
        sceneProps.is_render_draw = False
        sceneProps.is_vector_draw = False

        endTime = time.time()
        print("Time: " + str(endTime - startTime))

    return outpath



class SVGWriteElement(object):
    """ Minimal implementation of `svgwrite`'s BaseElement, which we use to
    inject simple ET.Element objects into its SVG Drawing. """

    def __init__(self, elem):
        SVG_NS = '{http://www.w3.org/2000/svg}'

        # Remove the SVG namespace
        for e in elem.iter():
            if e.tag.startswith(SVG_NS):
                e.tag = e.tag.replace(SVG_NS, '', 1)

        self.elem = elem
        self.elementname = elem.tag

    def get_xml(self):
        return self.elem
