import bpy
import gpu
import os
import copy
import webbrowser
import ezdxf

from random import randint
from bpy.props import (
    CollectionProperty,
    IntProperty,
    BoolProperty,
    StringProperty,
    FloatProperty,
    EnumProperty,
    PointerProperty
)
from bpy.types import PropertyGroup, Panel, Operator, UIList, Scene, Object
from bpy.app.handlers import persistent

from mathutils import Vector, Matrix

from . import vector_utils
from .measureit_arch_render import render_main, render_main_svg, recalc_index, get_view_outpath, draw_scene
from .measureit_arch_baseclass import TextField, draw_textfield_settings
from .measureit_arch_geometry import draw3d_loop
from .measureit_arch_viewports import Viewport
from . measureit_arch_utils import get_loaded_addons, get_resolution, get_view, _imp_scales_dict, _metric_scales_dict,OpenGL_Settings, Set_Render
from .measureit_arch_units import BU_TO_INCHES


PAPER_SIZES = (
    ('CUSTOM',  'Custom',  (None,     None)),
    ('A0',      'A0',      ('84.1cm', '118.9cm')),
    ('A1',      'A1',      ('59.4cm', '84.1cm')),
    ('A2',      'A2',      ('42cm',   '59.4cm')),
    ('A3',      'A3',      ('29.7cm', '42cm')),
    ('A4',      'A4',      ('21cm',   '29.7cm')),
    ('LEGAL',   'US Legal',            ('8.5in',  '14in')),
    ('ANSI_A',  'ANSI A (US Letter)',  ('8.5in',  '11in')),
    ('ANSI_B',  'ANSI B (US Tabloid)', ('11in',   '17in')),
    ('ANSI_C',  'ANSI C',  ('17in',   '22in')),
    ('ANSI_D',  'ANSI D',  ('22in',   '34in')),
    ('ANSI_E',  'ANSI E',  ('34in',   '44in')),
    ('ARCH_A',  'Arch A',  ('9in',    '12in')),
    ('ARCH_B',  'Arch B',  ('12in',   '18in')),
    ('ARCH_C',  'Arch C',  ('18in',   '24in')),
    ('ARCH_D',  'Arch D',  ('24in',   '36in')),
    ('ARCH_E',  'Arch E',  ('36in',   '48in')),
    ('ARCH_E1', 'Arch E1', ('30in',   '42in')),
    ('ARCH_E2', 'Arch E2', ('26in',   '38in')),
    ('ARCH_E3', 'Arch E3', ('27in',   '39in')),
)

paper_size_items = map(lambda o: (o[0], o[1], ''), PAPER_SIZES)

metric_scale_items = map(lambda o: (o, o, ''), _metric_scales_dict.keys())

imperial_scale_items = map(lambda o: (o, o, ''), _imp_scales_dict.keys())


def scene_text_update_flag(self, context):
    scene = context.scene
    scene.MeasureItArchProps.text_updated = True
    update(self, context)

def update(self, context):
    context.scene.MeasureItArchProps.update_object_list = True
    if context is None:
        context = bpy.context
    scene = context.scene
    ViewGen = scene.ViewGenerator
    view = ViewGen.views[ViewGen.active_index]
    camera = view.camera.data
    if camera is not None:
        camera.type = view.cameraType

    if view.world is not None:
        context.scene.world = view.world

    if view.end_frame < view.start_frame:
        view.end_frame = view.start_frame
    scene.frame_end = view.end_frame
    scene.frame_start = view.start_frame
    if bpy.app.version_string == '4.2.0':
        if view.render_engine == 'BLENDER_EEVEE':
            scene.render.engine = 'BLENDER_EEVEE_NEXT'
        else:
            scene.render.engine = view.render_engine
    else:
        scene.render.engine = view.render_engine
    scene.view_settings.view_transform = view.view_transform
    scene.render.film_transparent = view.film_transparent
    # scene.frame_current = view.start_frame

    #Update Compositior Render Layer if it exists
    tree = bpy.context.scene.node_tree
    if tree != None and view.view_layer != '':
        try:
            render_node = tree.nodes['Render Layers']
            render_node.layer = view.view_layer
        except KeyError:
            print('No Render Layers Node in Compositor')
            pass


    if view.res_type == 'res_type_paper':
        update_camera(scene, camera)
    else:
        update_camera_px(scene, camera)

    if view.view_layer != "":
        try:
            vl = context.scene.view_layers[view.view_layer]
            if context.window.view_layer != vl:
                context.window.view_layer = vl
        except KeyError:
            pass

def freestyle_update_flag(self, context):
    scene = context.scene
    view = get_view()
    if view.embed_freestyle_svg:
        scene.render.use_freestyle = view.embed_freestyle_svg
        scene.svg_export.use_svg_export = view.embed_freestyle_svg

