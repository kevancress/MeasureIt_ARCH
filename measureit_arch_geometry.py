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
from . import svg_shaders

lastMode = None
lineBatch3D = {}
dashedBatch3D = {}
hiddenBatch3D = {}

# define Shaders

# Alter which frag shaders are used depending on the blender version
# https://wiki.blender.org/wiki/Reference/Release_Notes/2.83/Python_API
# https://developer.blender.org/T74139

if bpy.app.version > (2,83,0):
    aafrag = Frag_Shaders_3D_B283.aa_fragment_shader
    basefrag = Frag_Shaders_3D_B283.base_fragment_shader
    dashedfrag = Frag_Shaders_3D_B283.dashed_fragment_shader
    textfrag = Frag_Shaders_3D_B283.text_fragment_shader
else:
    aafrag = Base_Shader_3D_AA.fragment_shader
    basefrag = Base_Shader_3D.fragment_shader
    dashedfrag = Dashed_Shader_3D.fragment_shader
    textfrag = Text_Shader.fragment_shader


lineShader = gpu.types.GPUShader(
    Base_Shader_3D.vertex_shader,
    aafrag,
    geocode=Line_Shader_3D.geometry_shader)
    
lineGroupShader = gpu.types.GPUShader(
    Line_Group_Shader_3D.vertex_shader,
    aafrag,
    geocode=Line_Group_Shader_3D.geometry_shader)

triShader = gpu.types.GPUShader(
    Base_Shader_3D.vertex_shader,
    basefrag)

dashedLineShader = gpu.types.GPUShader(
    Dashed_Shader_3D.vertex_shader,
    dashedfrag,
    geocode=Dashed_Shader_3D.geometry_shader)

pointShader = gpu.types.GPUShader(
    Point_Shader_3D.vertex_shader,
    aafrag,
    geocode=Point_Shader_3D.geometry_shader)

textShader = gpu.types.GPUShader(
    Text_Shader.vertex_shader,
    textfrag)

fontSizeMult = 6


def get_dim_tag(self,obj):
    dimGen = obj.DimensionGenerator[0]
    itemType = self.itemType
    idx = 0
    for wrap in dimGen.wrappedDimensions:
        if itemType == wrap.itemType:
            if itemType == 'D-ALIGNED':
                if self == dimGen.alignedDimensions[wrap.itemIndex]:
                    return idx
            elif itemType == 'D-AXIS':
                if self == dimGen.axisDimensions[wrap.itemIndex]:
                    return idx
            elif itemType == 'D-ARC':
                if self == dimGen.arcDimensions[wrap.itemIndex]:
                    return idx
        idx += 1

def recalc_dimWrapper_index(dimGen):
    wrappedDimensions = dimGen.wrappedDimensions
    id_aligned = 0
    id_angle = 0
    id_axis = 0
    id_arc = 0
    for dim in wrappedDimensions:
        if dim.itemType == 'D-ALIGNED':
            dim.itemIndex = id_aligned
            id_aligned += 1
        elif dim.itemType == 'D-ANGLE':
            dim.itemIndex = id_angle
            id_angle += 1
        elif dim.itemType == 'D-AXIS':
            dim.itemIndex = id_axis
            id_axis += 1
        elif dim.itemType == 'D-ARC':
            dim.itemIndex = id_arc
            id_axis += 1

def clear_batches():
    lineBatch3D.clear()
    dashedBatch3D.clear()
    hiddenBatch3D.clear()

def update_text(textobj, props, context):
    update_flag = False

    for textField in textobj.textFields:
        if textobj.text_updated or props.text_updated:
            textField.text_updated = True

        if textField.text_updated:
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
            fheight = blf.dimensions(font_id, 'Tpg"')[1]
            fwidth = blf.dimensions(font_id, text)[0]
            width = math.ceil(fwidth)
            height = math.ceil(fheight*1.3)
            

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

                    blf.position(font_id, 0, height*0.3, 0)
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
    textobj.text_updated = False    

def draw_alignedDimension(context, myobj, measureGen, dim, mat, svg=None):
    # GL Settings
    bgl.glEnable(bgl.GL_MULTISAMPLE)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glDepthFunc(bgl.GL_LEQUAL)
    bgl.glDepthMask(True)
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
    if dimProps.visibleInView is None or dimProps.visibleInView.name == context.scene.camera.data.name:
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

        p1Local = None
        p2Local = None

        deleteFlag = False
        try:
            p1Local = get_mesh_vertex(dim.dimObjectA,dim.dimPointA,dimProps.evalMods)
        except IndexError:
            print('p1 excepted for ' + dim.name + ' on ' + myobj.name)
            deleteFlag = True

        try:
            p2Local = get_mesh_vertex(dim.dimObjectB,dim.dimPointB,dimProps.evalMods)
        except IndexError:
            print('p2 excepted for ' + dim.name + ' on ' + myobj.name)
            deleteFlag = True

        if deleteFlag:
            dimGen = myobj.DimensionGenerator[0]
            wrapTag = get_dim_tag(dim, myobj)
            wrapper = dimGen.wrappedDimensions[wrapTag]
            tag = wrapper.itemIndex
            dimGen.alignedDimensions.remove(tag)
            dimGen.wrappedDimensions.remove(wrapTag)
            recalc_dimWrapper_index(dimGen)
            return

        p1 = get_point(p1Local, dim.dimObjectA,aMatrix)
        p2 = get_point(p2Local, dim.dimObjectB,bMatrix)
            


        #check dominant Axis
        sortedPoints = sortPoints(p1, p2)
        p1 = sortedPoints[0]
        p2 = sortedPoints[1]
    
        
        #calculate distance & MidpointGY
        distVector = Vector(p1)-Vector(p2)
        dist = distVector.length
        midpoint = interpolate3d(p1, p2, fabs(dist / 2))
        normDistVector = distVector.normalized()
        absNormDistVector = Vector((abs(normDistVector[0]),abs(normDistVector[1]),abs(normDistVector[2])))


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
       
        cardX = normDistVector.normalized() * sx
        cardY = userOffsetVector.normalized() *sy
        origin = Vector(textLoc) + cardY.normalized()*0.05

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
        dimLineVec = dimLineStart - dimLineEnd
        dimLineVec.normalize()
        dimLineEndCoord = dimLineEnd - dimLineVec * dimLineExtension 
        dimLineStartCoord = dimLineStart + dimLineVec * dimLineExtension 
        
        square = [(origin-(cardX/2)),(origin-(cardX/2)+cardY ),(origin+(cardX/2)+cardY ),(origin+(cardX/2))]

        if scene.measureit_arch_gl_show_d:
            draw_text_3D(context,dimText,dimProps,myobj,square)

        #Collect coords and endcaps
        coords = [leadStartA,leadEndA,leadStartB,leadEndB,dimLineStartCoord,dimLineEndCoord]
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
            triShader.uniform_float("offset", -0.001)

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
        lineShader.uniform_float("offset", -0.001)

        # batch & Draw Shader   
        batch3d = batch_for_shader(lineShader, 'LINES', {"pos": coords})

        if rgb[3] == 1:
            bgl.glBlendFunc(bgl.GL_SRC_ALPHA,bgl.GL_ONE_MINUS_SRC_ALPHA)
            bgl.glDepthMask(True)
            lineShader.uniform_float("depthPass",True)
            batch3d.program_set(lineShader)
            batch3d.draw()


        if sceneProps.is_render_draw:
            bgl.glBlendFunc(bgl.GL_SRC_ALPHA,bgl.GL_ONE_MINUS_SRC_ALPHA)
            #bgl.glBlendEquation(bgl.GL_FUNC_ADD)
            bgl.glBlendEquation(bgl.GL_MAX)

        bgl.glDepthMask(False)
        lineShader.uniform_float("depthPass",False)
        batch3d.program_set(lineShader)
        batch3d.draw()
        gpu.shader.unbind()

        if sceneProps.is_vector_draw:
            svg_dim = svg.add(svg.g(id=dim.name))
            svg_shaders.svg_line_shader(dim,coords, lineWeight, rgb, svg, parent=svg_dim)
            svg_shaders.svg_fill_shader(dim, filledCoords, rgb, svg, parent=svg_dim)
            svg_shaders.svg_text_shader(dim, dimText.text, origin, square, rgb, svg, parent=svg_dim)
    

        #Reset openGL Settings
        bgl.glBlendEquation(bgl.GL_FUNC_ADD)
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        bgl.glDepthMask(True)

