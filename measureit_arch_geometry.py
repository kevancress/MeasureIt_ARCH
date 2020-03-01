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
#  GNU General Public License for more details.a
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


# ----------------------------------------------------------
# support routines for OpenGL
# Author: Antonio Vazquez (antonioya), Kevan Cress
#
# ----------------------------------------------------------
# noinspection PyUnresolvedReferences
import bpy
# noinspection PyUnresolvedReferences
import bgl
import gpu
from gpu_extras.batch import batch_for_shader
# noinspection PyUnresolvedReferences
import blf
from blf import ROTATION
from math import fabs, degrees, radians, sqrt, cos, sin, pi, floor
from mathutils import Vector, Matrix, Euler, Quaternion
import bmesh
from bpy_extras import view3d_utils, mesh_utils
import bpy_extras.object_utils as object_utils
from sys import exc_info
from .shaders import *
import math
import time
import numpy as np
from array import array
import random


lastMode = None
lineBatch3D = None
dashedBatch3D = None
hiddenBatch3D = None

# define Shaders
shader = gpu.types.GPUShader(
    Base_Shader_2D.vertex_shader,
    Base_Shader_2D.fragment_shader)

lineShader = gpu.types.GPUShader(
    Base_Shader_3D.vertex_shader,
    Line_Shader_3D.fragment_shader,
    geocode=Line_Shader_3D.geometry_shader)

lineGroupShader = gpu.types.GPUShader(
    Line_Group_Shader_3D.vertex_shader,
    Line_Group_Shader_3D.fragment_shader,
    geocode=Line_Group_Shader_3D.geometry_shader)

triShader = gpu.types.GPUShader(
    Base_Shader_3D.vertex_shader,
    Base_Shader_3D.fragment_shader)

dashedLineShader = gpu.types.GPUShader(
    Dashed_Shader_3D.vertex_shader,
    Dashed_Shader_3D.fragment_shader,
    geocode=Dashed_Shader_3D.geometry_shader)

pointShader = gpu.types.GPUShader(
    Point_Shader_3D.vertex_shader,
    Point_Shader_3D.fragment_shader,
    geocode=Point_Shader_3D.geometry_shader)

lgPointShader = gpu.types.GPUShader(
    Line_Group_Shader_3D.vertex_shader,
    Point_Shader_3D.fragment_shader,
    geocode=Point_Shader_3D.geometry_shader)

textShader = gpu.types.GPUShader(
    Text_Shader.vertex_shader,
    Text_Shader.fragment_shader)

fontSizeMult = 6


def update_text(textobj, props, context):
    update_flag = False
    for textField in textobj.textFields:
        if textField.text_updated:
            update_flag = True
            
        if textobj.text_updated or textField.text_updated or props.text_updated or update_flag:
            # Get textitem Properties
            rawRGB = props.color
            rgb = (pow(rawRGB[0], (1/2.2)), pow(rawRGB[1], (1/2.2)), pow(rawRGB[2], (1/2.2)), rawRGB[3])
            size = 20
            resolution = props.textResolution

            # Get Font Id
            badfonts = [None]
            if 'Bfont' in bpy.data.fonts:
                badfonts.append(bpy.data.fonts['Bfont'])
            if props.font not in badfonts:
                vecFont = props.font
                fontPath = vecFont.filepath
                font_id = blf.load(fontPath)
            else:
                font_id = 0

            # Set BLF font Properties
            blf.color(font_id, rgb[0], rgb[1], rgb[2], rgb[3])
            blf.size(font_id, size, resolution)
            
            text = textField.text

            # Calculate Optimal Dimensions for Text Texture.
            fheight = blf.dimensions(font_id, 'Tp')[1]
            fwidth = blf.dimensions(font_id, text)[0]
            width = math.ceil(fwidth)
            height = math.ceil(fheight)
            

            # Save Texture size to textobj Properties
            textField.textHeight = height
            textField.textWidth = width

            # Start Offscreen Draw
            if width != 0 and height != 0:
                textOffscreen = gpu.types.GPUOffScreen(width, height)
                texture_buffer = bgl.Buffer(bgl.GL_BYTE, width * height * 4)
                
                with textOffscreen.bind():
                    # Clear Past Draw and Set 2D View matrix
                    bgl.glClearColor(rgb[0], rgb[1], rgb[2], 0)
                    bgl.glClear(bgl.GL_COLOR_BUFFER_BIT)
                    
                    view_matrix = Matrix([
                        [2 / width, 0, 0, -1],
                        [0, 2 / height, 0, -1],
                        [0, 0, 1, 0],
                        [0, 0, 0, 1]])
                    
                    gpu.matrix.reset()
                    gpu.matrix.load_matrix(view_matrix)
                    gpu.matrix.load_projection_matrix(Matrix.Identity(4))

                    blf.position(font_id, 0, height/5, 0)
                    blf.draw(font_id, text)
                    
                    # Read Offscreen To Texture Buffer
                    bgl.glReadBuffer(bgl.GL_BACK)
                    bgl.glReadPixels(0, 0, width, height, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, texture_buffer)
                    
                    # Write Texture Buffer to ID Property as List
                    if 'texture' in textField:
                        del textField['texture']
                    textField['texture'] = texture_buffer
                    textOffscreen.free()
                    textField.text_updated = False
                    textField.texture_updated = True
            
            # generate image datablock from buffer for debug preview
            # ONLY USE FOR DEBUG. SERIOUSLY SLOWS PREFORMANCE
            if context.scene.measureit_arch_debug_text:
                if not str('test') in bpy.data.images:
                    bpy.data.images.new(str('test'), width, height)
                image = bpy.data.images[str('test')]
                image.scale(width, height)
                image.pixels = [v / 255 for v in texture_buffer]


def draw_alignedDimension(context, myobj, measureGen, dim, mat):
    # GL Settings
    bgl.glEnable(bgl.GL_MULTISAMPLE)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glDepthFunc(bgl.GL_LEQUAL)
    bgl.glDepthMask(False)
    scene = context.scene
    sceneProps = scene.MeasureItArchProps

    dimProps = dim
    if dim.uses_style:
        for alignedDimStyle in context.scene.StyleGenerator.alignedDimensions:
            if alignedDimStyle.name == dim.style:
                dimProps = alignedDimStyle

    bgl.glEnable(bgl.GL_DEPTH_TEST)
    if dimProps.inFront:
         bgl.glDisable(bgl.GL_DEPTH_TEST)

    lineWeight = dimProps.lineWeight
    # check all visibility conditions
    if dim.dimVisibleInView is None or dim.dimVisibleInView.name == context.scene.camera.data.name:
        inView = True        
    else:
        inView = False    
    if dim.visible and dimProps.visible and inView:

        if sceneProps.is_render_draw:
            viewport = [context.scene.render.resolution_x, context.scene.render.resolution_y]
        else:
            viewport = [context.area.width, context.area.height]

        # Obj Properties
        scene = context.scene
        pr = scene.measureit_arch_gl_precision
        textFormat = "%1." + str(pr) + "f"
        rawRGB = dimProps.color
        rgb = (pow(rawRGB[0], (1/2.2)), pow(rawRGB[1], (1/2.2)), pow(rawRGB[2], (1/2.2)), rawRGB[3])
        
        # Define Caps as a tuple of capA and capB to reduce code duplications
        caps = (dimProps.endcapA, dimProps.endcapB)
        capSize = dimProps.endcapSize

        offset = dim.dimOffset
        geoOffset = dim.dimLeaderOffset

        # get points positions from indicies
        aMatrix = mat
        bMatrix = mat
        if dim.dimObjectB != dim.dimObjectA:
            bMatrix = dim.dimObjectB.matrix_world - dim.dimObjectA.matrix_world + mat

        # get points positions from indicies
        if dim.dimPointA == 9999999:
            p1 = dim.dimObjectA.location
        else:
            p1 = get_point(get_mesh_vertex(dim.dimObjectA,dim.dimPointA,dimProps.evalMods), dim.dimObjectA, aMatrix)

        if dim.dimPointB == 9999999:
            p2 = dim.dimObjectB.location
        else:
            p2 = get_point(get_mesh_vertex(dim.dimObjectB,dim.dimPointB,dimProps.evalMods), dim.dimObjectB, bMatrix)



        #check dominant Axis
        sortedPoints = sortPoints(p1, p2)
        p1 = sortedPoints[0]
        p2 = sortedPoints[1]
    
        
        #calculate distance & MidpointGY
        distVector = Vector(p1)-Vector(p2)
        dist = distVector.length
        midpoint = interpolate3d(p1, p2, fabs(dist / 2))
        normDistVector = distVector.normalized()
        absNormDisVector = Vector((abs(normDistVector[0]),abs(normDistVector[1]),abs(normDistVector[2])))


        # Compute offset vector from face normal and user input
        rotationMatrix = Matrix.Rotation(dim.dimRotation, 4, normDistVector)
        selectedNormal = Vector(select_normal(myobj, dim, normDistVector, midpoint, dimProps))
        
        userOffsetVector = rotationMatrix@selectedNormal
        offsetDistance = userOffsetVector*offset
        geoOffsetDistance = offsetDistance.normalized()*geoOffset

        if offsetDistance < geoOffsetDistance:
            offsetDistance = geoOffsetDistance


        #Set Gizmo Props
        dim.gizLoc = midpoint
        dim.gizRotDir = userOffsetVector
        
        # Define Lines
        leadStartA = Vector(p1) + geoOffsetDistance
        leadEndA = Vector(p1) + offsetDistance + (offsetDistance.normalized()*0.005*capSize)

        leadStartB = Vector(p2) + geoOffsetDistance
        leadEndB = Vector(p2) + offsetDistance + (offsetDistance.normalized()*0.005*capSize)

        dimLineStart = Vector(p1)+offsetDistance
        dimLineEnd = Vector(p2)+offsetDistance
        textLoc = interpolate3d(dimLineStart, dimLineEnd, fabs(dist / 2))

        # i,j,k as card axis
        i = Vector((1,0,0))
        j = Vector((0,1,0))
        k = Vector((0,0,1))

        # Check for text field
        if len(dim.textFields) == 0:
            dim.textFields.add()

        dimText = dim.textFields[0]

        # format text and update if necessary
        distanceText = str(format_distance(textFormat,dist))
        if dimText.text != str(distanceText):
            dimText.text = str(distanceText)
            dimText.text_updated = True
        
        width = dimText.textWidth
        height = dimText.textHeight 
        

        resolution = dimProps.textResolution
        size = dimProps.fontSize/fontSizeMult
        sx = (width/resolution)*0.1*size
        sy = (height/resolution)*0.1*size
        origin = Vector(textLoc)
        cardX = normDistVector.normalized() * sx
        cardY = userOffsetVector.normalized() *sy

        flipCaps = False
        if (cardX.length + capSize/100) > dist:
            flipCaps=True
            origin = Vector(dimLineEnd) - Vector(cardX/2 + cardX.normalized()*capSize/100) -Vector(cardY/2)
        
        square = [(origin-(cardX/2)),(origin-(cardX/2)+cardY),(origin+(cardX/2)+cardY),(origin+(cardX/2))]
        if scene.measureit_arch_gl_show_d:
            draw_text_3D(context,dimText,dimProps,myobj,square)

        #Collect coords and endcaps
        coords = [leadStartA,leadEndA,leadStartB,leadEndB,dimLineStart,dimLineEnd]
        filledCoords = []
        pos = (dimLineStart,dimLineEnd)
        i=0
        for cap in caps:
            capCoords = generate_end_caps(context,dimProps,cap,capSize,pos[i],userOffsetVector,textLoc,i,flipCaps)
            i += 1 
            for coord in capCoords[0]:
                coords.append(coord)
            for filledCoord in capCoords[1]:
                filledCoords.append(filledCoord)

        
        # Keep this out of the loop to avoid extra draw calls 
        if len(filledCoords) != 0:
            #bind shader
            bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
            triShader.bind()
            triShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
            triShader.uniform_float("offset", 0)

            batch = batch_for_shader(triShader, 'TRIS', {"pos": filledCoords})
            batch.program_set(triShader)
            batch.draw()
            gpu.shader.unbind()
            bgl.glDisable(bgl.GL_POLYGON_SMOOTH)
        
        #bind shader
        
        lineShader.bind()
        lineShader.uniform_float("Viewport",viewport)
        lineShader.uniform_float("thickness",lineWeight)
        lineShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
        lineShader.uniform_float("offset", 0)

        # batch & Draw Shader   
        batch = batch_for_shader(lineShader, 'LINES', {"pos": coords})
        batch.program_set(lineShader)
        batch.draw()
        gpu.shader.unbind()
        
        #Reset openGL Settings
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        bgl.glDepthMask(True)