def update_scale(self,context):
    if self.paper_scale_mode == 'METRIC':
        self.paper_scale = _metric_scales_dict[self.metric_scale][0]
        self.model_scale = _metric_scales_dict[self.metric_scale][1]
    if self.paper_scale_mode == 'IMPERIAL':
        self.paper_scale = _imp_scales_dict[self.imp_scale][0]
        self.model_scale = _imp_scales_dict[self.imp_scale][1]

def update_paper_size(self, context):
    if self.paper_size == 'CUSTOM':
        return

    for code, _, (width, height) in PAPER_SIZES:
        if code == self.paper_size:
            break

    if self.paper_orientation == 'LANDSCAPE':
        width, height = height, width

    unit_system = context.scene.unit_settings.system
    self.width = bpy.utils.units.to_value(unit_system, "LENGTH", width)
    self.height = bpy.utils.units.to_value(unit_system, "LENGTH", height)

def update_camera(scene, camera):
    render = scene.render
    ViewGen = scene.ViewGenerator
    view = ViewGen.views[ViewGen.active_index]
    width = view.width
    height = view.height
    modelScale = view.model_scale
    paperScale = view.paper_scale

    ppi = get_resolution(update_flag=True)
    print('updating camera and render res')
    render.resolution_percentage = 100
    render.resolution_x = int(width * ppi * BU_TO_INCHES)
    render.resolution_y = int(height * ppi * BU_TO_INCHES)

    if width > height:
        camera.ortho_scale = (
            render.resolution_x / ppi / BU_TO_INCHES) * (modelScale / paperScale)
    else:
        camera.ortho_scale = (
            render.resolution_y / ppi / BU_TO_INCHES) * (modelScale / paperScale)

def update_camera_px(scene, camera):
    render = scene.render
    ViewGen = scene.ViewGenerator
    view = ViewGen.views[ViewGen.active_index]
    width_px = view.width_px
    height_px = view.height_px
    modelScale = view.model_scale
    pixelScale = view.pixel_scale
    percentScale = view.percent_scale

    render.resolution_x = width_px
    render.resolution_y = height_px
    render.resolution_percentage = percentScale

    if width_px > height_px:
        camera.ortho_scale = (render.resolution_x) * (modelScale / (pixelScale * (percentScale / 100)))
    else:
        camera.ortho_scale = (render.resolution_y) * (modelScale / (pixelScale * (percentScale / 100)))

def change_scene_camera(self, context):
    print('change_scene_camera_update')
    scene = context.scene
    ViewGen = scene.ViewGenerator
    view = ViewGen.views[ViewGen.active_index]
    ViewGen.view_changed = True
    camera = view.camera
    update(self, context)
    if camera is not None:
        scene.camera = camera
        if scene.frame_current != view.start_frame:
            scene.frame_current = view.start_frame
        scene_text_update_flag(self, context)


def camera_poll(self, object):
    return object.type == 'CAMERA'

@persistent
def create_preset_view(dummy):
    """ Handler called when a Blend file is loaded to create a default view. """
    context = bpy.context
    scene = context.scene
    ViewGen = scene.ViewGenerator

    if len(ViewGen.views)<1:
        add_view(context)


