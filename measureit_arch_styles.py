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
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D, Scene
from bpy.props import (
        CollectionProperty,
        FloatVectorProperty,
        IntProperty,
        BoolProperty,
        StringProperty,
        FloatProperty,
        EnumProperty,
        )
from .measureit_arch_dimensions import AlignedDimensionProperties, add_alignedDimension_item
from .measureit_arch_annotations import AnnotationProperties, add_annotation_item
from .measureit_arch_lines import LineProperties, add_line_item


class StyleContainer(PropertyGroup):
    style_num: IntProperty(name='Number of styles', min=0, max=1000, default=0,
                                description='Number total of measureit_arch Dimension Styles')
    
    active_style_index: IntProperty(name='Active Style Index', min=0, max=1000, default=0,
                                description='Index of the current Style')
            
    # Array of styles
    alignedDimensions: CollectionProperty(type=AlignedDimensionProperties)
    annotations: CollectionProperty(type=AnnotationProperties)
    line_groups: CollectionProperty(type=LineProperties)
bpy.utils.register_class(StyleContainer)
Scene.StyleGenerator = CollectionProperty(type=StyleContainer)

class MeasureitArchDimensionSettingsPanel(Panel):
    bl_idname = "measureit_arch.settings_panel"
    bl_label = "Dimension Settings"
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
        
        col = layout.column(align = True)
        col.prop(scene, 'measureit_arch_gl_precision', text="Precision")
        col.prop(scene, 'measureit_arch_units')

        col = layout.column(align=True)
        col.prop(scene, 'measureit_arch_gl_show_d', text="Distances", toggle=True, icon="DRIVER_DISTANCE")
        col.prop(scene, 'measureit_arch_gl_show_n', text="Texts", toggle=True, icon="FONT_DATA")
        #col.prop(scene, 'measureit_arch_hide_units', text="Units", toggle=True, icon="DRIVER_DISTANCE")
        
        # Scale factor
        col = layout.column(align = True)
        col.use_property_split= True
        col.alignment = 'RIGHT'
        col.label(text = 'Override:')
        col.prop(scene, 'measureit_arch_scale', text="Scale",toggle=True,icon="EMPTY_ARROWS")
        col.prop(scene, 'measureit_arch_ovr', text="Style",toggle=True,icon="TRACKING_FORWARDS_SINGLE")

        if scene.measureit_arch_scale is True:
            scaleBox = layout.box()
            scaleBox.label(text='Scale Override')
            col = scaleBox.column(align = True)
            col.prop(scene, 'measureit_arch_scale_color', text="Color")
            col.prop(scene, 'measureit_arch_scale_factor', text="Factor")

            col = scaleBox.column(align = True)
            col.prop(scene, 'measureit_arch_gl_scaletxt', text="Text")
            col.prop(scene, 'measureit_arch_scale_font', text="Font Size")
            col.prop(scene, 'measureit_arch_scale_precision', text="Precision")
            
            col = scaleBox.column(align = True)
            col.prop(scene, 'measureit_arch_scale_pos_x')
            col.prop(scene, 'measureit_arch_scale_pos_y')

        # Override
        
        if scene.measureit_arch_ovr is True:
            styleBox = layout.box()
            styleBox.label(text='Style Override')
            col = styleBox.column(align = True)
            col.prop(scene, 'measureit_arch_ovr_color', text="Colour")
            col.prop(scene, 'measureit_arch_ovr_width', text="Width")
            col = styleBox.column(align = True)
            col.prop(scene, 'measureit_arch_ovr_font', text="Font Size")
            col.prop(scene, 'measureit_arch_ovr_font_align', text="Alignment")
            if scene.measureit_arch_ovr_font_align == 'L':
                col.prop(scene, 'measureit_arch_ovr_font_rotation', text="Rotation")

class MeasureitArchDimensionStylesPanel(Panel):
    bl_idname = "measureit_arch.dim_styles"
    bl_label = "Styles"
    bl_space_type = 'PROPERTIES'
    bl_region_type = "WINDOW"
    bl_context = 'scene'
    bl_options = {'DEFAULT_CLOSED'}

    
    # ------------------------------
    # Draw UI
    # ------------------------------
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        scene = context.scene
        #-------------------
        # Add Styles to Panel
        #--------------------
        col = layout.column()
        
        
        if 'StyleGenerator' in context.scene:          
            StyleGen = scene.StyleGenerator[0]
            col.operator("measureit_arch.addstylebutton", text="Add")
            
            col = layout.column(align=True)
            row = col.row(align=True)
            exp = row.operator("measureit_arch.expandcollapseallpropbutton", text="Expand All", icon="ADD")
            exp.state = True
            exp.is_style = True

            clp = row.operator("measureit_arch.expandcollapseallpropbutton", text="Collapse All", icon="REMOVE")
            clp.state = False
            clp.is_style = True

            annotationStyles = StyleGen.annotations
            lineStyles = StyleGen.line_groups
            alignedDimStyles = StyleGen.alignedDimensions
            
            
            idx = 0
            for annoStyle in annotationStyles:
                add_annotation_item(layout,idx,annoStyle)
                idx += 1

            idx = 0
            for alignedDimStyle in alignedDimStyles:
                add_alignedDimension_item(layout,idx,alignedDimStyle)
                idx += 1

            idx = 0
            for lineStyle in lineStyles:
                add_line_item(layout,idx,lineStyle)
                idx += 1
            
            col = layout.column()
            delOp = col.operator("measureit_arch.deleteallitemsbutton", text="Delete All Styles", icon="X")
            delOp.is_style = True
        else:
            col.operator("measureit_arch.addstylebutton", text="Use Styles", icon="ADD")

class AddStyleButton(Operator):
    bl_idname = "measureit_arch.addstylebutton"
    bl_label = "Add"
    bl_description = "Create A New Style (Select Type Below)"
    bl_category = 'MeasureitArch'
    
    styleType: EnumProperty(
        items=(('A', "Annotation", "Create a new Annotation Style",'FONT_DATA',1),
                ('L', "Line", "Create a new Line Style",'MESH_CUBE',2),
                ('D', "Dimension", "Create a new Dimension Style",'DRIVER_DISTANCE',3)),
        name="Type of Style to Add",
        description="Type of Style to Add")

    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # Add properties
                    scene = context.scene
                    if 'StyleGenerator' not in bpy.context.scene:
                        
                        return {'FINISHED'}

                    StyleGen = scene.StyleGenerator[0]
                    annotationStyles = StyleGen.annotations
                    lineStyles = StyleGen.line_groups
                    alignedDimStyles = StyleGen.alignedDimensions
                    
                    if self.styleType is 'A':
                        newStyle = annotationStyles.add()
                        newStyle.itemType = 'A'
                    elif self.styleType is 'L':
                        newStyle = lineStyles.add()
                        newStyle.itemType = 'L'
                    else:
                        newStyle = alignedDimStyles.add()
                        newStyle.itemType = 'D'
                    
                    newStyle.is_style = True
                    context.area.tag_redraw()
                    return {'FINISHED'}
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        if 'StyleGenerator' in context.scene:
            return wm.invoke_props_dialog(self)
        else:
            context.scene.StyleGenerator.add()
            return {'FINISHED'}

    
       