def draw_boundsDimension(context, myobj, measureGen, dim, mat):
    # GL Settings
    bgl.glEnable(bgl.GL_MULTISAMPLE)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glDepthFunc(bgl.GL_LEQUAL)
    bgl.glDepthMask(False)
    sceneProps = context.scene.MeasureItArchProps
    dimProps = dim
    if dim.uses_style:
        for alignedDimStyle in context.scene.StyleGenerator.alignedDimensions:
            if alignedDimStyle.name == dim.style:
                dimProps = alignedDimStyle

    bgl.glEnable(bgl.GL_DEPTH_TEST)
    if dim.inFront:
         bgl.glDisable(bgl.GL_DEPTH_TEST)

    lineWeight = dimProps.lineWeight
    # check all visibility conditions
    if dim.dimVisibleInView is None or dim.dimVisibleInView.name == context.scene.camera.data.name:
        inView = True        
    else:
        inView = False    
    if dim.visible and dimProps.visible and inView:

        if sceneProps.is_render_draw:
            viewport = [context.scene.render.resolution_x, context.scene.render.resolution_y]
        else:
            viewport = [context.area.width, context.area.height]

        # Obj Properties
        
        bounds = myobj.bound_box
        measureAxis = []
        scene = context.scene
        pr = scene.measureit_arch_gl_precision
        textFormat = "%1." + str(pr) + "f"
        rawRGB = dimProps.color
        rgb = (pow(rawRGB[0], (1/2.2)), pow(rawRGB[1], (1/2.2)), pow(rawRGB[2], (1/2.2)), rawRGB[3])
        
        # Define Caps as a tuple of capA and capB to reduce code duplications
        caps = (dimProps.endcapA, dimProps.endcapB)
        capSize = dimProps.endcapSize

        offset = dim.dimOffset
        geoOffset = dim.dimLeaderOffset

        # identify axis pairs
        zpairs = [[0,1],
                  [2,3],
                  [4,5],
                  [6,7]]
        
        xpairs = [[0,4],
                  [1,5],
                  [2,6],
                  [3,7]]

        ypairs = [[0,3],
                  [1,2],
                  [4,7],
                  [5,6]]

        ## Select Best Pairs

        diagonalPair = [2,4]
        dp1 = myobj.matrix_world @ Vector(bounds[2])
        dp2 = myobj.matrix_world @ Vector(bounds[4])
        dplength = Vector(dp1 - dp2).length
        centerpoint = interpolate3d(dp1,dp2,dplength/2)

        # get view vector
        i = Vector((1,0,0)) # X Unit Vector
        j = Vector((0,1,0)) # Y Unit Vector
        k = Vector((0,0,1)) # Z Unit Vector

        viewVec = Vector((0,0,0)) # dummy vector to avoid errors

        if sceneProps.is_render_draw:
            cameraLoc = context.scene.camera.location.normalized()
            viewAxis = cameraLoc
        else:
            viewRot = context.area.spaces[0].region_3d.view_rotation
            viewVec = k.copy()
            viewVec.rotate(viewRot)
            viewAxis = viewVec

        bestPairs = [xpairs[2],ypairs[1],zpairs[0]]
        pairs = [xpairs,ypairs,zpairs]
        #draw points for debug
        if False:
            pointShader.bind()
            pointShader.uniform_float("Viewport",viewport)
            pointShader.uniform_float("thickness", 5)
            pointShader.uniform_float("offset", 0)

    
        # establish measure loop
        idx = 0
        selectionVectors = [k,i,j]
        for axis in dim.drawAxis:
            if axis:
                # get points 
                axisViewVec = viewVec.copy()
                axisViewVec[idx] = 0
                p1 = myobj.matrix_world @ Vector(bounds[bestPairs[idx][0]])
                p2 = myobj.matrix_world @ Vector(bounds[bestPairs[idx][1]])

                #check dominant Axis
                sortedPoints = sortPoints(p1, p2)
                p1 = sortedPoints[0]
                p2 = sortedPoints[1]
            
                
                #calculate distance & MidpointGY
                distVector = Vector(p1)-Vector(p2)
                dist = distVector.length
                midpoint = interpolate3d(p1, p2, fabs(dist / 2))
                normDistVector = distVector.normalized()
                absNormDisVector = Vector((abs(normDistVector[0]),abs(normDistVector[1]),abs(normDistVector[2])))


                # Compute offset vector from face normal and user input
                rotationMatrix = Matrix.Rotation(dim.dimRotation, 4, normDistVector)

                selectedNormal = -absNormDisVector.cross(axisViewVec).normalized()

                #print(str(idx) + " " + str(abs(selectedNormal.dot(selectionVectors[idx]))))

                if abs(selectedNormal.dot(selectionVectors[idx])) > 0.8:
                    selectedNormal = selectionVectors[idx]
                else:
                    selectedNormal = -absNormDisVector.cross(selectionVectors[idx]).normalized()
                
                if selectedNormal.dot((Vector(midpoint)-Vector(centerpoint)).normalized())<0:
                    selectedNormal = -selectedNormal
                
                userOffsetVector = rotationMatrix@selectedNormal
                offsetDistance = userOffsetVector*offset
                geoOffsetDistance = offsetDistance.normalized()*geoOffset

                if offsetDistance < geoOffsetDistance:
                    offsetDistance = geoOffsetDistance


                #Set Gizmo Props
                dim.gizLoc = midpoint
                dim.gizRotDir = userOffsetVector
                
                # Define Lines
                leadStartA = Vector(p1) + geoOffsetDistance
                leadEndA = Vector(p1) + offsetDistance + (offsetDistance.normalized()*0.005*capSize)

                leadStartB = Vector(p2) + geoOffsetDistance
                leadEndB = Vector(p2) + offsetDistance + (offsetDistance.normalized()*0.005*capSize)

                dimLineStart = Vector(p1)+offsetDistance
                dimLineEnd = Vector(p2)+offsetDistance
                textLoc = interpolate3d(dimLineStart, dimLineEnd, fabs(dist / 2))

                #i,j,k as card axis
                i = Vector((1,0,0))
                j = Vector((0,1,0))
                k = Vector((0,0,1))

                # Check for text field
                #print (len(dim.textFields))
                dimText = dim.textFields[idx]

                # format text and update if necessary
                distanceText = str(format_distance(textFormat,dist))
                if dimText.text != str(distanceText):
                    dimText.text = str(distanceText)
                    dimText.text_updated = True
                
                width = dimText.textWidth
                height = dimText.textHeight 
                

                resolution = dimProps.textResolution
                size = dimProps.fontSize/fontSizeMult
                sx = (width/resolution)*0.1*size
                sy = (height/resolution)*0.1*size
                origin = Vector(textLoc)
                cardX = normDistVector.normalized() * sx
                cardY = userOffsetVector.normalized() *sy

                flipCaps = False
                if (cardX.length + capSize/100) > dist:
                    flipCaps=True
                    origin = Vector(dimLineEnd) - Vector(cardX/2 + cardX.normalized()*capSize/100) -Vector(cardY/2)
                
                square = [(origin-(cardX/2)),(origin-(cardX/2)+cardY),(origin+(cardX/2)+cardY),(origin+(cardX/2))]
                if scene.measureit_arch_gl_show_d:
                    draw_text_3D(context,dimText,dimProps,myobj,square)

            

                #Collect coords and endcaps
                coords = [leadStartA,leadEndA,leadStartB,leadEndB,dimLineStart,dimLineEnd]
                #coords.append((0,0,0))
                #coords.append(axisViewVec)
                filledCoords = []
                pos = (dimLineStart,dimLineEnd)
                i=0
                for cap in caps:
                    capCoords = generate_end_caps(context,dimProps,cap,capSize,pos[i],userOffsetVector,textLoc,i,flipCaps)
                    i += 1 
                    for coord in capCoords[0]:
                        coords.append(coord)
                    for filledCoord in capCoords[1]:
                        filledCoords.append(filledCoord)

                
                # Keep this out of the loop to avoid extra draw calls 
                if len(filledCoords) != 0:
                    #bind shader
                    bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
                    triShader.bind()
                    triShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
                    triShader.uniform_float("offset", 0)

                    batch = batch_for_shader(triShader, 'TRIS', {"pos": filledCoords})
                    batch.program_set(triShader)
                    batch.draw()
                    gpu.shader.unbind()
                    bgl.glDisable(bgl.GL_POLYGON_SMOOTH)
                
                #bind shader
                
                lineShader.bind()
                lineShader.uniform_float("Viewport",viewport)
                lineShader.uniform_float("thickness",lineWeight)
                lineShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
                lineShader.uniform_float("offset", 0)

                # batch & Draw Shader   
                batch = batch_for_shader(lineShader, 'LINES', {"pos": coords})
                batch.program_set(lineShader)
                batch.draw()
                gpu.shader.unbind()
            idx+=1
        #Reset openGL Settings
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        bgl.glDepthMask(True)



