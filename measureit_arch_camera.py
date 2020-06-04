import bpy
from bpy.types import Panel, Menu, Operator
from rna_prop_ui import PropertyPanel
from bl_operators.presets import AddPresetBase
from .custom_preset_base import Custom_Preset_Base
import os
from bpy.app.handlers import persistent

class Initialize_Camera_Properties:
    lastCamera = None
    def update_checker(scene):
        currentCam = scene.camera
        if currentCam.data.use_camera_res:
            lastCam = Initialize_Camera_Properties.lastCamera
            if lastCam == None:
                lastCam = currentCam
                print ('Setting camera')
            if lastCam != currentCam:
                Initialize_Camera_Properties.update_manager(scene)
            Initialize_Camera_Properties.lastCamera = currentCam
    
    @persistent
    def update_manager(scene):
        if scene.camera.data.res_type == 'res_type_paper':
            Initialize_Camera_Properties.update_camera(scene)
        else:
            Initialize_Camera_Properties.update_camera_px(scene)
    
    def update_camera(scene):
        render = scene.render
        camera = scene.camera.data
        width = camera.width
        height = camera.height
        modelScale = camera.mod_scale
        paperScale = camera.paper_scale
        
        ppi = camera.res
        
        if camera.use_camera_res:
            render.resolution_percentage = 100
            render.resolution_x = width *  ppi * 39.3701
            render.resolution_y = height * ppi * 39.3701
        
            if width > height:
                camera.ortho_scale = (render.resolution_x/ppi/39.3701) * (modelScale/paperScale)
            else:
                camera.ortho_scale = (render.resolution_y/ppi/39.3701) * (modelScale/paperScale)
    
    def update_camera_px(scene):
        render = scene.render
        camera = scene.camera.data
        width_px = camera.width_px
        height_px = camera.height_px
        modelScale = camera.mod_scale
        pixelScale = camera.pixel_scale
        percentScale = camera.percent_scale
        
        if camera.use_camera_res:
            render.resolution_x = width_px
            render.resolution_y = height_px
            render.resolution_percentage = percentScale
        
            if width_px > height_px:
                camera.ortho_scale = (render.resolution_x) * (modelScale/(pixelScale*(percentScale/100)))
            else:
                camera.ortho_scale = (render.resolution_y) * (modelScale/(pixelScale*(percentScale/100)))
     
    def update(self,context):
        Initialize_Camera_Properties.update_manager(context.scene)
        

    def add_camera_to_render_name(scene):
        filename = scene.render.Filename
        cameraName = scene.Camera.data.name
        scene.render.Filename = filename + '_' + cameraName

   
    #Width Property
    bpy.types.Camera.width =  bpy.props.FloatProperty(
        name = "Width", 
        description = "Camera Width in Units", 
        unit = 'LENGTH',
        default = 0.43, 
        min = 0.0, 
        update = update
        )
    
    #Height Property
    bpy.types.Camera.height = bpy.props.FloatProperty(
        name = "Height", 
        description = "Camera Height in Units", 
        unit = 'LENGTH', 
        default = 0.28, 
        min = 0.0, 
        update = update
        )
        
    #Width_px Property
    bpy.types.Camera.width_px =  bpy.props.IntProperty(
        name = "X", 
        description = "Camera Width in Pixels", 
        subtype = 'PIXEL',
        default = 1920, 
        min = 4, 
        update = update,
        step = 100
        )
        
    #Width_px Property
    bpy.types.Camera.height_px =  bpy.props.IntProperty(
        name = "Y", 
        description = "Camera Height in Pixels", 
        subtype = 'PIXEL',
        default = 1080, 
        min = 4, 
        update = update,
        step = 100
        )
    
    #Percent Scale Property
    bpy.types.Camera.percent_scale =  bpy.props.IntProperty(
        name = "Percent Scale", 
        description = "Percentage scale for render resolution", 
        subtype = 'PERCENTAGE',
        default = 50, 
        min = 1,
        max = 100,
        update = update,
        step = 100
        )
        
    #PPI Property
    bpy.types.Camera.res = bpy.props.IntProperty(
        name = "res_prop", 
        description = "Resolution in Pixels Per Inch", 
        subtype = 'FACTOR', 
        default = 150, 
        min = 1, 
        soft_max = 600, 
        soft_min =50,
        update = update, 
        step = 1, 
        )
    
    #Model Length
    bpy.types.Camera.mod_scale = bpy.props.FloatProperty(
        name = "mod_scale", 
        description = "Length on Model", 
        unit = 'LENGTH', 
        default = .1, 
        min = 0.0, 
        update = update
        )
    
    #Paper Length
    bpy.types.Camera.paper_scale = bpy.props.FloatProperty(
        name = "paper_scale",
        description = "Length on Paper",
        unit = 'LENGTH',
        default = 1, min = 0.0, 
        update = update
        )
        
    #Pixel Length
    bpy.types.Camera.pixel_scale = bpy.props.IntProperty(
        name = "Pixel Scale",
        description = "Number of Pixels",
        subtype = 'PIXEL',
        default = 100, 
        min = 0, 
        update = update
        )
    
    #Enable/Disable
    bpy.types.Camera.use_camera_res = bpy.props.BoolProperty(
        name = "use_camera_scale",
        description = "Enable Per Camera Render Settings",
        update = update
        )
    
    #Resolution Type
    bpy.types.Camera.res_type = bpy.props.EnumProperty(
        items=[
            ('res_type_paper','Paper','Define Resolution by Paper Size and Pixels Per Inch'), 
            ('res_type_pixels','Pixels','Blender Standard, Define Resolution in Pixels')
            ],
        name ="Resolution Type",
        description = 'Method For Defining Render Size', 
        default = 'res_type_pixels',
        update = update
        #options = 'ENUM_FLAG'
        )
        
    #CameraName As Render Suffix
    bpy.types.Camera.add_camera_name = bpy.props.BoolProperty(
        name = "Add Camera Name to Filename",
        description = "Add the camera name to the end of output file name",
        )

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

