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
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D, Scene, UIList
from bpy.props import (
        CollectionProperty,
        FloatVectorProperty,
        IntProperty,
        BoolProperty,
        StringProperty,
        FloatProperty,
        EnumProperty,
        PointerProperty
        )

from .measureit_arch_baseclass import DeletePropButton
from .measureit_arch_dimensions import AlignedDimensionProperties, add_alignedDimension_item
from .measureit_arch_annotations import AnnotationProperties, add_annotation_item
from .measureit_arch_lines import LineProperties, add_line_item

def recalc_index(self,context):
    #ensure index's are accurate
    StyleGen = context.scene.StyleGenerator[0]
    wrappedStyles = StyleGen.wrappedStyles
    id_l = 0
    id_a = 0
    id_d = 0
    for style in wrappedStyles:
        if style.itemType == 'L':
            style.itemIndex = id_l
            id_l += 1
        elif style.itemType == 'D':
            style.itemIndex = id_d
            id_d += 1
        elif style.itemType == 'A':
            style.itemIndex = id_a
            id_a += 1


class StyleWrapper(PropertyGroup):
    itemType:EnumProperty(
                items=(('L', "Line", ""),
                        ('A', "Annotation", ""),
                        ('D', "Dimension", "")),
                name="align Font",
                description="Set Font Position",
                update=recalc_index)
    itemIndex: IntProperty(name='Item Index')

bpy.utils.register_class(StyleWrapper)

class StyleContainer(PropertyGroup):
    active_style_index: IntProperty(name='Active Style Index', min=0, max=1000, default=0,
                                description='Index of the current Style')
            
    # Array of styles
    alignedDimensions: CollectionProperty(type=AlignedDimensionProperties)
    annotations: CollectionProperty(type=AnnotationProperties)
    line_groups: CollectionProperty(type=LineProperties)
    wrappedStyles: CollectionProperty(type=StyleWrapper)
    
bpy.utils.register_class(StyleContainer)
Scene.StyleGenerator = CollectionProperty(type=StyleContainer)

class M_ARCH_UL_styles_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        StyleGen = bpy.context.scene.StyleGenerator[0]
        lineStyles = StyleGen.line_groups
        annotationStyles = StyleGen.annotations
        dimensionStyles= StyleGen.alignedDimensions
    
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.use_property_decorate = False
            # Get correct item
            if item.itemType == 'L':
                item = lineStyles[item.itemIndex]
                draw_line_style_row(item,layout)

            
            elif item.itemType == 'A':
                item = annotationStyles[item.itemIndex]
                draw_annotation_style_row(item,layout)

            elif item.itemType == 'D':
                item = dimensionStyles[item.itemIndex]
                draw_dimension_style_row(item,layout)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')

