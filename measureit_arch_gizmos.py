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
# File: measureit_arch_gizmos.py
# Main panel for different MeasureitArch general actions
# Author: Antonio Vazquez (antonioya), Kevan Cress
#
# ----------------------------------------------------------

import bpy
from mathutils import Vector, Matrix, Euler, Quaternion
from math import degrees, radians
from bpy.types import (
    GizmoGroup,
    Gizmo,
    Scene
)

h = -2.5
# Coordinates (each one is a triangle).
custom_shape_verts = (
    (0.0, -1.16, 0.0), (1.0, -0.6, 0.0), (0.0, 0.0, 0.0),
    (1.0, -0.6, 0.0), (1.0, 0.6, 0.0) , (0.0, 0.0, 0.0),
    (1.0, 0.6, 0.0) , (0.0, 1.16, 0.0), (0.0, 0.0, 0.0),
    (0.0, 1.16, 0.0), (-1.0, 0.6, 0.0), (0.0, 0.0, 0.0),
    (-1.0, 0.6, 0.0), (-1.0, -0.6, 0.0), (0.0, 0.0, 0.0),
    (-1.0, -0.6, 0.0), (0.0, -1.16, 0.0),  (0.0, 0.0, 0.0),

    (0.0, -1.16, 0.0), (1.0, -0.6, 0.0), (0.0, 0.0, h),
    (1.0, -0.6, 0.0), (1.0, 0.6, 0.0) , (0.0, 0.0, h),
    (1.0, 0.6, 0.0) , (0.0, 1.16, 0.0), (0.0, 0.0, h),
    (0.0, 1.16, 0.0), (-1.0, 0.6, 0.0), (0.0, 0.0, h),
    (-1.0, 0.6, 0.0), (-1.0, -0.6, 0.0), (0.0, 0.0, h),
    (-1.0, -0.6, 0.0), (0.0, -  1.16, 0.0),  (0.0, 0.0, h),
)


class CustomShapeWidget(Gizmo):
    bl_idname = "VIEW3D_GT_Custom"
    bl_target_properties = (
        {"id": "offset", "type": 'FLOAT', "array_length": 1},
    )

    __slots__ = (
        "custom_shape",
        "init_mouse_y",
        "init_value",
    )

    def _update_offset_matrix(self):
        # offset behind the light
        self.matrix_offset.col[3][2] = self.target_get_value("offset")

    def draw(self, context):
        self._update_offset_matrix()
        self.draw_custom_shape(self.custom_shape)

    def draw_select(self, context, select_id):
        self._update_offset_matrix()
        self.draw_custom_shape(self.custom_shape, select_id=select_id)

    def setup(self):
        if not hasattr(self, "custom_shape"):
            self.custom_shape = self.new_custom_shape('TRIS', custom_shape_verts)

    def invoke(self, context, event):
        self.init_mouse_y = event.mouse_y
        self.init_value = self.target_get_value("offset")
        return {'RUNNING_MODAL'}

    def exit(self, context, cancel):
        context.area.header_text_set(None)
        if cancel:
            self.target_set_value("offset", self.init_value)

    def modal(self, context, event, tweak):
        delta = (event.mouse_y - self.init_mouse_y) / 50.0
        if 'SNAP' in tweak:
            delta = round(delta)
        if 'PRECISE' in tweak:
            delta /= 10.0
        value = self.init_value + delta
        self.target_set_value("offset", value)
        context.area.header_text_set("My Gizmo: %.4f" % value)
        return {'RUNNING_MODAL'}

bpy.utils.register_class(CustomShapeWidget)

class MyLightWidgetGroup(GizmoGroup):
    bl_idname = "OBJECT_GGT_light_test"
    bl_label = "Test Light Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT'}

    @classmethod
    def poll(cls, context):
        ob = context.object
        scene = context.scene
        if scene.measureit_arch_show_gizmos and context.window_manager.measureit_arch_run_opengl:
            if 'DimensionGenerator' in ob:
                if len(ob.DimensionGenerator[0].alignedDimensions) > 0:
                    return (ob)

    def createGiz(self,dimGen):
        for dim in dimGen.alignedDimensions:
            mpr = self.gizmos.new("VIEW3D_GT_Custom")
            mpr.target_set_prop("offset", dim, "dimOffset")
            #mpr.draw_style = 'BOX'
            
            basisMatrix = Matrix.Translation(Vector((0,0,0)))
            rot = Quaternion(Vector(dim.gizRotAxis),radians(-90))
            rotMatrix = rot.to_matrix()
            rotMatrix.resize_4x4()
            basisMatrix = basisMatrix @ rotMatrix
            basisMatrix.translation = Vector(dim.gizLoc)

            #basisMatrix = Matrix([
            #[ 1.0000, -0.0000, 0.0000, 0.0000],
            #[ 0.0000,  0.7089, 0.7053, 1.0000],
            #[-0.0000, -0.7053, 0.7089, 1.0000],
            #[ 0.0000,  0.0000, 0.0000, 1.0000]])

            #print(str(basisMatrix)+dim.name)
        
            mpr.matrix_basis = basisMatrix

            #rotateGiz = self.gizmos.new("GIZMO_GT_dial_3d")
            #rotateGiz.line_width = 3
            #rotateGiz.target_set_prop("offset", dim, "dimRotation")
            #rotateGiz.matrix_basis = ob.matrix_world.normalized()
            mpr.scale_basis = 0.075
            mpr.color = 0.0, 0.0, 0.0
            mpr.alpha = 0.5

            #rotateGiz.color = 0.0, 0.0, 0.0
            #rotateGiz.alpha = 0.5

            #rotateGiz.color_highlight = 0.0, 0.0, 0.0
            #rotateGiz.alpha_highlight = 0.5

            mpr.color_highlight = 1.0, 1.0, 1.0
            mpr.alpha_highlight = 0.5

            self.energy_widget = mpr
            #self.rotate_widget = rotateGiz


    def setup(self, context):
        # Arrow gizmo has one 'offset' property we can assign to the light energy.
        ob = context.object
        dimGen = ob.DimensionGenerator[0]
        self.createGiz(dimGen)


    def refresh(self, context):
        ob = context.object
        dimGen = ob.DimensionGenerator[0]
        self.gizmos.clear()
        self.createGiz(dimGen)
        
   


bpy.utils.register_class(MyLightWidgetGroup)