class ViewProperties(PropertyGroup):

    textFields: CollectionProperty(type=TextField)

    viewports: CollectionProperty(type=Viewport)

    render_engine: EnumProperty(
        items=(
            ('BLENDER_EEVEE', 'Eevee', ''),
            ('CYCLES', 'Cycles', ''),
            ('BLENDER_WORKBENCH', 'Workbench', ''),
        ),
        name="Render Engine",
        description="Render Engine used for this View",
        default='BLENDER_EEVEE',
        update=update)

    camera: PointerProperty(
        type=bpy.types.Object,
        poll=camera_poll)

    cameraType: EnumProperty(
        items=[
            ('PERSP', 'Perspective', ''),
            ('ORTHO', 'Ortho', '')
        ],
        name="Camera Type",
        description="Camera Type",
        default='ORTHO',
        update=update)

    world: PointerProperty(
        name = "View World",
        type=bpy.types.World,
        update = update)

    width: FloatProperty(
        name="Width",
        description="Camera Width in Units",
        unit='LENGTH',
        default=0.43,
        min=0.0,
        update=update)

    height: FloatProperty(
        name="Height",
        description="Camera Height in Units",
        unit='LENGTH',
        default=0.28,
        min=0.0,
        update=update)

    # Width_px Property
    width_px: IntProperty(
        name="X",
        description="Camera Width in Pixels",
        subtype='PIXEL',
        default=1920,
        min=4,
        update=update,
        step=100)

    # Width_px Property
    height_px: IntProperty(
        name="Y",
        description="Camera Height in Pixels",
        subtype='PIXEL',
        default=1080,
        min=4,
        update=update,
        step=100)

    # Percent Scale Property
    percent_scale: IntProperty(
        name="Percent Scale",
        description="Percentage scale for render resolution",
        subtype='PERCENTAGE',
        default=50,
        min=1,
        max=100,
        update=update,
        step=100)

    # PPI Property
    res: IntProperty(
        name="res_prop",
        description="Resolution in Pixels Per Inch",
        subtype='FACTOR',
        default=150,
        min=1,
        soft_max=600,
        soft_min=50,
        update=scene_text_update_flag,
        step=1)

    paper_scale_mode: EnumProperty(
        items=(
            ('METRIC', 'Metric', ''),
            ('IMPERIAL', 'Imperial', ''),
            ('CUSTOM', 'Custom', '')
        ),
        name="Scale Mode",
        description="",
        default='CUSTOM',
        update = update_scale)


    # Model Length
    model_scale: IntProperty(
        name="model_scale",
        description="Unit on Model",
        default=25,
        min=1,
        update=update)

    # Paper Length
    paper_scale: IntProperty(
        name="paper_scale",
        description="Length on Paper",
        default=1, min=1,
        update=update)

    # Pixel Length
    pixel_scale: IntProperty(
        name="Pixel Scale",
        subtype='PIXEL',
        default=10000,
        min=1,
        update=update)

    # Resolution Type
    res_type: EnumProperty(
        items=[
            ('res_type_paper', 'Paper',
             'Define Resolution by Paper Size and Pixels Per Inch'),
            ('res_type_pixels', 'Pixels',
             'Blender Standard, Define Resolution in Pixels')
        ],
        name="Resolution Type",
        description='Method For Defining Render Size',
        default='res_type_paper',
        update=update)

    paper_size: EnumProperty(
        items=paper_size_items,
        name="Paper size",
        description="Paper size used for rendering",
        update=update_paper_size)

    metric_scale: EnumProperty(
        items=metric_scale_items,
        name="Scale",
        description="Metric Scale",
        update=update_scale)

    imp_scale: EnumProperty(
        items=imperial_scale_items,
        name="Scale",
        description="Imperial Scale",
        update=update_scale)

    paper_orientation: EnumProperty(
        items=(
            ('PORTRAIT', 'Portrait', ''),
            ('LANDSCAPE', 'Landscape', ''),
        ),
        name="Paper orientation",
        description="Paper orientation used for rendering",
        default='PORTRAIT',
        update=update_paper_size)

    date_folder: BoolProperty(
        name="Date Folder",
        description="Adds a Folder with todays date to the end of the output path",
        default=False)

    name_folder: BoolProperty(
        name="Name Folder",
        description="Adds the project name to the output path",
        default=False)

    output_path: StringProperty(
        name="Output Path",
        description="Render Output Path for this View",
        subtype='FILE_PATH',
        default="//Renders",
        update=update)

    view_layer: StringProperty(
        name="View Layer",
        description="View Layer to use with this view",
        default="",
        update=update)

    titleBlock: StringProperty(
        name="Title Block",
        description="TitleBlock to use with this view layer",
        default="",
        update=update)

    view_num: StringProperty(
        name="Drawing Number",
        description="Drawing Number (A01, E02 etc.)",
        default="",
        update=update)

    start_frame: IntProperty(
        name="Start Frame",
        default=1,
        update=update)

    end_frame: IntProperty(
        name="End Frame",
        default=1,
        update=update)

    embed_scene_render: BoolProperty(
        name="Embed Scene Render",
        description="Render the scene and automatically combine the rendered image with the Measureit-ARCH render pass",
        default=False)

    embed_freestyle_svg: BoolProperty(
        name="Embed Freestyle SVG",
        description="Render a Freestyle SVG and automatically combine the rendered "
                    "image with the Measureit-ARCH render pass\n"
                    "Note: Requires 'Render: Freestyle SVG Export' addon to be enabled",
        default=False,
        update=freestyle_update_flag)


    embed_greasepencil_svg: BoolProperty(
        name="Embed Grease Pencil SVG",
        description="Export a Grease Pencil SVG and automatically combine the rendered "
                    "image with the Measureit-ARCH render pass",
        default=False,)

    vector_depthtest: BoolProperty(
        name="Use Vector Depth Test",
        description="Check for Occlusion when rendering to SVG\n"
                    "WARNING: SLOW, open system console before rendering to view progress",
        default=False)
    
    depth_test_method: EnumProperty(
        items=(
            ('DEPTH_BUFFER', 'Depth Buffer', ''),
            ('GEOMETRIC', 'Geometric', '')
        ),
        name="Depth Test Method",
        description="Method for depth testing when rendering vector linework",
        default='DEPTH_BUFFER',
        update=update)

    include_in_batch: BoolProperty(
        name="Include In Batch View Render",
        description="Include In Batch View Render",
        default=True,)

    view_transform: EnumProperty(
        items=(
            ('Standard', 'Standard', ''),
            ('Filmic', 'Filmic', ''),
        ),
        name="View Transform",
        description="View (Color) Transform used for rendering",
        default='Filmic',
        update=update)

    film_transparent: BoolProperty(
        name="Film Transparent",
        description="Film Transparent",
        default=False,
        update = update)

    skip_instances: BoolProperty(
        name="Skip Instances",
        description="Will skip drawing Measureit_ARCH elements from instanced Collections",
        default=False)

    use_resolution_override: BoolProperty(
        name="Use Resolution Override",
        description="When enabled, this view can specify its own resolution rather than"
                    " using the scene render resolution",
        default=False,
        update= update)
    
    skip_hatches: BoolProperty(
        name="Skip Hatches",
        description="Don't Draw hatches in this view",
        default=False)


