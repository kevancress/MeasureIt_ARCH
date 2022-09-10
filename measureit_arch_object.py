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
# File: measureit_arch_dimensions.py
# Main panel for MeasureitARCH object settings
# Author: Antonio Vazquez (antonioya), Kevan Cress
#
# ----------------------------------------------------------
import bpy
import bmesh
import random

from bpy.types import PropertyGroup, Panel, Object, Operator, UIList, Collection
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, \
    BoolProperty, StringProperty, FloatProperty, EnumProperty, \
    PointerProperty, BoolVectorProperty
from mathutils import Vector

from .measureit_arch_baseclass import BaseDim, recalc_dimWrapper_index
from .measureit_arch_utils import get_smart_selected, \
    get_selected_vertex_history, get_selected_faces
from .measureit_arch_units import BU_TO_FEET



class OBJECT_PT_Panel(Panel):
    """ Panel in the object properties window """
    bl_idname = 'OBJECT_PT_Panel'
    bl_label = "MeasureIt_ARCH"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):

        pass


class OBJECT_PT_UIObjSettings(Panel):
    """ A Panel in the Object properties window """
    bl_parent_id = 'OBJECT_PT_Panel'
    bl_label = "Object Settings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon='SETTINGS')

    def draw(self,context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        obj = context.active_object
        obj_props = obj.MeasureItArchProps

        col = layout.column(align=True)
        col.prop(obj_props, "ignore_in_depth_test", text = "Ignore in Vector Depthtest")
        col.prop(obj_props, 'obj_hatch_pattern', text="Object Pattern",)