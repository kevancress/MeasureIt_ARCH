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

from bpy.types import Operator, UIList, Panel
from bpy.props import IntProperty, StringProperty, BoolProperty

from .measureit_arch_baseclass import DeletePropButton
from .measureit_arch_styles import recalc_index


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
                draw_line_row(item,layout)

            
            elif item.itemType == 'A':
                item = annotationStyles[item.itemIndex]
                draw_annotation_row(item,layout)

            elif item.itemType == 'D':
                item = dimensionStyles[item.itemIndex]
                draw_dimension_row(item,layout)

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
                    draw_line_settings(activeLineStyle,layout)
                # Show Annotation Settings
                if activeWrapperItem.itemType == 'A':
                    activeAnnoStyle = StyleGen.annotations[activeWrapperItem.itemIndex]
                    draw_annotation_settings(activeAnnoStyle,layout)
                # Show Dimension Settings
                if activeWrapperItem.itemType == 'D':
                    activeDimStyle = StyleGen.alignedDimensions[activeWrapperItem.itemIndex]
                    draw_dim_settings(activeDimStyle,layout)
                

            # Delete Operator (Move this to a menu button beside list)
            col = layout.column()
            col.label(text="") # For Spacing
            delOp = col.operator("measureit_arch.deleteallitemsbutton", text="Delete All Styles", icon="X")

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

def draw_line_row(line,layout):
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
    subrow.scale_x = 0.4
    subrow.prop(line, 'color',emboss=True, text="")
    subrow = row.row(align=True)
    subrow.prop(line, 'isOutline', text="", toggle=True, icon=outIcon,emboss=False)
    subrow.prop(line, 'lineDrawHidden', text="", toggle=True, icon=hiddenIcon)
    subrow.prop(line, "visible", text="", icon = visIcon)

def draw_line_settings(line,layout):
    col = layout.column(align=True)
    col.label(text= line.name + ' Settings')
    col.prop(line, 'color', text="Color")
    col.prop(line, 'lineWeight', text="Lineweight" )
    col.prop(line, 'lineDepthOffset', text="Z Offset")

def draw_annotation_row(annotation,layout):
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

def draw_annotation_settings(annotation,layout):
    col = layout.column()
    col.label(text=annotation.name  + ' Settings')

    split = layout.split(factor=0.485)
    col = split.column()
    col.alignment ='RIGHT'
    col.label(text='Font')
    col = split.column()
    col.template_ID(annotation, "font", open="font.open", unlink="font.unlink")

    col = layout.column(align=True)
    col.prop(annotation, 'lineWeight', text="Line Weight" )

    col = layout.column(align=True)
    col.prop(annotation, 'textResolution', text="Resolution")
    col.prop(annotation, 'fontSize', text="Size")
    col.prop(annotation, 'textAlignment', text='Alignment')
    col.prop(annotation, 'textPosition', text='Position')

def draw_dimension_row(dim,layout):
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

def draw_dim_settings(dim,layout):

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