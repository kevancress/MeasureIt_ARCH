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

class mArchGizmoGroup(GizmoGroup):
    bl_idname = "OBJECT_GG_mArch"
    bl_label = "MeasureIt_ARCH Gizmo Group"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        scene = context.scene
        sceneProps = scene.MeasureItArchProps
        if sceneProps.show_gizmos and context.window_manager.measureit_arch_run_opengl:
            if obj is not None:
                if 'DimensionGenerator' in obj:
                    return (obj)
                if 'AnnotationGenerator' in obj:
                    return (obj)

    def createGiz(self,obj):
        objIndex = 0
        for obj in bpy.context.selected_objects:    
            if 'DimensionGenerator' in obj:
                dimGen = obj.DimensionGenerator[0]
                for dim in dimGen.alignedDimensions:
                    createDimOffsetGiz(self,dim,objIndex)
                for dim in dimGen.axisDimensions:
                    createDimOffsetGiz(self,dim,objIndex)
            if 'AnnotationGenerator' in obj:
                annotationGen = obj.AnnotationGenerator[0]
                createAnnotationTranslateGiz(self,annotationGen,objIndex)
                createAnnotationRotateGiz(self,annotationGen,objIndex)
            objIndex += 1

    def setup(self, context):
        obj = context.object
        self.createGiz(obj)

    def refresh(self, context):
        obj = context.object
        self.gizmos.clear()
        self.createGiz(obj)

bpy.utils.register_class(mArchGizmoGroup)

def createDimOffsetGiz(group,dim,objIndex):
    context = bpy.context
    dimProps = dim
    if dim.uses_style:
        for alignedDimStyle in context.scene.StyleGenerator.alignedDimensions:
            if alignedDimStyle.name == dim.style:
                dimProps = alignedDimStyle


    #Set Matrix
    k = Vector((0,0,1))
    basisMatrix = Matrix.Translation(Vector((0,0,0)))
    rot = k.rotation_difference(dim.gizRotDir)
    rotMatrix = rot.to_matrix()
    rotMatrix.resize_4x4()
    basisMatrix = basisMatrix @ rotMatrix
    basisMatrix.translation = Vector(dim.gizLoc)+(Vector(dim.gizRotDir)*0.2)
    
    #Offset Gizmo
    dimOffsetGiz = group.gizmos.new("GIZMO_GT_arrow_3d")
    dimOffsetGiz.target_set_prop("offset", dim, "dimOffset")
    dimOffsetGiz.draw_style = "NORMAL"

    dimOffsetGiz.length = 0
    dimOffsetGiz.matrix_basis = basisMatrix
    dimOffsetGiz.use_draw_value = True

    dimOffsetGiz.scale_basis = 1
    dimOffsetGiz.color = (pow(dimProps.color[0],(1/2.2)),pow(dimProps.color[1],(1/2.2)),pow(dimProps.color[2],(1/2.2)))
    dimOffsetGiz.alpha = 0.3

    dimOffsetGiz.color_highlight = (pow(dimProps.color[0],(1/2.2)),pow(dimProps.color[1],(1/2.2)),pow(dimProps.color[2],(1/2.2)))
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

