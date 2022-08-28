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

from mathutils import Vector, Matrix, Euler, Quaternion

from .measureit_arch_utils import get_view, get_rv3d

class Viewport(PropertyGroup,):
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


class SCENE_PT_Viewport(Panel):
    """ A panel in the Scene properties window """

    bl_parent_id = 'SCENE_PT_Views'
    bl_label = "Viewports"
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

        # Get Active View.
        active_view = get_view()

        # Draw The UI List
        row.template_list(
            "M_ARCH_UL_Sheets_list", "", active_view, "viewports", ViewportGen,
            "active_index", rows=2, type='DEFAULT')

        col = row.column(align=True)

        AddOp = col.operator(
            "measureit_arch.additem", text="", icon="ADD")
        AddOp.propPath = 'bpy.context.scene.ViewGenerator.views[bpy.context.scene.ViewGenerator.active_index].viewports'
        AddOp.idx = ViewportGen.active_index
        AddOp.add = True
        AddOp.name = "Viewport"
        
        RemoveOp = col.operator(
            "measureit_arch.additem", text="", icon="REMOVE")
        RemoveOp.propPath = 'bpy.context.scene.ViewGenerator.views[bpy.context.scene.ViewGenerator.active_index].viewports'
        RemoveOp.idx = ViewportGen.active_index
        RemoveOp.add = False

        if len(active_view.viewports) > 0 and ViewportGen.active_index < len(active_view.viewports):
            viewport = active_view.viewports[ViewportGen.active_index]

            # Settings Below List
            if ViewportGen.show_settings:
                settingsIcon = 'DISCLOSURE_TRI_DOWN'
            else:
                settingsIcon = 'DISCLOSURE_TRI_RIGHT'

            box = layout.box()
            col = box.column()
            row = col.row()
            row.prop(ViewportGen, 'show_settings', text="",
                     icon=settingsIcon, emboss=False)

            row.label(text=viewport.name + ' Settings:')

            if ViewportGen.show_settings:
                col = box.column()
                col.prop(viewport, 'scene', text="Scene")
                if viewport.scene is not None:
                    viewGen = viewport.scene.ViewGenerator
                    col.prop_search(viewport, 'view', viewGen, 'views',
                                        text="View", icon='CAMERA_DATA')

                col.prop(viewport, 'anchor', text='Anchor Object')
                col.prop(viewport,'draw_border')
    