def draw_boundsDimension(context, myobj, measureGen, dim, mat, svg=None):
    # GL Settings
    bgl.glEnable(bgl.GL_MULTISAMPLE)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glDepthFunc(bgl.GL_LEQUAL)
    bgl.glDepthMask(True)
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
    if dimProps.visibleInView is None or dimProps.visibleInView.name == context.scene.camera.data.name:
        inView = True        
    else:
        inView = False    
    if dim.visible and dimProps.visible and inView:

        if sceneProps.is_render_draw:
            viewport = [context.scene.render.resolution_x, context.scene.render.resolution_y]
        else:
            viewport = [context.area.width, context.area.height]

        # Obj Properties
        # For Collection Bounding Box
        if dim.dimCollection != None:
            collection = dim.dimCollection
            objects = collection.all_objects

            # get the axis aligned bounding coords for each object            
            coords = []
            for myobj in objects:
    
                boundsStr = str(myobj.name) + "_bounds"
                rotStr = str(myobj.name) + "_lastRot"
                locStr = str(myobj.name) + "_lastLoc"
                scaleStr = str(myobj.name) + "_lastScale"

                # if no rotation or non mesh obj just use the Objects bounding Box
                # Also clean up any chached values
                if myobj.matrix_world.to_quaternion() == Quaternion((1.0, 0.0, 0.0, 0.0)) or myobj.type != 'MESH':
                    bounds = myobj.bound_box
                    for coord in bounds:
                        coords.append(myobj.matrix_world @ Vector(coord))

                        # Also clean up any chached values
                        try:
                            del dim[locStr]
                            del dim[rotStr]
                            del dim[boundsStr]
                            del dim[scaleStr]
                        except KeyError:
                            pass

                else: # otherwise get its points and calc its AABB directly

                    try:
                        if myobj.matrix_world.to_quaternion() != Quaternion(dim[rotStr]) or myobj.location != Vector(dim[locStr]) or  myobj.scale !=  Vector(dim[scaleStr]):
                            obverts = get_mesh_vertices(myobj)
                            worldObverts = [myobj.matrix_world @ coord for coord in obverts]
                            maxX,minX,maxY,minY,maxZ,minZ = get_axis_aligned_bounds(worldObverts)
                            dim[boundsStr] = [maxX,minX,maxY,minY,maxZ,minZ]
                            dim[rotStr] = myobj.matrix_world.to_quaternion()
                            dim[locStr] = myobj.location
                            dim[scaleStr] = myobj.scale
                        else:
                            maxX,minX,maxY,minY,maxZ,minZ = dim[boundsStr]
                    except KeyError:
                        obverts = get_mesh_vertices(myobj)
                        worldObverts = [myobj.matrix_world @ coord for coord in obverts]
                        maxX,minX,maxY,minY,maxZ,minZ = get_axis_aligned_bounds(worldObverts)
                        dim[boundsStr] = [maxX,minX,maxY,minY,maxZ,minZ]
                        dim[rotStr] = myobj.matrix_world.to_quaternion()
                        dim[locStr] = myobj.location
                        dim[scaleStr] = myobj.scale


                    coords.append(Vector((maxX,maxY,maxZ)))
                    coords.append(Vector((minX,minY,minZ)))

                    
            # Get the axis aligned bounding coords for that set of coords
            maxX,minX,maxY,minY,maxZ,minZ = get_axis_aligned_bounds(coords)

            distX = maxX - minX
            distY = maxY - minY
            distZ = maxZ - minZ

            p0 = Vector((minX,minY,minZ))
            p1 = Vector((minX,minY,maxZ))
            p2 = Vector((minX,maxY,maxZ))
            p3 = Vector((minX,maxY,minZ))
            p4 = Vector((maxX,minY,minZ))
            p5 = Vector((maxX,minY,maxZ))
            p6 = Vector((maxX,maxY,maxZ))
            p7 = Vector((maxX,maxY,minZ))
            
            bounds = [p0,p1,p2,p3,p4,p5,p6,p7]
            #print ("X: " + str(distX) + ", Y: " + str(distY) + ", Z: " + str(distZ))

        # Single object bounding Box
        else:
            if not dim.calcAxisAligned:
                bounds = myobj.bound_box
                tempbounds = []
                for bound in bounds:
                    tempbounds.append(myobj.matrix_world @ Vector(bound))
                bounds = tempbounds

            else: # Calc AABB when rotation changes
                try:
                    if myobj.matrix_world.to_quaternion() != Quaternion(dim['lastRot']):
                        obverts = get_mesh_vertices(myobj)
                        worldObverts = [myobj.matrix_world @ coord for coord in obverts]
                        maxX,minX,maxY,minY,maxZ,minZ = get_axis_aligned_bounds(worldObverts)
                        dim['bounds'] = [maxX,minX,maxY,minY,maxZ,minZ]
                        dim['lastRot'] = myobj.matrix_world.to_quaternion()
                    else:
                        maxX,minX,maxY,minY,maxZ,minZ = dim['bounds']
                except KeyError:
                    obverts = get_mesh_vertices(myobj)
                    worldObverts = [myobj.matrix_world @ coord for coord in obverts]
                    maxX,minX,maxY,minY,maxZ,minZ = get_axis_aligned_bounds(worldObverts)
                    dim['bounds'] = [maxX,minX,maxY,minY,maxZ,minZ]
                    dim['lastRot'] = myobj.matrix_world.to_quaternion()
                    

                
                distX = maxX - minX
                distY = maxY - minY
                distZ = maxZ - minZ

                p0 = Vector((minX,minY,minZ))
                p1 = Vector((minX,minY,maxZ))
                p2 = Vector((minX,maxY,maxZ))
                p3 = Vector((minX,maxY,minZ))
                p4 = Vector((maxX,minY,minZ))
                p5 = Vector((maxX,minY,maxZ))
                p6 = Vector((maxX,maxY,maxZ))
                p7 = Vector((maxX,maxY,minZ))
                
                bounds = [p0,p1,p2,p3,p4,p5,p6,p7]
                   


        # Points for Bounding Box
        # 
        #       2-----------6
        #      /           /|
        #     /           / |
        #    /           /  |
        #   1 ----------5   7           Z
        #   |           |  /            |  y
        #   |           | /             | /
        #   |           |/              |/   
        #   0-----------4               |--------X


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


        ## Select Best Pairs
        diagonalPair = [2,4]
        dp1 = Vector(bounds[2])
        dp2 = Vector(bounds[4])
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

        # establish measure loop
        # this runs through the X, Y and Z axis
        idx = 0
        selectionVectors = [k,i,j]
        placementVec = [j,-i,-i]
        for axis in dim.drawAxis:
            if axis:
                # get points 
                p1 = Vector(bounds[bestPairs[idx][0]])
                p2 = Vector(bounds[bestPairs[idx][1]])

                #check dominant Axis
                sortedPoints = sortPoints(p1, p2)
                p1 = sortedPoints[0]
                p2 = sortedPoints[1]
            
                
                #calculate distance & MidpointGY
                distVector = Vector(p1)-Vector(p2)
                dist = distVector.length
                midpoint = interpolate3d(p1, p2, fabs(dist / 2))
                normDistVector = distVector.normalized()
                absNormDistVector = Vector((abs(normDistVector[0]),abs(normDistVector[1]),abs(normDistVector[2])))


                # Compute offset vector from face normal and user input
                axisViewVec = viewVec.copy()
                axisViewVec[idx] = 0
                rotationMatrix = Matrix.Rotation(dim.dimRotation, 4, normDistVector)

                selectedNormal = placementVec[idx]

                if dim.dimCollection == None and dim.calcAxisAligned == False:
                    rot = myobj.matrix_world.to_quaternion()
                    selectedNormal.rotate(rot)

                #print(str(idx) + " " + str(abs(selectedNormal.dot(selectionVectors[idx]))))

                
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
                cardX = normDistVector.normalized() * sx
                cardY = userOffsetVector.normalized() *sy
                origin = Vector(textLoc) + cardY.normalized()*0.05

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
                dimLineVec = dimLineStart - dimLineEnd
                dimLineVec.normalize()
                dimLineEndCoord = dimLineEnd - dimLineVec * dimLineExtension 
                dimLineStartCoord = dimLineStart + dimLineVec * dimLineExtension 
                
                square = [(origin-(cardX/2)),(origin-(cardX/2)+cardY ),(origin+(cardX/2)+cardY ),(origin+(cardX/2))]

                if scene.measureit_arch_gl_show_d:
                    draw_text_3D(context,dimText,dimProps,myobj,square)
        

                #Collect coords and endcaps
                coords = [leadStartA,leadEndA,leadStartB,leadEndB,dimLineStartCoord,dimLineEndCoord]
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
                    triShader.uniform_float("offset", -0.001)

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
                lineShader.uniform_float("offset", -0.001)

                # batch & Draw Shader   
                batch = batch_for_shader(lineShader, 'LINES', {"pos": coords})
                batch.program_set(lineShader)
                batch.draw()
                gpu.shader.unbind()
            idx+=1
        #Reset openGL Settings
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        bgl.glDepthMask(True)