class ViewContainer(PropertyGroup):
    active_index: IntProperty(
        name='Active View Index', min=0, max=1000, default=0,
        description='Index of the current View',
        update=change_scene_camera)

    view_changed: BoolProperty(name='View_Changed', default=False)
    show_settings: BoolProperty(name='Show View Settings', default=False)
    show_text_fields: BoolProperty(name='Show Text Fields', default=False)

    # Array of views
    views: CollectionProperty(type=ViewProperties)

class DeleteViewButton(Operator):
    bl_idname = "measureit_arch.deleteviewbutton"
    bl_label = "Delete View"
    bl_description = "Delete a View"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'}
    tag: IntProperty()

    def execute(self, context):
        # Add properties

        Generator = context.scene.ViewGenerator
        Generator.views.remove(Generator.active_index)

        return {'FINISHED'}

class DuplicateViewButton(Operator):
    bl_idname = "measureit_arch.duplicateviewbutton"
    bl_label = "Duplicate View"
    bl_description = "Duplicate a View"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'}
    tag: IntProperty()
    new_layer: BoolProperty(default = False)

    @classmethod
    def poll(cls, context):
        Generator = context.scene.ViewGenerator
        try:
            Generator.views[Generator.active_index]
        except:
            return False
        return True

    def execute(self, context):
        # Add properties

        Generator = context.scene.ViewGenerator
        ActiveView = Generator.views[Generator.active_index]
        newView = Generator.views.add()
        newView.name = ActiveView.name + ' copy'

        # Get props to loop through
        for key in Generator.views[Generator.active_index].__annotations__.keys():
            try:
                newView[key] = ActiveView[key]
            except:
                pass

        if self.new_layer:
            bpy.ops.scene.view_layer_add(type='COPY')
            newView.view_layer = context.view_layer.name

        return {'FINISHED'}

class DuplicateViewWithLayerButton(Operator):
    bl_idname = "measureit_arch.duplicateviewlayerbutton"
    bl_label = "Duplicate View with new View Layer"
    bl_description = "Duplicates a view"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'}
    new_name: StringProperty(name = "View Layer Name")
    new_camera: BoolProperty(default = False)
    new_collection: BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        Generator = context.scene.ViewGenerator
        try:
            Generator.views[Generator.active_index]
        except:
            return False
        return True

    def execute(self, context):
        # Add properties

        Generator = context.scene.ViewGenerator
        ActiveView = Generator.views[Generator.active_index]
        newView = Generator.views.add()
        newView.name = self.new_name

        # Get props to loop through
        for key in Generator.views[Generator.active_index].__annotations__.keys():
            try:
                newView[key] = ActiveView[key]
            except:
                pass


        bpy.ops.scene.view_layer_add(type='COPY')
        context.view_layer.name = self.new_name
        newView.view_layer = context.view_layer.name

        new_collection = None
        if self.new_collection:
            # Check For a "VIEWS" Collection, make one if doesn't exist
            views_collection = None
            try:
                views_collection = context.scene.collection.children['VIEWS']
            except KeyError:
                views_collection  = bpy.data.collections.new("VIEWS")
                context.scene.collection.children.link(views_collection)

            # Create our View Collection, add it to "VIEWS"
            new_collection  = bpy.data.collections.new(self.new_name)
            views_collection.children.link(new_collection)

            # Exclude our new View Collection from all other view Layers
            for layer in context.scene.view_layers:
                for collection in layer.layer_collection.children['VIEWS'].children:
                    #col.exclude = col.name != layer.name
                    if collection.name == self.new_name:
                        collection.exclude = True

        if self.new_camera:
            bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(0, 0, 0), rotation=(1.10871, 0.0132652, 1.14827), scale=(1, 1, 1))
            new_camera = bpy.context.active_object
            old_camera = bpy.context.scene.camera
            new_camera.name = self.new_name
            new_camera.location = old_camera.location
            new_camera.rotation_euler = old_camera.rotation_euler
            newView.camera = new_camera
            if new_collection != None:
                new_collection.objects.link(new_camera)
                #context.scene.collection.objects.unlink(new_camera)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        self.new_name = context.view_layer.name + ' copy'
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, "new_name", text = "View Layer Name")
        col.prop(self, "new_camera",text = "Create New Camera")
        col.prop(self, "new_collection",text = "Create View Collection")