def createAnnotationTranslateGiz(group,annotationGen,objIndex):
    # Set Basis Matrix
    idx = 0
    for anno in annotationGen.annotations:
        basisMatrix = Matrix.Translation(Vector((0,0,0)))
        obj = bpy.context.selected_objects[objIndex]
        mat = obj.matrix_world
        objrot = mat.to_quaternion()
        basisMatrix.translation = Vector(anno.gizLoc) - Vector(anno.annotationOffset) 
        scale = 1
        lineweight = 2
        length = 0.6
        offset = 0.05
        baseAlpha = 0.15

     

        # Basic Move Gizmo
        annotationMove = group.gizmos.new("GIZMO_GT_move_3d")
        annotationMove.target_set_prop("offset", anno, "annotationOffset")

        annotationMove.matrix_basis = basisMatrix
        annotationMove.scale_basis = 0.15
        annotationMove.draw_style = 'RING_2D'
        annotationMove.draw_options= {'ALIGN_VIEW'}
        annotationMove.line_width = lineweight
        annotationMove.color = 0.8, 0.8, 0.8
        annotationMove.alpha = 0.5
        annotationMove.use_draw_modal = True 

        annotationMove.color_highlight = 1.0, 1.0, 1.0
        annotationMove.alpha_highlight = 1

        #Translate Op Gizmos
        #X
        annotationOffsetX = group.gizmos.new("GIZMO_GT_arrow_3d")
        opX = annotationOffsetX.target_set_operator("measureit_arch.translate_annotation")
        opX.constrainAxis = (True,False,False)
        opX.objIndex = objIndex
        opX.idx = idx

        XbasisMatrix = basisMatrix.to_3x3()
        rot = Quaternion(Vector((0,1,0)),radians(90))
        XbasisMatrix.rotate(rot)
        XbasisMatrix.rotate(objrot)
        XbasisMatrix.resize_4x4()
        offsetVec = Vector((offset,0,0))
        offsetVec.rotate(objrot)
        XbasisMatrix.translation = Vector(anno.gizLoc) + offsetVec

        annotationOffsetX.matrix_basis = XbasisMatrix
        annotationOffsetX.use_draw_modal = False
        annotationOffsetX.scale_basis = scale
        annotationOffsetX.length = length
        annotationOffsetX.line_width = lineweight

        annotationOffsetX.color = 0.96, 0.2, 0.31
        annotationOffsetX.alpha = baseAlpha

        annotationOffsetX.color_highlight = 0.96, 0.2, 0.31
        annotationOffsetX.alpha_highlight = 1

        #Y
        annotationOffsetY = group.gizmos.new("GIZMO_GT_arrow_3d")
        opY = annotationOffsetY.target_set_operator("measureit_arch.translate_annotation")
        opY.constrainAxis = (False,True,False)
        opY.objIndex = objIndex
        opY.idx = idx

        YbasisMatrix = basisMatrix.to_3x3()
        rot = Quaternion(Vector((1,0,0)),radians(-90))
        YbasisMatrix.rotate(rot)
        YbasisMatrix.rotate(objrot)
        YbasisMatrix.resize_4x4()
        offsetVec = Vector((0,offset,0))
        offsetVec.rotate(objrot)
        YbasisMatrix.translation = Vector(anno.gizLoc) + offsetVec

        annotationOffsetY.matrix_basis = YbasisMatrix
        annotationOffsetY.use_draw_modal = False
        annotationOffsetY.scale_basis = scale
        annotationOffsetY.length = length
        annotationOffsetY.line_width = lineweight

        annotationOffsetY.color = 0.54, 0.86, 0
        annotationOffsetY.alpha = baseAlpha

        annotationOffsetY.color_highlight = 0.54, 0.86, 0
        annotationOffsetY.alpha_highlight = 1

        #Z
        annotationOffsetZ = group.gizmos.new("GIZMO_GT_arrow_3d")
        opZ = annotationOffsetZ.target_set_operator("measureit_arch.translate_annotation")
        opZ.constrainAxis = (False,False,True)
        opZ.objIndex = objIndex
        opZ.idx = idx

        ZbasisMatrix = basisMatrix.to_3x3()
        ZbasisMatrix.rotate(objrot)
        ZbasisMatrix.resize_4x4()
        offsetVec = Vector((0,0,offset))
        offsetVec.rotate(objrot)
        ZbasisMatrix.translation = Vector(anno.gizLoc) + offsetVec

        annotationOffsetZ.matrix_basis = ZbasisMatrix
        annotationOffsetZ.use_draw_modal = False
        annotationOffsetZ.scale_basis = scale
        annotationOffsetZ.length = length
        annotationOffsetZ.line_width = lineweight

        annotationOffsetZ.color = 0.15, 0.56, 1
        annotationOffsetZ.alpha = baseAlpha

        annotationOffsetZ.color_highlight = 0.15, 0.56, 1
        annotationOffsetZ.alpha_highlight = 1
        
        #add to group
        group.move_widget = annotationMove
        group.X_widget = annotationOffsetX
        group.Y_widget = annotationOffsetY
        group.Z_widget = annotationOffsetZ
        idx += 1

