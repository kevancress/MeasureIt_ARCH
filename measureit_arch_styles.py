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

from bpy.types import (
    PropertyGroup,
    Panel,
    Operator,
    Scene,
    UIList
)
from bpy.props import (
    CollectionProperty,
    IntProperty,
    BoolProperty,
    StringProperty,
    EnumProperty
)

from .measureit_arch_baseclass import DeletePropButton
from .measureit_arch_dimensions import (
    AlignedDimensionProperties,
    recalc_dimWrapper_index,
    draw_aligned_dimension_settings
)
from .measureit_arch_annotations import AnnotationProperties
from .measureit_arch_lines import LineProperties


def recalc_index(self, context):
    # ensure index's are accurate
    StyleGen = context.scene.StyleGenerator
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

# A Wrapper Object so multiple MeasureIt_ARCH element
# types can be shown in the same UI List


class StyleWrapper(PropertyGroup):
    itemType: EnumProperty(
        items=(('L', "Line", ""),
               ('A', "Annotation", ""),
               ('D', "Dimension", "")),
        name="Style Item Type",
        update=recalc_index)

    itemIndex: IntProperty(name='Item Index')


bpy.utils.register_class(StyleWrapper)


class StyleContainer(PropertyGroup):
    active_style_index: IntProperty(
        name='Active Style Index', min=0, max=1000, default=0,
        description='Index of the current Style')

    show_style_settings: BoolProperty(name='Show Style Settings', default=False)

    # Array of styles
    alignedDimensions: CollectionProperty(type=AlignedDimensionProperties)
    annotations: CollectionProperty(type=AnnotationProperties)
    line_groups: CollectionProperty(type=LineProperties)

    wrappedStyles: CollectionProperty(type=StyleWrapper)


bpy.utils.register_class(StyleContainer)
Scene.StyleGenerator = bpy.props.PointerProperty(type=StyleContainer)


class M_ARCH_UL_styles_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        StyleGen = bpy.context.scene.StyleGenerator
        lineStyles = StyleGen.line_groups
        annotationStyles = StyleGen.annotations
        dimensionStyles = StyleGen.alignedDimensions

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.use_property_decorate = False
            # Get correct item
            if item.itemType == 'L':
                item = lineStyles[item.itemIndex]
                draw_line_style_row(item, layout)

            elif item.itemType == 'A':
                item = annotationStyles[item.itemIndex]
                draw_annotation_style_row(item, layout)

            elif item.itemType == 'D':
                item = dimensionStyles[item.itemIndex]
                draw_dimension_style_row(item, layout)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')


class SCENE_PT_UIStyles(Panel):
    """Creates a Panel in the Object properties window"""
    bl_parent_id = 'SCENE_PT_Panel'
    bl_label = "Styles"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon='COLOR')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        scene = context.scene
        StyleGen = scene.StyleGenerator

        row = layout.row()

        # Draw The UI List
        row.template_list("M_ARCH_UL_styles_list", "", StyleGen, "wrappedStyles",
                          StyleGen, "active_style_index", rows=2, type='DEFAULT')

        # Operators Next to List
        col = row.column(align=True)
        col.operator("measureit_arch.addstylebutton", icon='ADD', text="")
        op = col.operator(
            "measureit_arch.listdeletepropbutton", text="", icon="X")
        op.tag = StyleGen.active_style_index  # saves internal data
        op.is_style = True

        col.separator()
        col.menu("SCENE_MT_styles_menu", icon='DOWNARROW_HLT', text="")

        # Settings Below List
        if (len(StyleGen.wrappedStyles) > 0 and
            StyleGen.active_style_index < len(StyleGen.wrappedStyles)):

            activeWrapperItem = StyleGen.wrappedStyles[StyleGen.active_style_index]

            if activeWrapperItem.itemType == 'L':
                item = StyleGen.line_groups[activeWrapperItem.itemIndex]
            if activeWrapperItem.itemType == 'A':
                item = StyleGen.annotations[activeWrapperItem.itemIndex]
            if activeWrapperItem.itemType == 'D':
                item = StyleGen.alignedDimensions[activeWrapperItem.itemIndex]

            if StyleGen.show_style_settings:
                settingsIcon = 'DISCLOSURE_TRI_DOWN'
            else:
                settingsIcon = 'DISCLOSURE_TRI_RIGHT'

            box = layout.box()
            col = box.column()
            row = col.row()
            row.prop(StyleGen, 'show_style_settings',
                     text="", icon=settingsIcon, emboss=False)

            row.label(text=item.name + ' Settings:')
            if StyleGen.show_style_settings:

                # Show Line Settings
                if activeWrapperItem.itemType == 'L':
                    draw_line_style_settings(item, box)
                # Show Annotation Settings
                if activeWrapperItem.itemType == 'A':
                    draw_annotation_style_settings(item, box)
                # Show Dimension Settings
                if activeWrapperItem.itemType == 'D':
                    draw_aligned_dimension_settings(item, box)


