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
from bpy.types import (
    GizmoGroup,
    Scene
)


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
        if scene.measureit_arch_show_gizmos:
            if 'DimensionGenerator' in ob:
                if len(ob.DimensionGenerator[0].alignedDimensions) > 0:
                    return (ob)

    def setup(self, context):
        # Arrow gizmo has one 'offset' property we can assign to the light energy.
        ob = context.object
        dimGen = ob.DimensionGenerator[0]
        for dim in dimGen.alignedDimensions:
            mpr = self.gizmos.new("GIZMO_GT_arrow_3d")
            mpr.target_set_prop("offset", dim, "dimOffset")
            mpr.matrix_basis = ob.matrix_world.normalized()
            mpr.draw_style = 'BOX'

            rotateGiz = self.gizmos.new("GIZMO_GT_dial_3d")
            rotateGiz.line_width = 3
            rotateGiz.target_set_prop("offset", dim, "dimRotation")
            rotateGiz.matrix_basis = ob.matrix_world.normalized()

            mpr.color = 0.0, 0.0, 0.0
            mpr.alpha = 0.5

            mpr.color_highlight = 1.0, 1.0, 1.0
            mpr.alpha_highlight = 0.5

            self.energy_widget = mpr
            self.rotate_widget = rotateGiz


    def refresh(self, context):
        ob = context.object
        dimGen = ob.DimensionGenerator[0]
        self.gizmos.clear()
        for dim in dimGen.alignedDimensions:
            mpr = self.gizmos.new("GIZMO_GT_arrow_3d")
            mpr.target_set_prop("offset", dim, "dimOffset")
            mpr.matrix_basis = ob.matrix_world.normalized()
            mpr.draw_style = 'BOX'

            rotateGiz = self.gizmos.new("GIZMO_GT_dial_3d")
            rotateGiz.line_width = 3
            rotateGiz.target_set_prop("offset", dim, "dimRotation")
            rotateGiz.matrix_basis = ob.matrix_world.normalized()

            mpr.color = 0.0, 0.0, 0.0
            mpr.alpha = 0.5

            rotateGiz.color = 0.0, 0.0, 0.0
            rotateGiz.alpha = 0.5

            rotateGiz.color_highlight = 0.0, 0.0, 0.0
            rotateGiz.alpha_highlight = 0.5

            mpr.color_highlight = 1.0, 1.0, 1.0
            mpr.alpha_highlight = 0.5

            self.energy_widget = mpr
            self.rotate_widget = rotateGiz


bpy.utils.register_class(MyLightWidgetGroup)