def draw_axisDimension(context, myobj, measureGen,dim, mat):
    # GL Settings

    #start = time.perf_counter()
    bgl.glEnable(bgl.GL_MULTISAMPLE)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glDepthFunc(bgl.GL_LEQUAL)
    bgl.glDepthMask(False)

    dimProps = dim

    if dim.uses_style:
        for alignedDimStyle in context.scene.StyleGenerator.alignedDimensions:
            if alignedDimStyle.name == dim.style:
                dimProps = alignedDimStyle

    sceneProps = context.scene.MeasureItArchProps

    bgl.glEnable(bgl.GL_DEPTH_TEST)
    if dimProps.inFront:
         bgl.glDisable(bgl.GL_DEPTH_TEST)

    lineWeight = dimProps.lineWeight
    #check all visibility conditions
    if dimProps.dimVisibleInView is None or dimProps.dimVisibleInView.name == context.scene.camera.data.name:
        inView = True        
    else:
        inView = False    
    if dim.visible and dimProps.visible and inView:

        # Get Viewport and CameraLoc or ViewRot
        if sceneProps.is_render_draw:
            viewport = [context.scene.render.resolution_x,context.scene.render.resolution_y]
            cameraLoc = context.scene.camera.location.normalized()
        else:
            viewport = [context.area.width,context.area.height]
            viewRot = context.area.spaces[0].region_3d.view_rotation


        # Obj Properties
        scene = context.scene
        pr = scene.measureit_arch_gl_precision
        textFormat = "%1." + str(pr) + "f"
        rawRGB = dimProps.color
        rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])
        
        axis = dim.dimAxis

        caps = (dimProps.endcapA, dimProps.endcapB)
        capSize = dimProps.endcapSize

        offset = dim.dimOffset
        geoOffset = dim.dimLeaderOffset
    
        # get points positions from indicies
        aMatrix = mat
        bMatrix = mat
        if dim.dimObjectB != dim.dimObjectA:
            bMatrix = dim.dimObjectB.matrix_world - dim.dimObjectA.matrix_world + mat 

        if dim.dimPointA == 9999999:
            p1 = dim.dimObjectA.location
        else:
            p1 = get_point(get_mesh_vertex(dim.dimObjectA,dim.dimPointA,dimProps.evalMods), dim.dimObjectA,aMatrix)
        
        if dim.dimPointB == 9999999:
            p2 = dim.dimObjectB.location
        else:
            p2 = get_point(get_mesh_vertex(dim.dimObjectB,dim.dimPointB,dimProps.evalMods), dim.dimObjectB,bMatrix)
        
        #Sort Points 
        sortedPoints = sortPoints(p1,p2)
        p1 = sortedPoints[0]
        p2 = sortedPoints[1]

        #i,j,k as base vectors
        i = Vector((1,0,0))
        j = Vector((0,1,0))
        k = Vector((0,0,1))
        
        if dim.dimViewPlane=='99':
            viewPlane = dimProps.dimViewPlane
        else:
            viewPlane = dim.dimViewPlane

        if viewPlane == 'XY':
            viewAxis = k
        elif viewPlane == 'XZ':
            viewAxis = j
        elif viewPlane == 'YZ':
            viewAxis = i
        elif viewPlane == '99':
            if sceneProps.is_render_draw:
                viewAxis = cameraLoc
            else:
                viewVec = k.copy()
                viewVec.rotate(viewRot)
                viewAxis = viewVec

        # define axis relatd values
        #basicThreshold = 0.5773
        if axis =='X':
            p1axis = (p1[0],0,0)
            p2axis = (p2[0],0,0)
            xThreshold = 0.95796
            yThreshold = 0.22146
            zThreshold = 0.197568
            axisVec = i
        elif axis == 'Y':
            p1axis = (0,p1[1],0)
            p2axis = (0,p2[1],0)
            xThreshold = 0.22146
            yThreshold = 0.95796
            zThreshold = 0.197568
            axisVec = j
        elif axis == 'Z':
            xThreshold = 0.24681
            yThreshold = 0.24681
            zThreshold = 0.93800
            p1axis = (0,0,p1[2])
            p2axis = (0,0,p2[2])
            axisVec = k

        # Divide the view space into four sectors by threshold
        if viewAxis[0] > xThreshold:
            viewSector = (1,0,0)
        elif viewAxis[0] < -xThreshold:
            viewSector = (-1,0,0)
        
        if viewAxis[1] > yThreshold:
            viewSector = (0,1,0)
        elif viewAxis[1] < -yThreshold:
            viewSector = (0,-1,0)

        if viewAxis[2] > zThreshold:
            viewSector = (0,0,1)
        elif viewAxis[2] < -zThreshold:
            viewSector = (0,0,-1)

        #calculate distance & Midpoint
        distVector = Vector(p1axis)-Vector(p2axis)
        
        dist = distVector.length
        midpoint = interpolate3d(p1, p2, fabs(dist / 2))
        normDistVector = distVector.normalized()
        absNormDistVector = Vector((abs(normDistVector[0]),abs(normDistVector[1]),abs(normDistVector[2])))

        # Compute offset vector from face normal and user input
        rotationMatrix = Matrix.Rotation(dim.dimRotation,4,normDistVector)
        selectedNormal = Vector(select_normal(myobj,dim,normDistVector,midpoint,dimProps))

        #The Direction of the Dimension Lines
        dirVector = Vector(viewSector).cross(axisVec)
        if dirVector.dot(selectedNormal) < 0:
            dirVector.negate()
        selectedNormal = dirVector.normalized()

        userOffsetVector = rotationMatrix@selectedNormal
        offsetDistance = userOffsetVector*offset
        geoOffsetDistance = offsetDistance.normalized()*geoOffset
        
        if offsetDistance < geoOffsetDistance:
            offsetDistance = geoOffsetDistance
   
        #Set Gizmo Props
        dim.gizLoc = midpoint
        dim.gizRotDir = userOffsetVector

        # Define Lines
        # get the components of p1 & p1 in the direction zvector
        p1Dir = Vector((p1[0]*dirVector[0],p1[1]*dirVector[1],p1[2]*dirVector[2]))
        p2Dir = Vector((p2[0]*dirVector[0],p2[1]*dirVector[1],p2[2]*dirVector[2]))
        
        domAxis = get_dom_axis(p1Dir)
        
        if p1Dir[domAxis] >= p2Dir[domAxis]:
            basePoint = p1
            secondPoint = p2
            secondPointAxis = Vector(p1axis) - Vector(p2axis)
            alignedDistVector = Vector(p2)-Vector(p1)
        else: 
            basePoint = p2
            secondPoint = p1
            secondPointAxis = Vector(p2axis) - Vector(p1axis)
            alignedDistVector = Vector(p1)-Vector(p2)


        # get the difference between the points in the view axis
        if viewPlane == '99':
            viewAxis = Vector(viewSector)
            if viewAxis[0]<0 or viewAxis[1]<0 or viewAxis[2]<0:
                viewAxis*= -1
        viewAxisDiff = Vector((alignedDistVector[0]*viewAxis[0],alignedDistVector[1]*viewAxis[1],alignedDistVector[2]*viewAxis[2]))
        
        dim.gizRotAxis = alignedDistVector

        #Lines
        leadStartA = Vector(basePoint) + geoOffsetDistance
        leadEndA = Vector(basePoint) + offsetDistance + (offsetDistance.normalized()*0.005*capSize)

        leadEndB =  leadEndA - Vector(secondPointAxis)
        leadStartB = Vector(secondPoint) - viewAxisDiff + geoOffsetDistance

        viewDiffStartB = leadStartB
        viewDiffEndB = leadStartB + viewAxisDiff

        

        dimLineStart = Vector(basePoint) + offsetDistance
        dimLineEnd = dimLineStart - Vector(secondPointAxis)
        textLoc = interpolate3d(dimLineStart, dimLineEnd, fabs(dist / 2))
       
       # Check for text field
        if len(dim.textFields) == 0:
            dim.textFields.add()

        dimText = dim.textFields[0]

        # format text and update if necessary
        distanceText = str(format_distance(textFormat,dist))
        if dimText.text != str(distanceText):
            dimText.text = str(distanceText)
            dimText.text_updated = True
        
        width = dimText.textWidth
        height = dimText.textHeight 

        resolution = dimProps.textResolution
        size = dimProps.fontSize/fontSizeMult
        sx = (width/resolution)*0.1*size
        sy = (height/resolution)*0.1*size
        origin = Vector(textLoc)
        cardX = Vector((abs(normDistVector[0]),-abs(normDistVector[1]),-abs(normDistVector[2]))) * sx
        cardY = userOffsetVector *sy

        # Flip endcaps if they're going to overlap the dim
        flipCaps = False
        if (cardX.length + capSize/80) > dist:
            flipCaps=True

        # Move dim to ext temporarily if the text is wider than the dimension line
        tempExtFlag = False
        if (cardX.length) > dist:
            if dim.textAlignment == 'C':
                tempExtFlag = True

        # Set Text Alignment 
        dimLineExtension = 0 # add some extension to the line if the dimension is ext
        if dim.textAlignment == 'L' :
            flipCaps=True
            dimLineExtension = capSize/50
            origin -= Vector((cardX.length/2 + dist/2 + dimLineExtension*1.2)* absNormDistVector) + Vector(cardY/2)
            
        elif dim.textAlignment == 'R':
            flipCaps=True
            dimLineExtension = capSize/50
            origin += Vector((cardX.length/2 + dist/2 + dimLineExtension*1.2)* absNormDistVector) - Vector(cardY/2)
             
        elif tempExtFlag:
            flipCaps=True
            dimLineExtension = capSize/50
            origin -= Vector((cardX.length/2 + dist/2 + dimLineExtension*1.2)* absNormDistVector) + Vector(cardY/2)

        if flipCaps:
            dimLineExtension = capSize/50

            

        # Add the Extension to the dimension line
        dimLineEndCoord = dimLineEnd - dimLineExtension * secondPointAxis.normalized()
        dimLineStartCoord = dimLineStart + dimLineExtension * secondPointAxis.normalized()
        
        square = [(origin-(cardX/2)),(origin-(cardX/2)+cardY ),(origin+(cardX/2)+cardY ),(origin+(cardX/2))]
        

       # end = time.perf_counter()
        #print(("calc time: "+ "%.3f"%((end-start)*1000)) + ' ms')  

        #start = time.perf_counter()
        if scene.measureit_arch_gl_show_d:
            draw_text_3D(context,dimText,dimProps,myobj,square)
        
        

        #Collect coords and endcaps
        coords = [leadStartA,leadEndA,leadStartB,leadEndB,dimLineStartCoord,dimLineEndCoord,viewDiffStartB,viewDiffEndB]
        filledCoords = []
        pos = (dimLineStart,dimLineEnd)
        i=0
        for cap in caps:
            capCoords = generate_end_caps(context,dimProps,cap,capSize,pos[i],userOffsetVector,textLoc,i,flipCaps)
            i += 1 
            for coord in capCoords[0]:
                coords.append(coord)
            for filledCoord in capCoords[1]:
                filledCoords.append(filledCoord)

        
        # Keep this out of the loop to avoid extra draw calls 
        if len(filledCoords) != 0:
            #bind shader
            bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
            triShader.bind()
            triShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
            triShader.uniform_float("offset", 0)

            batch = batch_for_shader(triShader, 'TRIS', {"pos": filledCoords})
            batch.program_set(triShader)
            batch.draw()
            gpu.shader.unbind()
            bgl.glDisable(bgl.GL_POLYGON_SMOOTH)
        
        #bind shader
        lineShader.bind()
        lineShader.uniform_float("Viewport",viewport)
        lineShader.uniform_float("thickness",lineWeight)
        lineShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
        lineShader.uniform_float("offset", 0)

        # batch & Draw Shader   
        batch = batch_for_shader(lineShader, 'LINES', {"pos": coords})
        batch.program_set(lineShader)
        batch.draw()
        gpu.shader.unbind()

        #Reset openGL Settings
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        bgl.glDepthMask(True)

        #end = time.perf_counter()
        #print(("draw time: "+ "%.3f"%((end-start)*1000)) + ' ms')  