def draw_axisDimension(context, myobj, measureGen,dim, mat, svg=None):
    # GL Settings

    #start = time.perf_counter()
    bgl.glEnable(bgl.GL_MULTISAMPLE)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glDepthFunc(bgl.GL_LEQUAL)
    bgl.glDepthMask(True)

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
    if dimProps.visibleInView is None or dimProps.visibleInView.name == context.scene.camera.data.name:
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

        p1Local = Vector((0,0,0))
        p2Local = Vector((0,0,0))

        deleteFlag = False
        try:
            p1Local = get_mesh_vertex(dim.dimObjectA,dim.dimPointA,dimProps.evalMods)
        except IndexError:
            print('p1 excepted for ' + dim.name + ' on ' + myobj.name)
            deleteFlag = True

        try:
            p2Local = get_mesh_vertex(dim.dimObjectB,dim.dimPointB,dimProps.evalMods)
        except IndexError:
            print('p2 excepted for ' + dim.name + ' on ' + myobj.name)
            deleteFlag = True

        if deleteFlag:
            dimGen = myobj.DimensionGenerator[0]
            wrapTag = get_dim_tag(dim, myobj)
            wrapper = dimGen.wrappedDimensions[wrapTag]
            tag = wrapper.itemIndex
            dimGen.axisDimensions.remove(tag)
            dimGen.wrappedDimensions.remove(wrapTag)
            recalc_dimWrapper_index(dimGen)
            return

        p1 = get_point(p1Local, dim.dimObjectA,aMatrix)
        p2 = get_point(p2Local, dim.dimObjectB,bMatrix)

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
            xThreshold = 0.95796
            yThreshold = 0.22146
            zThreshold = 0.197568
            axisVec = i
        elif axis == 'Y':
            xThreshold = 0.22146
            yThreshold = 0.95796
            zThreshold = 0.197568
            axisVec = j
        elif axis == 'Z':
            xThreshold = 0.24681
            yThreshold = 0.24681
            zThreshold = 0.93800
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

        #rotate the axis vector if necessary
        if dim.dimAxisObject != None:
            customMat = dim.dimAxisObject.matrix_world
            rot = customMat.to_quaternion()
            axisVec.rotate(rot)

        #calculate distance by projecting the distance vector onto the axis vector

        alignedDistVector = Vector(p1)-Vector(p2)
        distVector = alignedDistVector.project(axisVec)

        
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
            secondPointAxis = distVector
            alignedDistVector = Vector(p2)-Vector(p1)
        else: 
            basePoint = p2
            secondPoint = p1
            secondPointAxis = -distVector
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
        cardX = Vector(secondPointAxis.normalized()) * sx
        cardY = userOffsetVector *sy

        origin = Vector(textLoc) + cardY.normalized()*0.05
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
            triShader.uniform_float("offset", -0.001)

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
        lineShader.uniform_float("offset", -0.001)

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

def draw_angleDimension(context, myobj, DimGen, dim,mat, svg=None):
    dimProps = dim
    sceneProps = context.scene.MeasureItArchProps
    if dim.uses_style:
        for alignedDimStyle in context.scene.StyleGenerator.alignedDimensions:
            if alignedDimStyle.name == dim.style:
                dimProps = alignedDimStyle

    #check all visibility conditions
    inView = False

    if dimProps.visibleInView is None or dimProps.visibleInView.name == context.scene.camera.data.name:
        inView = True        
    else:
        inView = False    
    if dim.visible and dimProps.visible and inView:
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

        #configure shaders
        pointShader.bind()
        pointShader.uniform_float("Viewport",viewport)
        pointShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
        pointShader.uniform_float("thickness", lineWeight)
        pointShader.uniform_float("depthPass", False)
        pointShader.uniform_float("offset", -0.001)
        gpu.shader.unbind()

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


        batch = batch_for_shader(lineShader, 'LINES', {"pos": coords})
        batch.program_set(lineShader)
        batch.draw()
        gpu.shader.unbind()

        # Draw Filled Faces after
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


        #Reset openGL Settings
        bgl.glDisable(bgl.GL_DEPTH_TEST)
        bgl.glDepthMask(True)