class SCENE_MT_styles_menu(bpy.types.Menu):
    bl_label = "Custom Menu"

    def draw(self, context):
        layout = self.layout

        delOp = layout.operator(
            "measureit_arch.deleteallitemsbutton", text="Delete All Styles", icon="X")
        delOp.is_style = True


# The Way this Operator handles style & dimension wrappers is
# Super Messy -- Clean this up later
class ListDeletePropButton(Operator):
    bl_idname = "measureit_arch.listdeletepropbutton"
    bl_label = "Delete property"
    bl_description = "Delete a property"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'}
    tag: IntProperty()
    item_type: StringProperty()
    is_style: BoolProperty()

    def execute(self, context):
        # Add properties
        if self.is_style:
            Generator = context.scene.StyleGenerator
            wrapper = Generator.wrappedStyles[self.tag]

        elif not self.is_style and self.item_type == 'D':
            obj = context.object
            Generator = obj.DimensionGenerator[0]
            wrapper = Generator.wrappedDimensions[self.tag]

        wrapperTag = self.tag
        self.item_type = wrapper.itemType
        self.tag = wrapper.itemIndex

        if self.is_style:
            Generator.wrappedStyles.remove(wrapperTag)
            recalc_index(self, context)

        else:
            Generator.wrappedDimensions.remove(wrapperTag)
            recalc_dimWrapper_index(self, context)

        DeletePropButton.tag = self.tag
        DeletePropButton.item_type = self.item_type
        DeletePropButton.is_style = True
        DeletePropButton.execute(self, context)
        return {'FINISHED'}


class AddStyleButton(Operator):
    bl_idname = "measureit_arch.addstylebutton"
    bl_label = "Add"
    bl_description = "Create A New Style (Select Type Below)"
    bl_category = 'MeasureitArch'

    styleType: EnumProperty(
        items=(('A', "Annotation", "Create a new Annotation Style", 'FONT_DATA', 1),
               ('L', "Line", "Create a new Line Style", 'MESH_CUBE', 2),
               ('D', "Dimension", "Create a new Dimension Style", 'DRIVER_DISTANCE', 3)),
        name="Type of Style to Add",
        description="Type of Style to Add")

    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # Add properties

                    scene = context.scene
                    StyleGen = scene.StyleGenerator
                    annotationStyles = StyleGen.annotations
                    lineStyles = StyleGen.line_groups
                    alignedDimStyles = StyleGen.alignedDimensions
                    styleWrappers = StyleGen.wrappedStyles

                    newWrapper = styleWrappers.add()

                    if self.styleType == 'A':
                        newStyle = annotationStyles.add()
                        newStyle.itemType = 'A'
                        newStyle.fontSize = 18
                        newStyle.lineWeight = 1
                        newStyle.textAlignment = 'L'
                        newStyle.name = 'Annotation Style ' + \
                            str(len(annotationStyles))
                        newWrapper.itemType = 'A'

                    elif self.styleType == 'L':
                        newStyle = lineStyles.add()
                        newStyle.itemType = 'L'
                        newStyle.lineWeight = 1
                        newStyle.lineDepthOffset = 1
                        newStyle.name = 'Line Style ' + str(len(lineStyles))
                        newWrapper.itemType = 'L'

                    else:
                        newStyle = alignedDimStyles.add()
                        newStyle.itemType = 'D'
                        newStyle.fontSize = 18
                        newStyle.textAlignment = 'C'
                        newStyle.lineWeight = 1
                        newStyle.name = 'Dimension Style ' + \
                            str(len(alignedDimStyles))
                        newWrapper.itemType = 'D'

                    recalc_index(self, context)
                    newStyle.is_style = True
                    context.area.tag_redraw()
                    return {'FINISHED'}
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