def draw_angleDimension(context, myobj, DimGen, dim,mat):
    dimProps = dim
    sceneProps = context.scene.MeasureItArchProps
    if dim.uses_style:
        for alignedDimStyle in context.scene.StyleGenerator.alignedDimensions:
            if alignedDimStyle.name == dim.style:
                dimProps = alignedDimStyle

    # Check Visibility Conditions
    inView = False
    if dim.dimVisibleInView is None or dim.dimVisibleInView.name == context.scene.camera.data.name:
        inView = True
    
    if inView and dim.visible and dimProps.visible:
         # GL Settings
        bgl.glEnable(bgl.GL_MULTISAMPLE)
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        if dimProps.inFront:
            bgl.glDisable(bgl.GL_DEPTH_TEST)
        bgl.glDepthMask(False)

        lineWeight = dimProps.lineWeight
        if sceneProps.is_render_draw:
            viewport = [context.scene.render.resolution_x,context.scene.render.resolution_y]
        else:
            viewport = [context.area.width,context.area.height]


        scene = context.scene
        pr = scene.measureit_arch_gl_precision
        a_code = "\u00b0"  # degree
        fmt = "%1." + str(pr) + "f"
        rawRGB = dimProps.color
        rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])
        radius = dim.dimRadius
        offset = 0.001

        p1 = Vector(get_point(get_mesh_vertex(myobj,dim.dimPointA,dimProps.evalMods), myobj,mat))
        p2 = Vector(get_point(get_mesh_vertex(myobj,dim.dimPointB,dimProps.evalMods), myobj,mat))
        p3 = Vector(get_point(get_mesh_vertex(myobj,dim.dimPointC,dimProps.evalMods), myobj,mat))

        #calc normal to plane defined by points
        vecA = (p1-p2)
        vecA.normalize()
        vecB = (p3-p2)
        vecB.normalize()
        norm = vecA.cross(vecB).normalized()


        distVector = vecA-vecB
        dist = distVector.length
        angle = vecA.angle(vecB)
        startVec = vecA.copy()
        endVec = vecB.copy()

        #get Midpoint for Text Placement
        midVec = Vector(interpolate3d(vecA, vecB, (dist/2)))
        midVec.normalize()
        midPoint = (midVec*radius*1.05) + p2

        # Check use reflex Angle (reflex angle is an angle between 180 and 360 degrees)
        if dim.reflexAngle:
            angle = radians(360) - angle
            startVec = vecB.copy()
            endVec = vecA.copy()
            midVec.rotate(Quaternion(norm,radians(180)))
            midPoint = (midVec*radius*1.05) + p2

        #making it a circle
        numCircleVerts = math.ceil(radius/.2)+ int((degrees(angle))/2)
        verts = []
        for idx in range (numCircleVerts+1):
            rotangle= (angle/(numCircleVerts+1))*idx
            point = startVec.copy()
            point.rotate(Quaternion(norm,rotangle))
            #point.normalize()
            verts.append(point)


        
        #Format Angle
        if bpy.context.scene.unit_settings.system_rotation == "DEGREES":
            angle = degrees(angle)
        # format text
        angleText = " " + fmt % angle
        # Add degree symbol
        if bpy.context.scene.unit_settings.system_rotation == "DEGREES":
            angleText += a_code
        # Update if Necessary
        if len(dim.textFields) == 0:
            dim.textFields.add()

        if dim.textFields[0].text != str(angleText):
            dim.textFields[0].text = str(angleText)
            dim.textFields[0].text_updated = True
        
        #make text card
        vecX = midVec.cross(norm).normalized()
        width = dim.textFields[0].textWidth
        height = dim.textFields[0].textHeight 
        resolution = dimProps.textResolution
        size = dimProps.fontSize/fontSizeMult
        sx = (width/resolution)*0.1*size
        sy = (height/resolution)*0.1*size
        origin = Vector(midPoint)
        cardX = vecX * sx
        cardY = midVec *sy
        square = [(origin-(cardX/2)),(origin-(cardX/2)+cardY ),(origin+(cardX/2)+cardY ),(origin+(cardX/2))]

        if scene.measureit_arch_gl_show_d:
            draw_text_3D(context,dim.textFields[0],dimProps,myobj,square)



        #configure shaders
        pointShader.bind()
        pointShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
        pointShader.uniform_float("thickness", lineWeight)
        pointShader.uniform_float("offset", -offset)
        gpu.shader.unbind()

        lineShader.bind()
        lineShader.uniform_float("Viewport",viewport)
        lineShader.uniform_float("thickness",lineWeight)
        lineShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
        lineShader.uniform_float("offset", -offset)

        # Draw Point Pass for Clean Corners
        # I'm being lazy here, should do a proper lineadjacency
        # with miters and do this in one pass
        pointCoords = []
        pointCoords.append((startVec*radius)+p2)
        for vert in verts:
            pointCoords.append((vert*radius)+p2)
        pointCoords.append((endVec*radius)+p2)
        batch3d = batch_for_shader(pointShader, 'POINTS', {"pos":pointCoords})
        batch3d.program_set(pointShader)
        batch3d.draw()

        

        # batch & Draw Shader
        coords = []
        coords.append((startVec*radius)+p2)
        for vert in verts:
            coords.append((vert*radius)+p2)
            coords.append((vert*radius)+p2)
        coords.append((endVec*radius)+p2)

        filledCoords = []
        caps = (dimProps.endcapA,dimProps.endcapB)
        capSize = dimProps.endcapSize
        pos = ((startVec*radius)+p2,(endVec*radius)+p2)
        arrowoffset =  int(max(0, min(capSize, len(coords)/4))) #Clamp capsize between 0 and the length of the coords
        mids = (coords[arrowoffset+1], coords[len(coords)-arrowoffset-1]) #offset the arrow direction as arrow size increases
        i=0
        for cap in caps:
            #def        generate_end_caps(context,item,capType,capSize,pos,userOffsetVector,midpoint,posflag,flipCaps):
            capCoords = generate_end_caps(context,dimProps,cap,capSize,pos[i],midVec,mids[i],i,False)
            i += 1 
            for coord in capCoords[0]:
                coords.append(coord)
            for filledCoord in capCoords[1]:
                filledCoords.append(filledCoord)

       
        if len(filledCoords) != 0:
            #bind shader
            bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
            triShader.bind()
            triShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
            triShader.uniform_float("offset", -offset) #z offset this a little to avoid zbuffering

            batch = batch_for_shader(triShader, 'TRIS', {"pos": filledCoords})
            batch.program_set(triShader)
            batch.draw()
            gpu.shader.unbind()
            bgl.glDisable(bgl.GL_POLYGON_SMOOTH)

        batch = batch_for_shader(lineShader, 'LINES', {"pos": coords})
        batch.program_set(lineShader)
        batch.draw()
        gpu.shader.unbind()

        #Reset openGL Settings
        bgl.glDisable(bgl.GL_DEPTH_TEST)
        bgl.glDepthMask(True)

def select_normal(myobj, dim, normDistVector, midpoint, dimProps):
    #Set properties
    context = bpy.context
    sceneProps = context.scene.MeasureItArchProps
    i = Vector((1,0,0)) # X Unit Vector
    j = Vector((0,1,0)) # Y Unit Vector
    k = Vector((0,0,1)) # Z Unit Vector
    loc = Vector(get_location(myobj))
    centerRay = Vector((-1,1,1))
    badNormals = False 

    # Check for View Plane Overides
    if dim.dimViewPlane=='99':
        viewPlane = dimProps.dimViewPlane
    else:
        viewPlane = dim.dimViewPlane

    # Set viewAxis
    if viewPlane == 'XY':
        viewAxis = k
    elif viewPlane == 'XZ':
        viewAxis = j
    elif viewPlane == 'YZ':
        viewAxis = i

    if viewPlane == '99':
        # Get Viewport and CameraLoc or ViewRot
        if sceneProps.is_render_draw:
            cameraLoc = context.scene.camera.location.normalized()
            viewAxis = cameraLoc
        else:
            viewRot = context.area.spaces[0].region_3d.view_rotation
            viewVec = k.copy()
            viewVec.rotate(viewRot)
            viewAxis = viewVec

        # Use Basic Threshold
        basicThreshold = 0.5773

        # Set View axis Based on View Sector
        if viewAxis[0] > basicThreshold or viewAxis[0] < -basicThreshold:
            viewAxis = i
        if viewAxis[1] > basicThreshold or viewAxis[1] < -basicThreshold:
            viewAxis = j
        if viewAxis[2] > basicThreshold or viewAxis[2] < -basicThreshold:
            viewAxis = k

    # Mesh Dimension Behaviour
    if myobj.type == 'MESH':
        if dim.dimPointA != 9999999:
            vertA = myobj.data.vertices[dim.dimPointA]
            directionRay = vertA.normal + loc 
        else:
            directionRay = Vector((0,0,0))
            
        #get Adjacent Face normals if possible
        possibleNormals = []
        faces = myobj.data.polygons
        if len(faces)<2000:    
            for face in myobj.data.polygons:
                if dim.dimPointA in face.vertices and dim.dimPointB in face.vertices:
                    worldNormal = myobj.matrix_local@Vector(face.normal)
                    worldNormal -= myobj.location
                    worldNormal.normalize()
                    possibleNormals.append(worldNormal)
                        
        # Check if Face Normals are available
        if len(possibleNormals) != 2: badNormals = True
        else:
            bestNormal = Vector((0,0,0))
            sumNormal = Vector((0,0,0))
            for norm in possibleNormals:
                sumNormal += norm

            # Check relevent component against current best normal
            checkValue = 0 
            planeNorm = Vector((0,0,0))
            possibleNormals.append(viewAxis)
            for norm in possibleNormals:
                newCheckValue = viewAxis.dot(norm)
                if abs(newCheckValue) > abs(checkValue):
                    planeNorm = norm
                    checkValue = newCheckValue
            
            # Make Dim Direction perpindicular to the plane normal and dimension direction
            bestNormal = planeNorm.cross(normDistVector)

            # if length is 0 just use the sum
            if bestNormal.length == 0:
                bestNormal = sumNormal

            # Check Direction
            if bestNormal.dot(sumNormal)<0:
                bestNormal.negate()

    # If Face Normals aren't available;
    # use the cross product of the View Plane Normal and the dimensions distance vector.
    if myobj.type != 'MESH' or badNormals:

        bestNormal = viewAxis.cross(normDistVector)
        if bestNormal.length == 0:
            bestNormal = centerRay

        if bestNormal.dot(centerRay)<0:
            bestNormal.negate()

    #Normalize Result
    bestNormal.normalize()
    return bestNormal 
        
