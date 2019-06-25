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

#define Shaders
shader = gpu.types.GPUShader(
    Base_Shader_2D.vertex_shader,
    Base_Shader_2D.fragment_shader)

lineShader = gpu.types.GPUShader(
    Base_Shader_3D.vertex_shader,
    Base_Shader_3D.fragment_shader,
    geocode=Base_Shader_3D.geometry_shader)

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

textShader = gpu.types.GPUShader(
    Text_Shader.vertex_shader,
    Text_Shader.fragment_shader)

dimensionShader = gpu.types.GPUShader(
    Base_Shader_3D.vertex_shader,
    Base_Shader_3D.fragment_shader,
    geocode=Base_Shader_3D.geometry_shader)

fontSizeMult = 6
# -------------------------------------------------------------
# Draw segments
#
# rgb: Color
# fsize: Font size
# -------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyUnboundLocalVariable


def update_text(textobj,props,context):
    if textobj.text_updated is True or props.text_updated is True:
        #Get textitem Properties
        rawRGB = props.color
        rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])
        size = 20
        resolution = props.textResolution

        #Get Font Id
        badfonts=[None]
        if 'Bfont' in bpy.data.fonts:
            badfonts.append(bpy.data.fonts['Bfont'])
        if props.font not in badfonts:
            vecFont = props.font
            fontPath = vecFont.filepath
            font_id= blf.load(fontPath)
        else:
            font_id=0

        # Get Text
        if 'annotationTextSource' in textobj:
            if textobj.annotationTextSource is not '':
                text = str(context.object[textobj.annotationTextSource])
        else:
            text = textobj.text

        # Set BLF font Properties
        blf.color(font_id,rgb[0],rgb[1],rgb[2],rgb[3])
        blf.size(font_id,size,resolution)
        
        #Calculate Optimal Dimensions for Text Texture.
        fheight = blf.dimensions(font_id,'fp')[1]
        fwidth = blf.dimensions(font_id,text)[0]
        width = math.ceil(fwidth)
        height = math.ceil(fheight+4)
        blf.position(font_id,0,height/4,0)

        #Save Texture size to textobj Properties
        textobj.textHeight = height
        textobj.textWidth = width

        # Start Offscreen Draw
        if width != 0 and height != 0:
            textOffscreen = gpu.types.GPUOffScreen(width,height)
            texture_buffer = bgl.Buffer(bgl.GL_BYTE, width * height * 4)
            
            with textOffscreen.bind():
                # Clear Past Draw and Set 2D View matrix
                bgl.glClear(bgl.GL_COLOR_BUFFER_BIT)
                
                view_matrix = Matrix([
                [2 / width, 0, 0, -1],
                [0, 2 / height, 0, -1],
                [0, 0, 1, 0],
                [0, 0, 0, 1]])
                
                gpu.matrix.reset()
                gpu.matrix.load_matrix(view_matrix)
                gpu.matrix.load_projection_matrix(Matrix.Identity(4))

                blf.draw(font_id,text)
                
                # Read Offscreen To Texture Buffer
                bgl.glReadBuffer(bgl.GL_BACK)
                bgl.glReadPixels(0, 0, width, height, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, texture_buffer)
                
                # Write Texture Buffer to ID Property as List
                textobj['texture'] = texture_buffer.to_list()
                textOffscreen.free()
                textobj.text_updated = False
                textobj.texture_updated = True
            

        #generate image datablock from buffer for debug preview
        #ONLY USE FOR DEBUG. SERIOUSLY SLOWS PREFORMANCE
        if context.scene.measureit_arch_debug_text:
            if not str('test') in bpy.data.images:
                bpy.data.images.new(str('test'), width, height)
            image = bpy.data.images[str('test')]
            image.scale(width, height)
            image.pixels = [v / 255 for v in texture_buffer]