class BatchViewRender(Operator):
    bl_idname = "measureit_arch.batchviewrender"
    bl_label = "Render All Views"
    bl_description = "Render All Views"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'}

    _timer = None
    _updating = False
    view3d = None
    idx = 0

    def modal(self, context, event):
        scene = context.scene

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER' and not self._updating:
            self._updating = True
            numViews = len(context.scene.ViewGenerator.views)
            if self.idx <= numViews - 1:
                view = context.scene.ViewGenerator.views[self.idx]
                if view.include_in_batch:
                    context.scene.ViewGenerator.active_index = self.idx
                    self.view3d.tag_redraw()
                    print("MeasureIt_ARCH: Rendering View: " + view.name)
                    render_main_svg(self, context)

                self.idx += 1
                self._updating = False


            else:
                self.cancel(context)
                return {'CANCELLED'}

        self.view3d.tag_redraw()
        return {'PASS_THROUGH'}

    def execute(self, context):
        # Check camera
        # Check camera
        if not context.scene.camera:
            self.report({'ERROR'}, "Unable to render: no camera found!")
            return {'FINISHED'}

        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    self.view3d = area

        if self.view3d is None:
            self.report(
                {'ERROR'}, 'A 3D Viewport must be open to render MeasureIt_ARCH Animations')
            self.cancel(context)
            return {'CANCELLED'}

        wm = context.window_manager
        self._timer = wm.event_timer_add(1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        if self._timer != None:
            wm.event_timer_remove(self._timer)
        return {'CANCELLED'}

class BatchDXFRender(Operator):
    bl_idname = "measureit_arch.batchdxfrender"
    bl_label = "Render All Views to dxf"
    bl_description = "Render All Views to a single .dfx model space"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'}

    _timer = None
    _updating = False
    view3d = None
    idx = 0
    doc = None # DXF Document
    outpath = ""

    def modal(self, context, event):
        scene = context.scene
        sceneProps = scene.MeasureItArchProps

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER' and not self._updating:
            self._updating = True
            numViews = len(context.scene.ViewGenerator.views)
            if self.idx <= numViews - 1:
                view = context.scene.ViewGenerator.views[self.idx]
                if view.include_in_batch:
                    offset_x = 50 * self.idx
                    with Set_Render(sceneProps, is_dxf = True, offset_x = offset_x):
                        context.scene.ViewGenerator.active_index = self.idx
                        self.view3d.tag_redraw()
                        print("MeasureIt_ARCH: Rendering View: {} to DXF".format(view.name))
                        
                        ###### DXF RENDER  CODE
                        vector_utils.clear_db()
                        clipdepth = context.scene.camera.data.clip_end
                        objlist = context.view_layer.objects

                        # Get resolution
                        render_scale = scene.render.resolution_percentage / 100
                        width = int(scene.render.resolution_x * render_scale)
                        height = int(scene.render.resolution_y * render_scale)

                        view_matrix_3d = scene.camera.matrix_world.inverted()

                        if view.vector_depthtest:
                            print("Rendering Depth Buffer")
                            offscreen = gpu.types.GPUOffScreen(width, height)
                            with offscreen.bind():
                                # Clear Depth Buffer, set Clear Depth to Cameras Clip Distance
                                deps = context.evaluated_depsgraph_get()
                                projection_matrix = scene.camera.calc_matrix_camera(deps, x=width, y=height)
                                with OpenGL_Settings(None):
                                    fb = gpu.state.active_framebuffer_get()
                                    fb.clear(color=(0.0, 0.0, 0.0, 0.0), depth = clipdepth)

                                    gpu.matrix.reset()
                                    gpu.matrix.load_matrix(view_matrix_3d)
                                    gpu.matrix.load_projection_matrix(projection_matrix)

                                    print("Drawing Scene")
                                    draw_scene(self, context, projection_matrix)

                                    print("Reading to Buffer")
                                    depth_buffer = fb.read_depth(0, 0, width, height)
                                    depth_buffer.dimensions = width * height

                                    if 'depthbuffer' in sceneProps:
                                        del sceneProps['depthbuffer']
                                    sceneProps['depthbuffer'] = depth_buffer

                        vector_utils.set_globals()

   
                        if view and view.res_type == 'res_type_paper':
                            paperWidth = round(view.width * BU_TO_INCHES, 3)
                            paperHeight = round(view.height * BU_TO_INCHES, 3)
                        else:
                            print('No View Present, using default resolution')
                            paperWidth = width / sceneProps.res
                            paperHeight = height / sceneProps.res
                        
                        draw3d_loop(context, objlist,dxf=self.doc)

                self.idx += 1
                self._updating = False
                           

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

        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    self.view3d = area

        if self.view3d is None:
            self.report(
                {'ERROR'}, 'A 3D Viewport must be open to render MeasureIt_ARCH Animations')
            self.cancel(context)
            return {'CANCELLED'}

        wm = context.window_manager
        self._timer = wm.event_timer_add(1, window=context.window)
        wm.modal_handler_add(self)

        scene = context.scene
        sceneProps = scene.MeasureItArchProps

        # Set up outpath TODO: SHould be based on the file name, not the view
        view = get_view()
        self.outpath = get_view_outpath(
            scene, view, "{:04d}.dxf".format(scene.frame_current))

        # Set up the DXF document
        self.doc = ezdxf.new(dxfversion="AC1032", setup=True, units = 6)
        self.doc.modelspace()
        self.doc.units = ezdxf.units.M
        self.doc.header['$LUNITS'] = 2 # For Decimal
        self.doc.header['$INSUNITS'] = ezdxf.units.M
        self.doc.header['$MEASUREMENT'] = 1 #for Metric

        # Create the MeasureIt_ARCH dim style

        m_arch_style = self.doc.dimstyles.new(name='MeasureIt_ARCH')
        m_arch_style.dimscale = 1
        m_arch_style.dimtxt = 100

        # Setup Layers based on styles
        recalc_index(self, context)
        styles = context.scene.StyleGenerator.wrapper

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
                self.doc.layers.add(name, color=cad_col_id, linetype="DASHED2")
            else:
                self.doc.layers.add(name, color=cad_col_id)


        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        scene = context.scene
        sceneProps = scene.MeasureItArchProps

        if self._timer != None:
            wm.event_timer_remove(self._timer)
        if self.doc != None:
            self.doc.saveas(self.outpath)
        
        # restore default value
        sceneProps.is_render_draw = False
        sceneProps.is_vector_draw = False
        print('Finished .dxf Batch Render')
        return {'CANCELLED'}

class M_ARCH_UL_Views_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            view = item
            layout.use_property_decorate = False
            row = layout.row(align=True)
            split = row.split(factor=0.3)
            split.prop(view, "view_num", text="", emboss=False, icon='DOCUMENTS')
            split.prop(view, "name", text="", emboss=False)
            row.prop(view, 'camera', text="", icon='CAMERA_DATA')

            if view.include_in_batch:
                icon = "RESTRICT_RENDER_OFF"
            else:
                icon = "RESTRICT_RENDER_ON"

            row.separator()
            row.prop(view, 'include_in_batch', text="",emboss=False, icon=icon)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')

class SCENE_PT_Views(Panel):
    """ A panel in the Object properties window """
    bl_parent_id = 'SCENE_PT_Panel'
    bl_label = "Views"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon='DOCUMENTS')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        scene = context.scene
        ViewGen = scene.ViewGenerator
        SceneProps = scene.MeasureItArchProps

        row = layout.row()

        # Draw The UI List
        row.template_list("M_ARCH_UL_Views_list", "", ViewGen,
                          "views", ViewGen, "active_index", rows=2, type='DEFAULT')

        # Operators Next to List
        col = row.column(align=True)
        col.operator("measureit_arch.addviewbutton", icon='ADD', text="")
        op = col.operator("measureit_arch.deleteviewbutton", text="", icon="X")

        col.separator()
        up = col.operator("measureit_arch.movepropbutton", text="", icon="TRIA_UP")
        up.genPath = "bpy.context.scene.ViewGenerator"
        up.item_type = "views"
        up.upDown = -1

        down = col.operator("measureit_arch.movepropbutton", text="", icon="TRIA_DOWN")
        down.genPath = "bpy.context.scene.ViewGenerator"
        down.item_type = "views"
        down.upDown = 1

        op.tag = ViewGen.active_index  # saves internal data

        col.separator()
        col.menu("SCENE_MT_Views_menu", icon='DOWNARROW_HLT', text="")

        if len(ViewGen.views) > 0 and ViewGen.active_index < len(ViewGen.views):
            view = ViewGen.views[ViewGen.active_index]

            # Settings Below List
            if ViewGen.show_settings:
                settingsIcon = 'DISCLOSURE_TRI_DOWN'
            else:
                settingsIcon = 'DISCLOSURE_TRI_RIGHT'

            box = layout.box()
            col = box.column()
            row = col.row()
            row.prop(ViewGen, 'show_settings', text="",
                     icon=settingsIcon, emboss=False)

            row.label(text=view.name + ' Settings:')

            if ViewGen.show_settings:
                col = box.column()
                box = box.column()
                if view.camera is None:
                    col.label(text="Please set a Camera for this View")
                    box.enabled = False

                col = box.column(align=True)
                col.prop(view, "render_engine")
                col.prop(view, "world")
                col.prop(view, "view_transform")
                col.prop(view, "film_transparent")
                col = box.column(align=True)
                col.prop(view, "view_num")
                col.prop(view, "name")
                col.prop_search(view, 'titleBlock', bpy.data,
                                'scenes', text='Title Block')

                col = box.column(align=True)
                col.prop(view, "cameraType", text="Camera Type")
                col.prop_search(view, 'view_layer', context.scene,
                                'view_layers', text='View Layer')

                col = box.column(align=True)
                row = col.row(align=True)
                row.prop(view, "output_path")
                row.operator("measureit_arch.openinbrowser",text="",icon="WINDOW")
                col.prop(view, "date_folder", text="Date Folder")
                col.prop(view, "name_folder",)

                col = box.column(align=True)
                col.row().prop(view, 'res_type', expand=True)
                if view.res_type == 'res_type_paper':
                    split = box.split(factor=0.4)
                    col = split.column()
                    col.alignment = 'RIGHT'
                    row = split.row(align=True)

                    custom_paper_size = view.paper_size == 'CUSTOM'
                    col = box.column(align=True)
                    col.enabled = True
                    col.prop(view, 'paper_size', text='Paper size:')

                    col = box.column(align=True)
                    col.enabled = not custom_paper_size
                    col.row().prop(view, 'paper_orientation', expand=True)

                    col = box.column(align=True)
                    col.enabled = custom_paper_size
                    col.prop(view, 'width', text='Width:')
                    col.prop(view, 'height', text='Height:')

                    col = box.column(align=True)
                    col.enabled = True
                    col.prop(view, 'use_resolution_override')
                    col = box.column(align=True)
                    if view.use_resolution_override:
                        col.prop(view, 'res', text='Resolution (PPI):')
                    else:
                        col.prop(SceneProps, 'render_resolution', text='Scene Resolution (PPI):')

                else:
                    split = box.split(factor=0.4)
                    col = split.column()
                    col.alignment = 'RIGHT'
                    row = split.row(align=True)

                    # row.menu(CAMERA_PX_Presets.__name__, text=CAMERA_PX_Presets.bl_label)
                    # row.operator(AddPixelResPreset.bl_idname, text="", icon='ADD')
                    # row.operator(AddPixelResPreset.bl_idname, text="", icon='REMOVE').remove_active = True

                    col = box.column(align=True)
                    col.prop(view, 'width_px', text="Resolution X")
                    col.prop(view, 'height_px')
                    col.prop(view, 'percent_scale', text="%")

                # Scale Settings
                col = box.column(align=True)
                col.active = view.camera.data.type == 'ORTHO'
                if view.res_type == 'res_type_paper':
                    # row = col.row(align=True)
                    # row.menu(CAMERA_PAPER_SCALE_Presets.__name__, text=CAMERA_PAPER_SCALE_Presets.bl_label)
                    # row.operator(AddPaperScalePreset.bl_idname, text="", icon='ADD')
                    # row.operator(AddPaperScalePreset.bl_idname, text="", icon='REMOVE').remove_active = True

                    col.row().prop(view, 'paper_scale_mode', expand=True)
                    if view.paper_scale_mode == 'CUSTOM':
                        row = col.row(align=True)
                        row.prop(view, 'paper_scale', text="Scale")
                        row.prop(view, 'model_scale', text=":")

                    if view.paper_scale_mode == 'METRIC':
                        col.prop(view, 'metric_scale')

                    if view.paper_scale_mode == 'IMPERIAL':
                        col.prop(view, 'imp_scale')

                else:

                    # row = col.row(align=True)
                    # row.menu(CAMERA_PX_SCALE_Presets.__name__, text=CAMERA_PX_SCALE_Presets.bl_label)
                    # row.operator(AddPixelScalePreset.bl_idname, text="", icon='ADD')
                    # row.operator(AddPixelScalePreset.bl_idname, text="", icon='REMOVE').remove_active = True

                    row = col.row(align=True)
                    row.prop(view, 'pixel_scale', text="Scale")
                    row.prop(view, 'model_scale', text=":")

                # A quick Test, If BlenderBIM is available, add its view specific properties here too
                # try:
                #    col = box.column(align=True)
                #    col.prop(camera.BIMCameraProperties,'diagram_scale', text= 'BlenderBIM Scale')
                #    col.operator('bim.cut_section')
                # except:
                #    pass

                col = box.column(align=True)
                row = col.row(align=True)
                row.prop(view, 'start_frame', text="Frame Range")
                row.prop(view, 'end_frame', text="")

                col.prop(view, "embed_scene_render", text="Embed Scene Render")
                col.prop(view, "embed_greasepencil_svg", text="Embed Grease Pencil SVG")
                col.prop(view, "vector_depthtest", text="Use Vector Depth Test")
                col.prop(SceneProps, "depth_test_method", text = "Scene Depth Test Method")
                col.prop(view, "skip_instances",)
                col.prop(view, 'skip_hatches')

                col = box.column(align=True)
                freestyle_svg_export = 'render_freestyle_svg' in get_loaded_addons()
                col.active = freestyle_svg_export
                col.prop(view, "embed_freestyle_svg", text="Embed FreeStyle SVG")

            # Notes below Settings
            if ViewGen.show_text_fields:
                fieldsIcon = 'DISCLOSURE_TRI_DOWN'
            else:
                fieldsIcon = 'DISCLOSURE_TRI_RIGHT'

            box = layout.box()
            col = box.column()
            row = col.row(align=True)
            row.prop(ViewGen, 'show_text_fields',
                     text="", icon=fieldsIcon, emboss=False)
            row.label(text=view.name + ' Notes:')

            row.emboss = 'PULLDOWN_MENU'
            txtAddOp = row.operator(
                "measureit_arch.additem", text="", icon="ADD")
            txtAddOp.propPath = 'bpy.context.scene.ViewGenerator.views[bpy.context.scene.ViewGenerator.active_index].textFields'
            txtAddOp.idx = ViewGen.active_index
            txtAddOp.add = True

            txtRemoveOp = row.operator(
                "measureit_arch.additem", text="", icon="REMOVE")
            txtRemoveOp.propPath = 'bpy.context.scene.ViewGenerator.views[bpy.context.scene.ViewGenerator.active_index].textFields'
            txtRemoveOp.idx = ViewGen.active_index
            txtRemoveOp.add = False

            if ViewGen.show_text_fields:
                prop_path = 'bpy.context.scene.ViewGenerator.views[bpy.context.scene.ViewGenerator.active_index].textFields'
                draw_textfield_settings(view, box, prop_path)