def draw_line_group(context, myobj, lineGen, mat):
    bgl.glEnable(bgl.GL_MULTISAMPLE)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glEnable(bgl.GL_DEPTH_TEST)
    bgl.glDepthMask(False)
    scene = context.scene
    sceneProps = scene.MeasureItArchProps
    
    if sceneProps.is_render_draw:
        viewport = [context.scene.render.resolution_x,context.scene.render.resolution_y]
    else:
        viewport = [context.area.width,context.area.height]

    for idx in range(0, lineGen.line_num):
        lineGroup = lineGen.line_groups[idx]
        lineProps= lineGroup
        if lineGroup.uses_style:
            for lineStyle in context.scene.StyleGenerator.line_groups:
                if lineStyle.name == lineGroup.style:
                    lineProps= lineStyle
            
        if lineGroup.visible and lineProps.visible:
            bgl.glEnable(bgl.GL_DEPTH_TEST)
            if lineProps.inFront:
                bgl.glDisable(bgl.GL_DEPTH_TEST)


            rawRGB = lineProps.color        
            alpha = 1.0   
            if bpy.context.mode == 'EDIT_MESH':
                alpha=0.3
            else:
                alpha = rawRGB[3]

            #undo blenders Default Gamma Correction
            rgb = [pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),alpha]

            #overide line color with theme selection colors when selected
            if not sceneProps.is_render_draw:
                if myobj in context.selected_objects and bpy.context.mode != 'EDIT_MESH' and context.scene.measureit_arch_gl_ghost:
                    rgb[0] = bpy.context.preferences.themes[0].view_3d.object_selected[0]
                    rgb[1] = bpy.context.preferences.themes[0].view_3d.object_selected[1]
                    rgb[2] = bpy.context.preferences.themes[0].view_3d.object_selected[2]
                    rgb[3] = 1.0

                    if (context.view_layer.objects.active != None
                    and context.view_layer.objects.active.data != None
                    and myobj.data.name == context.view_layer.objects.active.data.name):
                        rgb[0] = bpy.context.preferences.themes[0].view_3d.object_active[0]
                        rgb[1] = bpy.context.preferences.themes[0].view_3d.object_active[1]
                        rgb[2] = bpy.context.preferences.themes[0].view_3d.object_active[2]
                        rgb[3] = 1.0

            #set other line properties
            isOrtho = False
            if sceneProps.is_render_draw:
                if scene.camera.data.type == 'ORTHO':
                    isOrtho = True
            else:
                for space in context.area.spaces:
                    if space.type == 'VIEW_3D':
                        r3d = space.region_3d
                if r3d.view_perspective == 'ORTHO':
                    isOrtho = True
                
            drawHidden = lineProps.lineDrawHidden
            lineWeight = lineProps.lineWeight

            # Calculate Offset with User Tweaks
            offset = lineWeight/2.5
            offset += lineProps.lineDepthOffset
            if isOrtho:
                offset /= 15
            if lineProps.isOutline:
                offset = -10 - offset
            offset /= 1000

            #gl Settings
            bgl.glDepthFunc(bgl.GL_LEQUAL) 

            
            #Get line data to be drawn
            coords =[]
            evalMods = lineProps.evalMods

            # Flag for re-evaluation of batches & mesh data
            verts=[]
            global lastMode
            recoordFlag = False
            if lastMode != myobj.mode:
                recoordFlag = True
                lastMode = myobj.mode
            
            if myobj.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(myobj.data)
                verts = bm.verts
            else:     
                eval_res = sceneProps.eval_mods
                if (eval_res or evalMods) and check_mods(myobj):
                    deps = bpy.context.view_layer.depsgraph
                    obj_eval = myobj.evaluated_get(deps)
                    mesh = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=deps)
                    verts = mesh.vertices          
                else:
                    verts = myobj.data.vertices

            # Get Coords
            sceneProps = bpy.context.scene.MeasureItArchProps
            if 'coordBuffer' not in lineGroup or evalMods or recoordFlag:
                tempCoords = [get_line_vertex(idx,verts,mat) for idx in lineGroup['lineBuffer']]
                lineGroup['coordBuffer'] = tempCoords

            
            coords = lineGroup['coordBuffer']
            start = time.time ()



            if drawHidden == True:
                # Invert The Depth test for hidden lines
                bgl.glDepthFunc(bgl.GL_GREATER)
                hiddenLineWeight = lineProps.lineHiddenWeight
                
                rawRGB = lineProps.lineHiddenColor
                #undo blenders Default Gamma Correction
                dashRGB = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])

                dashedLineShader.bind()
                dashedLineShader.uniform_float("u_Scale", lineProps.lineHiddenDashScale)
                dashedLineShader.uniform_float("Viewport",viewport)
                dashedLineShader.uniform_float("objectMatrix",mat)
                dashedLineShader.uniform_float("thickness",hiddenLineWeight)
                dashedLineShader.uniform_float("screenSpaceDash",lineProps.screenSpaceDashes)
                dashedLineShader.uniform_float("finalColor", (dashRGB[0], dashRGB[1], dashRGB[2], dashRGB[3]))
                dashedLineShader.uniform_float("offset", -offset)


                global hiddenBatch3D
                if  hiddenBatch3D == None or recoordFlag:
                    hiddenBatch3D = batch_for_shader(dashedLineShader,'LINES',{"pos":coords}) 
                if sceneProps.is_render_draw:
                    batchHidden = batch_for_shader(dashedLineShader,'LINES',{"pos":coords}) 
                else:
                    batchHidden = hiddenBatch3D

                batchHidden.program_set(dashedLineShader)
                batchHidden.draw()

                bgl.glDepthFunc(bgl.GL_LESS)
                gpu.shader.unbind()
                end= time.time()
                post = ' Hidden Line Shader for ' + str(math.ceil(len(lineGroup['lineBuffer'])/2)) + ' line segemtns'
                printTime(start,end,post)
                start = time.time ()
            
 
            if lineProps.lineDrawDashed:
                dashedLineShader.bind()
                dashedLineShader.uniform_float("u_Scale", lineProps.lineHiddenDashScale)
                dashedLineShader.uniform_float("Viewport",viewport)
                dashedLineShader.uniform_float("objectMatrix",mat)
                dashedLineShader.uniform_float("thickness",lineWeight)
                dashedLineShader.uniform_float("screenSpaceDash",lineProps.screenSpaceDashes)
                dashedLineShader.uniform_float("finalColor",  (rgb[0], rgb[1], rgb[2], rgb[3]))
                dashedLineShader.uniform_float("offset", -offset)

                global dashedBatch3D
                if dashedBatch3D == None or recoordFlag:
                    dashedBatch3D = batch_for_shader(dashedLineShader,'LINES',{"pos":coords}) 
                if sceneProps.is_render_draw:
                    batchDashed = batch_for_shader(dashedLineShader,'LINES',{"pos":coords}) 
                else:
                    batchDashed = dashedBatch3D

                batchDashed .program_set(dashedLineShader)
                batchDashed .draw()
                end= time.time()
                post = 'All Dashed Line Shader for ' + str(math.ceil(len(lineGroup['lineBuffer'])/2)) + ' line segemtns'
                printTime(start,end,post)
                start = time.time ()

            else:
                lineGroupShader.bind()
                lineGroupShader.uniform_float("Viewport",viewport)
                lineGroupShader.uniform_float("objectMatrix",mat)
                lineGroupShader.uniform_float("thickness",lineWeight)
                lineGroupShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
                lineGroupShader.uniform_float("offset", -offset)

                global lineBatch3D
                if lineBatch3D == None or recoordFlag:
                    lineBatch3D = batch_for_shader(lineGroupShader, 'LINES', {"pos": coords})
                    batch3d = lineBatch3D
                if sceneProps.is_render_draw:
                    batch3d = batch_for_shader(lineGroupShader, 'LINES', {"pos": coords})
                else:
                    batch3d = lineBatch3D
               
                batch3d.program_set(lineGroupShader)
                batch3d.draw()
                gpu.shader.unbind()
                end= time.time()
                post = ' Line Shader for ' + str(math.ceil(len(lineGroup['lineBuffer'])/2)) + ' line segemtns'
                printTime(start,end,post)
                start = time.time ()
    
    gpu.shader.unbind()
    bgl.glDisable(bgl.GL_DEPTH_TEST)
    bgl.glDepthMask(True)

