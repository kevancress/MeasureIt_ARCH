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

from bpy.app.handlers import persistent
from bpy.types import (
    PropertyGroup,
    Panel,
    Operator,
    UIList
)
from bpy.props import (
    CollectionProperty,
    IntProperty,
    BoolProperty,
    StringProperty,
    EnumProperty
)

from .measureit_arch_baseclass import DeletePropButton, recalc_dimWrapper_index
from .measureit_arch_dimensions import AlignedDimensionProperties, \
    draw_alignedDimensions_settings
from .measureit_arch_annotations import AnnotationProperties
from .measureit_arch_lines import LineProperties


@persistent
def create_preset_styles(dummy):
    """ Handler called when a Blend file is loaded to create default styles. """
    context = bpy.context

    has_dimension_styles = any(
        style.itemType == 'alignedDimensions'
        for style in context.scene.StyleGenerator.wrapper)
    if not has_dimension_styles:
        add_aligned_dimension_style(context)

    has_annotation_styles = any(
        style.itemType == 'annotations'
        for style in context.scene.StyleGenerator.wrapper)
    if not has_annotation_styles:
        add_annotation_style(context)

    has_line_group_styles = any(
        style.itemType == 'line_groups'
        for style in context.scene.StyleGenerator.wrapper)
    if not has_line_group_styles:
        add_line_group_style(context)


def recalc_index(self, context):
    # ensure index's are accurate
    StyleGen = context.scene.StyleGenerator
    wrapper = StyleGen.wrapper
    id_l = 0
    id_a = 0
    id_d = 0
    for style in wrapper:
        if style.itemType == 'line_groups':
            style.itemIndex = id_l
            id_l += 1
        elif style.itemType == 'alignedDimensions':
            style.itemIndex = id_d
            id_d += 1
        elif style.itemType == 'annotations':
            style.itemIndex = id_a
            id_a += 1


class StyleWrapper(PropertyGroup):
    itemType: EnumProperty(
        items=(
            ('line_groups', "Line", ""),
            ('annotations', "Annotation", ""),
            ('alignedDimensions', "Dimension", "")),
        name="Style Item Type",
        update=recalc_index)

    itemIndex: IntProperty(name='Item Index')


class StyleContainer(PropertyGroup):
    active_style_index: IntProperty(
        name='Active Style Index', min=0, max=1000, default=0,
        description='Index of the current Style')

    show_style_settings: BoolProperty(
        name='Show Style Settings', default=False)

    # Array of styles
    alignedDimensions: CollectionProperty(type=AlignedDimensionProperties)
    annotations: CollectionProperty(type=AnnotationProperties)
    line_groups: CollectionProperty(type=LineProperties)

    wrapper: CollectionProperty(type=StyleWrapper)