def draw_line_style_row(line, layout):
    row = layout.row(align=True)
    subrow = row.row()

    subrow.prop(line, "name", text="", emboss=False, icon='MESH_CUBE')

    if line.visible:
        visIcon = 'HIDE_OFF'
    else:
        visIcon = 'HIDE_ON'

        # if line.isOutline:
        #     outIcon = 'SEQ_CHROMA_SCOPE'
        # else:
        #     outIcon = 'FILE_3D'

    if line.lineDrawHidden:
        hiddenIcon = 'MOD_WIREFRAME'
    else:
        hiddenIcon = 'MESH_CUBE'

    subrow = row.row()
    subrow.scale_x = 0.5
    subrow.prop(line, 'color', emboss=True, text="")
    subrow.separator()
    subrow = row.row(align=True)
    # subrow.prop(line, 'isOutline', text="", toggle=True, icon=outIcon,emboss=False)
    subrow.prop(line, 'lineDrawHidden', text="",
                toggle=True, icon=hiddenIcon, emboss=False)
    subrow.prop(line, "visible", text="", icon=visIcon)


def draw_line_style_settings(line, layout):
    col = layout.column()
    col.prop_search(line, 'visibleInView', bpy.data,
                    'cameras', text='Visible In View')

    col.prop(line, 'color', text="Color")
    col.prop(line, 'lineWeight', text="Lineweight")
    col.prop(line, 'lineDepthOffset', text="Z Offset")

    col = layout.column(align=True)
    col.prop(line, 'lineOverExtension', text="Extension")
    col.prop(line, 'randomSeed', text="Seed")

    col = layout.column(align=True)
    if line.lineDrawHidden:
        col.enabled = True
    else:
        col.enabled = False
    col.prop(line, 'lineHiddenColor', text="Hidden Line Color")
    col.prop(line, 'lineHiddenWeight', text="Hidden Line Weight")

    col = layout.column(align=True)
    if line.lineDrawDashed or line.lineDrawHidden:
        col.enabled = True
    else:
        col.enabled = False
    col.prop(line, 'lineHiddenDashScale', text="Dash Scale")

    col = layout.column(align=True)
    col.prop(line, 'lineDrawDashed', text="Draw Dashed")
    col.prop(line, 'screenSpaceDashes', text="Screen Space Dashes")
    col.prop(line, 'lineDashSpace', text="Dash Spacing")
    col.prop(line, 'inFront', text="Draw In Front")
    col.prop(line, 'evalMods')


def draw_annotation_style_row(annotation, layout):
    row = layout.row(align=True)
    subrow = row.row()

    subrow.prop(annotation, "name", text="", emboss=False, icon='FONT_DATA')

    if annotation.visible:
        visIcon = 'HIDE_OFF'
    else:
        visIcon = 'HIDE_ON'

    subrow = row.row()
    subrow.scale_x = 0.6
    subrow.prop(annotation, 'color', text="")

    subrow = row.row(align=True)
    subrow.prop(annotation, "visible", text="", icon=visIcon, emboss=False)


def draw_annotation_style_settings(annotation, layout):
    col = layout.column()
    split = layout.split(factor=0.485)
    col = split.column()
    col.alignment = 'RIGHT'
    col.label(text='Font')
    col = split.column(align=True)
    col.template_ID(annotation, "font", open="font.open", unlink="font.unlink")
    col.prop_search(annotation, 'visibleInView', bpy.data,
                    'cameras', text='Visible In View')

    col = layout.column(align=True)
    col.prop(annotation, 'fontSize', text="Size")

    col = layout.column(align=True)
    col.prop(annotation, 'textAlignment', text='Alignment')
    col.prop(annotation, 'textPosition', text='Position')

    col = layout.column(align=True)
    col.prop(annotation, 'endcapA', text='End Cap')
    col.prop(annotation, 'endcapSize', text='Size')
    col.prop(annotation, 'endcapArrowAngle', text='Arrow Angle')

    col = layout.column(align=True)
    col.prop(annotation, 'lineWeight', text="Line Weight")
    col.prop(annotation, 'inFront', text="Draw In Front")
    col.prop(annotation, 'evalMods')
    col.prop(annotation, 'draw_leader', text='Draw Leader')


def draw_dimension_style_row(dim, layout):
    row = layout.row(align=True)
    subrow = row.row()

    subrow.prop(dim, "name", text="", emboss=False, icon='DRIVER_DISTANCE')

    if dim.visible:
        visIcon = 'HIDE_OFF'
    else:
        visIcon = 'HIDE_ON'

    subrow = row.row()
    subrow.scale_x = 0.6
    subrow.prop(dim, 'color', text="")

    subrow = row.row(align=True)
    subrow.prop(dim, "visible", text="", icon=visIcon, emboss=False)