def draw_annotation(context, myobj, annotationGen, mat):
    scene = context.scene
    bgl.glEnable(bgl.GL_MULTISAMPLE)
    bgl.glEnable(bgl.GL_BLEND)

    bgl.glDepthMask(False)
    sceneProps = scene.MeasureItArchProps

    if sceneProps.is_render_draw:
        viewport = [context.scene.render.resolution_x,context.scene.render.resolution_y]
    else:
        viewport = [context.area.width,context.area.height]
    

    for idx in range(0, annotationGen.num_annotations):
        annotation = annotationGen.annotations[idx]
        annotationProps = annotation
        if annotation.uses_style:
            for annotationStyle in context.scene.StyleGenerator.annotations:
                if annotationStyle.name == annotation.style:
                    annotationProps= annotationStyle

        bgl.glEnable(bgl.GL_DEPTH_TEST)
        if annotationProps.inFront:
            bgl.glDisable(bgl.GL_DEPTH_TEST)

        endcap = annotationProps.endcapA
        endcapSize = annotationProps.endcapSize

        if annotation.visible and annotationProps.visible:
            lineWeight = annotationProps.lineWeight
            rawRGB = annotationProps.color
            #undo blenders Default Gamma Correction
            rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])

            pointShader.bind()
            pointShader.uniform_float("Viewport",viewport)
            pointShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
            pointShader.uniform_float("thickness", lineWeight)
            pointShader.uniform_float("offset", 0)
            gpu.shader.unbind()

            lineShader.bind()
            lineShader.uniform_float("Viewport",viewport)
            lineShader.uniform_float("thickness",lineWeight)
            lineShader.uniform_float("offset", 0)
            lineShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))

            # Get Points
            if annotation.annotationAnchorObject.type == 'MESH':
                p1 = get_point(get_mesh_vertex(myobj,annotation.annotationAnchor,annotationProps.evalMods), myobj,mat)
            else:
                p1 = mat @ Vector((0,0,0))

            loc = mat.to_translation()
            diff = Vector(p1) - Vector(loc)
            offset = annotation.annotationOffset
            
            p2 =  Vector(offset)

            #Get local Rotation and Translation
            rot = mat.to_quaternion()
            loc = mat.to_translation()

            #Compose Rotation and Translation Matrix
            rotMatrix = Matrix.Identity(3)
            rotMatrix.rotate(rot)
            rotMatrix.resize_4x4()
            locMatrix = Matrix.Translation(loc)
            rotLocMatrix = locMatrix @ rotMatrix

            # Transform offset with Composed Matrix
            p2 = rotLocMatrix @ Vector(p2) + diff

            fieldIdx = 0
            if 'textFields' not in annotation:
                annotation.textFields.add()
            for textField in annotation.textFields:
                textcard = generate_text_card(context,textField,annotationProps,annotation.annotationRotation,(0,0,0))
                heightOffset = textcard[1] - textcard[0]
                # Transform Text Card with Composed Matrix
                textcard[0] = rotLocMatrix @ (textcard[0] + offset - (heightOffset*fieldIdx)) + diff
                textcard[1] = rotLocMatrix @ (textcard[1] + offset - (heightOffset*fieldIdx)) + diff
                textcard[2] = rotLocMatrix @ (textcard[2] + offset - (heightOffset*fieldIdx)) + diff
                textcard[3] = rotLocMatrix @ (textcard[3] + offset - (heightOffset*fieldIdx)) + diff

                textField['textcard'] = textcard
                fieldIdx += 1
            # Set Gizmo Properties
            annotation.gizLoc = p2

            # Draw
            if  p1 is not None and p2 is not None:

                coords =[]
                
                # Move end of line Back if arrow endcap
                if endcap == 'T':
                    axis = Vector(p1) - Vector(p2)
                    lineEnd = Vector(p1) - axis * 0.02 * lineWeight
                else: lineEnd = p1

                coords.append(lineEnd)
                coords.append(p2)
                coords.append(p2)

                textcard = annotation.textFields[0]['textcard']
                if annotation.textPosition == 'T':
                    coords.append(textcard[3])
                    pointcoords = [p2]
                elif annotation.textPosition == 'B':
                    coords.append(textcard[2])
                    pointcoords = [p2]

                batch3d = batch_for_shader(lineShader, 'LINES', {"pos": coords})
                batch3d.program_set(lineShader)
                batch3d.draw()
                gpu.shader.unbind()
                
                # Again This is Super Lazy, gotta write up a shader that handles
                # Mitered thick lines, but for now this works.
                #if annotation.textPosition == 'T' or annotation.textPosition == 'B':
                #    batch3d = batch_for_shader(pointShader, 'POINTS', {"pos": pointcoords})
                #    batch3d.program_set(pointShader)
                #    batch3d.draw()
            
            # Draw Line Endcaps
            if endcap == 'D':
                pointShader.bind()
                pointShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
                pointShader.uniform_float("thickness", endcapSize)
                pointShader.uniform_float("offset", -0.01)
                gpu.shader.unbind()
                
                pointcoords = [p1]
                batch3d = batch_for_shader(pointShader, 'POINTS', {"pos": pointcoords})
                batch3d.program_set(pointShader)
                batch3d.draw()
            
            if endcap == 'T':
                axis = Vector(p1) - Vector(p2)
                line = interpolate3d(Vector((0,0,0)), axis, -0.1)
                line = Vector(line) * endcapSize/10
                perp = line.orthogonal()
                rotangle = annotationProps.endcapArrowAngle-radians(5)
                line.rotate(Quaternion(perp,rotangle))
                coords = []
                for idx in range (12):
                    rotangle = radians(360/12)
                    coords.append(line.copy() + Vector(p1))
                    coords.append(Vector((0,0,0)) + Vector(p1))
                    line.rotate(Quaternion(axis,rotangle))
                    coords.append(line.copy() + Vector(p1))

                bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
                triShader.bind()
                triShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
                triShader.uniform_float("offset", (0,0,0))

                batch = batch_for_shader(triShader, 'TRIS', {"pos": coords})
                batch.program_set(triShader)
                batch.draw()
                gpu.shader.unbind()
                bgl.glDisable(bgl.GL_POLYGON_SMOOTH)

            if scene.measureit_arch_gl_show_d:
                for textField in annotation.textFields:
                    textcard = textField['textcard']
                    draw_text_3D(context,textField,annotationProps,myobj,textcard)                

    bgl.glDisable(bgl.GL_DEPTH_TEST)
    bgl.glDepthMask(True)

def draw_arc(basis,init_angle,current_angle):
    i = Vector((1,0,0))
    k = Vector((0,0,1))

    startrot = Quaternion(k,init_angle)
    endrot = Quaternion(k,current_angle)

    arcStart = i.copy()
    arcStart.rotate(startrot)

    angle = init_angle - current_angle
    radius = 1

    numCircleVerts = math.ceil(radius/.4)+ int((degrees(angle))/10)
    verts = []
    verts.append(Vector((0,0,0)))
    for idx in range (numCircleVerts+1):
        rotangle= (angle/(numCircleVerts+1))*idx
        point = arcStart.copy()
        point.rotate(Quaternion(k,rotangle))
        point = basis @ point
        verts.append(Vector((0,0,0)))
        verts.append(point)
        

    bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
    triShader.bind()
    triShader.uniform_float("finalColor", (1, 1, 1, 1))
    triShader.uniform_float("offset", 0)

    batch = batch_for_shader(triShader, 'TRIS', {"pos": verts})
    batch.program_set(triShader)
    batch.draw()
    gpu.shader.unbind()
    bgl.glDisable(bgl.GL_POLYGON_SMOOTH)

def draw_text_3D(context,textobj,textprops,myobj,card):
    #get props
    sceneProps = context.scene.MeasureItArchProps
    card[0] = Vector(card[0])
    card[1] = Vector(card[1])
    card[2] = Vector(card[2])
    card[3] = Vector(card[3])
    normalizedDeviceUVs= [(-1,-1),(-1,1),(1,1),(1,-1)]

    #i,j,k Basis Vectors
    i = Vector((1,0,0))
    j = Vector((0,1,0))
    k = Vector((0,0,1))
    basisVec=(i,j,k)

    #Get View rotation
    debug_camera = False
    if sceneProps.is_render_draw or debug_camera:
        cameraLoc = context.scene.camera.location.normalized()
        viewRot = context.scene.camera.rotation_euler.to_quaternion()
    else:
        viewRot = context.area.spaces[0].region_3d.view_rotation


    # Define Flip Matrix's
    flipMatrixX = Matrix([
        [-1,0],
        [ 0,1]   
    ])

    flipMatrixY = Matrix([
        [1, 0],
        [0,-1]   
    ])

    #Check Text Cards Direction Relative to view Vector
    # Card Indicies:
    #     
    #     1----------------2
    #     |                |
    #     |                |
    #     0----------------3

    cardDirX = (card[3]-card[0]).normalized()
    cardDirY = (card[1]-card[0]).normalized()
    cardDirZ = cardDirX.cross(cardDirY)

    viewAxisX = i.copy()
    viewAxisY = j.copy()
    viewAxisZ = k.copy()

    viewAxisX.rotate(viewRot)
    viewAxisY.rotate(viewRot)
    viewAxisZ.rotate(viewRot)
    
    # Skew Rotation slightly to avoid errors that occur
    # when the view Axis are perfectly orthogonal to the
    # card axis 
    rot = Quaternion(viewAxisZ,radians(0.5))
    viewAxisX.rotate(rot)
    viewAxisY.rotate(rot)

    if cardDirZ.dot(viewAxisZ) > 0:
        viewDif = viewAxisZ.rotation_difference(cardDirZ)
    else:
        viewAxisZ.negate()
        viewDif = viewAxisZ.rotation_difference(cardDirZ)
    
    viewAxisX.rotate(viewDif)
    viewAxisY.rotate(viewDif)

    if cardDirX.dot(viewAxisX)<0:
        flippedUVs = []
        for uv in normalizedDeviceUVs:
            uv = flipMatrixX@Vector(uv)
            flippedUVs.append(uv)
        normalizedDeviceUVs = flippedUVs

    if cardDirY.dot(viewAxisY)<0:
        flippedUVs = []
        for uv in normalizedDeviceUVs:
            uv = flipMatrixY@Vector(uv)
            flippedUVs.append(uv)
        normalizedDeviceUVs = flippedUVs
    
    #Draw View Axis in Red and Card Axis in Green for debug
    scene = bpy.context.scene
    autoflipdebug = sceneProps.debug_flip_text
    if autoflipdebug == True:
        viewport = [context.area.width,context.area.height]
        lineShader.bind()
        lineShader.uniform_float("Viewport",viewport)
        lineShader.uniform_float("thickness",4)
        lineShader.uniform_float("finalColor", (1, 0, 0, 1))
        lineShader.uniform_float("offset", 0)

        zero = Vector((0,0,0))
        coords = [zero,viewAxisX/2,zero,viewAxisY]
        batch = batch_for_shader(lineShader, 'LINES', {"pos": coords})
        batch.program_set(lineShader)
        batch.draw()
        
        lineShader.uniform_float("finalColor", (0, 1, 0, 1))
        coords = [zero,cardDirX/2,zero,cardDirY]
        batch = batch_for_shader(lineShader, 'LINES', {"pos": coords})
        batch.program_set(lineShader)
        batch.draw()

        print ("X dot: " + str(cardDirX.dot(viewAxisX)))
        print ("Y dot: " + str(cardDirY.dot(viewAxisY)))

    uvs = []
    for normUV in normalizedDeviceUVs:
        uv = (Vector(normUV) + Vector((1,1)))*0.5
        uvs.append(uv)

    # Batch Geometry
    batch = batch_for_shader(
        textShader, 'TRI_FAN',
        {
            "pos": card,
            "uv": uvs,
        },
    )

    # Gets Texture from Object
    width = textobj.textWidth
    height = textobj.textHeight 
    dim = width * height * 4

    if 'texture' in textobj and textobj.text != "":
        # np.asarray takes advantage of the buffer protocol and solves the bottleneck here!!!
        buffer = bgl.Buffer(bgl.GL_BYTE, dim, np.asarray(textobj['texture'], dtype=np.uint8))
        bgl.glTexImage2D(bgl.GL_TEXTURE_2D, 0, bgl.GL_RGBA, width, height, 0, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, buffer)
        bgl.glTexParameteri(bgl.GL_TEXTURE_2D, bgl.GL_TEXTURE_MIN_FILTER, bgl.GL_LINEAR)
        textobj.texture_updated=False
     
    # Draw Shader
    textShader.bind()
    textShader.uniform_float("image", 0)
    batch.draw(textShader)
    #bgl.glDeleteTextures(1, texBuf)
    gpu.shader.unbind()