def draw_arcDimension(context, myobj, DimGen, dim,mat, svg=None):
    
    dimProps = dim
    sceneProps = context.scene.MeasureItArchProps
    if dim.uses_style:
        for alignedDimStyle in context.scene.StyleGenerator.alignedDimensions:
            if alignedDimStyle.name == dim.style:
                dimProps = alignedDimStyle

    # Check Visibility Conditions
    inView = False
    if dimProps.visibleInView is None or dimProps.visibleInView.name == context.scene.camera.data.name:
        inView = True
    
    if inView and dim.visible and dimProps.visible:
        # GL Settings
        bgl.glEnable(bgl.GL_MULTISAMPLE)
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        if dimProps.inFront:
            bgl.glDisable(bgl.GL_DEPTH_TEST)
        bgl.glDepthMask(True)

        lineWeight = dimProps.lineWeight
        if sceneProps.is_render_draw:
            viewport = [context.scene.render.resolution_x,context.scene.render.resolution_y]
        else:
            viewport = [context.area.width,context.area.height]

        scene = context.scene
        pr = scene.measureit_arch_gl_precision
        a_code = "\u00b0"  # degree
        #arc_code = "\u25e0" #arc
        arc_code = ""
        fmt = "%1." + str(pr) + "f"
        rawRGB = dimProps.color
        rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])
        offset = 0.001
        radius = dim.dimOffset

        deleteFlag = False
        try:
            p1 = Vector(get_point(get_mesh_vertex(myobj,dim.dimPointA,dimProps.evalMods), myobj,mat))
            p2 = Vector(get_point(get_mesh_vertex(myobj,dim.dimPointB,dimProps.evalMods), myobj,mat))
            p3 = Vector(get_point(get_mesh_vertex(myobj,dim.dimPointC,dimProps.evalMods), myobj,mat))
        except IndexError:
            print('Get Point Error for ' + dim.name + ' on ' + myobj.name)
            deleteFlag = True

        if deleteFlag:
            dimGen = myobj.DimensionGenerator[0]
            wrapTag = get_dim_tag(dim, myobj)
            wrapper = dimGen.wrappedDimensions[wrapTag]
            tag = wrapper.itemIndex
            dimGen.arcDimensions.remove(tag)
            dimGen.wrappedDimensions.remove(wrapTag)
            recalc_dimWrapper_index(dimGen)
            return

        #calc normal to plane defined by points
        vecA = (p1-p2)
        vecA.normalize()
        vecB = (p3-p2)
        vecB.normalize()
        norm = vecA.cross(vecB).normalized()


        # Calculate the Arc Defined by our 3 points
        # reference for maths: http://en.wikipedia.org/wiki/Circumscribed_circle

        an_p1 = p1.copy()
        an_p2 = p2.copy()
        an_p3 = p3.copy()

        an_p12 = Vector((an_p1[0] - an_p2[0], an_p1[1] - an_p2[1], an_p1[2] - an_p2[2]))
        an_p13 = Vector((an_p1[0] - an_p3[0], an_p1[1] - an_p3[1], an_p1[2] - an_p3[2]))
        an_p21 = Vector((an_p2[0] - an_p1[0], an_p2[1] - an_p1[1], an_p2[2] - an_p1[2]))
        an_p23 = Vector((an_p2[0] - an_p3[0], an_p2[1] - an_p3[1], an_p2[2] - an_p3[2]))
        an_p31 = Vector((an_p3[0] - an_p1[0], an_p3[1] - an_p1[1], an_p3[2] - an_p1[2]))
        an_p32 = Vector((an_p3[0] - an_p2[0], an_p3[1] - an_p2[1], an_p3[2] - an_p2[2]))
        an_p12xp23 = an_p12.copy().cross(an_p23)

        alpha = pow(an_p23.length, 2) * an_p12.dot(an_p13) / (2 * pow(an_p12xp23.length, 2))
        beta = pow(an_p13.length, 2) * an_p21.dot(an_p23) / (2 * pow(an_p12xp23.length, 2))
        gamma = pow(an_p12.length, 2) * an_p31.dot(an_p32) / (2 * pow(an_p12xp23.length, 2))

        # THIS IS THE CENTER POINT
        a_p1 = (alpha * an_p1[0] + beta * an_p2[0] + gamma * an_p3[0],
                alpha * an_p1[1] + beta * an_p2[1] + gamma * an_p3[1],
                alpha * an_p1[2] + beta * an_p2[2] + gamma * an_p3[2])

        b_p1 = (an_p2[0], an_p2[1], an_p2[2])
        a_n = an_p12.cross(an_p23)
        a_n.normalize()  # normal vector
        arc_angle, arc_length = get_arc_data(an_p1, a_p1, an_p2, an_p3)
        
        center = Vector(a_p1)
        dim.arcCenter = center

        # DRAW EVERYTHING AT THE ORIGIN,
        # Well move all our coords back into place by
        # adding back our center vector later

        A = Vector(p1) - center
        B = Vector(p2) - center
        C = Vector(p3) - center

        #get circle verts
        startVec = A
        arc_angle = arc_angle
        numCircleVerts = math.ceil(radius/.2)+ int((degrees(arc_angle))/2)
        verts = []
        for idx in range (numCircleVerts+2):
            rotangle= -(arc_angle/(numCircleVerts+1))*idx
            point = startVec.copy()
            point.rotate(Quaternion(norm,rotangle))
            verts.append((point).normalized())

        # Radius
        radius = (B).length
        offsetRadius = radius + dim.dimOffset
        endVec = C
        coords = []

        # Map raw Circle Verts to radius for marker
        startVec = (verts[0]*offsetRadius)
        coords.append(startVec)
        for vert in verts:
            coords.append((vert*offsetRadius))
            coords.append((vert*offsetRadius))
        endVec = (verts[len(verts)-1]*offsetRadius)
        coords.append(endVec)

        # Define Radius Leader
        zeroVec = Vector((0,0,0))
        radiusLeader = C.copy()
        radiusLeader.rotate(Quaternion(norm,arc_angle/2))
        radiusMid = Vector(interpolate3d(radiusLeader,zeroVec,radius/2))

       
        # Generate end caps
        # Set up properties
        filledCoords = []
        midVec = A
        caps = [dimProps.endcapA,dimProps.endcapB]
        pos = [startVec,endVec]

        if dim.showRadius:
            caps.append(dim.endcapC)
            pos.append(radiusLeader)

        capSize = dimProps.endcapSize
        arrowoffset =  3 + int(max(0, min(math.ceil(capSize/4), len(coords)/5)))
        mids = (coords[arrowoffset], coords[len(coords)-arrowoffset], radiusMid) #offset the arrow direction as arrow size increases
        
        i=0
        for cap in caps:
            #def        generate_end_caps(context,item,capType,capSize,pos,userOffsetVector,midpoint,posflag,flipCaps):
            capCoords = generate_end_caps(context,dimProps,cap,capSize,pos[i],midVec,mids[i],i,False)
            i += 1 
            for coord in capCoords[0]:
                coords.append(coord)
            for filledCoord in capCoords[1]:
                filledCoords.append(filledCoord)

         # Add A and C Extension Lines
        coords.append(A)
        coords.append((((A).normalized())*(offsetRadius + arrowoffset/100)))
        
        coords.append(C)
        coords.append((((C).normalized())*(offsetRadius + arrowoffset/100)))

         # Add Radius leader
        if dim.showRadius:
            coords.append(zeroVec)
            coords.append(radiusLeader)

        
        #### TEXT
        scene = context.scene
        pr = scene.measureit_arch_gl_precision
        textFormat = "%1." + str(pr) + "f"

        # Check for text field
        if len(dim.textFields) != 2:
            dim.textFields.add()
            dim.textFields.add()

        radiusText = dim.textFields[0]
        
        lengthText = dim.textFields[1]
       


        # format text and update if necessary
        lengthStr = arc_code + str(format_distance(textFormat,arc_length))
        if dim.displayAsAngle:
            if bpy.context.scene.unit_settings.system_rotation == "DEGREES":
                arc_angle = degrees(arc_angle)
            else:
                a_code = " rad"
            lengthStr = " " + textFormat % arc_angle
            lengthStr += a_code

        if lengthText.text != str(lengthStr):
            lengthText.text = str(lengthStr)
            lengthText.text_updated = True

        if dim.showRadius:
            radStr = 'r ' + str(format_distance(textFormat,radius))
            if radiusText.text != str(lengthStr):
                radiusText.text = str(radStr)
                radiusText.text_updated = True
            
            #make Radius text card
            width = radiusText.textWidth
            height = radiusText.textHeight 
        
            midPoint = Vector(interpolate3d(zeroVec,radiusLeader,radius/2))
            vecY =  midPoint.cross(norm).normalized()
            vecX = midPoint.normalized()
            resolution = dimProps.textResolution
            size = dimProps.fontSize/fontSizeMult
            sx = (width/resolution)*0.1*size
            sy = (height/resolution)*0.1*size
            origin = Vector(midPoint) + 0.04*vecY
            cardX = vecX * sx
            cardY = vecY *sy
            tmp = [(origin-(cardX/2)),(origin-(cardX/2)+cardY ),(origin+(cardX/2)+cardY ),(origin+(cardX/2))]
            square = []
            for coord in tmp:
                square.append(coord+center)
                
            if scene.measureit_arch_gl_show_d:
                draw_text_3D(context,dim.textFields[0],dimProps,myobj,square)

        #make Length text card

        width = lengthText.textWidth
        height = lengthText.textHeight 
        
        midPoint = radiusLeader.normalized()*offsetRadius
        vecX =  midPoint.cross(norm).normalized()
        vecY = midPoint.normalized()
        resolution = dimProps.textResolution
        size = dimProps.fontSize/fontSizeMult
        sx = (width/resolution)*0.1*size
        sy = (height/resolution)*0.1*size
        origin = Vector(midPoint)
        cardX = vecX * sx
        cardY = vecY *sy
        tmp = [(origin-(cardX/2)),(origin-(cardX/2)+cardY ),(origin+(cardX/2)+cardY ),(origin+(cardX/2))]
        square = []
        for coord in tmp:
            square.append(coord+center)
            
        if scene.measureit_arch_gl_show_d:
            draw_text_3D(context,dim.textFields[1],dimProps,myobj,square)

        draw_coords = []
        point_coords = []
        for coord in coords:
            draw_coords.append(coord+center)
            point_coords.append(coord+center)

        # Draw Our Measurement
        pointShader.bind()
        pointShader.uniform_float("Viewport",viewport)
        pointShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
        pointShader.uniform_float("offset", 0)
        pointShader.uniform_float("depthPass", False)
        pointShader.uniform_float("thickness",lineWeight)
        batch = batch_for_shader(pointShader, 'POINTS', {"pos": point_coords})
        batch.program_set(pointShader)
        batch.draw()
        gpu.shader.unbind()


        lineShader.bind()
        lineShader.uniform_float("Viewport",viewport)
        lineShader.uniform_float("thickness",lineWeight)
        lineShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
        lineShader.uniform_float("offset", -0.005)

        batch = batch_for_shader(lineShader, 'LINES', {"pos": draw_coords})
        batch.program_set(lineShader)
        batch.draw()
        gpu.shader.unbind()

        # Draw the arc itself
        coords = []
        startVec = (verts[0]*radius)
        coords.append(startVec)
        for vert in verts:
            coords.append((vert*radius))
            coords.append((vert*radius))
        endVec = (verts[len(verts)-1]*radius)
        coords.append(endVec)

        
        draw_coords = []
        point_coords2 = []
        for coord in coords:
            draw_coords.append(coord+center)
            point_coords2.append(coord+center)  

        pointShader.bind()
        pointShader.uniform_float("Viewport",viewport)
        pointShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
        pointShader.uniform_float("offset", -offset)
        pointShader.uniform_float("depthPass", False)
        pointShader.uniform_float("thickness",lineWeight*3)
        batch = batch_for_shader(pointShader, 'POINTS', {"pos": point_coords2})
        batch.program_set(pointShader)
        batch.draw()
        gpu.shader.unbind()

        lineShader.bind()
        lineShader.uniform_float("thickness",lineWeight*3)
        batch = batch_for_shader(lineShader, 'LINES', {"pos": draw_coords})
        batch.program_set(lineShader)
        batch.draw()
        gpu.shader.unbind()


        if dim.showRadius:
            pointCenter = [center]
            pointShader.bind()
            pointShader.uniform_float("thickness",lineWeight*5)
            pointShader.uniform_float("Viewport",viewport)
            pointShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
            pointShader.uniform_float("offset", -0.01)
            pointShader.uniform_float("depthPass", False)
            batch = batch_for_shader(pointShader, 'POINTS', {"pos": pointCenter})
            batch.program_set(pointShader)
            batch.draw()
            gpu.shader.unbind()

        if len(filledCoords) != 0:
            #bind shader
            bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
            triShader.bind()
            triShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
            triShader.uniform_float("offset", -0.01) #z offset this a little to avoid zbuffering

            mappedFilledCoords = []
            for coord in filledCoords:
                mappedFilledCoords.append(coord+center)


            batch = batch_for_shader(triShader, 'TRIS', {"pos": mappedFilledCoords})
            batch.program_set(triShader)
            batch.draw()
            gpu.shader.unbind()
            bgl.glDisable(bgl.GL_POLYGON_SMOOTH)
        

 
        #Reset openGL Settings
        bgl.glDisable(bgl.GL_DEPTH_TEST)
        bgl.glDepthMask(True)

