import bpy
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D, Scene, UIList, Menu
from rna_prop_ui import PropertyPanel
from bl_operators.presets import AddPresetBase
from .custom_preset_base import Custom_Preset_Base
import os
from bpy.app.handlers import persistent
from bpy.props import (
        CollectionProperty,
        FloatVectorProperty,
        IntProperty,
        BoolProperty,
        StringProperty,
        FloatProperty,
        EnumProperty,
        PointerProperty,
        BoolVectorProperty
        )

from .measureit_arch_render import render_main
from datetime import datetime

def scene_text_update_flag(self, context):
    scene = context.scene
    scene.MeasureItArchProps.text_updated = True
    update(self,context)

def update(self,context):
    if context == None:
        context = bpy.context
    scene = context.scene
    ViewGen = scene.ViewGenerator
    view = ViewGen.views[ViewGen.active_index]
    camera = view.camera.data

    if view.end_frame < view.start_frame:
        view.end_frame = view.start_frame
    scene.frame_end = view.end_frame
    scene.frame_start = view.start_frame
    scene.frame_current = view.start_frame

    if view.res_type == 'res_type_paper':
        update_camera(scene,camera)
    else:
        update_camera_px(scene,camera)

    if view.view_layer != "":
        vl = context.scene.view_layers[view.view_layer]
        context.window.view_layer = vl

    render = scene.render
    if view.output_path is not "":
        filenameStr = context.view_layer.name + '_' + view.name 
        render.filepath = os.path.join(view.output_path, filenameStr)
        if view.date_folder:
            today = datetime.now()
            renderpath = bpy.path.abspath(view.output_path)
            datepath = os.path.join(renderpath, today.strftime('%Y%m%d'))
            if not os.path.exists(datepath):
                os.mkdir(renderpath + today.strftime('%Y%m%d'))
            render.filepath = os.path.join(datepath, filenameStr)
              
def update_camera(scene,camera):
    render = scene.render
    ViewGen = scene.ViewGenerator
    view = ViewGen.views[ViewGen.active_index]
    width = view.width
    height = view.height
    modelScale = view.model_scale
    paperScale = view.paper_scale
    
    ppi = view.res
    
    render.resolution_percentage = 100
    render.resolution_x = width *  ppi * 39.3701
    render.resolution_y = height * ppi * 39.3701

    if width > height:
        camera.ortho_scale = (render.resolution_x/ppi/39.3701) * (modelScale/paperScale)
    else:
        camera.ortho_scale = (render.resolution_y/ppi/39.3701) * (modelScale/paperScale)

def update_camera_px(scene,camera):
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
        camera.ortho_scale = (render.resolution_x) * (modelScale/(pixelScale*(percentScale/100)))
    else:
        camera.ortho_scale = (render.resolution_y) * (modelScale/(pixelScale*(percentScale/100)))

def change_scene_camera(self,context):
    scene = context.scene
    ViewGen = scene.ViewGenerator
    view = ViewGen.views[ViewGen.active_index]
    camera = view.camera
    update(self,context)
    if camera != None:
        scene.camera = camera
        scene_text_update_flag(self,context)

def camera_poll(self, object):
    return object.type == 'CAMERA'