def generate_end_caps(context,item,capType,capSize,pos,userOffsetVector,midpoint,posflag,flipCaps):
    capCoords = []
    filledCoords = []
    size = capSize/100
    distVector = Vector(pos-Vector(midpoint)).normalized()
    norm = distVector.cross(userOffsetVector)
    line = distVector*size
    arrowAngle = item.endcapArrowAngle

    if flipCaps:
        arrowAngle += radians(180)
    
    if capType == 99:
        pass
    
    #Line and Triangle Geometry
    elif capType == 'L' or capType == 'T' :
        rotangle = arrowAngle
        line.rotate(Quaternion(norm,rotangle))
        p1 = (pos - line)
        p2 = (pos)
        line.rotate(Quaternion(norm,-(rotangle*2)))
        p3 = (pos - line)
        
        if capType == 'T':
            filledCoords.append(p1)
            filledCoords.append(p2)
            filledCoords.append(p3)

        if capType == 'L':
            capCoords.append(p1)
            capCoords.append(p2)
            capCoords.append(p3)
            capCoords.append(p2)

    #Dashed Endcap Geometry
    elif capType == 'D':
        rotangle = radians(-90)
        line = userOffsetVector.copy()
        line *= 1/20
        line.rotate(Quaternion(norm,rotangle))
        p1 = (pos - line)
        p2 = (pos + line)

        # Define Overextension
        capCoords.append(pos)
        capCoords.append(line + pos)  

        # Define Square
        x = distVector.normalized() * capSize/20
        y = userOffsetVector.normalized() * capSize/20
        a = 0.055
        b = 0.085
       
        s1 = (a*x) + (b*y)
        s2 = (b*x) + (a*y)
        s3 = (-a*x) + (-b*y)
        s4 = (-b*x) + (-a*y)

        square = (s1,s2,s3,s4)

        for s in square:
            if posflag < 1:
                s.rotate(Quaternion(norm,rotangle))
            s += pos

        filledCoords.append(square[0])
        filledCoords.append(square[1])
        filledCoords.append(square[2])
        filledCoords.append(square[0])
        filledCoords.append(square[2])
        filledCoords.append(square[3]) 
    
    return capCoords, filledCoords

def generate_text_card(context,textobj,textProps,rotation,basePoint): 
    width = textobj.textWidth
    height = textobj.textHeight
    resolution = textProps.textResolution
    size = textProps.fontSize/fontSizeMult
    #Define annotation Card Geometry
    square = [(-0.5, 0.0, 0.0),(-0.5, 1.0, 0.0),(0.5, 1.0, 0.0),(0.5, 0.0, 0.0)]

    #pick approprate card based on alignment
    if textProps.textAlignment == 'R':
        aOff = (0.5,0.0,0.0)
    elif textProps.textAlignment == 'L':
        aOff = (-0.5,0.0,0.0)
    else:
        aOff = (0.0,0.0,0.0)

    if textProps.textPosition == 'M':
        pOff = (0.0,0.5,0.0)
    elif textProps.textPosition == 'B':
        pOff = (0.0,1.0,0.0)
    else:
        pOff = (0.0,0.0,0.0)

    #Define Transformation Matricies

    #x Rotation
    rx = rotation[0]
    rotateXMatrix = Matrix([
        [1,   0,      0,     0],
        [0,cos(rx) ,sin(rx), 0],
        [0,-sin(rx),cos(rx), 0],
        [0,   0,      0,     1]
    ])

    #y Rotation
    ry = rotation[1]
    rotateYMatrix = Matrix([
        [cos(ry),0,-sin(ry),0],
        [  0,    1,   0,    0],
        [sin(ry),0,cos(ry), 0],
        [  0,    0,   0,    1]
    ])

    #z Rotation
    rz = rotation[2]
    rotateZMatrix = Matrix([
        [cos(rz) ,sin(rz),0,0],
        [-sin(rz),cos(rz),0,0],
        [   0    ,   0   ,1,0],
        [   0    ,   0   ,0,1]
    ])

    #scale
    sx = (width/resolution)*0.1*size
    sy = (height/resolution)*0.1*size
    scaleMatrix = Matrix([
        [sx,0 ,0,0],
        [0 ,sy,0,0],
        [0 ,0 ,1,0],
        [0 ,0 ,0,1]
    ])

    #Transform
    tx = basePoint[0]
    ty = basePoint[1]
    tz = basePoint[2]
    translateMatrix = Matrix([
        [1,0,0,tx],
        [0,1,0,ty],
        [0,0,1,tz],
        [0,0,0, 1]
    ])

    # Transform Card By Transformation Matricies (Scale -> XYZ Euler Rotation -> Translate)
    xyzEulerRotMatrix = rotateXMatrix @ rotateYMatrix @ rotateZMatrix

    coords = []
    for coord in square:
        coord= Vector(coord) - Vector(aOff)
        coord= Vector(coord) - Vector(pOff)
        coord = scaleMatrix@Vector(coord)
        coord = rotateXMatrix@Vector(coord)
        coord = rotateYMatrix@Vector(coord)
        coord = rotateZMatrix@Vector(coord)
        coord = translateMatrix@Vector(coord)
        coords.append(coord)

    
    return (coords)

def sortPoints (p1, p2):
    tempDirVec = Vector(p1)-Vector(p2)

    domAxis = get_dom_axis(tempDirVec)

    #check dom axis alignment for text
    if domAxis==0:
        if p2[domAxis] > p1[domAxis]:
            switchTemp = p1
            p1 = p2
            p2 = switchTemp
    else:
        if p2[domAxis] < p1[domAxis]:
            switchTemp = p1
            p1 = p2
            p2 = switchTemp
    
    return p1,p2

def get_dom_axis (vector):
    domAxis = 0
    if abs(vector[0]) > abs(vector[1]) and abs(vector[0]) > abs(vector[2]):
        domAxis = 0
    if abs(vector[1]) > abs(vector[0]) and abs(vector[1]) > abs(vector[2]):
        domAxis = 1
    if abs(vector[2]) > abs(vector[0]) and abs(vector[2]) > abs(vector[1]):
        domAxis = 2
    
    return domAxis

# ------------------------------------------
# Get polygon area and paint area
# LEGACY
# ------------------------------------------
def get_area_and_paint(myvertices, myobj, obverts, region, rv3d):
    mymesh = myobj.data
    totarea = 0
    if len(myvertices) > 3:
        # Tessellate the polygon
        if myobj.mode != 'EDIT':
            tris = mesh_utils.ngon_tessellate(mymesh, myvertices)
        else:
            bm = bmesh.from_edit_mesh(myobj.data)
            myv = []
            for v in bm.verts:
                myv.extend([v.co])
            tris = mesh_utils.ngon_tessellate(myv, myvertices)

        for t in tris:
            v1, v2, v3 = t
            p1 = get_point(obverts[myvertices[v1]], myobj,mat)
            p2 = get_point(obverts[myvertices[v2]], myobj,mat)
            p3 = get_point(obverts[myvertices[v3]], myobj,mat)

            screen_point_p1 = get_2d_point(region, rv3d, p1)
            screen_point_p2 = get_2d_point(region, rv3d, p2)
            screen_point_p3 = get_2d_point(region, rv3d, p3)
            draw_triangle(screen_point_p1, screen_point_p2, screen_point_p3)

            # Area
            area = get_triangle_area(p1, p2, p3)

            totarea += area
    elif len(myvertices) == 3:
        v1, v2, v3 = myvertices
        p1 = get_point(obverts[v1], myobj,mat)
        p2 = get_point(obverts[v2], myobj,mat)
        p3 = get_point(obverts[v3], myobj,mat)

        screen_point_p1 = get_2d_point(region, rv3d, p1)
        screen_point_p2 = get_2d_point(region, rv3d, p2)
        screen_point_p3 = get_2d_point(region, rv3d, p3)
        draw_triangle(screen_point_p1, screen_point_p2, screen_point_p3)

        # Area
        area = get_triangle_area(p1, p2, p3)
        totarea += area
    else:
        return 0.0

    return totarea


# ------------------------------------------
# Get area using Heron formula
# LEGACY
# ------------------------------------------
def get_triangle_area(p1, p2, p3):
    d1, dn = distance(p1, p2)
    d2, dn = distance(p2, p3)
    d3, dn = distance(p1, p3)
    per = (d1 + d2 + d3) / 2.0
    area = sqrt(per * (per - d1) * (per - d2) * (per - d3))
    return area


# ------------------------------------------
# Get point in 2d space
# LEGACY
# ------------------------------------------
def get_2d_point(region, rv3d, point3d):
    if rv3d is not None and region is not None:
        return view3d_utils.location_3d_to_region_2d(region, rv3d, point3d)
    else:
        return get_render_location(point3d)



# -------------------------------------------------------------
# Draw a GPU line
# LEGACY
# -------------------------------------------------------------
def draw_line(v1, v2):
    # noinspection PyBroadException
    if v1 is not None and v2 is not None:
        bgl.glEnable(bgl.GL_MULTISAMPLE)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glEnable(bgl.GL_BLEND)




        coords = [v1,v2]
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": coords})
        #rgb = bpy.context.scene.measureit_arch_default_color
        batch.program_set(shader)
        batch.draw()
        
        #bgl.glBegin(bgl.GL_LINES)
        #bgl.glVertex2f(*v1)
        #bgl.glVertex2f(*v2)
        #bgl.glEnd()
    


# -------------------------------------------------------------
# Draw an OpenGL Rectangle
# LEGACY
# v1, v2 are corners (bottom left / top right)
# -------------------------------------------------------------
def draw_rectangle(v1, v2):
    # noinspection PyBroadException
    try:
        if v1 is not None and v2 is not None:
            v1b = (v2[0], v1[1])
            v2b = (v1[0], v2[1])
            draw_line(v1, v1b)
            draw_line(v1b, v2)
            draw_line(v2, v2b)
            draw_line(v2b, v1)
    except:
        pass


# -------------------------------------------------------------
# format a point as (x, y, z) for display
#
# -------------------------------------------------------------
def format_point(mypoint, pr):
    pf = "%1." + str(pr) + "f"
    fmt = " ("
    fmt += pf % mypoint[0]
    fmt += ", "
    fmt += pf % mypoint[1]
    fmt += ", "
    fmt += pf % mypoint[2]
    fmt += ")"

    return fmt


# --------------------------------------------------------------------
# Distance between 2 points in 3D space
# v1: first point
# v2: second point
# locx/y/z: Use this axis
# return: distance
# --------------------------------------------------------------------
def distance(v1, v2, locx=True, locy=True, locz=True):
    x = sqrt((v2[0] - v1[0]) ** 2 + (v2[1] - v1[1]) ** 2 + (v2[2] - v1[2]) ** 2)

    # If axis is not used, make equal both (no distance)
    v1b = [v1[0], v1[1], v1[2]]
    v2b = [v2[0], v2[1], v2[2]]
    if locx is False:
        v2b[0] = v1b[0]
    if locy is False:
        v2b[1] = v1b[1]
    if locz is False:
        v2b[2] = v1b[2]

    xloc = sqrt((v2b[0] - v1b[0]) ** 2 + (v2b[1] - v1b[1]) ** 2 + (v2b[2] - v1b[2]) ** 2)

    return x, xloc


# --------------------------------------------------------------------
# Interpolate 2 points in 3D space
# v1: first point
# v2: second point
# d1: distance
# return: interpolate point
# --------------------------------------------------------------------
def interpolate3d(v1, v2, d1):
    # calculate vector
    v = (v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2])
    # calculate distance between points
    d0, dloc = distance(v1, v2)

    # calculate interpolate factor (distance from origin / distance total)
    # if d1 > d0, the point is projected in 3D space
    if d0 > 0:
        x = d1 / d0
    else:
        x = d1

    final = (v1[0] + (v[0] * x), v1[1] + (v[1] * x), v1[2] + (v[2] * x))
    return final