def draw_alignedDimension(context, myobj, measureGen,dim,mat):
    # GL Settings
    bgl.glEnable(bgl.GL_MULTISAMPLE)
    bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glEnable(bgl.GL_DEPTH_TEST)
    bgl.glDepthFunc(bgl.GL_LEQUAL)
    bgl.glDepthMask(False)

    dimProps = dim
    lineWeight = dimProps.lineWeight

  
    if dim.uses_style:
        for alignedDimStyle in context.scene.StyleGenerator[0].alignedDimensions:
            if alignedDimStyle.name == dim.style:
                dimProps = alignedDimStyle

    #check all visibility conditions
    if dim.dimVisibleInView is None or dim.dimVisibleInView.name == context.scene.camera.data.name:
        inView = True        
    else:
        inView = False    
    if dim.visible and dimProps.visible and inView:

        if context.scene.measureit_arch_is_render_draw:
            viewport = [context.scene.render.resolution_x,context.scene.render.resolution_y]
        else:
            viewport = [context.area.width,context.area.height]

        # Obj Properties
        obvertA = get_mesh_vertices(dim.dimObjectA)
        obvertB = get_mesh_vertices(dim.dimObjectB)
        scene = context.scene
        pr = scene.measureit_arch_gl_precision
        textFormat = "%1." + str(pr) + "f"
        scale = bpy.context.scene.unit_settings.scale_length
        units = scene.measureit_arch_units
        rawRGB = dimProps.color
        rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])
        
        capA = dimProps.endcapA
        capB = dimProps.endcapB
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
            p1 = get_point(obvertA[dim.dimPointA], dim.dimObjectA,aMatrix)
        
        if dim.dimPointB == 9999999:
            p2 = dim.dimObjectB.location
        else:
            p2 = get_point(obvertB[dim.dimPointB], dim.dimObjectB,bMatrix)
        
        

        #check dominant Axis
        sortedPoints = sortPoints(p1,p2)
        p1 = sortedPoints[0]
        p2 = sortedPoints[1]
    
        
        #calculate distance & MidpointGY
        distVector = Vector(p1)-Vector(p2)
        dim.gizRotAxis = distVector
        dist = distVector.length
        midpoint = interpolate3d(p1, p2, fabs(dist / 2))
        normDistVector = distVector.normalized()
        absNormDisVector = Vector((abs(normDistVector[0]),abs(normDistVector[1]),abs(normDistVector[2])))
        dim.gizLoc = midpoint

        # Compute offset vector from face normal and user input
        rotationMatrix = Matrix.Rotation(dim.dimRotation,4,normDistVector)
        selectedNormal = Vector(select_normal(myobj,dim,normDistVector,midpoint,dimProps))
        if dim.dimFlip is True:
            selectedNormal.negate()
        
        userOffsetVector = rotationMatrix@selectedNormal
        offsetDistance = userOffsetVector*offset
        geoOffsetDistance = userOffsetVector*geoOffset
        
        # Define Lines
        leadStartA = Vector(p1) + geoOffsetDistance
        leadEndA = Vector(p1) + offsetDistance
        leadStartB = Vector(p2) + geoOffsetDistance
        leadEndB = Vector(p2)+offsetDistance
        dimLineStart = Vector(p1)+(offsetDistance-(userOffsetVector*0.05))
        dimLineEnd = Vector(p2)+(offsetDistance-(userOffsetVector*0.05))
        textLoc = interpolate3d(dimLineStart, dimLineEnd, fabs(dist / 2))

        #i,j,k as card axis
        i = Vector((1,0,0))
        j = Vector((0,1,0))
        k = Vector((0,0,1))


        #format text and update if necessary
        distanceText = str(format_distance(textFormat,units,dist))
        if dim.text != str(distanceText):
            dim.text = str(distanceText)
            dim.text_updated = True
        
        width = dim.textWidth
        height = dim.textHeight 
        

        resolution = dimProps.textResolution
        size = dimProps.fontSize/fontSizeMult
        sx = (width/resolution)*0.1*size
        sy = (height/resolution)*0.1*size
        origin = Vector(textLoc)
        cardX = normDistVector.normalized() * sx
        cardY = userOffsetVector.normalized() *sy
        
        square = [(origin-(cardX/2)),(origin-(cardX/2)+cardY),(origin+(cardX/2)+cardY),(origin+(cardX/2))]

        if scene.measureit_arch_gl_show_d:
            draw_text_3D(context,dim,myobj,square)


      
        #Collect coords and endcaps
        coords = [leadStartA,leadEndA,leadStartB,leadEndB,dimLineStart,dimLineEnd]
        ACoords = generate_end_caps(context,dim,capA,capSize,dimLineStart,userOffsetVector,textLoc)
        BCoords = generate_end_caps(context,dim,capB,capSize,dimLineEnd,userOffsetVector,textLoc)
        filledCoords = []
        if capA == 'L' or capA == 'D':
            for coord in ACoords:
                coords.append(coord)
        if capB == 'L' or capB == 'D' :
            for coord in BCoords:
                coords.append(coord)
        
        if capA == 'T':
            for coord in ACoords:
                filledCoords.append(coord)
        if capB == 'T':
            for coord in BCoords:
                filledCoords.append(coord)

        if capA == 'D':
                  # Define Square
            pos = dimLineStart
            x = distVector.normalized() * dimProps.endcapSize/20
            y = userOffsetVector.normalized() * dimProps.endcapSize/20
            a = 0.055
            b = 0.085
            s1 = (pos + (a*x) + (b*y))
            s2 = (pos + (b*x) + (a*y))
            s3 = (pos + (-a*x) + (-b*y))
            s4 = (pos + (-b*x) + (-a*y))
            filledCoords.append(s1)
            filledCoords.append(s2)
            filledCoords.append(s3)
            filledCoords.append(s1)
            filledCoords.append(s3)
            filledCoords.append(s4) 

        if capB == 'D':
                  # Define Square
            pos = dimLineEnd
            x = distVector.normalized() * dimProps.endcapSize/20
            y = userOffsetVector.normalized() * dimProps.endcapSize/20
            a = 0.055
            b = 0.085
            s1 = (pos + (a*x) + (b*y))
            s2 = (pos + (b*x) + (a*y))
            s3 = (pos + (-a*x) + (-b*y))
            s4 = (pos + (-b*x) + (-a*y))
            filledCoords.append(s1)
            filledCoords.append(s2)
            filledCoords.append(s3)
            filledCoords.append(s1)
            filledCoords.append(s3)
            filledCoords.append(s4) 

        if capB == 'T' or capA == 'T' or capA == 'D' or capB == 'D':
            #bind shader
            triShader.bind()
            triShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
            triShader.uniform_float("offset", (0,0,0))

            batch = batch_for_shader(triShader, 'TRIS', {"pos": filledCoords})
            batch.program_set(triShader)
            batch.draw()
            gpu.shader.unbind()

        
        #bind shader
        dimensionShader.bind()
        dimensionShader.uniform_float("Viewport",viewport)
        dimensionShader.uniform_float("thickness",lineWeight)
        dimensionShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
        dimensionShader.uniform_float("offset", (0,0,0))

        # batch & Draw Shader   
        batch = batch_for_shader(dimensionShader, 'LINES', {"pos": coords})
        batch.program_set(dimensionShader)
        batch.draw()
        gpu.shader.unbind()

        #Reset openGL Settings
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        bgl.glDisable(bgl.GL_POLYGON_SMOOTH)
        bgl.glDepthMask(True)