class SCENE_PT_UIStyles(Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "MeasureIt-ARCH Styles"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        
        obj = context.object
        if 'StyleGenerator' in context.scene:     
            scene = context.scene
            StyleGen = scene.StyleGenerator[0]

            row = layout.row()
            
            # Draw The UI List
            row.template_list("M_ARCH_UL_styles_list", "", StyleGen, "wrappedStyles", StyleGen, "active_style_index",rows=2, type='DEFAULT')
            
            # Operators Next to List
            col = row.column(align=True)
            col.operator("measureit_arch.addstylebutton", icon='ADD', text="")
            op = col.operator("measureit_arch.listdeletepropbutton", text="", icon="X")
            op.tag = StyleGen.active_style_index  # saves internal data

            
            # Settings Below List
            col = layout.column()
            if len(StyleGen.wrappedStyles) > 0 and  StyleGen.active_style_index < len(StyleGen.wrappedStyles):
                activeWrapperItem = StyleGen.wrappedStyles[StyleGen.active_style_index]
                # Show Line Settings
                if activeWrapperItem.itemType == 'L':
                    activeLineStyle = StyleGen.line_groups[activeWrapperItem.itemIndex]
                    draw_line_style_settings(activeLineStyle,layout)
                # Show Annotation Settings
                if activeWrapperItem.itemType == 'A':
                    activeAnnoStyle = StyleGen.annotations[activeWrapperItem.itemIndex]
                    draw_annotation_style_settings(activeAnnoStyle,layout)
                # Show Dimension Settings
                if activeWrapperItem.itemType == 'D':
                    activeDimStyle = StyleGen.alignedDimensions[activeWrapperItem.itemIndex]
                    draw_dim_style_settings(activeDimStyle,layout)
                

            # Delete Operator (Move this to a menu button beside list)
            col = layout.column()
            col.label(text="") # For Spacing
            delOp = col.operator("measureit_arch.deleteallitemsbutton", text="Delete All Styles", icon="X")
        else:
            
            layout.operator("measureit_arch.addstylebutton", text="Use Styles", icon="ADD")

class ListDeletePropButton(Operator):

    bl_idname = "measureit_arch.listdeletepropbutton"
    bl_label = "Delete property"
    bl_description = "Delete a property"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'} 
    tag= IntProperty()
    item_type: StringProperty()
    is_style: BoolProperty()

    def execute(self, context):
        # Add properties

        StyleGen = context.scene.StyleGenerator[0]
        wrapper = StyleGen.wrappedStyles[self.tag]

        wrapperTag = self.tag
        self.item_type = wrapper.itemType
        self.tag = wrapper.itemIndex
        self.is_style = True

        StyleGen.wrappedStyles.remove(wrapperTag)

        DeletePropButton.tag = self.tag
        DeletePropButton.item_type = self.item_type
        DeletePropButton.is_style = True
        DeletePropButton.execute(self,context)

        recalc_index(self,context)
        return {'FINISHED'}

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
                        bpy.context.scene.StyleGenerator.add()
                        return {'FINISHED'}

                    StyleGen = scene.StyleGenerator[0]
                    annotationStyles = StyleGen.annotations
                    lineStyles = StyleGen.line_groups
                    alignedDimStyles = StyleGen.alignedDimensions
                    styleWrappers = StyleGen.wrappedStyles

                    newWrapper = styleWrappers.add()

                    if self.styleType is 'A':
                        newStyle = annotationStyles.add()
                        newStyle.itemType = 'A'
                        newStyle.fontSize = 24
                        newStyle.lineWeight = 1
                        newStyle.name = 'Annotation Style ' + str(len(annotationStyles))
                        newWrapper.itemType = 'A'

                    elif self.styleType is 'L':
                        newStyle = lineStyles.add()
                        newStyle.itemType = 'L'
                        newStyle.lineWeight = 1
                        newStyle.lineDepthOffset =1
                        newStyle.name = 'Line Style ' + str(len(lineStyles))
                        newWrapper.itemType = 'L'

                    else:
                        newStyle = alignedDimStyles.add()
                        newStyle.itemType = 'D'
                        newStyle.fontSize = 24
                        newStyle.lineWeight = 1
                        newStyle.name = 'Dimension Style ' + str(len(alignedDimStyles))
                        newWrapper.itemType = 'D'
                    
                    recalc_index(self,context)
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

def draw_line_style_row(line,layout):
    row = layout.row(align=True)
    subrow = row.row()

    subrow.prop(line, "name", text="",emboss=False,icon='MESH_CUBE')
    
    if line.visible: visIcon = 'HIDE_OFF'
    else: visIcon = 'HIDE_ON'

    if line.isOutline: outIcon = 'SEQ_CHROMA_SCOPE' 
    else: outIcon = 'VOLUME'

    if line.lineDrawHidden: hiddenIcon = 'MOD_WIREFRAME'
    else: hiddenIcon = 'MESH_CUBE'

    subrow = row.row()
    subrow.scale_x = 0.5
    subrow.prop(line, 'color',emboss=True, text="")
    subrow = row.row(align=True)
    subrow.prop(line, 'isOutline', text="", toggle=True, icon=outIcon,emboss=False)
    subrow.prop(line, 'lineDrawHidden', text="", toggle=True, icon=hiddenIcon)
    subrow.prop(line, "visible", text="", icon = visIcon)

def draw_line_style_settings(line,layout):
    col = layout.column(align=True)
    col.label(text= line.name + ' Settings')
    col.prop(line, 'color', text="Color")
    col.prop(line, 'lineWeight', text="Lineweight" )
    col.prop(line, 'lineDepthOffset', text="Z Offset")

    
    col = layout.column(align=True)
    if line.lineDrawHidden is True: col.enabled = True
    else: col.enabled = False
    col.prop(line, 'lineHiddenColor', text="Hidden Line Color")
    col.prop(line, 'lineHiddenWeight',text="Hidden Line Weight")
    col.prop(line, 'lineHiddenDashScale',text="Dash Scale")

def draw_annotation_style_row(annotation,layout):
    row = layout.row(align=True)
    subrow = row.row()

    subrow.prop(annotation, "name", text="",emboss=False,icon='FONT_DATA')
    
    if annotation.visible: visIcon = 'HIDE_OFF'
    else: visIcon = 'HIDE_ON'
    
    subrow = row.row()
    subrow.scale_x = 0.6
    subrow.prop(annotation, 'color', text="" )

    subrow = row.row(align=True)
    subrow.prop(annotation, "visible", text="", icon = visIcon,emboss=False)

def draw_annotation_style_settings(annotation,layout):
    col = layout.column()
    col.label(text=annotation.name  + ' Settings')

    split = layout.split(factor=0.485)
    col = split.column()
    col.alignment ='RIGHT'
    col.label(text='Font')
    col = split.column(align=True)
    col.template_ID(annotation, "font", open="font.open", unlink="font.unlink")

    col = layout.column(align=True)
    col.prop(annotation, 'textResolution', text="Resolution")
    col.prop(annotation, 'fontSize', text="Size")

    col = layout.column(align=True)   
    col.prop(annotation, 'textAlignment', text='Alignment')
    col.prop(annotation, 'textPosition', text='Position')

    col = layout.column(align=True)
    col.prop(annotation, 'lineWeight', text="Line Weight" )

def draw_dimension_style_row(dim,layout):
    row = layout.row(align=True)
    subrow = row.row()

    subrow.prop(dim, "name", text="",emboss=False,icon='DRIVER_DISTANCE')

    if dim.visible: visIcon = 'HIDE_OFF'
    else: visIcon = 'HIDE_ON'
    
    subrow = row.row()
    subrow.scale_x = 0.6
    subrow.prop(dim, 'color', text="" )

    subrow = row.row(align=True)
    subrow.prop(dim, "visible", text="", icon = visIcon,emboss=False)

def draw_dim_style_settings(dim,layout):

    col = layout.column()
    col.label(text=dim.name  + ' Settings')
    
    split = layout.split(factor=0.485)
    col = split.column()
    col.alignment ='RIGHT'
    col.label(text='Font')
    col = split.column()

    col.template_ID(dim, "font", open="font.open", unlink="font.unlink")

    col = layout.column(align=True)
    col.prop(dim,'dimViewPlane', text='View Plane')
    col.prop_search(dim,'dimVisibleInView', bpy.data, 'cameras',text='Visible In View')
    col.prop(dim,'lineWeight',text='Line Weight')

    col = layout.column(align=True)
    col.prop(dim,'fontSize',text='Font Size')
    col.prop(dim,'textResolution',text='Resolution')
    col.prop(dim,'textAlignment',text='Alignment')
    col.prop(dim,'textPosition',text='Position')

    col = layout.column(align=True)
    col.prop(dim,'endcapA', text='Arrow Start')
    col.prop(dim,'endcapB', text='End')
    col.prop(dim,'endcapSize', text='Arrow Size')