class SCENE_MT_Views_menu(bpy.types.Menu):
    bl_label = "Custom Menu"

    def draw(self, context):
        layout = self.layout
        layout.operator(
            'measureit_arch.duplicateviewbutton',
            text="Duplicate Selected View", icon='DUPLICATE')

        layout.operator('measureit_arch.duplicateviewlayerbutton',
            text="Duplicate View with new Layer", icon='RENDERLAYERS')

        layout.operator('measureit_arch.batchviewrender',
            text = "Batch Render Views", icon = "DOCUMENTS")
        
        layout.operator('measureit_arch.batchdxfrender',
            text = "Batch Render DXF", icon = "DOCUMENTS")

class OpenInBrowser(Operator):
    bl_idname = "measureit_arch.openinbrowser"
    bl_label = "Open"
    bl_description = "Open the Output Folder is the OS File Browser"
    bl_category = 'MeasureitArch'

    def execute(self,context):
        view = get_view()
        outpath = get_view_outpath(bpy.context.scene,view,".png")
        path = bpy.path.abspath(outpath)
        path = os.path.split(path)[0]
        webbrowser.open(path)

        return {'FINISHED'}

class AddViewButton(Operator):
    bl_idname = "measureit_arch.addviewbutton"
    bl_label = "Add"
    bl_description = "Create A New View"
    bl_category = 'MeasureitArch'

    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # Add properties
                    add_view(context)
                    context.area.tag_redraw()
                    return {'FINISHED'}
        return {'FINISHED'}

def add_view(context):
    scene = context.scene
    ViewGen = scene.ViewGenerator
    newView = ViewGen.views.add()
    newView.name = 'View {}'.format(len(ViewGen.views))