class M_ARCH_UL_styles_list(UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        StyleGen = bpy.context.scene.StyleGenerator
        lineStyles = StyleGen.line_groups
        annotationStyles = StyleGen.annotations
        dimensionStyles = StyleGen.alignedDimensions

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.use_property_decorate = False
            # Get correct item
            if item.itemType == 'line_groups':
                item = lineStyles[item.itemIndex]
                draw_line_style_row(item, layout)

            elif item.itemType == 'annotations':
                item = annotationStyles[item.itemIndex]
                draw_annotation_style_row(item, layout)

            elif item.itemType == 'alignedDimensions':
                item = dimensionStyles[item.itemIndex]
                draw_dimension_style_row(item, layout)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')


class SCENE_PT_UIStyles(Panel):
    """ A panel in the Object properties window """

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
        row.template_list(
            "M_ARCH_UL_styles_list", "", StyleGen, "wrapper",
            StyleGen, "active_style_index", rows=2, type='DEFAULT')

        # Operators Next to List
        col = row.column(align=True)
        col.operator("measureit_arch.addstylebutton", icon='ADD', text="")
        op = col.operator(
            "measureit_arch.listdeletepropbutton", text="", icon="X")
        op.genPath = 'bpy.context.scene.StyleGenerator'
        op.tag = StyleGen.active_style_index  # saves internal data
        op.is_style = True

        col.separator()
        col.menu("SCENE_MT_styles_menu", icon='DOWNARROW_HLT', text="")

        # Settings Below List
        if (len(StyleGen.wrapper) > 0 and
            StyleGen.active_style_index < len(StyleGen.wrapper)):

            activeWrapperItem = StyleGen.wrapper[StyleGen.active_style_index]

            if activeWrapperItem.itemType == 'line_groups':
                item = StyleGen.line_groups[activeWrapperItem.itemIndex]
            if activeWrapperItem.itemType == 'annotations':
                item = StyleGen.annotations[activeWrapperItem.itemIndex]
            if activeWrapperItem.itemType == 'alignedDimensions':
                item = StyleGen.alignedDimensions[activeWrapperItem.itemIndex]

            if StyleGen.show_style_settings:
                settingsIcon = 'DISCLOSURE_TRI_DOWN'
            else:
                settingsIcon = 'DISCLOSURE_TRI_RIGHT'

            box = layout.box()
            col = box.column()
            row = col.row()
            row.prop(
                StyleGen, 'show_style_settings', text="", icon=settingsIcon,
                emboss=False)

            row.label(text='{} Settings:'.format(item.name))
            if StyleGen.show_style_settings:
                # Show Line Settings
                if activeWrapperItem.itemType == 'line_groups':
                    draw_line_style_settings(item, box)
                # Show Annotation Settings
                if activeWrapperItem.itemType == 'annotations':
                    draw_annotation_style_settings(item, box)
                # Show Dimension Settings
                if activeWrapperItem.itemType == 'alignedDimensions':
                    draw_alignedDimensions_settings(item, box)


class SCENE_MT_styles_menu(bpy.types.Menu):
    bl_label = "Custom Menu"

    def draw(self, context):
        layout = self.layout

        delOp = layout.operator(
            "measureit_arch.deleteallitemsbutton", text="Delete All Styles",
            icon="X")
        delOp.genPath = 'bpy.context.scene.StyleGenerator'
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
    genPath: StringProperty()
    item_type: StringProperty()
    is_style: BoolProperty()

    def execute(self, context):
        # Add properties
        Generator = eval(self.genPath)
        wrapper = Generator.wrapper[self.tag]

        wrapperTag = self.tag
        self.item_type = wrapper.itemType
        self.tag = wrapper.itemIndex

        Generator.wrapper.remove(wrapperTag)

        if self.is_style:
            recalc_index(self, context)
        else:
            recalc_dimWrapper_index(self, context)

        DeletePropButton.tag = self.tag
        DeletePropButton.genPath = self.genPath
        DeletePropButton.item_type = self.item_type
        DeletePropButton.is_style = self.is_style
        DeletePropButton.execute(self, context)
        return {'FINISHED'}


class AddStyleButton(Operator):
    bl_idname = "measureit_arch.addstylebutton"
    bl_label = "Add"
    bl_description = "Create A New Style (Select Type Below)"
    bl_category = 'MeasureitArch'

    styleType: EnumProperty(
        items=(
            ('annotations', "Annotation", "Create a new Annotation Style", 'FONT_DATA', 1),
            ('line_groups', "Line", "Create a new Line Style", 'MESH_CUBE', 2),
            ('alignedDimensions', "Dimension", "Create a new Dimension Style", 'DRIVER_DISTANCE', 3)),
        name="Type of Style to Add",
        description="Type of Style to Add")

    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    # Add properties
                    if self.styleType == 'annotations':
                        add_annotation_style(context)
                    elif self.styleType == 'line_groups':
                        add_line_group_style(context)
                    elif self.styleType == 'alignedDimensions':
                        add_aligned_dimension_style(context)
                    context.area.tag_redraw()
                    return {'FINISHED'}
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


def add_annotation_style(
        context, name='', font_size=18, line_weight=1, text_alignment='L'):
    annotation_styles = context.scene.StyleGenerator.annotations
    wrapper = context.scene.StyleGenerator.wrapper
    scene_props = context.scene.MeasureItArchProps

    if not name:
        name = 'Annotation Style {}'.format(len(annotation_styles) + 1)

    new_style = annotation_styles.add()
    new_style.itemType = 'annotations'
    new_style.name = name
    new_style.fontSize = font_size
    new_style.lineWeight = line_weight
    new_style.textAlignment = text_alignment

    new_wrapper = wrapper.add()
    new_wrapper.itemType = 'annotations'

    if not scene_props.default_annotation_style:
        scene_props.default_annotation_style = new_style.name

    recalc_index(None, context)
    return new_style


def add_line_group_style(context, name='', line_weight=1, line_depth_offset=1):
    line_styles = context.scene.StyleGenerator.line_groups
    wrapper = context.scene.StyleGenerator.wrapper
    scene_props = context.scene.MeasureItArchProps

    if not name:
        name = 'Line Style {}'.format(len(line_styles) + 1)

    new_style = line_styles.add()
    new_style.itemType = 'line_groups'
    new_style.name = name
    new_style.lineWeight = line_weight
    new_style.lineDepthOffset = line_depth_offset
    new_style.is_style = True

    new_wrapper = wrapper.add()
    new_wrapper.itemType = 'line_groups'

    if not scene_props.default_line_style:
        scene_props.default_line_style = new_style.name

    recalc_index(None, context)
    return new_style


def add_aligned_dimension_style(
        context, name='', font_size=18, text_alignment='C', line_weight=1):
    dimension_styles = context.scene.StyleGenerator.alignedDimensions
    wrapper = context.scene.StyleGenerator.wrapper
    scene_props = context.scene.MeasureItArchProps

    if not name:
        name = 'Dimension Style {}'.format(len(dimension_styles) + 1)

    new_style = dimension_styles.add()
    new_style.itemType = 'alignedDimensions'
    new_style.name = name
    new_style.fontSize = font_size
    new_style.textAlignment = text_alignment
    new_style.lineWeight = line_weight
    new_style.is_style = True

    new_wrapper = wrapper.add()
    new_wrapper.itemType = 'alignedDimensions'

    if not scene_props.default_dimension_style:
        scene_props.default_dimension_style = new_style.name

    recalc_index(None, context)
    return new_style


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
    subrow.prop(
        line, 'lineDrawHidden', text="", toggle=True, icon=hiddenIcon, emboss=False)
    subrow.prop(line, "visible", text="", icon=visIcon)


def draw_line_style_settings(line, layout):
    col = layout.column()
    col.prop_search(
        line, 'visibleInView', bpy.context.scene, 'view_layers', text='Visible In View')

    col.prop(line, 'color', text="Color")
    col.prop(line, 'lineWeight', text="Lineweight")
    col.prop(line, 'lineDepthOffset', text="Z Offset")

    col = layout.column(align=True)
    col.prop(line, 'lineOverExtension', text="Extension")
    # col.prop(line, 'randomSeed', text="Seed" )

    col = layout.column(align=True)
    if line.lineDrawHidden is True:
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
    col.prop(line, 'lineDashSpace', text="Dash Spacing")

    col = layout.column(align=True)
    col.prop(line, 'lineDrawDashed', text="Draw Dashed")
    col.prop(line, 'screenSpaceDashes', text="Screen Space Dashes")

    col.prop(line, 'inFront', text="Draw In Front")
    col.prop(line, 'evalMods')


def draw_annotation_style_row(annotation, layout):
    row = layout.row(align=True)
    subrow = row.row()

    subrow.prop(annotation, 'name', text="", emboss=False, icon='FONT_DATA')

    if annotation.visible:
        visIcon = 'HIDE_OFF'
    else:
        visIcon = 'HIDE_ON'

    subrow = row.row()
    subrow.scale_x = 0.6
    subrow.prop(annotation, 'color', text="")

    subrow = row.row(align=True)
    subrow.prop(annotation, 'visible', text="", icon=visIcon, emboss=False)


def draw_annotation_style_settings(annotation, layout):
    col = layout.column()
    split = layout.split(factor=0.485)
    col = split.column()
    col.alignment = 'RIGHT'
    col.label(text='Font')
    col = split.column(align=True)
    col.template_ID(annotation, 'font', open="font.open", unlink="font.unlink")

    col = layout.column(align=True)
    col.prop_search(
        annotation, 'visibleInView', bpy.context.scene, 'view_layers',
        text='Visible In View')

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
    col.prop(annotation, 'leader_length')
    col.prop(annotation, 'lineWeight', text="Line Weight")
    col.prop(annotation, 'inFront', text="Draw In Front")
    col.prop(annotation, 'evalMods')
    col.prop(annotation, 'draw_leader', text='Draw Leader')
    col.prop(annotation, 'align_to_camera')


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
