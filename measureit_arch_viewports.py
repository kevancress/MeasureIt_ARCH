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

from bpy.types import PropertyGroup, Panel, Operator, UIList, Scene, Object
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, \
    BoolProperty, StringProperty, PointerProperty


class Viewport(PropertyGroup):
    view: StringProperty(name="View Name")

    scene: PointerProperty(type=Scene)

    anchor: PointerProperty(type=Object)

    draw_border: BoolProperty(
        name="Draw Border",
        description="Draw a Border Around the Viewport",
        default=False)


class ViewportContainer(PropertyGroup):

    active_index: IntProperty(name='Active Sheet View Index')

    show_settings: BoolProperty(name='Show Sheet View Settings', default=False)

    # Array of segments
    viewports: CollectionProperty(type=Viewport)


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
    """ A panel in the Object properties window """

    bl_parent_id = 'OBJECT_PT_Panel'
    bl_label = "MeasureIt_ARCH Sheet"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon='RENDERLAYERS')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        ViewportGen = context.scene.ViewportGenerator

        row = layout.row()

        # Draw The UI List
        row.template_list(
            "M_ARCH_UL_Sheets_list", "", ViewportGen, "sheet_views", ViewportGen,
            "active_index", rows=2, type='DEFAULT')

    
