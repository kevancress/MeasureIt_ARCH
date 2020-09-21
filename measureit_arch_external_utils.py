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
#
# External Utilities to be accessed by BlenderBIM, Archipack and other Addons
# Author:  Kevan Cress
#
# ----------------------------------------------------------


from .measureit_arch_geometry import get_mesh_vertex, get_point, sortPoints, select_normal, interpolate3d
from mathutils import Vector, Matrix, Euler, Quaternion
from math import fabs, degrees, radians, sqrt, cos, sin, pi, floor

def blenderBIM_get_coords (context, offset_pos=True):
    dim_coords_list = []
    
    scene = context.scene
    sceneProps = scene.MeasureItArchProps

    # Display selected or all
    if sceneProps.show_all is False:
        objlist = context.selected_objects
    else:
        objlist = context.view_layer.objects

    # ---------------------------------------
    # Generate all OpenGL calls
    # ---------------------------------------
    for myobj in objlist:
    
        #Stash Object Vertices for use in Draw functions
          
        if myobj.visible_get() is True:
            mat = myobj.matrix_world

            #if 'LineGenerator' in myobj and myobj.LineGenerator[0].line_num != 0:
            #    lineGen = myobj.LineGenerator[0]
            #    draw_line_group(context,myobj,lineGen,mat)

            #if 'AnnotationGenerator' in myobj and myobj.AnnotationGenerator[0].num_annotations != 0:
            #    annotationGen = myobj.AnnotationGenerator[0]
            #    draw_annotation(context,myobj,annotationGen,mat)

            if 'DimensionGenerator' in myobj:
                DimGen = myobj.DimensionGenerator[0]
                
                for alignedDim in DimGen.alignedDimensions:
                    dim_coords_list.append(get_dim_coords(context, myobj, DimGen, alignedDim, mat, offset_pos=offset_pos))

            #    for angleDim in DimGen.angleDimensions:
            #        draw_angleDimension(context, myobj, DimGen, angleDim,mat)
            #
            #    for axisDim in DimGen.axisDimensions:
            #        draw_axisDimension(context,myobj,DimGen,axisDim,mat)
                
            #    for boundsDim in DimGen.boundsDimensions:
            #        draw_boundsDimension(context,myobj,DimGen,boundsDim,mat)
                
            #    for arcDim in DimGen.arcDimensions:
            #        draw_arcDimension(context,myobj,DimGen,arcDim,mat)

            #    for areaDim in DimGen.areaDimensions:
            #        draw_areaDimension(context,myobj,DimGen,areaDim,mat)

    print(dim_coords_list)
    return dim_coords_list

def get_dim_coords(context, myobj, DimGen, dim, mat, offset_pos = True):
    dimProps = dim
    if dim.uses_style:
        for alignedDimStyle in context.scene.StyleGenerator.alignedDimensions:
            if alignedDimStyle.name == dim.style:
                dimProps = alignedDimStyle

    # get points positions from indicies
    aMatrix = dim.dimObjectA.matrix_world
    bMatrix = dim.dimObjectB.matrix_world

    offset = dim.dimOffset
    geoOffset = dim.dimLeaderOffset

    # get points positions from indicies
    p1Local = None
    p2Local = None

    try:
        p1Local = get_mesh_vertex(dim.dimObjectA,dim.dimPointA,dimProps.evalMods)
    except IndexError:
        print('p1 excepted for ' + dim.name + ' on ' + myobj.name)

    try:
        p2Local = get_mesh_vertex(dim.dimObjectB,dim.dimPointB,dimProps.evalMods)
    except IndexError:
        print('p2 excepted for ' + dim.name + ' on ' + myobj.name)

    p1 = get_point(p1Local, dim.dimObjectA,aMatrix)
    p2 = get_point(p2Local, dim.dimObjectB,bMatrix)
        
    #check dominant Axis
    sortedPoints = sortPoints(p1, p2)
    p1 = sortedPoints[0]
    p2 = sortedPoints[1]

    distVector = Vector(p1)-Vector(p2)
    dist = distVector.length
    midpoint = interpolate3d(p1, p2, fabs(dist / 2))
    normDistVector = distVector.normalized()


    # Compute offset vector from face normal and user input
    rotationMatrix = Matrix.Rotation(dim.dimRotation, 4, normDistVector)
    selectedNormal = Vector(select_normal(myobj, dim, normDistVector, midpoint, dimProps))
    
    userOffsetVector = rotationMatrix@selectedNormal
    offsetDistance = userOffsetVector*offset
    geoOffsetDistance = offsetDistance.normalized()*geoOffset

    if offsetDistance < geoOffsetDistance:
        offsetDistance = geoOffsetDistance

    dimLineStart = Vector(p1)+offsetDistance
    dimLineEnd = Vector(p2)+offsetDistance
    
    if offset_pos:
        return [dimLineStart,dimLineEnd]
    else:
        return [p1,p2]