def draw_areaDimension(context, myobj, DimGen, dim, mat, svg=None):
    dimProps = dim
    sceneProps = context.scene.MeasureItArchProps
    scene = context.scene
    if dim.uses_style:
        for alignedDimStyle in context.scene.StyleGenerator.alignedDimensions:
            if alignedDimStyle.name == dim.style:
                dimProps = alignedDimStyle

    # Check Visibility Conditions
    inView = False
    if dimProps.visibleInView is None or dimProps.visibleInView.name == context.scene.camera.data.name:
        inView = True
    
    if inView and dim.visible and dimProps.visible:
        # GL Settings
        bgl.glEnable(bgl.GL_MULTISAMPLE)
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        if dimProps.inFront:
            bgl.glDisable(bgl.GL_DEPTH_TEST)
        bgl.glDepthMask(True)

        lineWeight = dimProps.lineWeight
        if sceneProps.is_render_draw:
            viewport = [context.scene.render.resolution_x,context.scene.render.resolution_y]
        else:
            viewport = [context.area.width,context.area.height]

        rawRGB = dim.fillColor
        rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),1)
        fillRGB = (rgb[0],rgb[1],rgb[2],dim.fillAlpha)

        rawRGB = dimProps.color
        textRGB = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])

        bm = bmesh.new()
        if myobj.mode != 'EDIT':
            eval_res = sceneProps.eval_mods
            if (eval_res or dim.evalMods) and check_mods(myobj): # From Evaluated Deps Graph
                bm.from_object(myobj,bpy.context.view_layer.depsgraph,deform=True)
            else:             
                bm.from_mesh(myobj.data)
        else:
            bm = bmesh.from_edit_mesh(myobj.data)
        
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        faces = bm.faces

        # Get the Filled Coord and Sum the Face Areas
        filledCoords = []
        sumArea = 0
        verts = bm.verts
        for faceIdx in dim['facebuffer'].to_list():
            face = faces[faceIdx]
            area = face.calc_area()
        
            indices = []
            for vert in face.verts:
                indices.append(vert.index)

            tris = mesh_utils.ngon_tessellate(myobj.data,indices)

            for tri in tris:
                v1, v2, v3 = tri
                p1 = mat @ verts[indices[v1]].co
                p2 = mat @ verts[indices[v2]].co
                p3 = mat @ verts[indices[v3]].co
                filledCoords.append(p1)
                filledCoords.append(p2)
                filledCoords.append(p3)
                area = get_triangle_area(p1, p2, p3)
                sumArea += area

        # Get the Perimeter Coords
        perimeterCoords = [] 
        for edgeIdx in dim['perimeterEdgeBuffer'].to_list():
            edge = bm.edges[edgeIdx]
            verts = edge.verts
            perimeterCoords.append(verts[0].co)
            perimeterCoords.append(verts[1].co)

        # Format and draw Text
        if 'textFields' not in dim:
            dim.textFields.add()

        dimText = dim.textFields[0]
        pr = scene.measureit_arch_gl_precision
        textFormat = "%1." + str(pr) + "f"
        areaText = format_distance(textFormat,sumArea,isArea=True)
        if dimText.text != str(areaText):
            dimText.text = str(areaText)
            dimText.text_updated = True
        
        width = dimText.textWidth
        height = dimText.textHeight 

        # get text location
        # We're using the active face center and normal for 
        # initial text placement 
        originFace = faces[dim.originFaceIdx]
        origin = originFace.calc_center_bounds()
        normal = originFace.normal
        tangent = originFace.calc_tangent_edge()
        origin += dim.dimTextPos + normal*0.001

        y= normal.cross(tangent)
        x= normal.cross(y)
        
        #y.rotate(Quaternion(normal,radians(-45)))
        #x.rotate(Quaternion(normal,radians(-45)))

        y.rotate(Quaternion(normal,dim.dimRotation))
        x.rotate(Quaternion(normal,dim.dimRotation))

        # get card vectors
        resolution = dimProps.textResolution
        size = dimProps.fontSize/fontSizeMult
        sx = (width/resolution)*0.1*size
        sy = (height/resolution)*0.1*size

        cardX = x*sx
        cardY = y*sy

        # Create card & Draw text
        square = [(origin-(cardX/2)),(origin-(cardX/2)+cardY),(origin+(cardX/2)+cardY),(origin+(cardX/2))]
        # account for obj mat
        tempCoords = []
        for coord in square:
            tempCoords.append(mat@coord)
        square = tempCoords
        del tempCoords

        if scene.measureit_arch_gl_show_d:
            draw_text_3D(context,dimText,dimProps,myobj,square)


        #Draw Fill
        bgl.glDepthMask(False)
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA,bgl.GL_ONE_MINUS_SRC_ALPHA)
        triShader.bind()
        triShader.uniform_float("finalColor", fillRGB)
        triShader.uniform_float("offset", -0.001) #z offset this a little to avoid zbuffering

        batch = batch_for_shader(triShader, 'TRIS', {"pos": filledCoords})
        batch.program_set(triShader)
        batch.draw()
        gpu.shader.unbind()


        # Draw Perimeter
        lineGroupShader.bind()
        lineGroupShader.uniform_float("Viewport",viewport)
        lineGroupShader.uniform_float("objectMatrix",mat)
        lineGroupShader.uniform_float("thickness",dimProps.lineWeight)
        lineGroupShader.uniform_float("extension",0)
        lineGroupShader.uniform_float("weightInfluence", 1)
        lineGroupShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
        lineGroupShader.uniform_float("zOffset", -0.001)
        
        tempWeights = [1.0] * len(perimeterCoords)

        batch3d = batch_for_shader(lineGroupShader, 'LINES', {"pos": perimeterCoords,"weight":tempWeights})

        bgl.glDepthMask(True)
        lineGroupShader.uniform_float("depthPass", True)
        batch3d.program_set(lineGroupShader)
        batch3d.draw()

        if sceneProps.is_render_draw:
            bgl.glBlendEquation(bgl.GL_MAX)

        bgl.glDepthMask(False)
        lineGroupShader.uniform_float("depthPass", False)
        batch3d.program_set(lineGroupShader)
        batch3d.draw()
        gpu.shader.unbind()


    gpu.shader.unbind()
    bgl.glBlendFunc(bgl.GL_SRC_ALPHA,bgl.GL_ONE_MINUS_SRC_ALPHA)
    bgl.glBlendEquation(bgl.GL_FUNC_ADD)
    bgl.glDisable(bgl.GL_DEPTH_TEST)
    bgl.glDepthMask(True)

