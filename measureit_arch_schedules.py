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


class ScheduleProperties(PropertyGroup):


    date_folder: BoolProperty(name= "Date Folder",
                description= "Adds a Folder with todays date to the end of the output path",
                default=False)

    output_path: StringProperty(
                name="Output Path",
                description="Render Output Path for this Schedule",
                subtype = 'FILE_PATH',
                default="",
                )

bpy.utils.register_class(ScheduleProperties)

class ScheduleContainer(PropertyGroup):
    active_index: IntProperty(name='Active Schedule Index', min=0, max=1000, default=0,
                                description='Index of the current Schedule')
    
    show_settings: BoolProperty(name='Show Schedule Settings', default=False)

    # Array of schedules
    schedules: CollectionProperty(type=ScheduleProperties) 

bpy.utils.register_class(ScheduleContainer)
Scene.ScheduleGenerator = bpy.props.PointerProperty(type=ScheduleContainer)

class DeleteScheduleButton(Operator):
    bl_idname = "measureit_arch.deleteschedulebutton"
    bl_label = "Delete Schedule"
    bl_description = "Delete a Schedule"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'} 
    tag: IntProperty()


    def execute(self, context):
        # Add properties

        Generator = context.scene.ScheduleGenerator
        Generator.schedules.remove(Generator.active_index)

        return {'FINISHED'}

class DuplicateScheduleButton(Operator):
    bl_idname = "measureit_arch.duplicateschedulebutton"
    bl_label = "Delete Schedule"
    bl_description = "Delete a Schedule"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'} 
    tag: IntProperty()

    #@classmethod
    #def poll(cls, context):
    #    Generator = context.scene.ScheduleGenerator
    #   
    #    try:
    #        ActiveSchedule = Generator.shedules[Generator.active_index]
    #        return True
    #    except:
    #        return False

    def execute(self, context):
        # Add properties


        Generator = context.scene.ScheduleGenerator
        ActiveSchedule = Generator.schedules[Generator.active_index]
        newSchedule = Generator.schedules.add()
        newSchedule.name = ActiveSchedule.name + ' copy'

        # Get props to loop through
        for key in Generator.schedules[Generator.active_index].__annotations__.keys():
            try:
                newSchedule[key] = ActiveSchedule[key]
            except:
                pass

        return {'FINISHED'}

class M_ARCH_UL_Schedules_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):    
            scene = bpy.context.scene
            
            if self.layout_type in {'DEFAULT', 'COMPACT'}:
                schedule = item
                layout.use_property_decorate = False
                row = layout.row(align=True)
                subrow = row.row()
                subrow.prop(schedule, "name", text="",emboss=False)

            elif self.layout_type in {'GRID'}:
                layout.alignment = 'CENTER'
                layout.label(text="", icon='MESH_CUBE')

class SCENE_PT_Schedules(Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "MeasureIt_ARCH Schedules"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        scene = context.scene
        ScheduleGen = scene.ScheduleGenerator

        row = layout.row()
        
        # Draw The UI List
        row.template_list("M_ARCH_UL_Schedules_list", "", ScheduleGen, "schedules", ScheduleGen, "active_index",rows=2, type='DEFAULT')
        
        # Operators Next to List
        col = row.column(align=True)
        col.operator("measureit_arch.addschedulebutton", icon='ADD', text="")
        op = col.operator("measureit_arch.deleteschedulebutton", text="", icon="X")
        op.tag = ScheduleGen.active_index  # saves internal data
        
        col.separator()
        col.menu("SCENE_MT_Schedules_menu", icon='DOWNARROW_HLT', text="")

        
        # Settings Below List
        if len(ScheduleGen.schedules) > 0 and  ScheduleGen.active_index < len(ScheduleGen.schedules):

            schedule = ScheduleGen.schedules[ScheduleGen.active_index]

            if ScheduleGen.show_settings: settingsIcon = 'DISCLOSURE_TRI_DOWN'
            else: settingsIcon = 'DISCLOSURE_TRI_RIGHT'
            
            box = layout.box()
            col = box.column()
            row = col.row()
            row.prop(ScheduleGen, 'show_settings', text="", icon=settingsIcon,emboss=False)

            row.label(text= schedule.name + ' Settings:')

            if ScheduleGen.show_settings:
                col = box.column()
                  
 
class SCENE_MT_Schedules_menu(bpy.types.Menu):
    bl_label = "Custom Menu"

    def draw(self,context):
        layout = self.layout
        scene = context.scene

        op = layout.operator('measureit_arch.duplicateschedulebutton', text="Duplicate Selected Schedule", icon='DUPLICATE')



class AddScheduleButton(Operator):
    bl_idname = "measureit_arch.addschedulebutton"
    bl_label = "Add"
    bl_description = "Create A New Schedule"
    bl_category = 'MeasureitArch'
    
    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # Add properties

                    scene = context.scene
                    ScheduleGen = scene.ScheduleGenerator
                    
                    newSchedule = ScheduleGen.schedules.add()
                    newSchedule.name = 'Schedule ' + str(len(ScheduleGen.schedules))

                    context.area.tag_redraw()
                    return {'FINISHED'}
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