def draw_axisDimension(context, myobj, measureGen,dim, mat):
    # GL Settings
    bgl.glEnable(bgl.GL_MULTISAMPLE)
    bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glEnable(bgl.GL_DEPTH_TEST)
    bgl.glDepthFunc(bgl.GL_LEQUAL)
    bgl.glDepthMask(False)
    dimProps = dim
    lineWeight = dimProps.lineWeight

  
    if dim.uses_style:
        for alignedDimStyle in context.scene.StyleGenerator[0].alignedDimensions:
            if alignedDimStyle.name == dim.style:
                dimProps = alignedDimStyle

    #check all visibility conditions
    if dimProps.dimVisibleInView is None or dimProps.dimVisibleInView.name == context.scene.camera.data.name:
        inView = True        
    else:
        inView = False    
    if dim.visible and dimProps.visible and inView:

        if context.scene.measureit_arch_is_render_draw:
            viewport = [context.scene.render.resolution_x,context.scene.render.resolution_y]
            cameraLoc = context.scene.camera.location.normalized()
        else:
            viewport = [context.area.width,context.area.height]
            viewRot = context.area.spaces[0].region_3d.view_rotation
            #cameraLoc = context.scene.camera.location.normalized()
            #print(cameraLoc)

        # Obj Properties
        obvertA = get_mesh_vertices(dim.dimObjectA)
        obvertB = get_mesh_vertices(dim.dimObjectB)
        scene = context.scene
        pr = scene.measureit_arch_gl_precision
        textFormat = "%1." + str(pr) + "f"
        scale = bpy.context.scene.unit_settings.scale_length
        units = scene.measureit_arch_units
        rawRGB = dimProps.color
        rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])
        
        axis = dim.dimAxis

        capA = dimProps.endcapA
        capB = dimProps.endcapB
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
            p1 = get_point(obvertA[dim.dimPointA], dim.dimObjectA,aMatrix)
        
        if dim.dimPointB == 9999999:
            p2 = dim.dimObjectB.location
        else:
            p2 = get_point(obvertB[dim.dimPointB], dim.dimObjectB,bMatrix)
        
        #Sort Points 
        sortedPoints = sortPoints(p1,p2)
        p1 = sortedPoints[0]
        p2 = sortedPoints[1]

        
        #i,j,k as card axis
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
            if context.scene.measureit_arch_is_render_draw:
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
        dim.gizLoc = midpoint

        # Compute offset vector from face normal and user input
        rotationMatrix = Matrix.Rotation(dim.dimRotation,4,normDistVector)
        selectedNormal = Vector(select_normal(myobj,dim,normDistVector,midpoint,dimProps))

        #The Direction of the Dimension Lines
        dirVector = Vector(viewSector).cross(axisVec)
        if dirVector.dot(selectedNormal) < 0:
            dirVector.negate()
        selectedNormal = dirVector.normalized()

        if dim.dimFlip is True:
            selectedNormal.negate()

        userOffsetVector = rotationMatrix@selectedNormal
        offsetDistance = userOffsetVector*offset
        geoOffsetDistance = userOffsetVector*geoOffset
        
        # Define Lines
        
        # get the components of p1 & p1 in the direction vector
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

        leadStartA = Vector(basePoint) + geoOffsetDistance
        leadEndA = Vector(basePoint)  + offsetDistance
        leadEndB =  leadEndA - Vector(secondPointAxis)
        leadStartB = Vector(secondPoint) - viewAxisDiff + geoOffsetDistance
        viewDiffStartB = leadStartB
        viewDiffEndB = leadStartB + viewAxisDiff
        dimLineStart = leadEndA -(userOffsetVector*0.05)
        dimLineEnd = leadEndB-(userOffsetVector*0.05)
        textLoc = interpolate3d(dimLineStart, dimLineEnd, fabs(dist / 2))

        #format text and update if necessary
        distanceText = str(format_distance(textFormat,units,dist))
        if dim.text != str(distanceText):
            dim.text = str(distanceText)
            dim.text_updated = True
        
        width = dim.textWidth
        height = dim.textHeight 
        resolution = dimProps.textResolution
        size = dimProps.fontSize/fontSizeMult
        sx = (width/resolution)*0.1*size
        sy = (height/resolution)*0.1*size
        origin = Vector(textLoc)
        cardX = Vector((abs(normDistVector[0]),-abs(normDistVector[1]),-abs(normDistVector[2]))) * sx
        cardY = userOffsetVector *sy
        square = [(origin-(cardX/2)),(origin-(cardX/2)+cardY ),(origin+(cardX/2)+cardY ),(origin+(cardX/2))]

        if scene.measureit_arch_gl_show_d:
            draw_text_3D(context,dim,myobj,square)


      
        #Collect coords and endcaps
        coords = [leadStartA,leadEndA,leadStartB,leadEndB,dimLineStart,dimLineEnd,viewDiffStartB,viewDiffEndB]
        ACoords = generate_end_caps(context,dim,capA,capSize,dimLineStart,userOffsetVector,textLoc)
        BCoords = generate_end_caps(context,dim,capB,capSize,dimLineEnd,userOffsetVector,textLoc)
        filledCoords = []
        if capA == 'L' or capA == 'D':
            for coord in ACoords:
                coords.append(coord)
        if capB == 'L' or capB == 'D' :
            for coord in BCoords:
                coords.append(coord)
        
        if capA == 'T':
            for coord in ACoords:
                filledCoords.append(coord)
        if capB == 'T':
            for coord in BCoords:
                filledCoords.append(coord)

        if capA == 'D':
                  # Define Square
            pos = dimLineStart
            x = distVector.normalized() * dimProps.endcapSize/20
            y = userOffsetVector.normalized() * dimProps.endcapSize/20
            a = 0.055
            b = 0.085
            s1 = (pos + (a*x) + (b*y))
            s2 = (pos + (b*x) + (a*y))
            s3 = (pos + (-a*x) + (-b*y))
            s4 = (pos + (-b*x) + (-a*y))
            filledCoords.append(s1)
            filledCoords.append(s2)
            filledCoords.append(s3)
            filledCoords.append(s1)
            filledCoords.append(s3)
            filledCoords.append(s4) 

        if capB == 'D':
                  # Define Square
            pos = dimLineEnd
            x = distVector.normalized() * dimProps.endcapSize/20
            y = userOffsetVector.normalized() * dimProps.endcapSize/20
            a = 0.055
            b = 0.085
            s1 = (pos + (a*x) + (b*y))
            s2 = (pos + (b*x) + (a*y))
            s3 = (pos + (-a*x) + (-b*y))
            s4 = (pos + (-b*x) + (-a*y))
            filledCoords.append(s1)
            filledCoords.append(s2)
            filledCoords.append(s3)
            filledCoords.append(s1)
            filledCoords.append(s3)
            filledCoords.append(s4) 

        if capB == 'T' or capA == 'T' or capA == 'D' or capB == 'D':
            #bind shader
            triShader.bind()
            triShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
            triShader.uniform_float("offset", (0,0,0))

            batch = batch_for_shader(triShader, 'TRIS', {"pos": filledCoords})
            batch.program_set(triShader)
            batch.draw()
            gpu.shader.unbind()

        
        #bind shader
        dimensionShader.bind()
        dimensionShader.uniform_float("Viewport",viewport)
        dimensionShader.uniform_float("thickness",lineWeight)
        dimensionShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
        dimensionShader.uniform_float("offset", (0,0,0))

        # batch & Draw Shader   
        batch = batch_for_shader(dimensionShader, 'LINES', {"pos": coords})
        batch.program_set(dimensionShader)
        batch.draw()
        gpu.shader.unbind()

        #Reset openGL Settings
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        bgl.glDisable(bgl.GL_POLYGON_SMOOTH)
        bgl.glDepthMask(True)