# takes a set of co-ordinates returns the min and max value for each axis
def get_axis_aligned_bounds(coords):
    maxX = None
    minX = None
    maxY = None
    minY = None
    maxZ = None
    minZ = None
    
    for coord in coords:
        if maxX == None:
            maxX = coord[0]
            minX = coord[0]
            maxY = coord[1]
            minY = coord[1]
            maxZ = coord[2]
            minZ = coord[2]
        if coord[0] > maxX: maxX = coord[0]
        if coord[0] < minX: minX = coord[0]
        if coord[1] > maxY: maxY = coord[1]
        if coord[1] < minY: minY = coord[1]
        if coord[2] > maxZ: maxZ = coord[2]
        if coord[2] < minZ: minZ = coord[2]
    
    return [maxX,minX,maxY,minY,maxZ,minZ]

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
        try:
            vertA = myobj.data.vertices[dim.dimPointA]
            directionRay = vertA.normal + loc 
        except:
            directionRay = Vector((0,0,0))
            
        #get Adjacent Face normals if possible
        possibleNormals = []
        faces = myobj.data.polygons
        # Create a Bmesh Instance from the selected object
        bm = bmesh.new()
        bm.from_mesh(myobj.data)
        bm.edges.ensure_lookup_table()

        # For each edge get its linked faces and vertex indicies
        for edge in bm.edges:
            bmEdgeIndices = [edge.verts[0].index,edge.verts[1].index]
            if dim.dimPointA in bmEdgeIndices and dim.dimPointB in bmEdgeIndices:
                linked_faces = edge.link_faces
                for face in linked_faces:
                    possibleNormals.append(face.normal)

        bm.free()
       

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
        