# --------------------------------------------------------------------
# Get point rotated and relative to parent
# v1: point
# mainobject
# --------------------------------------------------------------------
def get_point(v1, mainobject, mat):
    # Using World Matrix
    vt = Vector((v1[0], v1[1], v1[2], 1))
    m4 = mat
    vt2 = m4 @ vt
    v2 = [vt2[0], vt2[1], vt2[2]]

    return v2


# --------------------------------------------------------------------
# Get location in world space
# v1: point
# mainobject
# --------------------------------------------------------------------
def get_location(mainobject):
    # Using World Matrix
    m4 = mainobject.matrix_world

    return [m4[0][3], m4[1][3], m4[2][3]]




# --------------------------------------------------------------------
# Get position for scale text
#
# --------------------------------------------------------------------
def get_scale_txt_location(context):
    scene = context.scene
    pos_x = int(context.region.width * scene.measureit_arch_scale_pos_x / 100)
    pos_y = int(context.region.height * scene.measureit_arch_scale_pos_y / 100)

    return pos_x, pos_y


# --------------------------------------------------------------------
# Get position in final render image
# (Z < 0 out of camera)
# return 2d position
# --------------------------------------------------------------------
def get_render_location(mypoint):

    v1 = Vector(mypoint)
    scene = bpy.context.scene
    co_2d = object_utils.world_to_camera_view(scene, scene.camera, v1)
    # Get pixel coords
    render_scale = scene.render.resolution_percentage / 100
    render_size = (int(scene.render.resolution_x * render_scale),
                   int(scene.render.resolution_y * render_scale))

    return [round(co_2d.x * render_size[0]), round(co_2d.y * render_size[1])]


# ---------------------------------------------------------
# Get center of circle base on 3 points
#
# Point a: (x,y,z) arc start
# Point b: (x,y,z) center
# Point c: (x,y,z) midle point in the arc
# Point d: (x,y,z) arc end
# Return:
# ang: angle (radians)
# len: len of arc
#
# ---------------------------------------------------------
def get_arc_data(pointa, pointb, pointc, pointd):
    v1 = Vector((pointa[0] - pointb[0], pointa[1] - pointb[1], pointa[2] - pointb[2]))
    v2 = Vector((pointc[0] - pointb[0], pointc[1] - pointb[1], pointc[2] - pointb[2]))
    v3 = Vector((pointd[0] - pointb[0], pointd[1] - pointb[1], pointd[2] - pointb[2]))

    angle = v1.angle(v2) + v2.angle(v3)

    rclength = pi * 2 * v2.length * (angle / (pi * 2))

    return angle, rclength


# -------------------------------------------------------------
# Format a number to the right unit
#
# -------------------------------------------------------------
def format_distance(fmt, value, factor=1):
    s_code = "\u00b2"  # Superscript two THIS IS LEGACY (but being kept for when Area Measurements are re-implimented)
    hide_units = bpy.context.scene.measureit_arch_hide_units # Also Legacy, Could be re-implimented... Requested now, should re-impliment

    # Get Scene Unit Settings
    scaleFactor = bpy.context.scene.unit_settings.scale_length
    unit_system = bpy.context.scene.unit_settings.system
    unit_length = bpy.context.scene.unit_settings.length_unit
    seperate_units = bpy.context.scene.unit_settings.use_separate

    toInches = 39.3700787401574887
    value *= scaleFactor

    # Imperial Formating
    if unit_system == "IMPERIAL":
        base = int(bpy.context.scene.measureit_arch_imperial_precision)
        decInches = value * toInches

        if hide_units is False:
            fmt += "\""
        
        # Seperate ft and inches
        # Unless Inches are the specified Length Unit
        if unit_length != 'INCHES':
            feet = floor(decInches/12)
            decInches -= feet*12
        else:
            feet = 0
        
        #Seperate Fractional Inches
        inches = floor(decInches)
        if inches != 0:
            frac = round(base*(decInches-inches))
        else:
            frac = round(base*(decInches))
        
        #Set proper numerator and denominator
        if frac != base:
            numcycles = int(math.log2(base))
            for i in range(numcycles):
                if frac%2 == 0:
                    frac = int(frac/2)
                    base = int(base/2)
                else:
                    break
        else:
            frac = 0
            inches += 1

        # Check values and compose string
        if feet != 0:
            feetString = str(feet) + "' "
        else: feetString = ""

        if inches !=0:
            inchesString = str(inches)
            if frac != 0: inchesString += "-"
            else: inchesString += "\""
        else: inchesString = ""

        if frac != 0:
            fracString = str(frac) + "/" + str(base) +"\""
        else: fracString = ""

        tx_dist = feetString + inchesString + fracString
    

    # METRIC FORMATING
    elif unit_system == "METRIC":

        # Meters
        if unit_length == 'METERS':
            if hide_units is False:
                fmt += " m"
                tx_dist = fmt % value
        # Centimeters
        elif unit_length == 'CENTIMETERS':
            if hide_units is False:
                fmt += " cm"
                d_cm = value * (100)
                tx_dist = fmt % d_cm
        #Millimeters
        elif unit_length == 'MILLIMETERS':
            if hide_units is False:
                fmt += " mm"
                d_mm = value * (1000)
                tx_dist = fmt % d_mm

        # Otherwise Use Adaptive Units
        else:
            if round(value, 2) >= 1.0:
                if hide_units is False:
                    fmt += " m"
                tx_dist = fmt % value
            else:
                if round(value, 2) >= 0.01:
                    if hide_units is False:
                        fmt += " cm"
                    d_cm = value * (100)
                    tx_dist = fmt % d_cm
                else:
                    if hide_units is False:
                        fmt += " mm"
                    d_mm = value * (1000)
                    tx_dist = fmt % d_mm
    else:
        tx_dist = fmt % value
    return tx_dist


# -------------------------------------------------------------
# Get radian float based on angle choice
#
# -------------------------------------------------------------
def get_angle_in_rad(fangle):
    if fangle == 0:
        return 0.0
    else:
        return radians(fangle)

def draw_text(myobj, pos2d, display_text, rgb, fsize, align='L', text_rot=0.0):
    if pos2d is None:
        return

    # dpi = bpy.context.user_preferences.system.dpi
    gap = 12
    x_pos, y_pos = pos2d
    font_id = 0
    blf.size(font_id, fsize, 72)
    # blf.size(font_id, fsize, dpi)
    # height of one line
    mwidth, mheight = blf.dimensions(font_id, "Tp")  # uses high/low letters

    # Calculate sum groups
    m = 0
    while "<#" in display_text:
        m += 1
        if m > 10:   # limit loop
            break
        i = display_text.index("<#")
        tag = display_text[i:i + 4]
        #display_text = display_text.replace(tag, get_group_sum(myobj, tag.upper()))

    # split lines
    mylines = display_text.split("|")
    idx = len(mylines) - 1
    maxwidth = 0
    maxheight = len(mylines) * mheight
    # -------------------
    # Draw all lines
    # -------------------
    for line in mylines:
        text_width, text_height = blf.dimensions(font_id, line)
        if align is 'C':
            newx = x_pos - text_width / 2
        elif align is 'R':
            newx = x_pos - text_width - gap
        else:
            newx = x_pos
            blf.enable(font_id, ROTATION)
            blf.rotation(font_id, text_rot)
        # calculate new Y position
        new_y = y_pos + (mheight * idx)
        # Draw
        blf.position(font_id, newx, new_y, 0)
        blf.color(0,rgb[0], rgb[1], rgb[2], rgb[3])
        blf.draw(font_id, " " + line)
        # sub line
        idx -= 1
        # saves max width
        if maxwidth < text_width:
            maxwidth = text_width

    if align is 'L':
        blf.disable(font_id, ROTATION)

    return maxwidth, maxheight


# --------------------------------------------------------------------
# Get vertex data
# mainobject
# --------------------------------------------------------------------
def get_mesh_vertices(myobj):
    sceneProps = bpy.context.scene.MeasureItArchProps
    try:
        obverts = []
        verts=[]
        if myobj.type == 'MESH':
            if myobj.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(myobj.data)
                verts = bm.verts
            else:
                eval_res = sceneProps.eval_mods
                if eval_res or check_mods(myobj):
                    deps = bpy.context.view_layer.depsgraph
                    obj_eval = myobj.evaluated_get(deps)
                    mesh = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=deps)
                    verts = mesh.vertices
                else:
                    verts = myobj.data.vertices

            # We're going through every Vertex in the object here
            # probably excessive, should figure out a better way to
            # link dims to verts...

            obverts = [vert.co for vert in verts]
            
            return obverts
        else: return None 
    except AttributeError:
        return None


## A streamlined version of get mesh vertex for line drawing
def get_line_vertex(idx,verts,mat):
    vert = verts[idx].co
    return vert


def get_mesh_vertex(myobj,idx,evalMods):
    sceneProps = bpy.context.scene.MeasureItArchProps
    try:
        verts=[]
        if myobj.type == 'MESH':
            if myobj.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(myobj.data)
                verts = bm.verts
            else:     
                eval_res = sceneProps.eval_mods
                if (eval_res or evalMods) and check_mods(myobj):
                    deps = bpy.context.view_layer.depsgraph
                    obj_eval = myobj.evaluated_get(deps)
                    mesh = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=deps)
                    verts = mesh.vertices          
                else:
                    verts = myobj.data.vertices
            if idx < len(verts):
                return verts[idx].co
            else: return None
        else: return None 
    except AttributeError:
        return None

def check_mods(myobj):
    goodMods = ["DATA_TRANSFER ", "NORMAL_EDIT", "WEIGHTED_NORMAL",
                'UV_PROJECT', 'UV_WARP', 'ARRAY', 
                'EDGE_SPLIT', 'MASK', 'MIRROR', 'MULTIRES', 'SCREW',
                'SOLIDIFY', 'SUBSURF', 'TRIANGULATE', 'ARMATURE', 
                'CAST', 'CURVE', 'DISPLACE', 'HOOK', 'LAPLACIANDEFORM',
                'LATTICE', 'MESH_DEFORM', 'SHRINKWRAP', 'SIMPLE_DEFORM',
                'SMOOTH', 'CORRECTIVE_SMOOTH', 'LAPLACIANSMOOTH',
                'SURFACE_DEFORM', 'WARP', 'WAVE', 'CLOTH', 'COLLISION', 
                'DYNAMIC_PAINT', 'PARTICLE_INSTANCE', 'PARTICLE_SYSTEM',
                'SMOKE', 'SOFT_BODY', 'SURFACE','SOLIDIFY']
    if myobj.modifiers == None:
        return False
    for mod in myobj.modifiers:
        if mod.type not in goodMods:
            return False
    return True

def printTime(start,end,post):
    totalTime= (end-start)*1000
    mystring = '{:.2f}'.format(totalTime) +' ms'
    mystring += post
    print(mystring)