def draw_angleDimension(context, myobj, DimGen, dim,mat):
    dimProps = dim
    if dim.uses_style:
        for alignedDimStyle in context.scene.StyleGenerator[0].alignedDimensions:
            if alignedDimStyle.name == dim.style:
                dimProps = alignedDimStyle

    # Check Visibility Conditions
    inView = False
    if dim.dimVisibleInView is None or dim.dimVisibleInView.name == context.scene.camera.data.name:
        inView = True
    
    if inView and dim.visible and dimProps.visible:
         # GL Settings
        bgl.glEnable(bgl.GL_MULTISAMPLE)
        bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        bgl.glDepthMask(False)

        lineWeight = dimProps.lineWeight
        if context.scene.measureit_arch_is_render_draw:
            viewport = [context.scene.render.resolution_x,context.scene.render.resolution_y]
        else:
            viewport = [context.area.width,context.area.height]


        scene = context.scene
        pr = scene.measureit_arch_gl_precision
        a_code = "\u00b0"  # degree
        fmt = "%1." + str(pr) + "f"
        obverts = get_mesh_vertices(myobj)
        rawRGB = dimProps.color
        rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])
        radius = dim.dimRadius
        offset = 0.001

        p1 = Vector(get_point(obverts[dim.dimPointA], myobj,mat))
        p2 = Vector(get_point(obverts[dim.dimPointB], myobj,mat))
        p3 = Vector(get_point(obverts[dim.dimPointC], myobj,mat))

        #calc normal to plane defined by points
        vecA = (p1-p2)
        vecA.normalize()
        vecB = (p3-p2)
        vecB.normalize()
        norm = vecA.cross(vecB)

        #endpoints
        endpointA = (vecA*radius)+p2
        endpointB = (vecB*radius)+p2

        #making it a circle
        distVector = vecA-vecB
        dist = distVector.length
        angle = vecA.angle(vecB)
        numCircleVerts = math.ceil(radius/.4)+ int((degrees(angle))/10)
        verts = []
        for idx in range (numCircleVerts+1):
            rotangle= (angle/(numCircleVerts+1))*idx
            point = Vector((vecA[0],vecA[1],vecA[2]))
            point.rotate(Quaternion(norm,rotangle))
            #point.normalize()
            verts.append(point)


        #get Midpoint for Text Placement
        midVec = Vector(interpolate3d(vecA, vecB, (dist/2)))
        midVec.normalize()
        midPoint = (midVec*radius) + p2
        
        #calculate angle
        angle = vecA.angle(vecB)
        if bpy.context.scene.unit_settings.system_rotation == "DEGREES":
            angle = degrees(angle)
        # format text
        angleText = " " + fmt % angle
        # Add degree symbol
        if bpy.context.scene.unit_settings.system_rotation == "DEGREES":
            angleText += a_code
        # Update if Necessary
        if dim.text != str(angleText):
            dim.text = str(angleText)
            dim.text_updated = True
        
        #make text card
        vecX = vecB-vecA
        width = dim.textWidth
        height = dim.textHeight 
        resolution = dimProps.textResolution
        size = dimProps.fontSize/fontSizeMult
        sx = (width/resolution)*0.1*size
        sy = (height/resolution)*0.2*size
        origin = Vector(midPoint)
        cardX = vecX * 0.25 * sx
        cardY = midVec * 0.25 *sy
        square = [(origin-cardX),(origin-cardX+cardY ),(origin+cardX+cardY ),(origin+cardX)]

        if scene.measureit_arch_gl_show_d:
            draw_text_3D(context,dim,myobj,square)



        #configure shaders
        pointShader.bind()
        pointShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
        pointShader.uniform_float("thickness", lineWeight)
        pointShader.uniform_float("offset", -offset)
        gpu.shader.unbind()

        dimensionShader.bind()
        dimensionShader.uniform_float("Viewport",viewport)
        dimensionShader.uniform_float("thickness",lineWeight)
        dimensionShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
        dimensionShader.uniform_float("offset", -offset)

        # Draw Point Pass for Clean Corners
        # I'm being lazy here, should do a proper lineadjacency
        # with miters and do this in one pass
        pointCoords = []
        pointCoords.append(endpointA)
        for vert in verts:
            pointCoords.append((vert*radius)+p2)
        pointCoords.append(endpointB)
        batch3d = batch_for_shader(pointShader, 'POINTS', {"pos":pointCoords})
        batch3d.program_set(pointShader)
        batch3d.draw()

        # batch & Draw Shader
        coords = []
        coords.append(endpointA)
        for vert in verts:
            coords.append((vert*radius)+p2)
            coords.append((vert*radius)+p2)
        coords.append(endpointB)
        batch = batch_for_shader(dimensionShader, 'LINES', {"pos": coords})
        batch.program_set(dimensionShader)
        batch.draw()
        gpu.shader.unbind()

        #Reset openGL Settings
        bgl.glDisable(bgl.GL_DEPTH_TEST)
        bgl.glDisable(bgl.GL_POLYGON_SMOOTH)
        bgl.glDepthMask(True)

def select_normal(myobj, dim, normDistVector, midpoint, dimProps):
    #Set properties
    i = Vector((1,0,0)) # X Unit Vector
    j = Vector((0,1,0)) # Y Unit Vector
    k = Vector((0,0,1)) # Z Unit Vector
    loc = Vector(get_location(myobj))
    centerRay = Vector((-1,1,1))

    if dim.dimViewPlane=='99':
        viewPlane = dimProps.dimViewPlane
    else:
        viewPlane = dim.dimViewPlane

    if myobj.type == 'MESH':
        if dim.dimPointA != 9999999:
            vertA = myobj.data.vertices[dim.dimPointA]
            directionRay = vertA.normal + loc 
        else:
            directionRay = Vector((0,0,0))
        #get Adjacent Face normals if possible
        possibleNormals = []
        for face in myobj.data.polygons:
            if dim.dimPointA in face.vertices and dim.dimPointB in face.vertices:
                worldNormal = myobj.matrix_local@Vector(face.normal)
                worldNormal -= myobj.location
                worldNormal.normalize()
                possibleNormals.append(worldNormal)
                
        bestNormal = directionRay
    
        #Face Normals Available Test Conditions
        if len(possibleNormals) > 1:  
            bestNormal = Vector((1,1,1))
            if viewPlane == 'XY':
                for norm in possibleNormals:
                    if abs(norm[2])< abs(bestNormal[2]):
                        bestNormal=norm

            elif viewPlane == 'YZ':
                for norm in possibleNormals:
                    if abs(norm[0])< abs(bestNormal[0]):
                        bestNormal=norm   

            elif viewPlane == 'XZ':
                for norm in possibleNormals:
                    if abs(norm[1])< abs(bestNormal[1]):
                        bestNormal=norm
            else:
                bestNormal = Vector((0,0,0))
                for norm in possibleNormals:
                    bestNormal += norm
            
        #Face Normals Not Available 
        else:
            if viewPlane == 'XY':
                bestNormal = k.cross(normDistVector)
            elif viewPlane == 'YZ':
                bestNormal = i.cross(normDistVector)
            elif viewPlane == 'XZ':
                bestNormal = j.cross(normDistVector)
            else:
                bestNormal = directionRay

            if bestNormal.dot(directionRay)<0:
                bestNormal.negate()
    
    #not mesh obj
    else:
        if viewPlane == 'XY':
            bestNormal = k.cross(normDistVector)
        elif viewPlane == 'YZ':
            bestNormal = i.cross(normDistVector)
        elif viewPlane == 'XZ':
            bestNormal = j.cross(normDistVector)
        else:
            bestNormal = centerRay

        if bestNormal.dot(centerRay)<0:
            bestNormal.negate()

    #Normalize Result
    bestNormal.normalize()
    return bestNormal 
        