def draw_line_group(context, myobj, lineGen, mat, svg=None):
    scene = context.scene
    sceneProps = scene.MeasureItArchProps

    # Blending Settings
    bgl.glEnable(bgl.GL_BLEND)

    # Depth Settings
    bgl.glEnable(bgl.GL_DEPTH_TEST)
    bgl.glDepthFunc(bgl.GL_LEQUAL) 


    
    
    if sceneProps.is_render_draw:
        viewport = [context.scene.render.resolution_x,context.scene.render.resolution_y]
    else:
        ## Use render resolution scaled to viewport aspect ratio
        rv3d = context.area.spaces[0].region_3d
        zoom = (rv3d.view_camera_zoom+30)/63
        viewport = [context.scene.render.resolution_x/zoom,context.scene.render.resolution_y/zoom]
        viewport = [context.area.width,context.area.height]
        #viewAspect = viewport[0]/viewport[1]
        #render = [context.scene.render.resolution_x,context.scene.render.resolution_y]
        #renderAspect = render[0]/render[1]
        #apsectDiff = (viewAspect/renderAspect)/2
        #render = [render[0]*apsectDiff,render[1]/apsectDiff]
        #viewport = render

    for idx in range(0, lineGen.line_num):
        lineGroup = lineGen.line_groups[idx]
        lineProps = lineGroup
        if lineGroup.uses_style:
            for lineStyle in context.scene.StyleGenerator.line_groups:
                if lineStyle.name == lineGroup.style:
                    lineProps= lineStyle

        if lineProps.visibleInView is None or lineProps.visibleInView.name == context.scene.camera.data.name:
            inView = True        
        else:
            inView = False  
            
        if lineGroup.visible and lineProps.visible and inView:
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

            
            #Get line data to be drawn
    
            evalMods = lineProps.evalMods

            # Flag for re-evaluation of batches & mesh data
            verts=[]
            global lastMode
            recoordFlag = False
            evalModsGlobal = sceneProps.eval_mods
            if lastMode != myobj.mode or evalMods or evalModsGlobal:
                recoordFlag = True
                lastMode = myobj.mode
                
            if myobj.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(myobj.data)
                verts = bm.verts
            else:     
                if (evalModsGlobal or evalMods) and check_mods(myobj):
                    deps = bpy.context.view_layer.depsgraph
                    obj_eval = myobj.evaluated_get(deps)
                    mesh = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=deps)
                    verts = mesh.vertices          
                else:
                    verts = myobj.data.vertices

            # Get Coords
            sceneProps = bpy.context.scene.MeasureItArchProps
            if 'coordBuffer' not in lineGroup or evalMods or recoordFlag:
                # Handle line groups created with older versions of measureIt-ARCH
                if 'singleLine' in lineGroup and 'lineBuffer' not in lineGroup:
                    toLineBuffer = []
                    for line in lineGroup['singleLine']:
                        toLineBuffer.append(line['pointA'])
                        toLineBuffer.append(line['pointB'])
                    lineGroup['lineBuffer'] = toLineBuffer
                
                if 'lineBuffer' in lineGroup:
                    tempCoords = [get_line_vertex(idx,verts,mat) for idx in lineGroup['lineBuffer']]
                    lineGroup['coordBuffer'] = tempCoords

            coords = []            
            coords = lineGroup['coordBuffer']

            ### line weight group setup
            tempWeights = []
            if lineGroup.lineWeightGroup is not "":
                vertexGroup = myobj.vertex_groups[lineGroup.lineWeightGroup]
                for idx in lineGroup['lineBuffer']:
                    tempWeights.append(vertexGroup.weight(idx))
            else:
                tempWeights = [1.0] * len(lineGroup['lineBuffer'])

            

            if drawHidden == True:
                # Invert The Depth test for hidden lines
                bgl.glDepthFunc(bgl.GL_GREATER)
                hiddenLineWeight = lineProps.lineHiddenWeight
                
                rawRGB = lineProps.lineHiddenColor
                #undo blenders Default Gamma Correction
                dashRGB = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])

                dashedLineShader.bind()
                dashedLineShader.uniform_float("u_Scale", lineProps.lineHiddenDashScale)
                dashedLineShader.uniform_float("dashSpace", lineProps.lineDashSpace)
                dashedLineShader.uniform_float("Viewport",viewport)
                dashedLineShader.uniform_float("objectMatrix",mat)
                dashedLineShader.uniform_float("thickness",hiddenLineWeight)
                dashedLineShader.uniform_float("screenSpaceDash",lineProps.screenSpaceDashes)
                dashedLineShader.uniform_float("finalColor", (dashRGB[0], dashRGB[1], dashRGB[2], dashRGB[3]))
                dashedLineShader.uniform_float("offset", -offset)
    
                global hiddenBatch3D
                batchKey = myobj.name + lineGroup.name
                if  batchKey not in hiddenBatch3D or recoordFlag:
                    hiddenBatch3D[batchKey] = batch_for_shader(dashedLineShader,'LINES',{"pos":coords}) 
                if sceneProps.is_render_draw:
                    batchHidden = batch_for_shader(dashedLineShader,'LINES',{"pos":coords}) 
                else:
                    batchHidden = hiddenBatch3D[batchKey]

                batchHidden.program_set(dashedLineShader)
                batchHidden.draw()

                bgl.glDepthFunc(bgl.GL_LESS)
                gpu.shader.unbind()          
 
            if lineProps.lineDrawDashed:
                dashedLineShader.bind()
                dashedLineShader.uniform_float("u_Scale", lineProps.lineHiddenDashScale)
                dashedLineShader.uniform_float("dashSpace", lineProps.lineDashSpace)
                dashedLineShader.uniform_float("Viewport",viewport)
                dashedLineShader.uniform_float("objectMatrix",mat)
                dashedLineShader.uniform_float("thickness",lineWeight)
                dashedLineShader.uniform_float("screenSpaceDash",lineProps.screenSpaceDashes)
                dashedLineShader.uniform_float("finalColor",  (rgb[0], rgb[1], rgb[2], rgb[3]))
                dashedLineShader.uniform_float("offset", -offset)

            
                global dashedBatch3D
                batchKey = myobj.name + lineGroup.name
                if batchKey not in dashedBatch3D or recoordFlag:
                    dashedBatch3D[batchKey] = batch_for_shader(dashedLineShader,'LINES',{"pos":coords}) 
                if sceneProps.is_render_draw:
                    batchDashed = batch_for_shader(dashedLineShader,'LINES',{"pos":coords}) 
                else:
                    batchDashed = dashedBatch3D[batchKey]

                batchDashed.program_set(dashedLineShader)
                batchDashed.draw()

            else:
                lineGroupShader.bind()
                lineGroupShader.uniform_float("Viewport",viewport)
                lineGroupShader.uniform_float("objectMatrix",mat)
                lineGroupShader.uniform_float("thickness",lineWeight)
                lineGroupShader.uniform_float("extension",lineGroup.lineOverExtension)
                lineGroupShader.uniform_float("weightInfluence",lineGroup.weightGroupInfluence)
                lineGroupShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
                lineGroupShader.uniform_float("zOffset", -offset)
                
                #colors = [(rgb[0], rgb[1], rgb[2], rgb[3]) for coord in range(len(coords))]

                global lineBatch3D
                batchKey = myobj.name + lineGroup.name
                if batchKey not in lineBatch3D or recoordFlag or myobj.mode == 'WEIGHT_PAINT':
                    lineBatch3D[batchKey] = batch_for_shader(lineGroupShader, 'LINES', {"pos": coords,"weight":tempWeights})
                    batch3d = lineBatch3D[batchKey]
                if sceneProps.is_render_draw:
                    batch3d = batch_for_shader(lineGroupShader, 'LINES', {"pos": coords,"weight":tempWeights})
                else:
                    batch3d = lineBatch3D[batchKey]

                if rgb[3] == 1:
                    bgl.glBlendFunc(bgl.GL_SRC_ALPHA,bgl.GL_ONE_MINUS_SRC_ALPHA)
                    bgl.glDepthMask(True)
                    lineGroupShader.uniform_float("depthPass",True)
                    batch3d.program_set(lineGroupShader)
                    batch3d.draw()


                if sceneProps.is_render_draw:
                    bgl.glBlendFunc(bgl.GL_SRC_ALPHA,bgl.GL_ONE_MINUS_SRC_ALPHA)
                    #bgl.glBlendEquation(bgl.GL_FUNC_ADD)
                    bgl.glBlendEquation(bgl.GL_MAX)
                
                if sceneProps.is_vector_draw:
                    svg_shaders.svg_line_shader(lineGroup, coords, lineWeight, rgb, svg, mat=mat)

                bgl.glDepthMask(False)
                lineGroupShader.uniform_float("depthPass",False)
                batch3d.program_set(lineGroupShader)
                batch3d.draw()


                gpu.shader.unbind()
    
    gpu.shader.unbind()
    bgl.glBlendFunc(bgl.GL_SRC_ALPHA,bgl.GL_ONE_MINUS_SRC_ALPHA)
    bgl.glBlendEquation(bgl.GL_FUNC_ADD)
    bgl.glDisable(bgl.GL_DEPTH_TEST)
    bgl.glDepthMask(True)

