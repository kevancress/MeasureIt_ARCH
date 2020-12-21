import bpy
from .measureit_arch_main import SCENE_PT_Panel
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D, Scene, UIList, Menu, Collection
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


class HatchProperties(PropertyGroup):

    material: PointerProperty(type= bpy.types.Material)

    pattern: PointerProperty(name = 'Hatch Pattern', type=Collection)

    fill_color: FloatVectorProperty(name="Color",
            description="Color for the Item",
            default= (0.0,0.0,0.0, 1.0),
            min=0,
            max=1,
            subtype='COLOR',
            size=4,)
    
    line_color: FloatVectorProperty(name="Color",
            description="Color for the Item",
            default= (0.0,0.0,0.0, 1.0),
            min=0,
            max=1,
            subtype='COLOR',
            size=4,)
    
    lineWeight: FloatProperty(name="Line Weight",
                description="Lineweight",
                default = 1,
                soft_min = 1.0,
                step = 25,
                min = 0)





bpy.utils.register_class(HatchProperties)

class HatchContainer(PropertyGroup):
    active_index: IntProperty(name='Active Hatch Index', min=0, max=1000, default=0,
                                description='Index of the current Hatch')
    
    show_settings: BoolProperty(name='Show Hatch Settings', default=False)
    

    # Array of hatches
    hatches: CollectionProperty(type=HatchProperties) 

bpy.utils.register_class(HatchContainer)
Scene.HatchGenerator = bpy.props.PointerProperty(type=HatchContainer)

class DeleteHatchButton(Operator):
    bl_idname = "measureit_arch.deletehatchbutton"
    bl_label = "Delete Hatch"
    bl_description = "Delete a Hatch"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'} 
    tag: IntProperty()


    def execute(self, context):
        # Add properties

        Generator = context.scene.HatchGenerator
        Generator.hatches.remove(Generator.active_index)

        return {'FINISHED'}

class M_ARCH_UL_Hatches_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):    
            scene = bpy.context.scene
            
            if self.layout_type in {'DEFAULT', 'COMPACT'}:
                hatch = item
                layout.use_property_decorate = False
                row = layout.row(align=True)
                subrow = row.row()
                subrow.prop(hatch, "name", text="",emboss=False)
                row.prop(hatch,'material', text="", icon = 'MATERIAL_DATA')
                row.prop(hatch,'fill_color', text="",)

            elif self.layout_type in {'GRID'}:
                layout.alignment = 'CENTER'
                layout.label(text="", icon='MESH_CUBE')

class SCENE_PT_Hatches(Panel):
    """Creates a Panel in the Object properties window"""
    bl_parent_id = 'SCENE_PT_Panel'
    bl_label = "Hatches"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon= 'FILE_VOLUME')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        scene = context.scene
        HatchGen = scene.HatchGenerator

        row = layout.row()
        
        # Draw The UI List
        row.template_list("M_ARCH_UL_Hatches_list", "", HatchGen, "hatches", HatchGen, "active_index",rows=2, type='DEFAULT')
        
        # Operators Next to List
        col = row.column(align=True)
        col.operator("measureit_arch.addhatchbutton", icon='ADD', text="")
        op = col.operator("measureit_arch.deletehatchbutton", text="", icon="X")
        op.tag = HatchGen.active_index  # saves internal data
        
        #col.separator()
        #col.menu("SCENE_MT_styles_menu", icon='DOWNARROW_HLT', text="")

        
        # Settings Below List
        # I'll bring this back, but right now hatches only do fills so
        # Theres not really enough props for a full UI

        if len(HatchGen.hatches) > 0 and  HatchGen.active_index < len(HatchGen.hatches):

            hatch = HatchGen.hatches[HatchGen.active_index]

            if HatchGen.show_settings: settingsIcon = 'DISCLOSURE_TRI_DOWN'
            else: settingsIcon = 'DISCLOSURE_TRI_RIGHT'
            
            box = layout.box()
            col = box.column()
            row = col.row()
            row.prop(HatchGen, 'show_settings', text="", icon=settingsIcon,emboss=False)

            row.label(text= hatch.name + ' Settings:')

            if HatchGen.show_settings:
                col = box.column()
                col.prop(hatch,'fill_color', text="Fill Color",)
                col.prop(hatch,'line_color', text="Line Color",)
                col.prop(hatch,'lineWeight', text="Line Weight",)
                col.prop(hatch,'pattern', text="Pattern",)
        

              
 

class AddHatchButton(Operator):
    bl_idname = "measureit_arch.addhatchbutton"
    bl_label = "Add"
    bl_description = "Create A New Hatch"
    bl_category = 'MeasureitArch'
    
    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # Add properties

                    scene = context.scene
                    HatchGen = scene.HatchGenerator
                    
                    newHatch = HatchGen.hatches.add()
                    newHatch.name = 'Hatch ' + str(len(HatchGen.hatches))

                    context.area.tag_redraw()
                    return {'FINISHED'}
        return {'FINISHED'}