def draw_line_group(context, myobj, lineGen, mat):
    scene = context.scene
    obverts = get_mesh_vertices(myobj)
    bgl.glEnable(bgl.GL_MULTISAMPLE)
    bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glEnable(bgl.GL_DEPTH_TEST)
    bgl.glDepthMask(False)
    
    if context.scene.measureit_arch_is_render_draw:
        viewport = [context.scene.render.resolution_x,context.scene.render.resolution_y]
    else:
        viewport = [context.area.width,context.area.height]

    for idx in range(0, lineGen.line_num):
        lineGroup = lineGen.line_groups[idx]
        lineProps= lineGroup
        if lineGroup.uses_style:
            for lineStyle in context.scene.StyleGenerator[0].line_groups:
                if lineStyle.name == lineGroup.style:
                    lineProps= lineStyle
            
        if lineGroup.visible and lineProps.visible:
            
            rawRGB = lineProps.color        
            alpha = 1.0   
            if bpy.context.mode == 'EDIT_MESH':
                alpha=0.3
            else:
                alpha = rawRGB[3]

            #undo blenders Default Gamma Correction
            rgb = [pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),alpha]

            #overide line color with theme selection colors when selected
            if not context.scene.measureit_arch_is_render_draw:
                if myobj in context.selected_objects and bpy.context.mode != 'EDIT_MESH' and context.scene.measureit_arch_gl_ghost:
                    rgb[0] = bpy.context.preferences.themes[0].view_3d.object_selected[0]
                    rgb[1] = bpy.context.preferences.themes[0].view_3d.object_selected[1]
                    rgb[2] = bpy.context.preferences.themes[0].view_3d.object_selected[2]
                    rgb[3] = alpha

                    if (context.view_layer.objects.active != None
                    and context.view_layer.objects.active.data != None
                    and myobj.data.name == context.view_layer.objects.active.data.name):
                        rgb[0] = bpy.context.preferences.themes[0].view_3d.object_active[0]
                        rgb[1] = bpy.context.preferences.themes[0].view_3d.object_active[1]
                        rgb[2] = bpy.context.preferences.themes[0].view_3d.object_active[2]
                        rgb[3] = alpha

            #set other line properties
            isOrtho = False
            if scene.measureit_arch_is_render_draw:
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
                offset = -10*offset
            offset /= 1000

            #gl Settings
            bgl.glDepthFunc(bgl.GL_LEQUAL) 

            #configure Shaders
            pointShader.bind()
            pointShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
            pointShader.uniform_float("Viewport",viewport)
            pointShader.uniform_float("thickness", lineWeight)
            pointShader.uniform_float("offset", -offset)
            gpu.shader.unbind()

            lineShader.bind()
            lineShader.uniform_float("Viewport",viewport)
            lineShader.uniform_float("thickness",lineWeight)
            lineShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
            lineShader.uniform_float("offset", -offset)
           
            
            #Get line data to be drawn
            coords =[]
            pointcoord =[]
            arclengths = []
            for x in range(0,lineGroup.numLines):
                sLine = lineGroup.singleLine[x]
                
                if sLine.pointA <= len(obverts) and sLine.pointB <= len(obverts):
                    a_p1 = get_point(obverts[sLine.pointA], myobj,mat)
                    b_p1 = get_point(obverts[sLine.pointB], myobj,mat)

                if  a_p1 is not None and b_p1 is not None:
                    coords.append(a_p1)
                    pointcoord.append(a_p1)
                    arclengths.append(0)
                    
                    coords.append(b_p1)
                    arclengths.append((Vector(a_p1)-Vector(b_p1)).length)
                    
            #Draw Point Pass for Clean Corners
            batch3d = batch_for_shader(pointShader, 'POINTS', {"pos": pointcoord})
            batch3d.program_set(pointShader)
            batch3d.draw()

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
                dashedLineShader.uniform_float("thickness",hiddenLineWeight)
                dashedLineShader.uniform_float("finalColor", (dashRGB[0], dashRGB[1], dashRGB[2], dashRGB[3]))
            
                batchHidden = batch_for_shader(dashedLineShader,'LINES',{"pos":coords,"arcLength":arclengths}) 
                batchHidden.program_set(dashedLineShader)
                batchHidden.draw()
                bgl.glDepthFunc(bgl.GL_LESS)
                gpu.shader.unbind()
            
            # Draw Lines
            batch3d = batch_for_shader(lineShader, 'LINES', {"pos": coords})
            batch3d.program_set(lineShader)
            batch3d.draw()
            gpu.shader.unbind()
            
    gpu.shader.unbind()
    bgl.glDisable(bgl.GL_DEPTH_TEST)
    bgl.glDisable(bgl.GL_POLYGON_SMOOTH)
    bgl.glDepthMask(True)