def createAnnotationRotateGiz(group,annotationGen,objIndex):
    # Set Basis Matrix
    idx = 0
    rotateGizScale = 0.5
    for anno in annotationGen.annotations:
        basisMatrix = Matrix.Translation(Vector((0,0,0)))
        basisMatrix.translation = Vector(anno.gizLoc)
        obj = bpy.context.selected_objects[objIndex]
        mat = obj.matrix_world
        objrot = mat.to_quaternion()
        lineweight = 2
        baseAlpha = 0.15

        #Translate Op Gizmos
        #X
        annotationRotateX = group.gizmos.new("GIZMO_GT_move_3d")
        annotationRotateX.use_draw_modal = True
        opX = annotationRotateX.target_set_operator("measureit_arch.rotate_annotation")
        opX.constrainAxis = (True,False,False)
        opX.objIndex = objIndex
        opX.idx = idx

        XbasisMatrix = basisMatrix.to_3x3()
        rot = Quaternion(Vector((0,1,0)),radians(90))
        XbasisMatrix.rotate(rot)
        XbasisMatrix.rotate(objrot)
        XbasisMatrix.resize_4x4()
        XbasisMatrix.translation = Vector(anno.gizLoc)
        

        annotationRotateX.matrix_basis = XbasisMatrix
        annotationRotateX.scale_basis = rotateGizScale
        annotationRotateX.line_width = lineweight

        annotationRotateX.color = 0.96, 0.2, 0.31
        annotationRotateX.alpha = baseAlpha

        annotationRotateX.color_highlight = 0.96, 0.2, 0.31
        annotationRotateX.alpha_highlight = 1

        #Y
        annotationRotateY = group.gizmos.new("GIZMO_GT_move_3d")
        annotationRotateY.use_draw_modal = True
        opY = annotationRotateY.target_set_operator("measureit_arch.rotate_annotation")
        opY.constrainAxis = (False,True,False)
        opY.objIndex = objIndex
        opY.idx = idx

        YbasisMatrix = basisMatrix.to_3x3()
        rot = Quaternion(Vector((1,0,0)),radians(-90))
        YbasisMatrix.rotate(rot)
        YbasisMatrix.rotate(objrot)
        YbasisMatrix.resize_4x4()
        YbasisMatrix.translation = Vector(anno.gizLoc)

        annotationRotateY.matrix_basis = YbasisMatrix
        annotationRotateY.scale_basis = rotateGizScale
        annotationRotateY.line_width = lineweight

        annotationRotateY.color = 0.54, 0.86, 0
        annotationRotateY.alpha = baseAlpha

        annotationRotateY.color_highlight = 0.54, 0.86, 0
        annotationRotateY.alpha_highlight = 1

        #Z
        annotationRotateZ = group.gizmos.new("GIZMO_GT_move_3d")
        annotationRotateZ.use_draw_modal = True
        opZ = annotationRotateZ.target_set_operator("measureit_arch.rotate_annotation")
        opZ.constrainAxis = (False,False,True)
        opZ.objIndex = objIndex
        opZ.idx = idx

        ZbasisMatrix = basisMatrix.to_3x3()
        ZbasisMatrix.rotate(objrot)
        ZbasisMatrix.resize_4x4()
        ZbasisMatrix.translation = Vector(anno.gizLoc)

        annotationRotateZ.matrix_basis = ZbasisMatrix
        annotationRotateZ.scale_basis = rotateGizScale
        annotationRotateZ.line_width = lineweight

        annotationRotateZ.color = 0.15, 0.56, 1
        annotationRotateZ.alpha = baseAlpha

        annotationRotateZ.color_highlight = 0.15, 0.56, 1
        annotationRotateZ.alpha_highlight = 1
        
        #add to group

        group.X_widget = annotationRotateX
        group.Y_widget = annotationRotateY
        group.Z_widget = annotationRotateZ
        idx += 1

