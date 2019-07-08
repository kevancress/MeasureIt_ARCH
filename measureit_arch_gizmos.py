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
        "init_mouse_x",
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
        self.init_mouse_x = event.mouse_x
        self.init_value = self.target_get_value("offset")
        return {'RUNNING_MODAL'}

    def exit(self, context, cancel):
        context.area.header_text_set(None)
        if cancel:
            self.target_set_value("offset", self.init_value)

    def modal(self, context, event, tweak):
        delta = ((event.mouse_y - self.init_mouse_y)+(event.mouse_x - self.init_mouse_x)) / 100.0
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
            annotationGen = obj.AnnotationGenerator[0]
            createAnnotationGiz(self,annotationGen)

    def setup(self, context):
        obj = context.object
        self.createGiz(obj)

    def refresh(self, context):
        print(self.bl_owner_id)
        obj = context.object
        self.gizmos.clear()
        self.createGiz(obj)

bpy.utils.register_class(mArchGizmoGroup)

def createDimOffsetGiz(group,dim):
    #Set Matrix
    k = Vector((0,0,1))
    basisMatrix = Matrix.Translation(Vector((0,0,0)))
    rot = k.rotation_difference(dim.gizRotDir)
    rotMatrix = rot.to_matrix()
    rotMatrix.resize_4x4()
    basisMatrix = basisMatrix @ rotMatrix
    basisMatrix.translation = Vector(dim.gizLoc)+(Vector(dim.gizRotDir)*0.1)
    
    #Offset Gizmo
    dimOffsetGiz = group.gizmos.new("GIZMO_GT_arrow_3d")
    dimOffsetGiz.target_set_prop("offset", dim, "dimOffset")
    dimOffsetGiz.draw_style = "NORMAL"

    dimOffsetGiz.length = 0
    dimOffsetGiz.matrix_basis = basisMatrix

    dimOffsetGiz.scale_basis = 0.8
    dimOffsetGiz.color = (pow(dim.color[0],(1/2.2)),pow(dim.color[1],(1/2.2)),pow(dim.color[2],(1/2.2)))
    dimOffsetGiz.alpha = 0.25

    dimOffsetGiz.color_highlight = (pow(dim.color[0],(1/2.2)),pow(dim.color[1],(1/2.2)),pow(dim.color[2],(1/2.2)))
    dimOffsetGiz.alpha_highlight = 1

    #Button Gizmo
    #dimButton = group.gizmos.new("GIZMO_GT_button_2d")
    #dimButton.icon = 'PREFERENCES'
    #dimButton.scale_basis = 0.2
    #dimButton.matrix_basis = basisMatrix

    # Add Gizmos to group
    group.offset_widget = dimOffsetGiz
    #group.settings_widget = dimButton
    #self.rotate_widget = rotateGiz

def createAnnotationGiz(group,annotationGen):
    # Set Basis Matrix
    idx = 0
    for anno in annotationGen.annotations:
        basisMatrix = Matrix.Translation(Vector((0,0,0)))
        basisMatrix.translation = Vector(anno.gizLoc)

        # Basic Move Gizmo
        annotationMove = group.gizmos.new("GIZMO_GT_move_3d")
        annotationMove.target_set_prop("offset", anno, "annotationOffset")

        annotationMove.matrix_basis = basisMatrix
        annotationMove.scale_basis = 0.1
        annotationMove.draw_style = 'RING_2D'
        annotationMove.draw_options= {'ALIGN_VIEW'}
        
        annotationMove.color = 0.8, 0.8, 0.8
        annotationMove.alpha = 0.5

        annotationMove.color_highlight = 1.0, 1.0, 1.0
        annotationMove.alpha_highlight = 0.5

        #Translate Op Gizmos
        #X
        annotationOffsetX = group.gizmos.new("GIZMO_GT_arrow_3d")
        opX = annotationOffsetX.target_set_operator("measureit_arch.translate_annotation")
        opX.constrainAxis = (True,False,False)
        opX.idx = idx

        XbasisMatrix = basisMatrix.to_3x3()
        rot = Quaternion(Vector((0,1,0)),radians(90))
        XbasisMatrix.rotate(rot)
        XbasisMatrix.resize_4x4()
        XbasisMatrix.translation = Vector(anno.gizLoc) + Vector(anno.annotationOffset) + Vector((0.05,0,0))

        annotationOffsetX.matrix_basis = XbasisMatrix
        annotationOffsetX.use_draw_modal = False
        annotationOffsetX.scale_basis = 1
        annotationOffsetX.length = 0.6
        annotationOffsetX.line_width = 2

        annotationOffsetX.color = 0.96, 0.2, 0.31
        annotationOffsetX.alpha = 0.5

        annotationOffsetX.color_highlight = 0.96, 0.2, 0.31
        annotationOffsetX.alpha_highlight = 1

        #Y
        annotationOffsetY = group.gizmos.new("GIZMO_GT_arrow_3d")
        opY = annotationOffsetY.target_set_operator("measureit_arch.translate_annotation")
        opY.constrainAxis = (False,True,False)
        opY.idx = idx

        YbasisMatrix = basisMatrix.to_3x3()
        rot = Quaternion(Vector((1,0,0)),radians(-90))
        YbasisMatrix.rotate(rot)
        YbasisMatrix.resize_4x4()
        YbasisMatrix.translation = Vector(anno.gizLoc) + Vector(anno.annotationOffset) + Vector((0,0.05,0))

        annotationOffsetY.matrix_basis = YbasisMatrix
        annotationOffsetY.use_draw_modal = False
        annotationOffsetY.scale_basis = 1
        annotationOffsetY.length = 0.6
        annotationOffsetY.line_width = 2

        annotationOffsetY.color = 0.54, 0.86, 0
        annotationOffsetY.alpha = 0.5

        annotationOffsetY.color_highlight = 0.54, 0.86, 0
        annotationOffsetY.alpha_highlight = 1

        #Z
        annotationOffsetZ = group.gizmos.new("GIZMO_GT_arrow_3d")
        opZ = annotationOffsetZ.target_set_operator("measureit_arch.translate_annotation")
        opZ.constrainAxis = (False,False,True)
        opZ.idx = idx

        ZbasisMatrix = basisMatrix.copy()
        ZbasisMatrix.translation = Vector(anno.gizLoc) + Vector(anno.annotationOffset) + Vector((0,0,0.05))

        annotationOffsetZ.matrix_basis = ZbasisMatrix
        annotationOffsetZ.use_draw_modal = False
        annotationOffsetZ.scale_basis = 1
        annotationOffsetZ.length = 0.6
        annotationOffsetZ.line_width = 2

        annotationOffsetZ.color = 0.15, 0.56, 1
        annotationOffsetZ.alpha = 0.5

        annotationOffsetZ.color_highlight = 0.15, 0.56, 1
        annotationOffsetZ.alpha_highlight = 1
        
        #add to group
        group.move_widget = annotationMove
        group.X_widget = annotationOffsetX
        group.Y_widget = annotationOffsetY
        group.Z_widget = annotationOffsetZ
        idx += 1