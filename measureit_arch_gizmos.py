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

class mArchGizmoGroup(GizmoGroup):
    bl_idname = "OBJECT_GG_mArch"
    bl_label = "MeasureIt-ARCH Gizmo Group"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        scene = context.scene
        if scene.measureit_arch_show_gizmos and context.window_manager.measureit_arch_run_opengl:
            if 'DimensionGenerator' in obj:
                return (obj)
            if 'AnnotationGenerator' in obj:
                return (obj)

    def createGiz(self,obj):
        if 'DimensionGenerator' in obj:
            dimGen = obj.DimensionGenerator[0]
            for dim in dimGen.alignedDimensions:
                createDimOffsetGiz(self,dim)
            for dim in dimGen.axisDimensions:
                createDimOffsetGiz(self,dim)
        if 'AnnotationGenerator' in obj:
            annoGen = obj.AnnotationGenerator[0]
            for anno in annoGen.annotations:
                createAnnotationGiz(self,anno)

    def setup(self, context):
        obj = context.object
        self.createGiz(obj)

    def refresh(self, context):
        obj = context.object
        self.gizmos.clear()
        self.createGiz(obj)

bpy.utils.register_class(mArchGizmoGroup)

def createDimOffsetGiz(group,dim):
    dimOffsetGiz = group.gizmos.new("VIEW3D_GT_Custom")
    dimOffsetGiz.target_set_prop("offset", dim, "dimOffset")
    
    k = Vector((0,0,1))

    basisMatrix = Matrix.Translation(Vector((0,0,0)))
    rot = k.rotation_difference(dim.gizRotDir)
    rotMatrix = rot.to_matrix()
    rotMatrix.resize_4x4()
    basisMatrix = basisMatrix @ rotMatrix
    basisMatrix.translation = Vector(dim.gizLoc)-(Vector(dim.gizRotDir)*0.1)

    dimOffsetGiz.matrix_basis = basisMatrix

    dimOffsetGiz.scale_basis = 0.075
    dimOffsetGiz.color = 0.0, 0.0, 0.0
    dimOffsetGiz.alpha = 0.5

    dimOffsetGiz.color_highlight = 1.0, 1.0, 1.0
    dimOffsetGiz.alpha_highlight = 0.5

    group.offset_widget = dimOffsetGiz
    #self.rotate_widget = rotateGiz

def createAnnotationGiz(group,anno):
    annoGizX = group.gizmos.new("GIZMO_GT_move_3d")
    annoGizX.target_set_prop("offset", anno, "annotationOffset")

    basisMatrix = Matrix.Translation(Vector((0,0,0)))
    basisMatrix.translation = Vector(anno.gizLoc)

    annoGizX.matrix_basis = basisMatrix
    annoGizX.scale_basis = 0.075
    annoGizX.draw_style = 'RING_2D'
    annoGizX.draw_options= {'ALIGN_VIEW'}
    
    annoGizX.color = 0.8, 0.8, 0.8
    annoGizX.alpha = 0.5

    annoGizX.color_highlight = 1.0, 1.0, 1.0
    annoGizX.alpha_highlight = 0.5