class ViewProperties(PropertyGroup):

    camera: PointerProperty(type= bpy.types.Object,
                            poll = camera_poll)

    width: FloatProperty(name = "Width", 
                                        description = "Camera Width in Units", 
                                        unit = 'LENGTH',
                                        default = 0.43, 
                                        min = 0.0, 
                                        update = update
                                        )
    
    #Height Property
    height: FloatProperty(name = "Height", 
                                        description = "Camera Height in Units", 
                                        unit = 'LENGTH', 
                                        default = 0.28, 
                                        min = 0.0, 
                                        update = update
                                        )
            
    #Width_px Property
    width_px: IntProperty(name = "X", 
                                        description = "Camera Width in Pixels", 
                                        subtype = 'PIXEL',
                                        default = 1920, 
                                        min = 4, 
                                        update = update,
                                        step = 100
                                        )
        
    #Width_px Property
    height_px: IntProperty(name = "Y", 
                                        description = "Camera Height in Pixels", 
                                        subtype = 'PIXEL',
                                        default = 1080, 
                                        min = 4, 
                                        update = update,
                                        step = 100
                                        )
    
    #Percent Scale Property
    percent_scale: IntProperty(name = "Percent Scale", 
                                        description = "Percentage scale for render resolution", 
                                        subtype = 'PERCENTAGE',
                                        default = 50, 
                                        min = 1,
                                        max = 100,
                                        update = update,
                                        step = 100
                                        )
        
    #PPI Property
    res: IntProperty(name = "res_prop", 
                                        description = "Resolution in Pixels Per Inch", 
                                        subtype = 'FACTOR', 
                                        default = 150, 
                                        min = 1, 
                                        soft_max = 600, 
                                        soft_min =50,
                                        update = scene_text_update_flag, 
                                        step = 1, 
                                        )
    
    #Model Length
    model_scale: IntProperty(
                                    name = "model_scale", 
                                    description = "Unit on Model", 
                                    default = 25, 
                                    min = 1, 
                                    update = update
                                    )
    
    #Paper Length
    paper_scale: IntProperty(
                                    name = "paper_scale",
                                    description = "Length on Paper",
                                    default = 1, min = 1, 
                                    update = update
                                    )
        
    #Pixel Length
    pixel_scale: IntProperty(
                                    name = "Pixel Scale",
                                    subtype = 'PIXEL',
                                    default = 10000, 
                                    min = 1, 
                                    update = update
                                    )
        
    #Resolution Type
    res_type: EnumProperty(
                                items=[
                                    ('res_type_paper','Paper','Define Resolution by Paper Size and Pixels Per Inch'), 
                                    ('res_type_pixels','Pixels','Blender Standard, Define Resolution in Pixels')
                                    ],
                                name ="Resolution Type",
                                description = 'Method For Defining Render Size', 
                                default = 'res_type_paper',
                                update = update
                                #options = 'ENUM_FLAG'
                                )
    date_folder: BoolProperty(name= "Date Folder",
                description= "Adds a Folder with todays date to the end of the output path",
                default=False)

    output_path: StringProperty(
                name="Output Path",
                description="Render Output Path for this View",
                subtype = 'FILE_PATH',
                default="",
                update= update
                )
    
    view_layer: StringProperty(
                name="View Layer",
                description="View Layer to use with this view",
                default="",
                update= update
                )
    
    titleBlock: StringProperty(
            name="Title Block",
            description="TitleBlock to use with this view layer",
            default="",
            update= update
            )

    start_frame: IntProperty(
                name = "Start Frame",
                default = 1, 
                min = 1, 
                update = update
                )
    
    end_frame: IntProperty(
                name = "End Frame",
                default = 1, 
                min = 1, 
                update = update
                )

bpy.utils.register_class(ViewProperties)

class ViewContainer(PropertyGroup):
    active_index: IntProperty(name='Active View Index', min=0, max=1000, default=0,
                                description='Index of the current View',
                                update = change_scene_camera)
    
    show_settings: BoolProperty(name='Show View Settings', default=False)

    # Array of views
    views: CollectionProperty(type=ViewProperties) 

bpy.utils.register_class(ViewContainer)
Scene.ViewGenerator = bpy.props.PointerProperty(type=ViewContainer)

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

class M_ARCH_UL_Views_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):    
            scene = bpy.context.scene
            
            if self.layout_type in {'DEFAULT', 'COMPACT'}:
                view = item
                layout.use_property_decorate = False
                row = layout.row(align=True)
                subrow = row.row()
                subrow.prop(view, "name", text="",emboss=False)
                row.prop(view,'camera', text="", icon = 'CAMERA_DATA')

            elif self.layout_type in {'GRID'}:
                layout.alignment = 'CENTER'
                layout.label(text="", icon='MESH_CUBE')