class Camera_Res_Panel(Panel):
    bl_idname = "MEASUREIT_PT_Camera_panel"
    bl_label = "MeasureIt-ARCH Camera Resolution"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"
    
    @classmethod
    def poll(cls, context):
        return context.camera

    def draw_header(self, context):
        camera = context.camera

        self.layout.prop(camera, "use_camera_res", text="")
        
        
    def draw(self, context):
        scene = context.scene
        camera = context.camera
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.
        
        layout.active=camera.use_camera_res
        col = layout.column()
        col.operator("bind_marker.bind_marker", text = "Bind Camera To Frame", icon = 'CAMERA_DATA')
        col.prop(camera, "type", text="Camera Type")
        col.row().prop(camera, 'res_type', expand=True)
 

        if camera.res_type == 'res_type_paper':
            
            col = layout.column()

            col = layout.column(align=True)
            split = layout.split(factor=0.4)
            col = split.column()
            col.alignment ='RIGHT'
            row = split.row(align=True)

            row.menu(CAMERA_PAPER_Presets.__name__, text=CAMERA_PAPER_Presets.bl_label)
            row.operator(AddPaperResPreset.bl_idname, text="", icon='ADD')
            row.operator(AddPaperResPreset.bl_idname, text="", icon='REMOVE').remove_active = True
            
            col = layout.column(align=True)
            col.prop(camera,'width', text = 'Width:')
            col.prop(camera,'height', text = 'Height:')
            col.prop(camera,'res', text = 'Resolution (PPI):') 
                    
        else:
            col = layout.column()

            col = layout.column(align=True)
            split = layout.split(factor=0.4)
            col = split.column()
            col.alignment ='RIGHT'
            row = split.row(align=True)
            
            row.menu(CAMERA_PX_Presets.__name__, text=CAMERA_PX_Presets.bl_label)
            row.operator(AddPixelResPreset.bl_idname, text="", icon='ADD')
            row.operator(AddPixelResPreset.bl_idname, text="", icon='REMOVE').remove_active = True
            
            col = layout.column(align=True)
            col.prop(camera,'width_px', text="Resolution X")
            col.prop(camera,'height_px')
            col.prop(camera,'percent_scale', text="%")
            

bpy.utils.register_class(Camera_Res_Panel)


class Bind_Marker(bpy.types.Operator):
    bl_idname = "bind_marker.bind_marker"
    bl_label = "Bind Marker"
    bl_description = "Makes this camera the active camera on your current frame"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene
        frame = scene.frame_current
        camera = context.camera
        
        for marker in scene.timeline_markers:
            if marker.name == camera.name:
                scene.timeline_markers.remove(marker)
       
        for marker in scene.timeline_markers:
            if marker.frame == frame:
                scene.timeline_markers.remove(marker)
        
        marker = scene.timeline_markers.new(camera.name,frame=frame)
        scene.camera = context.object
        marker.camera = context.object
        
        return {"FINISHED"}


class Camera_Scale_Panel(Panel):

    bl_idname = "MEASUREIT_PT_Camera_Scale_panel"
    bl_label = "Orthographic Scale"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"
    bl_parent_id ="MEASUREIT_PT_Camera_panel"

    @classmethod
    def poll(cls, context):
        return context.camera


    def draw(self, context):
        camera = context.camera
        layout = self.layout
        layout.active = camera.type == 'ORTHO'
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.
        
        col = layout.column()

        if camera.res_type == 'res_type_paper':
            row = col.row(align=True)
            row.menu(CAMERA_PAPER_SCALE_Presets.__name__, text=CAMERA_PAPER_SCALE_Presets.bl_label)
            row.operator(AddPaperScalePreset.bl_idname, text="", icon='ADD')
            row.operator(AddPaperScalePreset.bl_idname, text="", icon='REMOVE').remove_active = True
            
            col = layout.column(align=True)
            col.prop(camera, 'paper_scale', text = "Paper:")
            col.prop(camera, 'mod_scale', text = "Model:")

        else:
            
            row = col.row(align=True)
            
            row.menu(CAMERA_PX_SCALE_Presets.__name__, text=CAMERA_PX_SCALE_Presets.bl_label)
            row.operator(AddPixelScalePreset.bl_idname, text="", icon='ADD')
            row.operator(AddPixelScalePreset.bl_idname, text="", icon='REMOVE').remove_active = True

            col = layout.column(align=True)
            col.prop(camera, 'pixel_scale', text = "Pixels:")
            col.prop(camera, 'mod_scale', text = "Model:")