def draw_annotation(context, myobj, annotationGen, mat):
    obverts = get_mesh_vertices(myobj)
    scene = context.scene
    bgl.glEnable(bgl.GL_MULTISAMPLE)
    bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glEnable(bgl.GL_DEPTH_TEST)
    bgl.glDepthMask(False)

    if context.scene.measureit_arch_is_render_draw:
        viewport = [context.scene.render.resolution_x,context.scene.render.resolution_y]
    else:
        viewport = [context.area.width,context.area.height]
    

    for idx in range(0, annotationGen.num_annotations):
        annotation = annotationGen.annotations[idx]
        annotationProps = annotation
        
        if annotation.uses_style:
            for annotationStyle in context.scene.StyleGenerator[0].annotations:
                if annotationStyle.name == annotation.style:
                    annotationProps= annotationStyle

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
            lineShader.uniform_float("offset",-0.01)
            lineShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))

            # Get Points
            if annotation.annotationAnchorObject.type == 'MESH':
                p1 = get_point(obverts[annotation.annotationAnchor], myobj,mat)
            else:
                p1 = mat @ Vector((0,0,0))

            loc = mat.to_translation()
            diff = Vector(p1) - Vector(loc)
            offset = annotation.annotationOffset
            
            p2 =  Vector(offset)
            textcard = generate_text_card(context,annotation,annotationProps,annotation.annotationRotation,(0,0,0))

            #Get local Rotation and Translation
            rot = mat.to_quaternion()
            loc = mat.to_translation()

            #Compose Rotation and Translation Matrix
            rotMatrix = Matrix.Identity(3)
            rotMatrix.rotate(rot)
            rotMatrix.resize_4x4()
            locMatrix = Matrix.Translation(loc)
            rotLocMatrix = locMatrix @ rotMatrix

            # Transform offset and Text Card with Composed Matrix
            p2 = rotLocMatrix @ Vector(p2) + diff
            textcard[0] = rotLocMatrix @ (textcard[0] + offset) + diff
            textcard[1] = rotLocMatrix @ (textcard[1] + offset) + diff
            textcard[2] = rotLocMatrix @ (textcard[2] + offset) + diff
            textcard[3] = rotLocMatrix @ (textcard[3] + offset) + diff



            if  p1 is not None and p2 is not None:

                coords =[]
                coords.append(p1)
                coords.append(p2)
                coords.append(p2)
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
                if annotation.textPosition == 'T' or annotation.textPosition == 'B':
                    batch3d = batch_for_shader(pointShader, 'POINTS', {"pos": pointcoords})
                    batch3d.program_set(pointShader)
                    batch3d.draw()
            
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
                rotangle = radians(20)
                line.rotate(Quaternion(perp,rotangle))
                coords = []
                for idx in range (12):
                    rotangle = radians(360/12)
                    coords.append(line.copy() + Vector(p1))
                    coords.append(Vector((0,0,0)) + Vector(p1))
                    line.rotate(Quaternion(axis,rotangle))
                    coords.append(line.copy() + Vector(p1))
                
                triShader.bind()
                triShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
                triShader.uniform_float("offset", (0,0,0))

                batch = batch_for_shader(triShader, 'TRIS', {"pos": coords})
                batch.program_set(triShader)
                batch.draw()
                gpu.shader.unbind()

            if scene.measureit_arch_gl_show_d:
                draw_text_3D(context,annotation,myobj,textcard)                

    bgl.glDisable(bgl.GL_DEPTH_TEST)
    bgl.glDisable(bgl.GL_POLYGON_SMOOTH)
    bgl.glDepthMask(True)

def draw_text_3D(context,textobj,myobj,card):
    #get props
    normalizedDeviceUVs= [(-1,-1),(-1,1),(1,1),(1,-1)]

    # Define Flip Matrix's
    flipMatrixX = Matrix([
        [-1,0],
        [ 0,1]   
    ])

    flipMatrixY = Matrix([
        [1, 0],
        [0,-1]   
    ])

    # Flip UV's if user selected
    if textobj.textFlippedX is True or textobj.textFlippedY is True:
        flippedUVs = []
        for uv in normalizedDeviceUVs:
            if textobj.textFlippedX is True:
                uv = flipMatrixX@Vector(uv)
            if textobj.textFlippedY is True:
                uv = flipMatrixY@Vector(uv)
            flippedUVs.append(uv)
        normalizedDeviceUVs = flippedUVs
        
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
    if 'texture' in textobj:
        buffer = bgl.Buffer(bgl.GL_BYTE, dim, textobj['texture'].to_list())
        #texBuf = bgl.Buffer(bgl.GL_INT, 1)
        #bgl.glFinish()
        #bgl.glGenTextures(1, texBuf)
        #bgl.glActiveTexture(bgl.GL_TEXTURE0)
        #bgl.glBindTexture(bgl.GL_TEXTURE_2D, texBuf.to_list()[0])

        bgl.glTexImage2D(bgl.GL_TEXTURE_2D, 0, bgl.GL_RGBA, width, height, 0, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, buffer)
        bgl.glTexParameteri(bgl.GL_TEXTURE_2D, bgl.GL_TEXTURE_MIN_FILTER, bgl.GL_LINEAR)
        textobj.texture_updated=False
        
    # Draw Shader
    textShader.bind()
    textShader.uniform_float("image", 0)
    batch.draw(textShader)
    #bgl.glDeleteTextures(1, texBuf)
    gpu.shader.unbind()

def generate_end_caps(context,item,capType,capSize,pos,userOffsetVector,midpoint):
    capCoords = []
    size = capSize/100
    distVector = Vector(pos-Vector(midpoint)).normalized()
    norm = distVector.cross(userOffsetVector)
    #norm = Vector((abs(norm[0]),abs(norm[1]),abs(norm[2])))
    line = distVector*size
    
    #normDistVector.normalize()
    if capType == 99:
        pass
    elif capType == 'L' or capType == 'T' :
        rotangle = radians(45)
        line.rotate(Quaternion(norm,rotangle))
        p1 = (pos - line)
        p2 = (pos)
        line.rotate(Quaternion(norm,-(rotangle*2)))
        p3 = (pos - line)

        capCoords.append(p1)
        capCoords.append(p2)
        capCoords.append(p3)
        if capType == 'L':
            capCoords.append(p2)

    elif capType == 'D':
        rotangle = radians(-45)
        line = userOffsetVector.copy()
        line *= 1/20
        line.rotate(Quaternion(norm,rotangle))
        p1 = (pos - line)
        p2 = (pos + line)
        line.rotate(Quaternion(norm,rotangle))
        # Define Overextension
        capCoords.append(pos)
        capCoords.append(line + pos)
        # We Draw the square outside in the draw method   
    return capCoords

def generate_text_card(context,textobj,textProps,rotation,basePoint): 
    width = textobj.textWidth
    height = textobj.textHeight
    resolution = textobj.textResolution
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

    return coords


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
#
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
#
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
#
# ------------------------------------------
def get_2d_point(region, rv3d, point3d):
    if rv3d is not None and region is not None:
        return view3d_utils.location_3d_to_region_2d(region, rv3d, point3d)
    else:
        return get_render_location(point3d)