class SCENE_PT_Views(Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "MeasureIt_ARCH Views"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        scene = context.scene
        ViewGen = scene.ViewGenerator

        row = layout.row()
        
        # Draw The UI List
        row.template_list("M_ARCH_UL_Views_list", "", ViewGen, "views", ViewGen, "active_index",rows=2, type='DEFAULT')
        
        # Operators Next to List
        col = row.column(align=True)
        col.operator("measureit_arch.addviewbutton", icon='ADD', text="")
        op = col.operator("measureit_arch.deleteviewbutton", text="", icon="X")
        op.tag = ViewGen.active_index  # saves internal data
        
        #col.separator()
        #col.menu("SCENE_MT_styles_menu", icon='DOWNARROW_HLT', text="")

        
        # Settings Below List
        if len(ViewGen.views) > 0 and  ViewGen.active_index < len(ViewGen.views):

            view = ViewGen.views[ViewGen.active_index]

            if ViewGen.show_settings: settingsIcon = 'DISCLOSURE_TRI_DOWN'
            else: settingsIcon = 'DISCLOSURE_TRI_RIGHT'
            
            box = layout.box()
            col = box.column()
            row = col.row()
            row.prop(ViewGen, 'show_settings', text="", icon=settingsIcon,emboss=False)

            row.label(text= view.name + ' Settings:')

            if ViewGen.show_settings:
                col = box.column()
                if view.camera !=None:

                    camera = view.camera.data
                    col.operator("measureit_arch.renderpreviewbutton", icon='RENDER_STILL', text="Render View Preview")
                    #col.operator("bind_marker.bind_marker", text = "Bind Camera To Frame", icon = 'CAMERA_DATA')
                    col.prop(camera, "type", text="Camera Type")
                    col.prop_search(view,'view_layer', context.scene, 'view_layers',text='View Layer')
                    col.prop_search(view,'titleBlock', bpy.data, 'scenes', text='Title Block')  
                    col.prop(view, "output_path")
                    col.prop(view, "date_folder", text="Date Folder")
                    
                    col.row().prop(view, 'res_type', expand=True)
                    
                    if view.res_type == 'res_type_paper':
                
                        col = box.column(align=True)
                        split = box.split(factor=0.4)
                        col = split.column()
                        col.alignment ='RIGHT'
                        row = split.row(align=True)

                        #row.menu(CAMERA_PAPER_Presets.__name__, text=CAMERA_PAPER_Presets.bl_label)
                        #row.operator(AddPaperResPreset.bl_idname, text="", icon='ADD')
                        #row.operator(AddPaperResPreset.bl_idname, text="", icon='REMOVE').remove_active = True
                        
                        col = box.column(align=True)
                        col.prop(view,'width', text = 'Width:')
                        col.prop(view,'height', text = 'Height:')
                        col.prop(view,'res', text = 'Resolution (PPI):') 
                                
                    else:
                        col = box.column(align=True)
                        split = box.split(factor=0.4)
                        col = split.column()
                        col.alignment ='RIGHT'
                        row = split.row(align=True)
                        
                        #row.menu(CAMERA_PX_Presets.__name__, text=CAMERA_PX_Presets.bl_label)
                        #row.operator(AddPixelResPreset.bl_idname, text="", icon='ADD')
                        #row.operator(AddPixelResPreset.bl_idname, text="", icon='REMOVE').remove_active = True
                    
                        col = box.column(align=True)
                        col.prop(view,'width_px', text="Resolution X")
                        col.prop(view,'height_px')
                        col.prop(view,'percent_scale', text="%")
                                                   
                    # Scale Settings
                    col = box.column(align=True)
                    col.active = view.camera.data.type == 'ORTHO'
                    if view.res_type == 'res_type_paper':
                        #row = col.row(align=True)
                        #row.menu(CAMERA_PAPER_SCALE_Presets.__name__, text=CAMERA_PAPER_SCALE_Presets.bl_label)
                        #row.operator(AddPaperScalePreset.bl_idname, text="", icon='ADD')
                        #row.operator(AddPaperScalePreset.bl_idname, text="", icon='REMOVE').remove_active = True

                        
                        row = col.row(align=True)
                        row.prop(view, 'paper_scale', text = "Scale")
                        row.prop(view, 'model_scale', text = ":")

                    else:
                        
                        #row = col.row(align=True)
                        #row.menu(CAMERA_PX_SCALE_Presets.__name__, text=CAMERA_PX_SCALE_Presets.bl_label)
                        #row.operator(AddPixelScalePreset.bl_idname, text="", icon='ADD')
                        #row.operator(AddPixelScalePreset.bl_idname, text="", icon='REMOVE').remove_active = True

                        row = col.row(align=True)
                        row.prop(view, 'pixel_scale', text = "Scale")
                        row.prop(view, 'model_scale', text = ":")

                    # A quick Test, If BlenderBIM is available, add its view specific properties here too
                    #try:
                    #    col = box.column(align=True)
                    #    col.prop(camera.BIMCameraProperties,'diagram_scale', text= 'BlenderBIM Scale')
                    #    col.operator('bim.cut_section')
                    #except:
                    #    pass

                    col = box.column(align=True)
                    row = col.row(align=True)
                    row.prop(view, 'start_frame', text = "Frame Range")
                    row.prop(view, 'end_frame', text = "")
 

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

                    scene = context.scene
                    ViewGen = scene.ViewGenerator
                    
                    newView = ViewGen.views.add()
                    newView.name = 'View ' + str(len(ViewGen.views))

                    context.area.tag_redraw()
                    return {'FINISHED'}
        return {'FINISHED'}

class M_ARCH_OP_Render_Preview(Operator):
    bl_idname = "measureit_arch.renderpreviewbutton"
    bl_label = "Render Veiw Preview"
    bl_description = " Create A Preview Render of this view to be used in sheet layouts. \n The Results can also be accessed in the Image Editor"
    bl_category = 'MeasureitArch'
    tag: IntProperty()

    # ------------------------------
    # Execute button action
    # ------------------------------
    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def execute(self, context):
        scene = context.scene
        ViewGen = scene.ViewGenerator
        view = ViewGen.views[ViewGen.active_index]

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
        render_results = render_main(self, context)
        if render_results[0] is True:
            self.report({'INFO'}, msg)
            if 'preview' in view:
                del view['preview']
            view['preview'] = render_results[1]
        del render_results

            

        return {'FINISHED'}


############################
#### LEGACY PRESET CODE ####
############################

class CAMERA_PX_Presets(Menu):
    bl_label = "Resolution Presets"
    default_lable = "Resolution Presets"
    preset_subdir = "pixel"
    preset_operator = "script.execute_preset"
    draw = Custom_Preset_Base.draw_preset

class AddPixelResPreset(Custom_Preset_Base, Operator):
    '''Add a Object Draw Preset'''
    bl_idname = "camera.add_pixel_res_preset"
    bl_label = "Add Camera Res Preset"
    preset_menu = "CAMERA_PX_Presets"

    # variable used for all preset values
    preset_defines = [
        "camera = bpy.context.camera"
        ]

    # properties to store in the preset
    preset_values = [
        "camera.width_px",
        "camera.height_px",
        "camera.percent_scale"
        ]

    # where to store the preset
    preset_subdir = "pixel"
       
class CAMERA_PX_SCALE_Presets(Menu):
    bl_label = "Pixel Scale"
    default_lable = "Pixel Scale"
    preset_subdir = "scale_pixel"
    preset_operator = "script.execute_preset"
    draw = Custom_Preset_Base.draw_preset

class AddPixelScalePreset(Custom_Preset_Base, Operator):
    '''Add a Object Draw Preset'''
    bl_idname = "camera.add_pixel_scale_preset"
    bl_label = "Add Camera Scale Preset"
    preset_menu = "CAMERA_PX_SCALE_Presets"

    # variable used for all preset values
    preset_defines = [
        "camera = bpy.context.camera"
        ]

    # properties to store in the preset
    preset_values = [
        "camera.pixel_scale",
        "camera.mod_scale",
        ]

    # where to store the preset
    preset_subdir = "scale_pixel"
    
class CAMERA_PAPER_Presets(Menu):
    bl_label = "Paper Size Presets"
    default_lable = "Paper Size Presets"
    preset_subdir = "paper"
    preset_operator = "script.execute_preset"
    draw = Custom_Preset_Base.draw_preset

class AddPaperResPreset(Custom_Preset_Base, Operator):
    bl_idname = "camera.add_paper_res_preset"
    bl_label = "Add Camera Res Preset"
    preset_menu = "CAMERA_PAPER_Presets"

    # variable used for all preset values
    preset_defines = [
        "camera = bpy.context.camera"
        ]

    # properties to store in the preset
    preset_values = [
        "camera.width",
        "camera.height",
        ]

    # where to store the preset
    preset_subdir = "paper"
    
class CAMERA_PAPER_SCALE_Presets(Menu):
    bl_label = "Paper Scale"
    default_lable = "Paper Scale"
    preset_subdir = "scale_paper"
    preset_operator = "script.execute_preset"
    draw = Custom_Preset_Base.draw_preset

class AddPaperScalePreset(Custom_Preset_Base, Operator):
    bl_idname = "camera.add_paper_scale_preset"
    bl_label = "Add paper scale preset"
    preset_menu = "CAMERA_PAPER_SCALE_Presets"

    # variable used for all preset values
    preset_defines = [
        "camera = bpy.context.camera"
        ]

    # properties to store in the preset
    preset_values = [
        "camera.paper_scale",
        "camera.mod_scale",
        ]

    # where to store the preset
    preset_subdir = "scale_paper"