def draw_annotation(context, myobj, annotationGen, mat, svg=None):
    scene = context.scene
    bgl.glEnable(bgl.GL_MULTISAMPLE)
    bgl.glEnable(bgl.GL_BLEND)

    bgl.glDepthMask(False)
    sceneProps = scene.MeasureItArchProps

    if sceneProps.is_render_draw:
        viewport = [context.scene.render.resolution_x,context.scene.render.resolution_y]
    else:
        viewport = [context.area.width,context.area.height]
    

    for annotation in annotationGen.annotations:
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

        if annotation.visibleInView is None or annotation.visibleInView.name == context.scene.camera.data.name:
            inView = True        
        else:
            inView = False    

        if annotation.visible and annotationProps.visible and inView:
            lineWeight = annotationProps.lineWeight
            rawRGB = annotationProps.color
            #undo blenders Default Gamma Correction
            rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])

            pointShader.bind()
            pointShader.uniform_float("Viewport",viewport)
            pointShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
            pointShader.uniform_float("thickness", lineWeight)
            pointShader.uniform_float("depthPass", False)
            pointShader.uniform_float("offset", -0.001)
            gpu.shader.unbind()

            lineShader.bind()
            lineShader.uniform_float("Viewport",viewport)
            lineShader.uniform_float("thickness",lineWeight)
            lineShader.uniform_float("offset", -0.001)
            lineShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))

            # Get Points
            deleteFlag = False
            try:
                p1local = get_mesh_vertex(myobj,annotation.annotationAnchor,annotationProps.evalMods)
                p1 = get_point(p1local, myobj,mat)
            except IndexError: 
                deleteFlag = True

            if deleteFlag:
                idx = 0
                for anno in annotationGen.annotations:
                    if annotation == anno:
                        annotationGen.annotations.remove(idx)
                        return
                    idx += 1




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
            
            # Some Backwards Compatibility for annotations
            if annotation.textFields[0].text == "" and annotation.name == "":
                annotation.textFields[0].text = annotation.text
                annotation.name = annotation.text

            for textField in annotation.textFields:
                textcard = generate_text_card(context,textField,annotationProps,annotation.annotationRotation,(0,0,0))
                yoff = (Vector(textcard[1] - textcard[0]).normalized())
                heightOffset = (textcard[1] - textcard[0]) + yoff*0.05
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
                if annotationProps.textPosition == 'T':
                    coords.append(textcard[3])
                    pointcoords = [p2]
                elif annotationProps.textPosition == 'B':
                    coords.append(textcard[2])
                    pointcoords = [p2]

                batch3d = batch_for_shader(lineShader, 'LINES', {"pos": coords})
                batch3d.program_set(lineShader)
                batch3d.draw()
                gpu.shader.unbind()
                
                # Again This is Super Lazy, gotta write up a shader that handles
                # Mitered thick lines, but for now this works.
                if annotationProps.textPosition == 'T' or annotationProps.textPosition == 'B':
                    batch3d = batch_for_shader(pointShader, 'POINTS', {"pos": pointcoords})
                    batch3d.program_set(pointShader)
                    batch3d.draw()
            
            # Draw Line Endcaps
            if endcap == 'D':
                pointShader.bind()
                pointShader.uniform_float("Viewport",viewport)
                pointShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
                pointShader.uniform_float("thickness", endcapSize)
                pointShader.uniform_float("depthPass", False)
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

                bgl.glDisable(bgl.GL_POLYGON_SMOOTH)
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
    normalizedDeviceUVs= [(-1.3,-1.3),(-1.3,1.3),(1.3,1.3),(1.3,-1.3)]

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
        texArray = bgl.Buffer(bgl.GL_INT,[1])
        bgl.glGenTextures(1,texArray)

        bgl.glActiveTexture(bgl.GL_TEXTURE0)
        bgl.glBindTexture(bgl.GL_TEXTURE_2D, texArray[0])

        bgl.glTexParameteri(bgl.GL_TEXTURE_2D, bgl.GL_TEXTURE_WRAP_S, bgl.GL_CLAMP_TO_BORDER)
        bgl.glTexParameteri(bgl.GL_TEXTURE_2D, bgl.GL_TEXTURE_WRAP_T, bgl.GL_CLAMP_TO_BORDER)
        bgl.glTexParameteri(bgl.GL_TEXTURE_2D, bgl.GL_TEXTURE_MIN_FILTER, bgl.GL_LINEAR)

        tex = bgl.Buffer(bgl.GL_BYTE, dim, np.asarray(textobj['texture'], dtype=np.uint8))
        bgl.glTexImage2D(bgl.GL_TEXTURE_2D, 0, bgl.GL_RGBA, width, height, 0, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, tex)
       

        textobj.texture_updated=False
     
    # Draw Shader
    textShader.bind()
    textShader.uniform_float("image", 0)
    batch.draw(textShader)
    gpu.shader.unbind()

def generate_end_caps(context,item,capType,capSize,pos,userOffsetVector,midpoint,posflag,flipCaps):
    capCoords = []
    filledCoords = []
    size = capSize/100
    distVector = Vector(pos-Vector(midpoint)).normalized()
    norm = distVector.cross(userOffsetVector).normalized()
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
def format_distance(fmt, value, factor=1,isArea=False):
    s_code = "\u00b2"  # Superscript two THIS IS LEGACY (but being kept for when Area Measurements are re-implimented)
    hide_units = bpy.context.scene.measureit_arch_hide_units # Also Legacy, Could be re-implimented... Requested now, should re-impliment

    # Get Scene Unit Settings
    scaleFactor = bpy.context.scene.unit_settings.scale_length
    unit_system = bpy.context.scene.unit_settings.system
    unit_length = bpy.context.scene.unit_settings.length_unit
    seperate_units = bpy.context.scene.unit_settings.use_separate

    toInches = 39.3700787401574887
    inPerFoot = 11.999

    if isArea:
        toInches = 1550
        inPerFoot = 143.999

    value *= scaleFactor

    # Imperial Formating
    if unit_system == "IMPERIAL":
        base = int(bpy.context.scene.measureit_arch_imperial_precision)
        decInches = value * toInches
        
        # Seperate ft and inches
        # Unless Inches are the specified Length Unit
        if unit_length != 'INCHES':
            feet = floor(decInches/inPerFoot)
            decInches -= feet*inPerFoot
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
        if inches == 12:
            feet += 1
            inches = 0

        if inches !=0:
            inchesString = str(inches)
            if frac != 0: inchesString += "-"
            else: inchesString += "\""
        else: inchesString = ""

        if feet != 0:
            feetString = str(feet) + "' "
        else: feetString = ""

        if frac != 0:
            fracString = str(frac) + "/" + str(base) +"\""
        else: fracString = ""

        if not isArea:
            tx_dist = feetString + inchesString + fracString
        else:
            tx_dist = str(fmt % (value*toInches/inPerFoot)) + " sq. ft."
    

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
        if isArea:
            tx_dist += s_code
    else:
        tx_dist = fmt % value


    return tx_dist


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
    verts=[]
    coord = Vector((0,0,0))
    bm = bmesh.new()

    if myobj.type == 'MESH':
        # Get Vertices
        verts = myobj.data.vertices
        if myobj.mode == 'EDIT': # From Edit Mesh
            bm = bmesh.from_edit_mesh(myobj.data)
            verts = bm.verts
        else:
            eval_res = sceneProps.eval_mods
            if (eval_res or evalMods) and check_mods(myobj): # From Evaluated Deps Graph
                bm.from_object(myobj,bpy.context.view_layer.depsgraph,deform=True)
                bm.verts.ensure_lookup_table()
                verts= bm.verts               
        # Get Co-ordinate for Index in Vertices
        if idx < len(verts):
            coord = verts[idx].co
        else:
            if idx != 9999999:
                raise IndexError
            coord = myobj.location
            
    # free Bmesh and return
    return coord
        

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