# -------------------------------------------------------------
# Draw a GPU line
#
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
#
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


# -------------------------------------------------------------
# Draw object num for debug
#
# -------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyUnboundLocalVariable,PyUnusedLocal
def draw_object(context, myobj, region, rv3d):
    scene = bpy.context.scene
    rawRGB = scene.measureit_arch_debug_obj_color
    #undo blenders Default Gamma Correction
    rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])
    fsize = scene.measureit_arch_debug_font
    precision = scene.measureit_arch_debug_precision
    # --------------------
    # object Loop
    # --------------------
    objs = bpy.context.scene.objects
    obidxs = list(range(len(bpy.context.scene.objects)))
    for o in obidxs:
        # Display only selected
        if scene.measureit_arch_debug_select is True:
            if objs[o].select is False:
                continue
        a_p1 = Vector(get_location(objs[o]))
        # colour
        
        #bgl .glColor4f(rgb[0], rgb[1], rgb[2], rgb[3])
        # Text
        txt = ''
        if scene.measureit_arch_debug_objects is True:
            txt += str(o)
        if scene.measureit_arch_debug_object_loc is True:
            txt += format_point(a_p1, precision)
        # converting to screen coordinates
        txtpoint2d = get_2d_point(region, rv3d, a_p1)
        draw_text(myobj, txtpoint2d, txt, rgb, fsize)
    return


# -------------------------------------------------------------
# Draw vertex num for debug
#
# -------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyUnboundLocalVariable,PyUnusedLocal
def draw_vertices(context, myobj, region, rv3d):
    # Only meshes
    if myobj.type != "MESH":
        return

    scene = bpy.context.scene
    rawRGB = scene.measureit_arch_debug_vert_color
    #undo blenders Default Gamma Correction
    rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])

    fsize = scene.measureit_arch_debug_font
    precision = scene.measureit_arch_debug_precision
    # --------------------
    # vertex Loop
    # --------------------
    if scene.measureit_arch_debug_vert_loc_toggle == '1':
        co_mult = lambda c: c
    else:  # if global, convert local c to global
        co_mult = lambda c: myobj.matrix_world @ c

    if myobj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(myobj.data)
        obverts = bm.verts
    else:
        obverts = myobj.data.vertices

    for v in obverts:
        # Display only selected
        if scene.measureit_arch_debug_select is True:
            if v.select is False:
                continue
        # noinspection PyBroadException
        # try:
        a_p1 = get_point(v.co, myobj,mat)
        # colour

        #bgl .glColor4f(rgb[0], rgb[1], rgb[2], rgb[3])
        # converting to screen coordinates
        txtpoint2d = get_2d_point(region, rv3d, a_p1)
        # Text
        txt = ''
        if scene.measureit_arch_debug_vertices is True:
            txt += str(v.index)
        if scene.measureit_arch_debug_vert_loc is True:
            txt += format_point(co_mult(v), precision)
        draw_text(myobj, txtpoint2d, txt, rgb, fsize)
        # except:
        #     print("Unexpected error:" + str(exc_info()))
        #     pass

    return


# -------------------------------------------------------------
# Draw edge num for debug
#
# -------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyUnboundLocalVariable,PyUnusedLocal
def draw_edges(context, myobj, region, rv3d):
    # Only meshes
    if myobj.type != "MESH":
        return

    scene = bpy.context.scene
    rawRGB = scene.measureit_arch_debug_edge_color
    #undo blenders Default Gamma Correction
    rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])

    fsize = scene.measureit_arch_debug_font
    precision = scene.measureit_arch_debug_precision
    # --------------------
    # edge Loop
    # 
    # uses lambda for edge midpoint finder (midf) because edit mode
    # edge vert coordinate is not stored in same places as in obj mode
    # --------------------
    if myobj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(myobj.data)
        obedges = bm.edges
        obverts = None  # dummy value to avoid duplicating for loop
        midf = lambda e, v: e.verts[0].co.lerp(e.verts[1], 0.5)
    else:
        obedges = myobj.data.edges
        obverts = myobj.data.vertices
        midf = lambda e, v: v[e.vertices[0]].lerp(v[e.vertices[1]], 0.5)

    for e in obedges:
        # Display only selected
        if scene.measureit_arch_debug_select is True:
            if e.select is False:
                continue
        a_mp = midf(e, obverts)
        a_p1 = get_point(a_mp, myobj,mat)
        # colour

        #bgl.glColor4f(rgb[0], rgb[1], rgb[2], rgb[3])
        # converting to screen coordinates
        txtpoint2d = get_2d_point(region, rv3d, a_p1)
        draw_text(myobj, txtpoint2d, str(e.index), rgb, fsize)
    return


