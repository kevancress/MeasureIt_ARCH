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
# Author: Kevan Cress
#
# ----------------------------------------------------------

import bpy

from bpy.types import PropertyGroup, Panel, Object, Operator, UIList, Scene
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, \
    BoolProperty, StringProperty, PointerProperty


class SheetViewProperties(PropertyGroup):

    rotation: FloatVectorProperty(
        name='annotationOffset',
        description='Rotation for Annotation',
        default=(0.0, 0.0, 0.0),
        subtype='EULER')

    location: FloatVectorProperty(
        name='annotationOffset',
        description='Offset for Annotation',
        default=(0.0, 0.0, 0.0),
        subtype='TRANSLATION')

    view: StringProperty(name="View Name")

    scene: PointerProperty(type=Scene)


bpy.utils.register_class(SheetViewProperties)


class SheetViewContainer(PropertyGroup):

    active_index: IntProperty(name='Active Sheet View Index')

    show_settings: BoolProperty(name='Show Sheet View Settings', default=False)

    # Array of segments
    sheet_views: CollectionProperty(type=SheetViewProperties)


bpy.utils.register_class(SheetViewContainer)
Object.SheetGenerator = bpy.props.PointerProperty(type=SheetViewContainer)


class AddSheetViewButton(Operator):
    bl_idname = "measureit_arch.addsheetviewbutton"
    bl_label = "Add"
    bl_description = "Create A New Sheet View"
    bl_category = 'MeasureitArch'

    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen
            obj = context.object
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # Add properties
                    SheetGen = obj.SheetGenerator

                    newView = SheetGen.sheet_views.add()
                    newView.name = 'View ' + str(len(SheetGen.sheet_views))

                    context.area.tag_redraw()
                    return {'FINISHED'}
        return {'FINISHED'}


class DeleteSheetViewButton(Operator):
    bl_idname = "measureit_arch.deletesheetviewbutton"
    bl_label = "Delete View"
    bl_description = "Delete a View"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'}

    tag: IntProperty()

    def execute(self, context):
        # Add properties

        Generator = context.object.SheetGenerator
        Generator.sheet_views.remove(Generator.active_index)

        return {'FINISHED'}


class M_ARCH_UL_Sheets_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            view = item
            layout.use_property_decorate = False
            row = layout.row(align=True)
            subrow = row.row()
            subrow.prop(view, "name", text="", emboss=False)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')


class SCENE_PT_Sheet(Panel):
    """Creates a Panel in the Object properties window"""
    bl_parent_id = 'OBJECT_PT_Panel'
    bl_label = "MeasureIt_ARCH Sheet"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        if context.scene.MeasureItArchProps.enable_experimental:
            return (context.object.type == 'CAMERA')
        else:
            return False

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon='RENDERLAYERS')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        SheetGen = context.object.SheetGenerator

        row = layout.row()

        # Draw The UI List
        row.template_list(
            "M_ARCH_UL_Sheets_list", "", SheetGen, "sheet_views", SheetGen,
            "active_index", rows=2, type='DEFAULT')

        # Operators Next to List
        col = row.column(align=True)
        col.operator("measureit_arch.addsheetviewbutton", icon='ADD', text="")
        op = col.operator(
            "measureit_arch.deletesheetviewbutton", text="", icon="X")
        op.tag = SheetGen.active_index  # saves internal data

        # col.separator()
        # col.menu("SCENE_MT_styles_menu", icon='DOWNARROW_HLT', text="")

        # Settings Below List
        if (len(SheetGen.sheet_views) > 0 and
            SheetGen.active_index < len(SheetGen.sheet_views)):

            view = SheetGen.sheet_views[SheetGen.active_index]

            if SheetGen.show_settings:
                settingsIcon = 'DISCLOSURE_TRI_DOWN'
            else:
                settingsIcon = 'DISCLOSURE_TRI_RIGHT'

            box = layout.box()
            col = box.column()
            row = col.row()
            row.prop(SheetGen, 'show_settings', text="",
                     icon=settingsIcon, emboss=False)

            row.label(text=view.name + ' Settings:')

            if SheetGen.show_settings:
                col = box.column()
                col.prop(view, 'scene', text="Scene")

                if view.scene is not None:
                    viewGen = view.scene.ViewGenerator
                    col.prop_search(view, 'view', viewGen, 'views',
                                    text="View", icon='CAMERA_DATA')

                    col.prop(view, 'location', text='Location')
                    # col.prop(view, 'rotation', text='Rotation')