# -------------------------------------------------------------
# Draw face num for debug
#
# -------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyUnboundLocalVariable,PyUnusedLocal
def draw_faces(context, myobj, region, rv3d):
    # Only meshes
    if myobj.type != "MESH":
        return

    scene = bpy.context.scene
    rawRGB = scene.measureit_arch_debug_face_color
    #undo blenders Default Gamma Correction
    rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])


    rawRGB2 = scene.measureit_arch_debug_norm_color
    #undo blenders Default Gamma Correction
    rgb2 = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])


    fsize = scene.measureit_arch_debug_font
    ln = scene.measureit_arch_debug_normal_size
    th = scene.measureit_arch_debug_width
    precision = scene.measureit_arch_debug_precision

    # --------------------
    # face Loop
    # --------------------
    if myobj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(myobj.data)
        obverts = bm.verts
        myfaces = bm.faces
    else:
        obverts = myobj.data.vertices
        myfaces = myobj.data.polygons

    for f in myfaces:
        normal = f.normal
        # Display only selected
        if scene.measureit_arch_debug_select is True:
            if f.select is False:
                continue
        # noinspection PyBroadException
        try:
            if myobj.mode == 'EDIT':
                a_p1 = get_point(f.calc_center_median(), myobj,mat)
            else:
                a_p1 = get_point(f.center, myobj,mat)

            a_p2 = (a_p1[0] + normal[0] * ln, a_p1[1] + normal[1] * ln, a_p1[2] + normal[2] * ln)

          
            #bgl.glColor4f(rgb[0], rgb[1], rgb[2], rgb[3])
            # converting to screen coordinates
            txtpoint2d = get_2d_point(region, rv3d, a_p1)
            point2 = get_2d_point(region, rv3d, a_p2)
            # Text
            if scene.measureit_arch_debug_faces is True:
                draw_text(myobj, txtpoint2d, str(f.index), rgb, fsize)
            # Draw Normal
            if scene.measureit_arch_debug_normals is True:
                shader.bind()
                #shader.uniform_float("thickness", th)
                shader.uniform_float("color", (rgb[0], rgb[1], rgb[2], rgb[3]))
                #bgl .glColor4f(rgb2[0], rgb2[1], rgb2[2], rgb2[3])
                draw_arrow(txtpoint2d, point2, 10, "99", "1")

                if len(obverts) > 2 and scene.measureit_arch_debug_normal_details is True:
                    if myobj.mode == 'EDIT':
                        i1 = f.verts[0].index
                        i2 = f.verts[1].index
                        i3 = f.verts[2].index
                    else:
                        i1 = f.vertices[0]
                        i2 = f.vertices[1]
                        i3 = f.vertices[2]

                    a_p1 = get_point(obverts[i1], myobj,mat)
                    a_p2 = get_point(obverts[i2], myobj,mat)
                    a_p3 = get_point(obverts[i3], myobj,mat)
                    # converting to screen coordinates
                    a2d = get_2d_point(region, rv3d, a_p1)
                    b2d = get_2d_point(region, rv3d, a_p2)
                    c2d = get_2d_point(region, rv3d, a_p3)
                    # draw vectors
                    draw_arrow(a2d, b2d, 10, "99", "1")
                    draw_arrow(b2d, c2d, 10, "99", "1")
                    # Normal vector data
                    txt = format_point(normal, precision)
                    draw_text(myobj, point2, txt, rgb2, fsize)

        except:
            print("Unexpected error:" + str(exc_info()))
            pass

    return


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
# Get vertex data
# mainobject
# --------------------------------------------------------------------
def get_mesh_vertices(myobj):
    try:
        obverts = []
        verts=[]
        if myobj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(myobj.data)
            verts = bm.verts
        else:
            bm = bmesh.new()
            eval_res = bpy.context.scene.measureit_arch_eval_mods
            if eval_res:
                bm.from_object(myobj,bpy.context.view_layer.depsgraph,deform=True)
                verts= bm.verts 
            else:
                verts = myobj.data.vertices
        for vert in verts:
            obverts.append(vert.co)
       #bm.free()
        return obverts
    except AttributeError:
        return None

def check_mods(myobj):
    goodMods = ["DATA_TRANSFER ", "NORMAL_EDIT", "WEIGHTED_NORMAL",
                'UV_PROJECT', 'UV_WARP', 'ARRAY', 'DECIMATE', 
                'EDGE_SPLIT', 'MASK', 'MIRROR', 'MULTIRES', 'SCREW',
                'SOLIDIFY', 'SUBSURF', 'TRIANGULATE', 'ARMATURE', 
                'CAST', 'CURVE', 'DISPLACE', 'HOOK', 'LAPLACIANDEFORM',
                'LATTICE', 'MESH_DEFORM', 'SHRINKWRAP', 'SIMPLE_DEFORM',
                'SMOOTH', 'CORRECTIVE_SMOOTH', 'LAPLACIANSMOOTH',
                'SURFACE_DEFORM', 'WARP', 'WAVE', 'CLOTH', 'COLLISION', 
                'DYNAMIC_PAINT', 'PARTICLE_INSTANCE', 'PARTICLE_SYSTEM',
                'SMOKE', 'SOFT_BODY', 'SURFACE','SOLIDIFY']
    for mod in myobj.modifiers:
        if mod.type not in goodMods:
            return False
    return True

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
def format_distance(fmt, units, value, factor=1):
    s_code = "\u00b2"  # Superscript two
    hide_units = bpy.context.scene.measureit_arch_hide_units
    # ------------------------
    # Units automatic
    # ------------------------
    if units == "1":
        # Units
        if bpy.context.scene.unit_settings.system == "IMPERIAL":
            feet = value * (3.2808399 ** factor)
            if round(feet, 2) >= 1.0:
                if hide_units is False:
                    fmt += " ft"
                if factor == 2:
                    fmt += s_code
                tx_dist = fmt % feet
            else:
                inches = value * (39.3700787 ** factor)
                if hide_units is False:
                    fmt += " in"
                if factor == 2:
                    fmt += s_code
                tx_dist = fmt % inches
        elif bpy.context.scene.unit_settings.system == "METRIC":
            if round(value, 2) >= 1.0:
                if hide_units is False:
                    fmt += " m"
                if factor == 2:
                    fmt += s_code
                tx_dist = fmt % value
            else:
                if round(value, 2) >= 0.01:
                    if hide_units is False:
                        fmt += " cm"
                    if factor == 2:
                        fmt += s_code
                    d_cm = value * (100 ** factor)
                    tx_dist = fmt % d_cm
                else:
                    if hide_units is False:
                        fmt += " mm"
                    if factor == 2:
                        fmt += s_code
                    d_mm = value * (1000 ** factor)
                    tx_dist = fmt % d_mm
        else:
            tx_dist = fmt % value
    # ------------------------
    # Units meters
    # ------------------------
    elif units == "2":
        if hide_units is False:
            fmt += " m"
        if factor == 2:
            fmt += s_code
        tx_dist = fmt % value
    # ------------------------
    # Units centimeters
    # ------------------------
    elif units == "3":
        if hide_units is False:
            fmt += " cm"
        if factor == 2:
            fmt += s_code
        d_cm = value * (100 ** factor)
        tx_dist = fmt % d_cm
    # ------------------------
    # Units milimiters
    # ------------------------
    elif units == "4":
        if hide_units is False:
            fmt += " mm"
        if factor == 2:
            fmt += s_code
        d_mm = value * (1000 ** factor)
        tx_dist = fmt % d_mm
    # ------------------------
    # Units feet
    # ------------------------
    elif units == "5":
        if hide_units is False:
            fmt += "\""
        if factor == 2:
            fmt += s_code
        decFeet= value * (3.2808399 ** factor)
        feet = int (floor(decFeet))
        if feet != 0:
            inches = 12*(decFeet%feet)
        else:
            inches = 12*(decFeet)
        tx_dist = str(feet) + "' " + fmt % inches
    # ------------------------
    # Units inches
    # ------------------------
    elif units == "6":
        if hide_units is False:
            fmt += " in"
        if factor == 2:
            fmt += s_code
        inches = value * (39.3700787 ** factor)
        tx_dist = fmt % inches
    # ------------------------
    # Default
    # ------------------------
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


