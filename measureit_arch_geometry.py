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

from textwrap import fill
import bpy
import gpu
import bgl
import blf
import bmesh
import math
import numpy as np
import svgwrite
import time

from bpy_extras import mesh_utils
from datetime import datetime
from gpu_extras.batch import batch_for_shader
from math import fabs, degrees, radians, sin, pi
from mathutils import Vector, Matrix, Euler, Quaternion
from mathutils.geometry import area_tri
from sys import getrecursionlimit, setrecursionlimit

from . import svg_shaders
from . import dxf_shaders
from .shaders import *
from .measureit_arch_baseclass import TextField, recalc_dimWrapper_index
from .measureit_arch_units import BU_TO_INCHES, format_distance, format_angle, \
    format_area
from .measureit_arch_utils import get_rv3d, get_view, interpolate3d, get_camera_z_dist, get_camera_z, recursionlimit,\
    OpenGL_Settings, get_sv3d, safe_name, _imp_scales_dict, _metric_scales_dict, _cad_col_dict, get_resolution, get_scale

lastMode = {}
lineBatch3D = {}
dashedBatch3D = {}
hiddenBatch3D = {}

# define Shaders

# Alter which frag shaders are used depending on the blender version
# https://wiki.blender.org/wiki/Reference/Release_Notes/2.83/Python_API
# https://developer.blender.org/T74139

if bpy.app.version > (2, 83, 0):
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


def get_dim_tag(self, obj):
    dimGen = obj.DimensionGenerator
    itemType = self.itemType
    idx = 0
    for wrap in dimGen.wrapper:
        try:
            if itemType == wrap.itemType:
                if self == eval('dimGen.' + itemType + '[wrap.itemIndex]'):
                    return idx
        except IndexError:
            print('Index Error in get_dim_tag')
            return idx
        idx += 1
    return idx


def clear_batches():
    lineBatch3D.clear()
    dashedBatch3D.clear()
    hiddenBatch3D.clear()


def update_text(textobj, props, context, fields=[]):
    scene = context.scene
    sceneProps = scene.MeasureItArchProps

    textFields = textobj.textFields
    if len(fields) != 0:
        textFields = fields

    for textField in textFields:
        if textobj.text_updated or props.text_updated or sceneProps.is_render_draw:
            textField.text_updated = True

        if textField.text_updated or sceneProps.text_updated:
            # Get textitem Properties
            rgb = rgb_gamma_correct(props.color)
            size = 20
            resolution = get_resolution()

            # Get Font Id
            badfonts = [None]
            if 'Bfont Regular' in bpy.data.fonts or 'Bfont' in bpy.data.fonts:
                try:
                    badfonts.append(bpy.data.fonts['Bfont Regular'])
                    badfonts.append(bpy.data.fonts['Bfont'])
                except KeyError:
                    pass
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
            lines = text.split('\n')


            # Calculate Optimal Dimensions for Text Texture.
            line_height =  blf.dimensions(font_id, 'Tpg')[1] *1.2

            fheight = 0
            fwidth = 0
            for line in lines:
                fheight += line_height
                text = line
                if props.all_caps:
                    text = line.upper()
                line_width = blf.dimensions(font_id, text + '  ')[0]
                if line_width > fwidth:
                    fwidth = line_width

            width = math.ceil(fwidth)
            height = math.ceil(fheight)

            # Save Texture size to textobj Properties
            textField.textHeight = height
            textField.textWidth = width

            # Start Offscreen Draw
            if width != 0 and height != 0:
                textOffscreen = gpu.types.GPUOffScreen(width, height)

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

                    idx = 1
                    y_offset = height - line_height * 0.8
                    for line in lines:
                        blf.position(font_id, 0, y_offset, 0)
                        text = line
                        if props.all_caps:
                            text = line.upper()
                        blf.draw(font_id, text)
                        idx += 1
                        y_offset -= line_height * 1.1

                    # Read Offscreen To Texture Buffer
                    texture_buffer = bgl.Buffer(
                        bgl.GL_BYTE, width * height * 4)
                    bgl.glReadBuffer(bgl.GL_COLOR_ATTACHMENT0)
                    bgl.glReadPixels(0, 0, width, height, bgl.GL_RGBA,
                                     bgl.GL_UNSIGNED_BYTE, texture_buffer)

                    # Write Texture Buffer to ID Property as List
                    if 'texture' in textField:
                        del textField['texture']
                    textField['texture'] = texture_buffer
                    textField.text_updated = False
                    textField.texture_updated = True

                    # generate image datablock from buffer for debug preview
                    # ONLY USE FOR DEBUG. SERIOUSLY SLOWS PREFORMANCE
                    if sceneProps.measureit_arch_debug_text:
                        if not str('test') in bpy.data.images:
                            bpy.data.images.new(str('test'), width, height)
                        image = bpy.data.images[str('test')]
                        image.scale(width, height)
                        image.pixels = [v / 255 for v in texture_buffer]
    textobj.text_updated = False


def draw_sheet_views(context, myobj, sheetGen, sheet_view, mat, svg=None, dxf=None):

    pass

def get_hatch_name(mat_name, hatch, obj):
    if hatch.use_object_pattern:
        hatch_name = obj.MeasureItArchProps.obj_hatch_pattern.name
    else:
        hatch_name = hatch.pattern.name

    name = mat_name + '_' + hatch_name

    #Check valid name
    if " " in name:
        name = name.replace(" ", "_")

    return name


def draw_material_hatches(context, myobj, mat, svg=None, dxf=None, is_instance_draw = False):
    sceneProps = context.scene.MeasureItArchProps
    view = get_view()
    scale = get_scale()

    if sceneProps.is_vector_draw:
        try:
            svg_obj = svg.add(svg.g(id=myobj.name))
        except UnicodeDecodeError:
            svg_obj = svg.add(svg.g(id="BAD NAME AHHH"))


    if not myobj.hide_render:

        bm = bmesh.new()
        # polys = mesh.polygons
        if myobj.type == 'MESH':

            if myobj.mode == 'OBJECT':
                bm.from_object(myobj, bpy.context.view_layer.depsgraph)
                #depsgraph = bpy.context.view_layer.depsgraph
                #eval_obj = myobj.evaluated_get(depsgraph)
                #temp_mesh = eval_obj.data
                #bm.from_mesh(temp_mesh)
            else:
                mesh = myobj.data
                bm = bmesh.from_edit_mesh(mesh)

        if myobj.type == 'CURVE' and is_instance_draw:
            return

        if myobj.type == 'CURVE':
            depsgraph = bpy.context.evaluated_depsgraph_get()
            eval_obj = myobj.evaluated_get(depsgraph)

            mesh =  bpy.data.meshes.new_from_object(eval_obj, depsgraph =  bpy.context.evaluated_depsgraph_get())

            try:
                bm.from_mesh(mesh)
            except AttributeError:
                print('No Mesh Data for Obj: {}'.format(myobj.name))

            #bpy.data.meshes.remove(mesh)


        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        faces = bm.faces

        faces = z_order_faces(faces, myobj)

        matSlots = myobj.material_slots
        objMaterials = []
        hatchDict = {}

        #Write Patterns for all hatches on the object
        for slot in matSlots:
            if slot.material is None:
                continue
            hatch = slot.material.Hatch

            objMaterials.append(slot.material)

            pattern = hatch.pattern
            size = hatch.patternSize * ( (1/get_scale()) * BU_TO_INCHES * get_resolution())
            rotation = math.degrees(hatch.patternRot)

            if hatch.use_object_pattern:
                pattern = myobj.MeasureItArchProps.obj_hatch_pattern
                size = myobj.MeasureItArchProps.obj_patternSize * ( (1/get_scale()) * BU_TO_INCHES * get_resolution())
                rotation = math.degrees(myobj.MeasureItArchProps.obj_patternRot)

            if pattern is not None:
                name = get_hatch_name(slot.material.name, hatch, myobj)
                objs = pattern.objects
                weight = hatch.patternWeight
                scale = get_scale()
                ortho_scale = view.camera.data.ortho_scale
               
                color = hatch.line_color
                

                if sceneProps.is_vector_draw:
                    pattern = svgwrite.pattern.Pattern(width="{}px".format(size), height="{}px".format(size), id=name, patternUnits="userSpaceOnUse", **{
                        'patternTransform': 'rotate({} {} {})'.format(
                            rotation, 0, 0
                        )})
                    svg_shaders.svg_line_pattern_shader(
                        pattern, svg, objs, weight, color, size)
                    svg.defs.add(pattern)


        for face in faces:
            matIdx = face.material_index
            try:
                faceMat = objMaterials[matIdx]
            except:
                continue

            # Check For Material Override
            hatch = faceMat.Hatch
            if context.view_layer.material_override != None:
                print('HAS OVERRIDE')
                hatch = context.view_layer.material_override.Hatch

            pattern = hatch.pattern
            if hatch.use_object_pattern:
                pattern = myobj.MeasureItArchProps.obj_hatch_pattern

            if hatch.visible :

                if hatch.use_object_color:
                    fillRGB = rgb_gamma_correct(myobj.color)
                else:
                    fillRGB = rgb_gamma_correct(hatch.fill_color)
                lineRGB = rgb_gamma_correct(hatch.line_color)
                weight = hatch.lineWeight
                fillURL = ''
                if pattern is not None:
                    name = get_hatch_name(faceMat.name,hatch,myobj)
                    fillURL = 'url(#{})'.format(name)

                coords = []

                for vert in face.verts:
                    coords.append(mat @ vert.co)

                try:
                    if sceneProps.is_vector_draw:
                        svg_hatch = svg_obj.add(svg.g(id=slot.material.name))
                        svg_shaders.svg_poly_fill_shader(
                            hatch, coords, fillRGB, svg, parent=svg_hatch,
                            line_color=lineRGB, lineWeight=weight, fillURL=fillURL)
                except AttributeError:
                    print('Error Drawing Hatch, Maybe Empty Material Slot?')

                if sceneProps.is_dxf_draw:
                    dxf_shaders.dxf_hatch_shader(hatch,coords,dxf,faceMat)


def draw_alignedDimension(context, myobj, measureGen, dim, mat=None, svg=None, dxf=None):

    scene = context.scene
    sceneProps = scene.MeasureItArchProps

    dimProps = get_style(dim,'alignedDimensions')

    # Enable GL Settings


    lineWeight = dimProps.lineWeight
    # check all visibility conditions
    with OpenGL_Settings(dimProps):
        if not check_vis(dim, dimProps):
            return

        # Obj Properties
        scene = context.scene
        rgb = get_color(dimProps.color, myobj, is_active=dim.is_active)

        # Define Caps as a tuple of capA and capB to reduce code duplications
        caps = (dimProps.endcapA, dimProps.endcapB)
        capSize = dimProps.endcapSize

        offset = dimProps.dimOffset
        if dim.uses_style:
            offset += dim.tweakOffset

        geoOffset = dimProps.dimLeaderOffset

        # get points positions from indicies
        aMatrix = dim.dimObjectA.matrix_world
        bMatrix = dim.dimObjectB.matrix_world

        if mat is not None:
            aMatrix = mat @ aMatrix
            bMatrix = mat @ bMatrix

        # get points positions from indicies
        p1Local = None
        p2Local = None

        try:
            p1Local = get_mesh_vertex(
                dim.dimObjectA, dim.dimPointA, dimProps.evalMods)
            p2Local = get_mesh_vertex(
                dim.dimObjectB, dim.dimPointB, dimProps.evalMods)
        except IndexError:
            print('point excepted for ' + dim.name + ' on ' + myobj.name)
            dimGen = myobj.DimensionGenerator
            try:
                wrapTag = get_dim_tag(dim, myobj)
                wrapper = dimGen.wrapper[wrapTag]
                tag = wrapper.itemIndex
                dimGen.alignedDimensions.remove(tag)
                dimGen.wrapper.remove(wrapTag)
            except IndexError:
                dimGen.alignedDimensions.remove(0)

            recalc_dimWrapper_index(None, context)
            return

        p1 = get_point(p1Local, aMatrix)
        p2 = get_point(p2Local, bMatrix)

        # check dominant Axis
        sortedPoints = sortPoints(p1, p2)
        p1 = sortedPoints[0]
        p2 = sortedPoints[1]

        # calculate distance & Midpoint
        distVector = Vector(p1) - Vector(p2)
        dist = distVector.length
        midpoint = interpolate3d(p1, p2, fabs(dist / 2))
        normDistVector = distVector.normalized()

        # Compute offset vector from face normal and user input
        rotation = dimProps.dimRotation
        rotationMatrix = Matrix.Rotation(rotation, 4, normDistVector)
        selectedNormal = Vector(select_normal(
            myobj, dim, normDistVector, midpoint, dimProps))

        userOffsetVector = rotationMatrix @ selectedNormal
        offsetDistance = userOffsetVector * offset
        geoOffsetDistance = offsetDistance.normalized() * geoOffset

        if offsetDistance < geoOffsetDistance:
            offsetDistance = geoOffsetDistance



        # Define Lines
        leadStartA = Vector(p1) + geoOffsetDistance
        leadEndA = Vector(p1) + offsetDistance + \
            cap_extension(offsetDistance, capSize, dimProps.endcapArrowAngle)

        leadStartB = Vector(p2) + geoOffsetDistance
        leadEndB = Vector(p2) + offsetDistance + \
            cap_extension(offsetDistance, capSize, dimProps.endcapArrowAngle)

        dimLineStart = Vector(p1) + offsetDistance
        dimLineEnd = Vector(p2) + offsetDistance
        textLoc = interpolate3d(dimLineStart, dimLineEnd, fabs(dist / 2))

        # Set Gizmo Props
        dim.gizLoc = textLoc
        dim.gizRotDir = userOffsetVector
        dim['length'] = dist

        origin = Vector(textLoc)

        placementResults = setup_dim_text(myobj,dim,dimProps,dist,origin,distVector,offsetDistance)
        flipCaps = placementResults[0]
        dimLineExtension = placementResults[1]
        origin = placementResults[2]

        # Add the Extension to the dimension line
        dimLineVec = dimLineStart - dimLineEnd
        dimLineVec.normalize()
        dimLineEndCoord = dimLineEnd - dimLineVec * dimLineExtension
        dimLineStartCoord = dimLineStart + dimLineVec * dimLineExtension

        # Collect coords and endcaps
        coords = [leadStartA, leadEndA, leadStartB,
                leadEndB, dimLineStartCoord, dimLineEndCoord]
        filledCoords = []
        pos = (dimLineStart, dimLineEnd)
        for i, cap in enumerate(caps):
            capCoords = generate_end_caps(
                context, dimProps, cap, capSize, pos[i], userOffsetVector, textLoc, i, flipCaps)
            for coord in capCoords[0]:
                coords.append(coord)
            for filledCoord in capCoords[1]:
                filledCoords.append(filledCoord)

        # Filled Coords Call
        if len(filledCoords) != 0:
            draw_filled_coords(filledCoords, rgb)

        # Line Shader Calls

        draw_lines(lineWeight, rgb, coords, twoPass=True)

        if sceneProps.is_vector_draw:
            svg_dim = svg.add(svg.g(id=dim.name))
            svg_shaders.svg_line_shader(
                dim, dimProps, coords, lineWeight, rgb, svg, parent=svg_dim)
            svg_shaders.svg_fill_shader(
                dim, filledCoords, rgb, svg, parent=svg_dim)
            for textField in dim.textFields:
                textcard = textField['textcard']
                svg_shaders.svg_text_shader(
                    dim, dimProps, textField.text, origin, textcard, rgb, svg, parent=svg_dim)

        if sceneProps.is_dxf_draw:
            dxf_shaders.dxf_aligned_dimension(dim, dimProps, p1, p2, origin, dxf)



def draw_boundsDimension(context, myobj, measureGen, dim, mat, svg=None, dxf=None):
    sceneProps = context.scene.MeasureItArchProps

    dimProps = get_style(dim,'alignedDimensions')


    with OpenGL_Settings(dimProps):

        lineWeight = dimProps.lineWeight

        if not check_vis(dim, dimProps):
            return

        # Obj Properties
        # For Collection Bounding Box
        if dim.dimCollection is not None:
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

                else:  # otherwise get its points and calc its AABB directly

                    try:
                        if (myobj.matrix_world.to_quaternion() != Quaternion(dim[rotStr]) or
                            myobj.location != Vector(dim[locStr]) or
                                myobj.scale != Vector(dim[scaleStr])):

                            obverts = get_mesh_vertices(myobj)
                            worldObverts = [myobj.matrix_world @
                                            coord for coord in obverts]
                            maxX, minX, maxY, minY, maxZ, minZ = get_axis_aligned_bounds(
                                worldObverts)
                            dim[boundsStr] = [maxX, minX, maxY, minY, maxZ, minZ]
                            dim[rotStr] = myobj.matrix_world.to_quaternion()
                            dim[locStr] = myobj.location
                            dim[scaleStr] = myobj.scale
                        else:
                            maxX, minX, maxY, minY, maxZ, minZ = dim[boundsStr]
                    except KeyError:
                        obverts = get_mesh_vertices(myobj)
                        worldObverts = [myobj.matrix_world @
                                        coord for coord in obverts]
                        maxX, minX, maxY, minY, maxZ, minZ = get_axis_aligned_bounds(
                            worldObverts)
                        dim[boundsStr] = [maxX, minX, maxY, minY, maxZ, minZ]
                        dim[rotStr] = myobj.matrix_world.to_quaternion()
                        dim[locStr] = myobj.location

                        dim[scaleStr] = myobj.scale

                    coords.append(Vector((maxX, maxY, maxZ)))
                    coords.append(Vector((minX, minY, minZ)))

            # Get the axis aligned bounding coords for that set of coords
            maxX, minX, maxY, minY, maxZ, minZ = get_axis_aligned_bounds(coords)

            # distX = maxX - minX
            # distY = maxY - minY
            # distZ = maxZ - minZ

            p0 = Vector((minX, minY, minZ))
            p1 = Vector((minX, minY, maxZ))
            p2 = Vector((minX, maxY, maxZ))
            p3 = Vector((minX, maxY, minZ))
            p4 = Vector((maxX, minY, minZ))
            p5 = Vector((maxX, minY, maxZ))
            p6 = Vector((maxX, maxY, maxZ))
            p7 = Vector((maxX, maxY, minZ))

            bounds = [p0, p1, p2, p3, p4, p5, p6, p7]
            # print ("X: " + str(distX) + ", Y: " + str(distY) + ", Z: " + str(distZ))

        # Single object bounding Box
        else:
            if not dim.calcAxisAligned:
                bounds = myobj.bound_box
                tempbounds = []
                for bound in bounds:
                    tempbounds.append(myobj.matrix_world @ Vector(bound))
                bounds = tempbounds

            else:  # Calc AABB when rotation changes
                try:
                    if myobj.matrix_world.to_quaternion() != Quaternion(dim['lastRot']):
                        obverts = get_mesh_vertices(myobj)
                        worldObverts = [myobj.matrix_world @
                                        coord for coord in obverts]
                        maxX, minX, maxY, minY, maxZ, minZ = get_axis_aligned_bounds(
                            worldObverts)
                        dim['bounds'] = [maxX, minX, maxY, minY, maxZ, minZ]
                        dim['lastRot'] = myobj.matrix_world.to_quaternion()
                    else:
                        maxX, minX, maxY, minY, maxZ, minZ = dim['bounds']
                except KeyError:
                    obverts = get_mesh_vertices(myobj)
                    worldObverts = [myobj.matrix_world @
                                    coord for coord in obverts]
                    maxX, minX, maxY, minY, maxZ, minZ = get_axis_aligned_bounds(
                        worldObverts)
                    dim['bounds'] = [maxX, minX, maxY, minY, maxZ, minZ]
                    dim['lastRot'] = myobj.matrix_world.to_quaternion()

                # distX = maxX - minX
                # distY = maxY - minY
                # distZ = maxZ - minZ

                p0 = Vector((minX, minY, minZ))
                p1 = Vector((minX, minY, maxZ))
                p2 = Vector((minX, maxY, maxZ))
                p3 = Vector((minX, maxY, minZ))
                p4 = Vector((maxX, minY, minZ))
                p5 = Vector((maxX, minY, maxZ))
                p6 = Vector((maxX, maxY, maxZ))
                p7 = Vector((maxX, maxY, minZ))

                bounds = [p0, p1, p2, p3, p4, p5, p6, p7]

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
        zpairs = [[0, 1],
                [2, 3],
                [4, 5],
                [6, 7]]

        xpairs = [[0, 4],
                [1, 5],
                [2, 6],
                [3, 7]]

        ypairs = [[0, 3],
                [1, 2],
                [4, 7],
                [5, 6]]

        # measureAxis = []
        # scene = context.scene
        rgb = get_color(dimProps.color, myobj, is_active=dim.is_active)

        # Define Caps as a tuple of capA and capB to reduce code duplications
        caps = (dimProps.endcapA, dimProps.endcapB)
        capSize = dimProps.endcapSize

        offset = dimProps.dimOffset
        if dim.uses_style:
            offset += dim.tweakOffset

        geoOffset = dim.dimLeaderOffset

        # get view vector
        i = Vector((1, 0, 0))  # X Unit Vector
        j = Vector((0, 1, 0))  # Y Unit Vector
        k = Vector((0, 0, 1))  # Z Unit Vector

        viewVec = Vector((0, 0, 0))  # dummy vector to avoid errors

        if not sceneProps.is_render_draw:
            viewRot = context.area.spaces[0].region_3d.view_rotation
            viewVec = k.copy()
            viewVec.rotate(viewRot)

        bestPairs = [xpairs[2], ypairs[1], zpairs[0]]

        # establish measure loop
        # this runs through the X, Y and Z axis
        idx = 0
        placementVec = [j, -i, -i]
        for axis in dim.drawAxis:
            if axis:
                # get points
                p1 = Vector(bounds[bestPairs[idx][0]])
                p2 = Vector(bounds[bestPairs[idx][1]])

                # check dominant Axis
                sortedPoints = sortPoints(p1, p2)
                p1 = sortedPoints[0]
                p2 = sortedPoints[1]

                # calculate distance & MidpointGY
                distVector = Vector(p1) - Vector(p2)
                dist = distVector.length
                midpoint = interpolate3d(p1, p2, fabs(dist / 2))
                normDistVector = distVector.normalized()

                # Compute offset vector from face normal and user input
                axisViewVec = viewVec.copy()
                axisViewVec[idx] = 0
                rotationMatrix = Matrix.Rotation(
                    dim.dimRotation, 4, normDistVector)

                selectedNormal = placementVec[idx]

                if dim.dimCollection is None and not dim.calcAxisAligned:
                    rot = myobj.matrix_world.to_quaternion()
                    selectedNormal.rotate(rot)

                userOffsetVector = rotationMatrix @ selectedNormal
                offsetDistance = userOffsetVector * offset
                geoOffsetDistance = offsetDistance.normalized() * geoOffset

                if offsetDistance < geoOffsetDistance:
                    offsetDistance = geoOffsetDistance

                # Set Gizmo Props
                dim.gizLoc = Vector(midpoint) + \
                    (userOffsetVector * dim.dimOffset)
                dim.gizRotDir = userOffsetVector

                # Define Lines
                leadStartA = Vector(p1) + geoOffsetDistance
                leadEndA = Vector(p1) + offsetDistance + cap_extension(
                    offsetDistance, capSize, dimProps.endcapArrowAngle)

                leadStartB = Vector(p2) + geoOffsetDistance
                leadEndB = Vector(p2) + offsetDistance + cap_extension(
                    offsetDistance, capSize, dimProps.endcapArrowAngle)

                dimLineStart = Vector(p1) + offsetDistance
                dimLineEnd = Vector(p2) + offsetDistance
                textLoc = interpolate3d(
                    dimLineStart, dimLineEnd, fabs(dist / 2))
                origin = Vector(textLoc)

                # i,j,k as card axis
                i = Vector((1, 0, 0))
                j = Vector((0, 1, 0))
                k = Vector((0, 0, 1))

                # Check for text field
                dimText = dim.textFields[idx]

                # format text and update if necessary
                distanceText = format_distance(dist,dim=dim)
                if dimText.text != distanceText:
                    dimText.text = distanceText
                    dimText.text_updated = True

                placementResults = dim_text_placement(
                    dim, dimProps, origin, dist, distVector, offsetDistance, capSize, textField = dimText)
                flipCaps = placementResults[0]
                dimLineExtension = placementResults[1]
                origin = placementResults[2]

                # Add the Extension to the dimension line
                dimLineVec = dimLineStart - dimLineEnd
                dimLineVec.normalize()
                dimLineEndCoord = dimLineEnd - dimLineVec * dimLineExtension
                dimLineStartCoord = dimLineStart + dimLineVec * dimLineExtension

                if sceneProps.show_dim_text:
                    square = dimText['textcard']
                    draw_text_3D(context, dimText, dimProps, myobj, square)

                # Collect coords and endcaps
                coords = [leadStartA, leadEndA, leadStartB,
                        leadEndB, dimLineStartCoord, dimLineEndCoord]
                # coords.append((0,0,0))
                # coords.append(axisViewVec)
                filledCoords = []
                pos = (dimLineStart, dimLineEnd)
                i = 0
                for cap in caps:
                    capCoords = generate_end_caps(
                        context, dimProps, cap, capSize, pos[i], userOffsetVector, textLoc, i, flipCaps)
                    i += 1
                    for coord in capCoords[0]:
                        coords.append(coord)
                    for filledCoord in capCoords[1]:
                        filledCoords.append(filledCoord)

                # Keep this out of the loop to avoid extra draw calls
                if len(filledCoords) != 0:
                    draw_filled_coords(filledCoords, rgb)

                # bind shader
                draw_lines(lineWeight, rgb, coords, twoPass=True)

                if sceneProps.is_vector_draw:
                    svg_dim = svg.add(svg.g(id=dim.name))
                    svg_shaders.svg_line_shader(
                        dim, dimProps, coords, lineWeight, rgb, svg, parent=svg_dim)
                    svg_shaders.svg_fill_shader(
                        dim, filledCoords, rgb, svg, parent=svg_dim)
                    svg_shaders.svg_text_shader(
                        dim, dimProps, dimText.text, origin, square, rgb, svg, parent=svg_dim)

            idx += 1



def draw_axisDimension(context, myobj, measureGen, dim, mat, svg=None, dxf=None):

    sceneProps = context.scene.MeasureItArchProps

    dimProps = get_style(dim,'alignedDimensions')

    with OpenGL_Settings(dimProps):

        lineWeight = dimProps.lineWeight

        if not check_vis(dim, dimProps):
            return

        # Get CameraLoc or ViewRot
        if sceneProps.is_render_draw:
            cameraLoc = context.scene.camera.matrix_world.to_translation().normalized()
        else:
            viewRot = context.area.spaces[0].region_3d.view_rotation

        # Obj Properties
        rgb = get_color(dimProps.color, myobj, is_active=dim.is_active)

        axis = dim.dimAxis

        caps = (dimProps.endcapA, dimProps.endcapB)

        offset = dimProps.dimOffset
        if dim.uses_style:
            offset += dim.tweakOffset
        geoOffset = dimProps.dimLeaderOffset

        # get points positions from indicies
        aMatrix = mat
        bMatrix = mat
        if dim.dimObjectB != dim.dimObjectA:
            bMatrix = dim.dimObjectB.matrix_world - dim.dimObjectA.matrix_world + mat

        p1Local = None
        p2Local = None

        try:
            p1Local = get_mesh_vertex(
                dim.dimObjectA, dim.dimPointA, dimProps.evalMods)
            p2Local = get_mesh_vertex(
                dim.dimObjectB, dim.dimPointB, dimProps.evalMods)
        except IndexError:
            print('point excepted for ' + dim.name + ' on ' + myobj.name)
            dimGen = myobj.DimensionGenerator
            wrapTag = get_dim_tag(dim, myobj)
            wrapper = dimGen.wrapper[wrapTag]
            tag = wrapper.itemIndex
            dimGen.axisDimensions.remove(tag)
            dimGen.wrapper.remove(wrapTag)
            recalc_dimWrapper_index(context, dimGen)
            return

        p1 = get_point(p1Local, aMatrix)
        p2 = get_point(p2Local, bMatrix)

        # Sort Points
        sortedPoints = sortPoints(p1, p2)
        p1 = sortedPoints[0]
        p2 = sortedPoints[1]

        # i,j,k as base vectors
        i = Vector((1, 0, 0))
        j = Vector((0, 1, 0))
        k = Vector((0, 0, 1))

        viewPlane = get_view_plane(dim, dimProps)
        viewAxis = get_view_axis(context, dim, dimProps)

        # define axis relatd values
        # basicThreshold = 0.5773
        if axis == 'X':
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
            viewSector = (1, 0, 0)
        elif viewAxis[0] < -xThreshold:
            viewSector = (-1, 0, 0)

        if viewAxis[1] > yThreshold:
            viewSector = (0, 1, 0)
        elif viewAxis[1] < -yThreshold:
            viewSector = (0, -1, 0)

        if viewAxis[2] > zThreshold:
            viewSector = (0, 0, 1)
        elif viewAxis[2] < -zThreshold:
            viewSector = (0, 0, -1)

        # rotate the axis vector if necessary
        if dim.dimAxisObject is not None:
            customMat = dim.dimAxisObject.matrix_world
            rot = customMat.to_quaternion()
            axisVec.rotate(rot)

        # calculate distance by projecting the distance vector onto the axis vector

        alignedDistVector = Vector(p1) - Vector(p2)
        distVector = alignedDistVector.project(axisVec)

        dist = distVector.length
        midpoint = interpolate3d(Vector(p1), Vector(p2), fabs(dist / 2))
        normDistVector = distVector.normalized()

        # Compute offset vector from face normal and user input
        rotationMatrix = Matrix.Rotation(dim.dimRotation, 4, normDistVector)
        selectedNormal = Vector(select_normal(
            myobj, dim, normDistVector, midpoint, dimProps))

        # The Direction of the Dimension Lines
        dirVector = Vector(viewSector).cross(axisVec)
        if dirVector.dot(selectedNormal) < 0:
            dirVector.negate()
        selectedNormal = dirVector.normalized()

        userOffsetVector = rotationMatrix @ selectedNormal
        offsetDistance = userOffsetVector * offset
        geoOffsetDistance = offsetDistance.normalized() * geoOffset

        if offsetDistance < geoOffsetDistance:
            offsetDistance = geoOffsetDistance

        # Set Gizmo Props

        dim.gizRotDir = userOffsetVector

        # Define Lines
        # get the components of p1 & p1 in the direction zvector
        p1Dir = Vector((
            p1[0] * dirVector[0],
            p1[1] * dirVector[1],
            p1[2] * dirVector[2]))
        p2Dir = Vector((
            p2[0] * dirVector[0],
            p2[1] * dirVector[1],
            p2[2] * dirVector[2]))

        domAxis = get_dom_axis(p1Dir)

        if p1Dir[domAxis] >= p2Dir[domAxis]:
            basePoint = p1
            secondPoint = p2
            secondPointAxis = distVector
            alignedDistVector = Vector(p2) - Vector(p1)
        else:
            basePoint = p2
            secondPoint = p1
            secondPointAxis = -distVector
            alignedDistVector = Vector(p1) - Vector(p2)

        # Get the difference between the points in the view axis
        if viewPlane == '99':
            viewAxis = Vector(viewSector)
            if viewAxis[0] < 0 or viewAxis[1] < 0 or viewAxis[2] < 0:
                viewAxis *= -1
        
        vec = -axisVec.cross(dirVector).normalized()
        viewAxisDiff = Vector((
            alignedDistVector[0] * vec[0],
            alignedDistVector[1] * vec[1],
            alignedDistVector[2] * vec[2]))

        dim.gizRotAxis = alignedDistVector

        # Lines
        leadStartA = Vector(basePoint) + geoOffsetDistance
        leadEndA = Vector(basePoint) + offsetDistance + cap_extension(offsetDistance, dimProps.endcapSize, dimProps.endcapArrowAngle)

        leadEndB = leadEndA - Vector(secondPointAxis)
        leadStartB = Vector(secondPoint) -viewAxisDiff  + geoOffsetDistance

        viewDiffStartB = leadStartB
        viewDiffEndB = leadStartB + viewAxisDiff

        dimLineStart = Vector(basePoint) + offsetDistance
        dimLineEnd = dimLineStart - Vector(secondPointAxis)
        textLoc = interpolate3d(dimLineStart, dimLineEnd, fabs(dist / 2))
        origin = Vector(textLoc)

        dim.gizLoc = textLoc
        dim['length'] = dist

        # Setup Text Fields
        placementResults = setup_dim_text(myobj,dim,dimProps,dist,origin,distVector,offsetDistance)
        flipCaps = placementResults[0]
        dimLineExtension = placementResults[1]
        origin = placementResults[2]
        # Add the Extension to the dimension line
        dimLineEndCoord = dimLineEnd - dimLineExtension * secondPointAxis.normalized()
        dimLineStartCoord = dimLineStart + dimLineExtension * secondPointAxis.normalized()



        # Collect coords and endcaps
        coords = [leadStartA, leadEndA, leadStartB, leadEndB,
                dimLineStartCoord, dimLineEndCoord, viewDiffStartB, viewDiffEndB]
        filledCoords = []
        pos = (dimLineStart, dimLineEnd)
        i = 0
        for cap in caps:
            capCoords = generate_end_caps(
                context, dimProps, cap, dimProps.endcapSize, pos[i], userOffsetVector, textLoc, i, flipCaps)
            i += 1
            for coord in capCoords[0]:
                coords.append(coord)
            for filledCoord in capCoords[1]:
                filledCoords.append(filledCoord)

        if len(filledCoords) != 0:
            draw_filled_coords(filledCoords, rgb)

        # bind shader
        draw_lines(lineWeight, rgb, coords, twoPass=True)

        if sceneProps.is_vector_draw:
            svg_dim = svg.add(svg.g(id=dim.name))
            svg_shaders.svg_line_shader(
                dim, dimProps, coords, lineWeight, rgb, svg, parent=svg_dim)
            svg_shaders.svg_fill_shader(
                dim, filledCoords, rgb, svg, parent=svg_dim)
            for textField in dim.textFields:
                textcard = textField['textcard']
                svg_shaders.svg_text_shader(
                    dim, dimProps, textField.text, origin, textcard, rgb, svg, parent=svg_dim)

        if sceneProps.is_dxf_draw:
            dxf_shaders.dxf_axis_dimension(dim, dimProps, p1, p2, origin, dxf)


def draw_angleDimension(context, myobj, DimGen, dim, mat, svg=None, dxf=None):
    dimProps = get_style(dim,'alignedDimensions')
    sceneProps = context.scene.MeasureItArchProps
    with OpenGL_Settings(dimProps):

        if not check_vis(dim, dimProps):
            return

        lineWeight = dimProps.lineWeight

        rgb = get_color(dimProps.color, myobj, is_active=dim.is_active)
        radius = dim.dimRadius

        try:
            p1 = Vector(get_point(get_mesh_vertex(
                myobj, dim.dimPointA, dimProps.evalMods), mat))
            p2 = Vector(get_point(get_mesh_vertex(
                myobj, dim.dimPointB, dimProps.evalMods), mat))
            p3 = Vector(get_point(get_mesh_vertex(
                myobj, dim.dimPointC, dimProps.evalMods), mat))
        except IndexError:
            dimGen = myobj.DimensionGenerator
            wrapTag = get_dim_tag(dim, myobj)
            wrapper = dimGen.wrapper[wrapTag]
            tag = wrapper.itemIndex
            dimGen.angleDimensions.remove(tag)
            dimGen.wrapper.remove(wrapTag)
            recalc_dimWrapper_index(context, dimGen)
            return

        # calc normal to plane defined by points
        vecA = (p1 - p2)
        vecA.normalize()
        vecB = (p3 - p2)
        vecB.normalize()
        norm = vecA.cross(vecB).normalized()

        distVector = vecA - vecB
        dist = distVector.length
        angle = vecA.angle(vecB)
        startVec = vecA.copy()
        endVec = vecB.copy()

        # get Midpoint for Text Placement
        midVec = Vector(interpolate3d(vecA, vecB, (dist / 2)))
        midVec.normalize()
        midPoint = (midVec * radius * 1.05) + p2

        # Check use reflex Angle (reflex angle is an angle between 180 and 360 degrees)
        if dim.reflexAngle:
            angle = radians(360) - angle
            startVec = vecB.copy()
            endVec = vecA.copy()
            midVec.rotate(Quaternion(norm, radians(180)))
            midPoint = Vector((midVec * radius * 1.05) + p2)

        # making it a circle
        numCircleVerts = math.ceil(radius / .2) + int((degrees(angle)) / 2)
        verts = []
        for idx in range(numCircleVerts + 1):
            rotangle = (angle / (numCircleVerts + 1)) * idx
            point = startVec.copy()
            point.rotate(Quaternion(norm, rotangle))
            # point.normalize()
            verts.append(point)

        # Format Angle
        angleText = format_angle(angle)

        # Update if Necessary
        if len(dim.textFields) == 0:
            dim.textFields.add()

        if dim.textFields[0].text != angleText:
            dim.textFields[0].text = angleText
            dim.textFields[0].text_updated = True

        dimText = dim.textFields[0]
        origin = midPoint

        # make text card
        vecX = midVec.cross(norm).normalized()
        square = generate_text_card(
            context, dim.textFields[0], dimProps, basePoint=midPoint, xDir=vecX, yDir=midVec)


        if sceneProps.show_dim_text:
            draw_text_3D(context, dim.textFields[0], dimProps, myobj, square)

        # Get coords for point pass
        pointCoords = []
        pointCoords.append((startVec * radius) + p2)
        for vert in verts:
            pointCoords.append((vert * radius) + p2)
        pointCoords.append((endVec * radius) + p2)

        # batch & Draw Shader
        coords = []
        coords.append((startVec * radius) + p2)
        for vert in verts:
            coords.append((vert * radius) + p2)
            coords.append((vert * radius) + p2)
        coords.append((endVec * radius) + p2)

        filledCoords = []
        caps = (dimProps.endcapA, dimProps.endcapB)
        capSize = dimProps.endcapSize
        pos = ((startVec * radius) + p2, (endVec * radius) + p2)
        # Clamp cap size between 0 and the length of the coords
        arrowoffset = int(max(0, min(capSize, len(coords) / 4)))
        # offset the arrow direction as arrow size increases
        mids = (coords[arrowoffset + 1], coords[len(coords) - arrowoffset - 1])
        i = 0
        for cap in caps:
            capCoords = generate_end_caps(
                context, dimProps, cap, capSize, pos[i], midVec, mids[i], i, False)
            i += 1
            for coord in capCoords[0]:
                coords.append(coord)
            for filledCoord in capCoords[1]:
                filledCoords.append(filledCoord)

        # Draw Filled Faces after
        if len(filledCoords) != 0:
            draw_filled_coords(filledCoords, rgb)

        draw_lines(lineWeight, rgb, coords, twoPass=True,
                pointPass=True, pointCoords=pointCoords)

        if sceneProps.is_vector_draw:
            svg_dim = svg.add(svg.g(id=dim.name))
            svg_shaders.svg_line_shader(
                dim, dimProps, coords, lineWeight, rgb, svg, parent=svg_dim)
            svg_shaders.svg_fill_shader(
                dim, filledCoords, rgb, svg, parent=svg_dim)
            svg_shaders.svg_text_shader(
                dim, dimProps, dimText.text, origin, square, rgb, svg, parent=svg_dim)



def draw_arcDimension(context, myobj, DimGen, dim, mat, svg=None, dxf=None):

    dimProps = get_style(dim,'alignedDimensions')
    sceneProps = context.scene.MeasureItArchProps


    with OpenGL_Settings(dimProps):

        if not check_vis(dim, dimProps):
            return

        lineWeight = dimProps.lineWeight
        rgb = get_color(dimProps.color, myobj, is_active=dim.is_active)
        radius = dim.dimOffset

        deleteFlag = False
        try:
            p1 = Vector(get_point(get_mesh_vertex(
                myobj, dim.dimPointA, dimProps.evalMods), mat))
            p2 = Vector(get_point(get_mesh_vertex(
                myobj, dim.dimPointB, dimProps.evalMods), mat))
            p3 = Vector(get_point(get_mesh_vertex(
                myobj, dim.dimPointC, dimProps.evalMods), mat))
        except IndexError:
            print('Get Point Error for ' + dim.name + ' on ' + myobj.name)
            deleteFlag = True

        if deleteFlag:
            dimGen = myobj.DimensionGenerator
            wrapTag = get_dim_tag(dim, myobj)
            wrapper = dimGen.wrapper[wrapTag]
            tag = wrapper.itemIndex
            dimGen.arcDimensions.remove(tag)
            dimGen.wrapper.remove(wrapTag)
            recalc_dimWrapper_index(None, context)
            return

        # calc normal to plane defined by points
        vecA = (p1 - p2)
        vecA.normalize()
        vecB = (p3 - p2)
        vecB.normalize()
        norm = vecA.cross(vecB).normalized()

        # Calculate the Arc Defined by our 3 points
        # reference for maths: http://en.wikipedia.org/wiki/Circumscribed_circle

        an_p1 = p1.copy()
        an_p2 = p2.copy()
        an_p3 = p3.copy()

        an_p12 = Vector((
            an_p1[0] - an_p2[0],
            an_p1[1] - an_p2[1],
            an_p1[2] - an_p2[2]))
        an_p13 = Vector((
            an_p1[0] - an_p3[0],
            an_p1[1] - an_p3[1],
            an_p1[2] - an_p3[2]))
        an_p21 = Vector((
            an_p2[0] - an_p1[0],
            an_p2[1] - an_p1[1],
            an_p2[2] - an_p1[2]))
        an_p23 = Vector((
            an_p2[0] - an_p3[0],
            an_p2[1] - an_p3[1],
            an_p2[2] - an_p3[2]))
        an_p31 = Vector((
            an_p3[0] - an_p1[0],
            an_p3[1] - an_p1[1],
            an_p3[2] - an_p1[2]))
        an_p32 = Vector((
            an_p3[0] - an_p2[0],
            an_p3[1] - an_p2[1],
            an_p3[2] - an_p2[2]))
        an_p12xp23 = an_p12.copy().cross(an_p23)

        alpha = pow(an_p23.length, 2) * an_p12.dot(an_p13) / \
            (2 * pow(an_p12xp23.length, 2))
        beta = pow(an_p13.length, 2) * an_p21.dot(an_p23) / \
            (2 * pow(an_p12xp23.length, 2))
        gamma = pow(an_p12.length, 2) * an_p31.dot(an_p32) / \
            (2 * pow(an_p12xp23.length, 2))

        # THIS IS THE CENTER POINT
        a_p1 = (alpha * an_p1[0] + beta * an_p2[0] + gamma * an_p3[0],
                alpha * an_p1[1] + beta * an_p2[1] + gamma * an_p3[1],
                alpha * an_p1[2] + beta * an_p2[2] + gamma * an_p3[2])

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

        # get circle verts
        startVec = A
        arc_angle = arc_angle
        numCircleVerts = math.ceil(radius / .2) + int((degrees(arc_angle)) / 2)
        verts = []
        for idx in range(numCircleVerts + 2):
            rotangle = -(arc_angle / (numCircleVerts + 1)) * idx
            point = startVec.copy()
            point.rotate(Quaternion(norm, rotangle))
            verts.append((point).normalized())

        # Radius
        radius = (B).length
        offsetRadius = radius + dim.dimOffset
        endVec = C
        coords = []

        # Map raw Circle Verts to radius for marker
        startVec = (verts[0] * offsetRadius)
        coords.append(startVec)
        for vert in verts:
            coords.append((vert * offsetRadius))
            coords.append((vert * offsetRadius))
        endVec = (verts[len(verts) - 1] * offsetRadius)
        coords.append(endVec)

        # Define Radius Leader
        zeroVec = Vector((0, 0, 0))
        radiusLeader = C.copy()
        radiusLeader.rotate(Quaternion(norm, arc_angle / 2))
        radiusMid = Vector(interpolate3d(radiusLeader, zeroVec, radius / 2))

        # Generate end caps
        # Set up properties
        filledCoords = []
        midVec = A
        caps = [dimProps.endcapA, dimProps.endcapB]
        pos = [startVec, endVec]

        if dim.showRadius:
            caps.append(dim.endcapC)
            pos.append(radiusLeader)

        capSize = dimProps.endcapSize
        arrowoffset = 3 + int(max(0, min(math.ceil(capSize / 4), len(coords) / 5)))
        # offset the arrow direction as arrow size increases
        mids = (coords[arrowoffset], coords[len(coords) - arrowoffset], radiusMid)

        i = 0
        for cap in caps:
            capCoords = generate_end_caps(
                context, dimProps, cap, capSize, pos[i], midVec, mids[i], i, False)
            i += 1
            for coord in capCoords[0]:
                coords.append(coord)
            for filledCoord in capCoords[1]:
                filledCoords.append(center + filledCoord)

        # Add A and C Extension Lines
        coords.append(A)
        coords.append((((A).normalized()) * (offsetRadius + arrowoffset / 1000)))

        coords.append(C)
        coords.append((((C).normalized()) * (offsetRadius + arrowoffset / 1000)))

        # Add Radius leader
        if dim.showRadius:
            coords.append(zeroVec)
            coords.append(radiusLeader)

        # Check for text field
        if len(dim.textFields) != 2:
            dim.textFields.add()
            dim.textFields.add()

        radiusText = dim.textFields[0]
        lengthText = dim.textFields[1]

        # format text and update if necessary
        lengthStr = format_distance(arc_length)

        if dim.displayAsAngle:
            lengthStr = format_angle(arc_angle)

        if lengthText.text != lengthStr:
            lengthText.text = lengthStr
            lengthText.text_updated = True

        if dim.showRadius:
            radStr = 'r ' + format_distance(radius)
            if radiusText.text != radStr:
                radiusText.text = radStr
                radiusText.text_updated = True

            # make Radius text card
            midPoint = Vector(interpolate3d(zeroVec, radiusLeader, radius / 2))
            vecY = midPoint.cross(norm).normalized()
            vecX = midPoint.normalized()
            rad_origin = Vector(midPoint) + 0.04 * vecY + center
            dim.textAlignment = 'C'
            rad_square = generate_text_card(
                context, radiusText, dimProps, basePoint=rad_origin, xDir=vecX, yDir=vecY)

            if sceneProps.show_dim_text:
                draw_text_3D(
                    context, dim.textFields[0], dimProps, myobj, rad_square)

        # make Length text card
        midPoint = radiusLeader.normalized() * offsetRadius
        vecX = midPoint.cross(norm).normalized()
        vecY = midPoint.normalized()
        len_origin = Vector(midPoint) + center
        len_square = generate_text_card(
            context, lengthText, dimProps, basePoint=len_origin, xDir=vecX, yDir=vecY)

        if sceneProps.show_dim_text:
            draw_text_3D(
                context, dim.textFields[1], dimProps, myobj, len_square)

        measure_coords = []
        measure_pointCoords = []
        for coord in coords:
            measure_coords.append(coord + center)
            measure_pointCoords.append(coord + center)

        # Draw Our Measurement
        draw_lines(lineWeight, rgb, measure_coords, twoPass=True,
                pointPass=True, pointCoords=measure_pointCoords)

        # Draw the arc itself
        coords = []
        startVec = (verts[0] * radius)
        coords.append(startVec)
        for vert in verts:
            coords.append((vert * radius))
            coords.append((vert * radius))
        endVec = (verts[len(verts) - 1] * radius)
        coords.append(endVec)

        arc_coords = []
        arc_pointCoords = []
        for coord in coords:
            arc_coords.append(coord + center)
            arc_pointCoords.append(coord + center)

        draw_lines(lineWeight * 2, rgb, arc_coords, twoPass=True,
                pointPass=True, pointCoords=arc_pointCoords)

        if dim.showRadius:
            pointCenter = [center]
            draw_points(lineWeight * 5, rgb, pointCenter)

        if len(filledCoords) != 0:
            draw_filled_coords(filledCoords, rgb)

        if sceneProps.is_vector_draw:
            svg_dim = svg.add(svg.g(id=dim.name))
            svg_shaders.svg_line_shader(
                dim, dimProps, coords, lineWeight, rgb, svg, parent=svg_dim)
            svg_shaders.svg_line_shader(
                dim, dimProps, measure_coords, lineWeight * 2, rgb, svg, parent=svg_dim)
            svg_shaders.svg_fill_shader(
                dim, filledCoords, rgb, svg, parent=svg_dim)
            # def svg_text_shader(item, style, text, mid, textCard, color, svg, parent=None)
            svg_shaders.svg_text_shader(
                dim, dimProps, lengthText.text, len_origin, len_square, rgb, svg, parent=svg_dim)
            if dim.showRadius:
                svg_shaders.svg_text_shader(
                    dim, dimProps, radiusText.text, rad_origin, rad_square, rgb, svg, parent=svg_dim)
                svg_shaders.svg_circle_shader(dim,center,lineWeight * 5,rgb,svg,parent=svg_dim)



def draw_areaDimension(context, myobj, DimGen, dim, mat, svg=None, dxf=None):
    dimProps = get_style(dim,'alignedDimensions')
    sceneProps = context.scene.MeasureItArchProps



    with OpenGL_Settings(dimProps):

        # Check Visibility Conditions
        if not check_vis(dim, dimProps):
            return

        lineWeight = dimProps.lineWeight

        rgb = get_color(dim.fillColor, myobj, is_active=dim.is_active)
        fillRGB = (rgb[0], rgb[1], rgb[2], dim.fillAlpha)

        rawTextRGB = dimProps.color
        textRGB = rgb_gamma_correct(rawTextRGB)

        bm = bmesh.new()
        if myobj.mode != 'EDIT':
            eval_res = sceneProps.eval_mods
            if (eval_res or dim.evalMods) and check_mods(myobj):  # From Evaluated Deps Graph
                bm.from_object(
                    myobj, bpy.context.view_layer.depsgraph)
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
        center = Vector((0,0,0))
        area_faces = dim['facebuffer'].to_list()
        for faceIdx in area_faces:
            face = faces[faceIdx]
            area = face.calc_area()
            center += face.calc_center_median_weighted()

            indices = []
            for vert in face.verts:
                indices.append(vert.index)

            tris = mesh_utils.ngon_tessellate(myobj.data, indices)

            for tri in tris:
                v1, v2, v3 = tri
                p1 = mat @ verts[indices[v1]].co
                p2 = mat @ verts[indices[v2]].co
                p3 = mat @ verts[indices[v3]].co
                filledCoords.append(p1)
                filledCoords.append(p2)
                filledCoords.append(p3)
                area = area_tri(p1, p2, p3)
                sumArea += area

        center /= len(area_faces)
        # Get the Perimeter Coords
        perimeterCoords = []
        polyfillCoords = []
        if 'perimeterVertBuffer' in dim:
            buffer_list = dim['perimeterVertBuffer'].to_list()
        else:
            buffer_list = []
            dim['perimeterVertBuffer'] = []
            print("No Peimeter Vert Buffer found in {} on {}. Please re-create area dimension".format(dim.name,myobj.name))
        idx = 0
        for vert_idx in buffer_list:
            idx += 1
            v1 = bm.verts[vert_idx]
            polyfillCoords.append(mat @ v1.co)
            perimeterCoords.append(mat @ v1.co)

            if idx < len(buffer_list):
                v2 = bm.verts[buffer_list[idx]]
                perimeterCoords.append(mat @ v2.co)

        #print(dim['perimeterEdgeBuffer'].to_list())

        # Get local Rotation and Translation
        rot = mat.to_quaternion()

        # Compose Rotation and Translation Matrix
        rotMatrix = Matrix.Identity(3)
        rotMatrix.rotate(rot)
        rotMatrix.resize_4x4()

        originFace = faces[dim.originFaceIdx]
        #origin = originFace.calc_center_bounds()
        origin = center
        normal = rotMatrix @ originFace.normal

        origin += dim.dimTextPos + normal * 0.01


        # Get Camera X
        # Only use the z rot of the annotation rotation
        annoMat = Matrix.Identity(3).copy()
        annoEuler = Euler((0, 0, dim.dimRotation), 'XYZ')
        annoMat.rotate(annoEuler)
        annoMat = annoMat.to_4x4()

        # use Camera rot for the rest

        camera = context.scene.camera
        cameraMat = camera.matrix_world
        cameraRot = cameraMat.decompose()[1]
        cameraRotMat = Matrix.Identity(3)
        cameraRotMat.rotate(cameraRot)
        cameraRotMat = cameraRotMat.to_4x4()


        fullRotMat = annoMat @ cameraRotMat

        cameraX = cameraRotMat @ Vector((1, 0, 0))

        ### Get camera X projected onto the area plane
        proj_camera_x_on_normal = (cameraX.dot(normal)/normal.length**2)*normal
        proj_camera_x_on_plane = cameraX - proj_camera_x_on_normal

        vecX = proj_camera_x_on_plane
        vecY = normal.cross(vecX)

        # y.rotate(Quaternion(normal,radians(-45)))
        # x.rotate(Quaternion(normal,radians(-45)))

        vecY.rotate(Quaternion(normal, dim.dimRotation))
        vecX.rotate(Quaternion(normal, dim.dimRotation))

        origin = mat @ origin


        dimProps.textAlignment = 'C'
        dimProps.textPosition = 'M'

        # Setup Text Fields
        #def setup_dim_text(myobj,dim,dimProps,dist,origin,distVector,offsetDistance, is_area=False):
        #placementResults = setup_dim_text(myobj,dim,dimProps, sumArea,origin,vecX,vecY, is_area=True)
        if len(dim.textFields) == 0:
            dim.textFields.add()

        dimText = dim.textFields[0]

        # format text and update if necessary
        if not dim.use_custom_text:


            distanceText = format_area(sumArea, dim=dim)

            if dimText.text != distanceText:
                dimText.text = distanceText
                dimText.text_updated = True

        idx = 0
        for textField in dim.textFields:
            set_text(textField, myobj)

            textcard = generate_text_card(context, textField, dimProps, basePoint=origin, xDir=vecX, yDir=vecY.normalized() ,cardIdx=idx)
            textField['textcard'] = textcard

            if sceneProps.show_dim_text:
                draw_text_3D(context, textField, dimProps, myobj, textField['textcard'])
            idx += 1

        # Draw Fill
        draw_filled_coords(filledCoords, fillRGB, polySmooth=False)



        # Draw Perimeter
        draw_lines(lineWeight, rgb, perimeterCoords,
                twoPass=True, pointPass=True)


        # Draw SVG
        if sceneProps.is_vector_draw:
            svg_dim = svg.add(svg.g(id=dim.name))
            svg_shaders.svg_poly_fill_shader( dim, polyfillCoords,(0,0,0,0),svg, line_color = rgb, lineWeight= lineWeight, itemProps=dimProps)

            svg_shaders.svg_poly_fill_shader(
                dim, polyfillCoords, fillRGB, svg, parent=svg_dim)
            for textField in dim.textFields:
                textcard = textField['textcard']
                svg_shaders.svg_text_shader(
                    dim, dimProps, textField.text, origin, textcard, textRGB, svg, parent=svg_dim)

# takes a set of co-ordinates returns the min and max value for each axis
def get_axis_aligned_bounds(coords):
    """
    Takes a set of co-ordinates returns the min and max value for each axis
    """
    maxX = None
    minX = None
    maxY = None
    minY = None
    maxZ = None
    minZ = None

    for coord in coords:
        if maxX is None:
            maxX = coord[0]
            minX = coord[0]
            maxY = coord[1]
            minY = coord[1]
            maxZ = coord[2]
            minZ = coord[2]
        if coord[0] > maxX:
            maxX = coord[0]
        if coord[0] < minX:
            minX = coord[0]
        if coord[1] > maxY:
            maxY = coord[1]
        if coord[1] < minY:
            minY = coord[1]
        if coord[2] > maxZ:
            maxZ = coord[2]
        if coord[2] < minZ:
            minZ = coord[2]

    return [maxX, minX, maxY, minY, maxZ, minZ]

def get_view_plane(dim,dimProps):
    # Check for View Plane Overides
    if dim.dimViewPlane == '99':
        viewPlane = dimProps.dimViewPlane
    else:
        viewPlane = dim.dimViewPlane

    return viewPlane

def get_view_axis(context, dim, dimProps):
    i = Vector((1, 0, 0))  # X Unit Vector
    j = Vector((0, 1, 0))  # Y Unit Vector
    k = Vector((0, 0, 1))  # Z Unit Vector

    viewPlane = get_view_plane(dim,dimProps)

    # Set viewAxis
    if viewPlane == 'XY':
        viewAxis = k
    elif viewPlane == 'XZ':
        viewAxis = j
    elif viewPlane == 'YZ':
        viewAxis = i

    if viewPlane == '99':
        # Get Viewport and CameraLoc or ViewRot

        if context.scene.camera != None:
            cameraRot = context.scene.camera.matrix_world.to_quaternion()

            viewVec = -k.copy()
            viewVec.rotate(cameraRot)
            viewAxis = viewVec

        elif context.scene.camera == None:
            space3D = None
            for space in context.area.spaces:
                if space.type == 'VIEW_3D':
                    space3D = space

            if space3D is None:
                return Vector((0, 0, 0))

            viewRot = space3D.region_3d.view_rotation
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

    return viewAxis

def select_normal(myobj, dim, normDistVector, midpoint, dimProps):
    # Set properties
    context = bpy.context
    sceneProps = context.scene.MeasureItArchProps
    i = Vector((1, 0, 0))  # X Unit Vector
    j = Vector((0, 1, 0))  # Y Unit Vector
    k = Vector((0, 0, 1))  # Z Unit Vector
    centerRay = Vector((-1, 1, 1))
    badNormals = False

    viewAxis = get_view_axis(context, dim, dimProps)

    # Mesh Dimension Behaviour
    if myobj.type == 'MESH':
        # get Adjacent Face normals if possible
        possibleNormals = []

        # Create a Bmesh Instance from the selected object
        bm = bmesh.new()
        bm.from_mesh(myobj.data)
        bm.edges.ensure_lookup_table()

        # For each edge get its linked faces and vertex indicies
        for edge in bm.edges:
            bmEdgeIndices = [edge.verts[0].index, edge.verts[1].index]
            if dim.dimPointA in bmEdgeIndices and dim.dimPointB in bmEdgeIndices:
                linked_faces = edge.link_faces
                for face in linked_faces:
                    possibleNormals.append(face.normal)

        bm.free()

        # Check if Face Normals are available
        if len(possibleNormals) != 2:
            badNormals = True
        else:
            bestNormal = Vector((0, 0, 0))
            sumNormal = Vector((0, 0, 0))
            for norm in possibleNormals:
                sumNormal += norm

            # Check relevent component against current best normal
            checkValue = 0
            planeNorm = Vector((0, 0, 0))
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
            if bestNormal.dot(sumNormal) < 0:
                bestNormal.negate()

    if archipack_datablock(myobj):
        # Use archipack dimension matrix y vector
        bestNormal = myobj.matrix_world.col[1].to_3d()

    elif myobj.type != 'MESH' or badNormals:
        # If Face Normals aren't available;
        # use the cross product of the View Plane Normal and the dimensions distance vector.
        bestNormal = viewAxis.cross(normDistVector)
        if bestNormal.length == 0:
            bestNormal = centerRay

        if bestNormal.dot(centerRay) < 0:
            bestNormal.negate()

    # Normalize Result
    bestNormal.normalize()
    if dim.dimFlip:
        bestNormal *= -1.0
    return bestNormal


def draw_line_group(context, myobj, lineGen, mat, svg=None, dxf=None, is_instance_draw = False):
    scene = context.scene
    sceneProps = scene.MeasureItArchProps

    viewport = get_viewport()

    #print('Drawing Line group on {}, is instance: {}'.format(myobj.name, is_instance_draw))

    # Check for object mode changes, outside of line group loop
    global lastMode
    mode_change_flag = False
    evalModsGlobal = sceneProps.eval_mods
    try:
        obj_last_mode = lastMode[myobj.name]
    except KeyError:
        obj_last_mode = myobj.mode
        lastMode[myobj.name] = obj_last_mode

    if obj_last_mode != myobj.mode:
        mode_change_flag = True
        lastMode[myobj.name] = myobj.mode

    # Draw Line Groups
    for lineGroup in lineGen.line_groups:
        lineProps = get_style(lineGroup,'line_groups')

        with OpenGL_Settings(lineProps):

            if not check_vis(lineGroup, lineProps):
                continue

            rgb = get_color(lineProps.color, myobj, is_active= not lineGroup.is_active, cad_col_idx= lineProps.cad_col_idx)

            # set other line properties
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
            offset = lineWeight / 2.5
            offset += lineProps.lineDepthOffset
            if isOrtho:
                offset /= 15
            if lineProps.isOutline:
                offset = -10 - offset
            offset /= 1000

            # Get line data to be drawn
            evalMods = lineProps.evalMods

            # Flag for re-evaluation of batches & mesh data
            verts = []

            # Conditions for re calculating Line Co-ordinates
            if mode_change_flag or \
                myobj.mode == 'WEIGHT_PAINT' or \
                sceneProps.is_render_draw or\
                scene.ViewGenerator.view_changed or\
                evalModsGlobal or\
                evalMods:
                recoord_flag = True
            else:
                recoord_flag = False

            if is_instance_draw: recoord_flag = False

            if recoord_flag and check_mods(myobj) and not is_instance_draw:
                if myobj.type == 'MESH':
                    deps = bpy.context.view_layer.depsgraph
                    obj_eval = myobj.evaluated_get(deps)
                    mesh = obj_eval.data
                    verts = mesh.vertices


            # Get Coords
            sceneProps = bpy.context.scene.MeasureItArchProps
            if ('coordBuffer' not in lineGroup or recoord_flag):
                # Handle line groups created with older versions of MeasureIt_ARCH
                if 'singleLine' in lineGroup and 'lineBuffer' not in lineGroup:
                    toLineBuffer = []
                    for line in lineGroup['singleLine']:
                        toLineBuffer.append(line['pointA'])
                        toLineBuffer.append(line['pointB'])
                    lineGroup['lineBuffer'] = toLineBuffer

                # Get Coords From non Dynamic Lines
                if 'lineBuffer' in lineGroup:
                    tempCoords = [get_line_vertex(
                        idx, verts) for idx in lineGroup['lineBuffer']]
                    lineGroup['coordBuffer'] = tempCoords

                # Calculate dynamic lines or curve lines (only for non instances)
                if lineGroup.useDynamicCrease and not is_instance_draw:
                    tempCoords = []
                    tempIdxs = []
                    # Create a Bmesh Instance from the selected object
                    bm = bmesh.new()
                    mesh = myobj.data
                    try:
                        camera_z = get_camera_z()
                    except AttributeError:
                        camera_z = Vector((0,0,1))
                    rot = mat.to_quaternion()

                    if myobj.mode != 'OBJECT':
                        return

                    if myobj.type == 'MESH':
                        depsgraph = bpy.context.view_layer.depsgraph
                        eval_obj = myobj.evaluated_get(depsgraph)
                        temp_mesh = eval_obj.data
                        bm.from_mesh(temp_mesh)
                        #bm.from_object(myobj, bpy.context.view_layer.depsgraph)

                    if myobj.type == 'CURVE':
                        depsgraph = bpy.context.view_layer.depsgraph
                        eval_obj = myobj.evaluated_get(depsgraph)
                        temp_mesh = bpy.data.meshes.new_from_object(eval_obj, depsgraph = bpy.context.view_layer.depsgraph)
                        bm.from_mesh(temp_mesh)

                    # For each edge get its linked faces and vertex indicies
                    for idx, edge in enumerate(bm.edges):
                        linked_faces = edge.link_faces
                        pointA = edge.verts[0].co
                        pointB = edge.verts[1].co

                        #Check Filter Vertex Group
                        if lineGroup.lineWeightGroup != '':
                            #print('has filter group')
                            eval_obj = myobj.evaluated_get(bpy.context.view_layer.depsgraph)
                            vertex_group = eval_obj.vertex_groups[lineGroup.lineWeightGroup]
                            group_idx = vertex_group.index
                            v1_groups = eval_obj.data.vertices[edge.verts[0].index].groups
                            v2_groups = eval_obj.data.vertices[edge.verts[1].index].groups
                            id1 = []
                            id2 = []
                            for item in v1_groups:
                                id1.append(item.group)
                                #print('v1 in group: {} looking for group: {}'.format(item.group,group_idx))
                            for item in v2_groups:
                                id2.append(item.group)
                                #print('v2 in group: {} looking for group: {}'.format(item.group,group_idx))



                            if lineGroup.invertGroupFilter - (group_idx not in id1 or group_idx not in id2):
                                #print('skipping line segment')
                                continue


                        if len(linked_faces) == 2:
                            normalA = Vector(
                                linked_faces[0].normal).normalized()
                            normalB = Vector(
                                linked_faces[1].normal).normalized()
                            dotProd = (normalA.dot(normalB))

                            #Check angle of adjacent faces
                            if dotProd >= -1 and dotProd <= 1 and not lineGroup.dynamic_sil:
                                creaseAngle = math.acos(dotProd)
                                if creaseAngle > lineGroup.creaseAngle:
                                    tempCoords.append(pointA)
                                    tempCoords.append(pointB)
                                    tempIdxs.append(edge.verts[0].index)
                                    tempIdxs.append(edge.verts[1].index)

                            #Check dynamic silhouette
                            if lineGroup.dynamic_sil:
                                normalA.rotate(rot)
                                normalB.rotate(rot)
                                a_dot = camera_z.dot(normalA)
                                b_dot = camera_z.dot(normalB)
                                sign_a = np.sign(a_dot)
                                sign_b = np.sign(b_dot)
                                if sign_a != sign_b:
                                    tempCoords.append(pointA)
                                    if not lineGroup.chain:
                                        tempCoords.append(pointB)


                        # Any edge with greater or less
                        # than 2 linked faces is non manifold
                        else:
                            tempCoords.append(pointA)
                            if not lineGroup.chain or idx == (len(bm.edges)-1):
                                tempCoords.append(pointB)





                    lineGroup['coordBuffer'] = tempCoords.copy()
                    lineGroup['lineBuffer'] = tempIdxs.copy()
                    if len(tempCoords) == 0:
                        lineGroup['coordBuffer'] = []
                        return
                    bm.free()


                # Get vertex group for evaluated mesh
                # line weight group setup
                tempWeights = []
                #if lineGroup.lineWeightGroup != "":
                #    obj_eval = myobj.evaluated_get(bpy.context.view_layer.depsgraph)
                #    vertex_group = obj_eval.vertex_groups[lineGroup.lineWeightGroup]
                #    group_idx = vertex_group.index
                #    for idx in lineGroup['lineBuffer']:
                #        try:
                #            vert = obj_eval.data.vertices[idx]
                #            print(vert.groups)
                #            tempWeights.append(vert.groups[group_idx].weight)
                #        except IndexError as e:
                #            print("Index: {} not in Vertex Group: {} on obj: {}".format(idx,lineGroup.lineWeightGroup,myobj.name))
                #            tempWeights.append(0.0)
                #else:
                tempWeights = [1.0] * len(lineGroup['coordBuffer'])

                lineGroup['weightBuffer'] = tempWeights

            coords = []
            coords = lineGroup['coordBuffer']

            try:
                weights = lineGroup['weightBuffer']
            except KeyError:
                tempWeights = [1.0] * len(lineGroup['coordBuffer'])
                lineGroup['weightBuffer'] = tempWeights
                weights = lineGroup['weightBuffer']

            lineGroup.weightGroupInfluence = 0.0

            if len(coords) == 0:
                #print("No Coords")
                return

            dotcoords = []
            filledcoords = []

            if lineGroup.endcapA != 'NONE':
                dot,fill =  draw_annotation_endcaps(lineGroup,lineGroup.endcapA, mat@Vector(coords[0])  , mat@Vector(coords[-1]) , rgb, lineGroup.endcapSize)
                dotcoords.append(dot)
                filledcoords.append(fill)

            if lineGroup.endcapB != 'NONE':
                dot,fill =  draw_annotation_endcaps(lineGroup, lineGroup.endcapB, mat@Vector(coords[-1]) , mat@Vector(coords[-2]) , rgb, lineGroup.endcapSize)
                dotcoords.append(dot)
                filledcoords.append(fill)

            res = get_resolution()
            if drawHidden:
                # Invert The Depth test for hidden lines
                bgl.glDepthFunc(bgl.GL_GREATER)
                hiddenLineWeight = lineProps.lineHiddenWeight
                dashRGB = get_color(lineProps.lineHiddenColor,myobj, is_active= not lineGroup.is_active)
                view = get_view()
                dashedLineShader.bind()

                dashedLineShader.uniform_float("resolution",  res)
                dashedLineShader.uniform_float("u_dashSize",  lineProps.d1_length)
                dashedLineShader.uniform_float("u_gapSize", lineProps.g1_length)
                dashedLineShader.uniform_float("Viewport", viewport)
                dashedLineShader.uniform_float("Render", (scene.render.resolution_x, scene.render.resolution_y) )
                dashedLineShader.uniform_float("objectMatrix", mat)
                dashedLineShader.uniform_float("thickness", hiddenLineWeight)
                dashedLineShader.uniform_float(
                    "screenSpaceDash", lineProps.screenSpaceDashes)
                dashedLineShader.uniform_float(
                    "finalColor", (dashRGB[0], dashRGB[1], dashRGB[2], dashRGB[3]))
                dashedLineShader.uniform_float("offset", -offset)

                global hiddenBatch3D
                batchKey = myobj.name + lineGroup.name + lineGroup.creation_time
                if batchKey not in hiddenBatch3D or recoord_flag:
                    hiddenBatch3D[batchKey] = batch_for_shader(
                        dashedLineShader, 'LINES', {"pos": coords})
                if sceneProps.is_render_draw:
                    batchHidden = batch_for_shader(
                        dashedLineShader, 'LINES', {"pos": coords})
                else:
                    batchHidden = hiddenBatch3D[batchKey]

                batchHidden.program_set(dashedLineShader)
                batchHidden.draw()

                bgl.glDepthFunc(bgl.GL_LESS)
                gpu.shader.unbind()


            if lineProps.lineDrawDashed:
                dashedLineShader.bind()
                view = get_view()
                dashedLineShader.uniform_float("resolution",  res)
                dashedLineShader.uniform_float("u_dashSize",  lineProps.d1_length)
                dashedLineShader.uniform_float("u_gapSize", lineProps.g1_length)
                dashedLineShader.uniform_float("Viewport", viewport)
                dashedLineShader.uniform_float("Render", (scene.render.resolution_x, scene.render.resolution_y) )
                dashedLineShader.uniform_float("objectMatrix", mat)
                dashedLineShader.uniform_float("thickness", lineWeight)
                dashedLineShader.uniform_float(
                    "screenSpaceDash", lineProps.screenSpaceDashes)
                dashedLineShader.uniform_float(
                    "finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
                dashedLineShader.uniform_float("offset", -offset)

                global dashedBatch3D
                batchKey = myobj.name + lineGroup.name + lineGroup.creation_time
                if batchKey not in dashedBatch3D or recoord_flag:
                    if not lineGroup.chain:
                        dashedBatch3D[batchKey] = batch_for_shader(
                            dashedLineShader, 'LINES', {"pos": coords})
                        batchDashed = dashedBatch3D[batchKey]
                    else:
                        dashedBatch3D[batchKey] = batch_for_shader(
                            dashedLineShader, 'LINE_STRIP', {"pos": coords})
                        batchDashed = dashedBatch3D[batchKey]
                else:
                    batchDashed = dashedBatch3D[batchKey]

                batchDashed.program_set(dashedLineShader)
                batchDashed.draw()

            else:
                lineGroupShader.bind()
                lineGroupShader.uniform_float("Viewport", viewport)
                lineGroupShader.uniform_float("objectMatrix", mat)
                lineGroupShader.uniform_float("thickness", lineWeight)
                lineGroupShader.uniform_float(
                    "extension", lineGroup.lineOverExtension)
                lineGroupShader.uniform_float("pointPass", lineProps.pointPass)
                lineGroupShader.uniform_float(
                    "weightInfluence", lineGroup.weightGroupInfluence)
                lineGroupShader.uniform_float(
                    "finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
                lineGroupShader.uniform_float("zOffset", -offset)

                # colors = [(rgb[0], rgb[1], rgb[2], rgb[3]) for coord in range(len(coords))]

                global lineBatch3D
                batchKey = myobj.name + lineGroup.name + lineGroup.creation_time
                batch3d = None
                if batchKey not in lineBatch3D or recoord_flag:
                    if not lineGroup.chain:
                        lineBatch3D[batchKey] = batch_for_shader(
                            lineGroupShader, 'LINES', {"pos": coords, "weight": weights})
                        batch3d = lineBatch3D[batchKey]
                    else:
                        lineBatch3D[batchKey] = batch_for_shader(
                            lineGroupShader, 'LINE_STRIP', {"pos": coords, "weight": weights})
                        batch3d = lineBatch3D[batchKey]

                else:
                    batch3d = lineBatch3D[batchKey]

                if rgb[3] == 1:
                    bgl.glBlendFunc(bgl.GL_SRC_ALPHA,
                                    bgl.GL_ONE_MINUS_SRC_ALPHA)
                    bgl.glDepthMask(True)
                    lineGroupShader.uniform_float("depthPass", True)
                    batch3d.program_set(lineGroupShader)
                    batch3d.draw()

                if sceneProps.is_render_draw:
                    bgl.glBlendFunc(bgl.GL_SRC_ALPHA,
                                    bgl.GL_ONE_MINUS_SRC_ALPHA)
                    # bgl.glBlendEquation(bgl.GL_FUNC_ADD)
                    bgl.glBlendEquation(bgl.GL_MAX)

                bgl.glDepthMask(False)
                lineGroupShader.uniform_float("depthPass", False)
                batch3d.program_set(lineGroupShader)
                batch3d.draw()

                gpu.shader.unbind()

            if sceneProps.is_vector_draw:
                if not lineProps.chain:
                    svg_shaders.svg_line_shader(
                        lineGroup, lineProps, coords, lineWeight, rgb, svg, mat=mat)
                else:
                    svg_shaders.svg_poly_fill_shader(lineGroup,coords,(0,0,0,0),svg,line_color = rgb, lineWeight= lineProps.lineWeight, itemProps=lineProps,closed=False, mat=mat)

                for dotcoord in dotcoords:
                    if dotcoord:
                        svg_shaders.svg_circle_shader(lineGroup,dotcoord[0],dotcoord[1],rgb,svg,parent=svg)
                for fill in filledcoords:
                    svg_shaders.svg_fill_shader(
                        lineGroup, fill, rgb, svg, parent=svg)

            if sceneProps.is_dxf_draw:
                dxf_shaders.dxf_line_shader(lineGroup, lineProps, coords, lineWeight, rgb, dxf,myobj, mat=mat, )
    gpu.shader.unbind()


def get_color(rawRGB, myobj, is_active=True, only_active=False, cad_col_idx = 256):
    # undo blenders Default Gamma Correction

    context = bpy.context
    sceneProps = bpy.context.scene.MeasureItArchProps
    if sceneProps.use_cad_col and cad_col_idx != 256:
        try:
            rawRGB = _cad_col_dict[cad_col_idx]
        except KeyError:
            rawRGB = rawRGB


    rgb = rgb_gamma_correct(rawRGB)

    if not sceneProps.highlight_selected or sceneProps.is_render_draw:
        return rgb

    # overide line color with theme selection colors when selected
    if not only_active:
        if myobj in context.selected_objects and is_active:
            rgb[0] = bpy.context.preferences.themes[0].view_3d.object_selected[0]
            rgb[1] = bpy.context.preferences.themes[0].view_3d.object_selected[1]
            rgb[2] = bpy.context.preferences.themes[0].view_3d.object_selected[2]
            rgb[3] = 1.0

    if myobj in context.selected_objects and myobj == context.object and is_active:
        rgb[0] = bpy.context.preferences.themes[0].view_3d.object_active[0]
        rgb[1] = bpy.context.preferences.themes[0].view_3d.object_active[1]
        rgb[2] = bpy.context.preferences.themes[0].view_3d.object_active[2]
        rgb[3] = 1.0

    return rgb

def get_style(item, type_str):
    scene = bpy.context.scene
    sceneProps = scene.MeasureItArchProps

    source_scene = sceneProps.source_scene
    itemProps = item
    style_source = eval("source_scene.StyleGenerator.{}".format(type_str))
    if item.uses_style:
        for style_item in style_source:
            if style_item.name == item.style:
                itemProps = style_item
                return itemProps
        # if we got out of the loop, the style wasn't found
        # Check previous names to updata property
        for style_item in style_source:
            if style_item.previous_name == item.style:
                item.style = style_item.name
                itemProps = style_item

    return itemProps

def draw_annotation(context, myobj, annotationGen, mat, svg=None, dxf=None, instance = None):
    scene = context.scene
    sceneProps = scene.MeasureItArchProps
    customCoords = []
    customFilledCoords = []
    for annotation in annotationGen.annotations:
        annotationProps = get_style(annotation,"annotations")


        with OpenGL_Settings(annotationProps):

            endcap = annotationProps.endcapA
            endcapSize = annotationProps.endcapSize

            if not check_vis(annotation, annotationProps):
                return
            lineWeight = annotationProps.lineWeight
            # undo blenders Default Gamma Correction
            rgb = get_color(annotationProps.color, myobj, is_active=annotation.is_active)

            # Get Points
            deleteFlag = False
            try:
                p1local = get_mesh_vertex(
                    myobj, annotation.annotationAnchor, annotationProps.evalMods, spline_idx=annotation.annotationAnchorSpline)
                p1 = get_point(p1local, mat)
                annotation['p1anchorCoord'] = p1
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
            offset = annotation.annotationOffset

            offset = Vector(offset)

            # Get local Rotation and Translation
            rot = mat.to_quaternion()
            loc = mat.to_translation()
            scale = mat.to_scale()

            # Compose Rotation and Translation Matrix
            rotMatrix = Matrix.Identity(3)
            rotMatrix.rotate(rot)
            rotMatrix.resize_4x4()
            locMatrix = Matrix.Translation(loc)
            scaleMatrix = Matrix.Identity(3)
            scaleMatrix[0][0] *= scale[0]
            scaleMatrix[1][1] *= scale[1]
            scaleMatrix[2][2] *= scale[2]
            scaleMatrix.to_4x4()
            noScaleMat = locMatrix @ rotMatrix
            # locMatrix = Matrix.Translation(loc)

            p1Scaled = scaleMatrix @ Vector(p1local)
            p1 = locMatrix @ rotMatrix @ p1Scaled

            # Transform offset with Composed Matrix
            p2 = (rotMatrix @ offset) + Vector(p1)

            # Draw Custom Shape

            offsetMat = Matrix.Translation(p1Scaled)
            rotMat = Matrix.Identity(3).copy()
            rotEuler = Euler(annotation.annotationRotation, 'XYZ')
            rotMat.rotate(rotEuler)
            rotMat = rotMat.to_4x4()
            customScale = Matrix.Scale(annotation.custom_scale, 4)

            if annotation.custom_shape_location == 'T':
                offsetMat = Matrix.Translation(
                    p1Scaled + annotation.annotationOffset)

            extMat = noScaleMat @ offsetMat @ rotMat @ customScale

            leaderDist = annotationProps.leader_length
            mult = 1
            if annotationProps.align_to_camera:
                # Only use the z rot of the annotation rotation
                annoMat = Matrix.Identity(3).copy()
                annoEuler = Euler((0, 0, annotation.annotationRotation.z), 'XYZ')
                annoMat.rotate(annoEuler)
                annoMat = annoMat.to_4x4()

                # use Camera rot for the rest
                camera = context.scene.camera
                cameraMat = camera.matrix_world
                cameraRot = cameraMat.decompose()[1]
                cameraRotMat = Matrix.Identity(3)
                cameraRotMat.rotate(cameraRot)
                cameraRotMat = cameraRotMat.to_4x4()

                fullRotMat = annoMat @ cameraRotMat
                extMat = locMatrix @ fullRotMat @ customScale

                cameraX = cameraRotMat @ Vector((1, 0, 0))
                leader1 = p1 - p2
                proj = leader1.dot(cameraX)
                if proj > 0:
                    mult = -1

            else:
                fullRotMat = rotMatrix @ rotMat

            p3dir = fullRotMat @ Vector((1, 0, 0))
            p3dir.normalize()

            p3 = p2 + p3dir * (leaderDist*get_scale()*0.5) * mult

            if annotation.customShape is not None:
                col = annotation.customShape
                objs = col.objects
                try:
                    if col.objects[myobj.name] is not None:
                        print(
                            "Annotations Cannot be a part of its custom shape collection")
                        annotation.customShape = None
                        return
                except:
                    pass

                draw3d_loop(context, objs, svg=svg, extMat=extMat,
                            multMat=annotationProps.custom_local_transforms,custom_call=True)


            fieldIdx = 0
            if 'textFields' not in annotation:
                annotation.textFields.add()

            # Some Backwards Compatibility for annotations
            if annotation.textFields[0].text == "" and annotation.name == "":
                annotation.textFields[0].text = annotation.text
                annotation.name = annotation.text

            fields = []
            notesFlag = False
            for textField in annotation.textFields:
                fields.append(textField)

            for textField in fields:
                if instance is None:
                    set_text(textField, myobj, style = annotationProps, item = annotation)
                else:
                    set_text(textField,instance.parent, style = annotationProps, item = annotation)
                origin = p3.copy()
                if annotationProps.leader_length > 0:
                    pass
                    origin += p3dir * (0.0015*get_scale()) * mult
                xDir = fullRotMat @ Vector((1 * mult, 0, 0))
                yDir = fullRotMat @ Vector((0, 1, 0))

                # draw_lines(1,(0,1,0,1),[(0,0,0),xDir,(0,0,0),yDir])

                textcard = generate_text_card(
                    context, textField, annotationProps, basePoint=origin, xDir=xDir, yDir=yDir, cardIdx=fieldIdx)
                textField['textcard'] = textcard
                fieldIdx += 1
            # Set Gizmo Properties
            annotation.gizLoc = p2

            # Draw
            if p1 is not None and p2 is not None:

                coords = []

                # Move end of line Back if arrow endcap
                if endcap == 'T':
                    axis = Vector(p1) - Vector(p2)
                    lineEnd = Vector(p1) - axis * 0.005 * endcapSize
                else:
                    lineEnd = p1

                coords.append(lineEnd)
                coords.append(p2)
                coords.append(p2)
                coords.append(p3)

                textcard = fields[0]['textcard']

                if not annotationProps.draw_leader:
                    coords = []


                dotcoords = []
                filledcoords = []
                dot,fill = draw_annotation_endcaps(annotationProps, endcap, p1 , p2, rgb, endcapSize)
                dotcoords.append(dot)
                filledcoords.append(fill)
                # draw_secondary_leader
                for leader in annotation.secondaryLeaders:
                    obj = leader.anchor
                    if obj == None:
                        continue
                    anchor_point = obj.location

                    coords.append(anchor_point)
                    coords.append(p2)

                    dot,fill = draw_annotation_endcaps(annotationProps, endcap, anchor_point , p2, rgb, endcapSize)
                    dotcoords.append(dot)
                    filledcoords.append(fill)

                draw_lines(lineWeight, rgb, coords,
                        twoPass=True, pointPass=True)


            if sceneProps.show_dim_text:
                for textField in fields:
                    textcard = textField['textcard']
                    draw_text_3D(context, textField, annotationProps, myobj, textcard)

            if sceneProps.is_vector_draw:
                svg_anno = svg.add(svg.g(id=annotation.name))
                svg_shaders.svg_line_shader(
                    annotation, annotationProps, coords, lineWeight, rgb, svg, parent=svg_anno)
                if annotation.customShape is not None:
                    svg_shaders.svg_line_shader(
                        annotation, annotationProps, customCoords, lineWeight, rgb, svg, parent=svg_anno)
                    svg_shaders.svg_fill_shader(
                        annotation, customFilledCoords, rgb, svg, parent=svg_anno)
                for dotcoord in dotcoords:
                    if dotcoord:
                        svg_shaders.svg_circle_shader(annotation,dotcoord[0],dotcoord[1],rgb,svg,parent=svg_anno)
                for fill in filledcoords:
                    svg_shaders.svg_fill_shader(
                        annotation, fill, rgb, svg, parent=svg_anno)
                for textField in fields:
                    textcard = textField['textcard']
                    svg_shaders.svg_text_shader(
                        annotation, annotationProps, textField.text, origin, textcard, rgb, svg, parent=svg_anno)

            if sceneProps.is_dxf_draw:
                dxf_shaders.dxf_annotation_shader(annotation,annotationProps,coords,origin,dxf)


def draw_table(context, myobj, tableGen, mat, svg=None, dxf=None, instance = None):
    scene = context.scene
    sceneProps = scene.MeasureItArchProps 

    # Get Camera Aligned Rot Mats
  
    
    # Get local Rotation and Translation
    rot = mat.to_quaternion()
    loc = mat.to_translation()
    scale = mat.to_scale()

    # Only use the z rot of the annotation rotation
    locMatrix = Matrix.Translation(loc)
    annoMat = Matrix.Identity(3).copy()
    annoEuler = Euler((0, 0, 0), 'XYZ')
    annoMat.rotate(annoEuler)
    annoMat = annoMat.to_4x4()

    # use Camera rot for the rest
    camera = context.scene.camera
    cameraMat = camera.matrix_world
    cameraRot = cameraMat.decompose()[1]
    cameraRotMat = Matrix.Identity(3)
    cameraRotMat.rotate(cameraRot)
    cameraRotMat = cameraRotMat.to_4x4()

    fullRotMat = annoMat @ cameraRotMat
    extMat = locMatrix @ fullRotMat 

    cameraX = cameraRotMat @ Vector((1, 0, 0))

    for table in tableGen.tables:

        # Populate Text Fields from source file
        if table.textFile == None:
            continue
        text_string = table.textFile.as_string()
        text_lines = text_string.splitlines()

        #check that we have enough rows
        row_idx = 0
        for line in text_lines:
            try: row = table.rows[row_idx]
            except IndexError: 
                table.rows.add()
                row = table.rows[row_idx]
            row_idx += 1

        # Set text Fields
        row_idx = 0
        for row in table.rows:
            # Remove extra rows
            if row_idx >= len(text_lines):
                table.rows.remove(row_idx)
                continue

            line = text_lines[row_idx]
            text_list = line.split(',')

            idx = 0
            for item in text_list:
                try:
                    row.textFields[idx].text = item
                except IndexError:
                    row.textFields.add()
                    row.textFields[idx].text = item
                idx += 1
            
            idx = 0
            for textField in row.textFields:
                if idx >= len(text_list):
                    row.textFields.remove(idx)
                idx += 1
                
              
            
            row_idx += 1



        # Fit Card Width & height
        tallest = 0
        widest = 0

        for row in table.rows:
            for textField in row.textFields:
                if textField.textWidth > widest: widest = textField.textWidth
                if textField.textHeight > tallest: tallest = textField.textHeight

        # Scale by res
        res = get_resolution()
        scale = get_scale()
        tallest *= scale / res / 20
        widest *= scale / res / 20


        origin = loc
        col_idx = 0
        header_drawn = False

        row_idx = 0
        for row in table.rows:

            for textField in row.textFields:
                        # Draw the table
            
                textField.textAlignment = 'C'
                textField.textPosition = 'M'
                xDir = fullRotMat @ Vector((1, 0, 0)) * widest
                yDir = fullRotMat @ Vector((0, 1, 0)) * tallest

                if table.use_header and (not header_drawn):
                    xDir *= table.num_columns

                field_origin = origin + xDir * col_idx - yDir * row_idx

                c1 = field_origin
                c2 = field_origin + xDir
                c3 = field_origin + xDir + yDir
                c4 = field_origin + yDir

                coords = [c1,c2,c2,c3,c3,c4,c4,c1]


                draw_lines(1,(0,0,0,1),coords)

                textcard = generate_text_card(
                    context, textField, table, basePoint=field_origin, xDir=xDir, yDir=yDir, cardIdx=0)
                textField['textcard'] = textcard

                if table.use_header and (not header_drawn):
                    header_drawn = True
                    continue

                col_idx += 1
            
            row_idx += 1
            col_idx = 0

            if sceneProps.show_dim_text:
                for row in table.rows:
                    for textField in row.textFields:
                        if 'textcard' in textField:
                            textcard = textField['textcard']
                            draw_text_3D(context, textField, table, myobj, textcard)
            # Work out width




def draw_annotation_endcaps(annotationProps, endcap, p1 , p2, rgb, endcapSize):
    # Draw Line Endcaps
    dotcoord = None
    if endcap == 'D':
        pointcoords = [p1]
        size = endcapSize * get_scale() / 10
        dotcoord = [p1,size]
        draw_points(size, rgb, pointcoords, depthpass=True)


    filledCoords = []
    if endcap == 'T':
        axis = Vector(p1) - Vector(p2)
        line = interpolate3d(Vector((0, 0, 0)), axis, -0.1)
        line = Vector(line) * endcapSize * get_scale() / 100
        perp = line.orthogonal()
        rotangle = annotationProps.endcapArrowAngle - radians(5)
        line.rotate(Quaternion(perp, rotangle))

        for idx in range(12):
            rotangle = radians(360 / 12)
            filledCoords.append(line.copy() + Vector(p1))
            filledCoords.append(Vector((0, 0, 0)) + Vector(p1))
            line.rotate(Quaternion(axis, rotangle))
            filledCoords.append(line.copy() + Vector(p1))

        draw_filled_coords(filledCoords, rgb, polySmooth=False)

    return dotcoord, filledCoords

def set_text(textField, obj, style=None, item=None):

    old_text = textField.text


    if textField.autoFillText:
        textField.text_updated = True
        text_source = textField.textSource

        if text_source == 'DATE':
            textField.text = datetime.now().strftime('%y/%m/%d')

        elif text_source == 'VIEW':
            view = get_view()
            if view is not None:
                textField.text = view.name

        elif text_source == 'NOTES':
            view = get_view()
            textField.text = ''
            for viewField in view.textFields:
                set_text(viewField, None)
                textField.text += viewField.text
                textField.text += '\n'

        elif text_source == 'SCALE':
            view = get_view()
            scaleStr = "{}:{}".format(view.paper_scale, view.model_scale)
            textField.text = scaleStr

            if view.paper_scale_mode == 'IMPERIAL':
                textField.text = view.imp_scale

        elif text_source == 'VIEWNUM':
            view = get_view()
            textField.text = view.view_num


        elif text_source == 'ELEVATION':
            if item == None:
                textField.text = ""
            elif "p1anchorCoord" in item:
                textField.text = format_distance(item['p1anchorCoord'][2])


        elif text_source == 'C_LENGTH': ## TODO: Remove this when I add a curve dimension
            if obj.type == 'CURVE':
                if len(obj.data.splines) > 1:
                    text = "USE ON SINGLE SPLINE CURVE"
                elif obj.scale[0] != 1.0 or obj.scale[1] != 1.0 or obj.scale[1] != 1.0:
                    text = "APPLY SCALE"
                else:
                    length = obj.data.splines[0].calc_length()
                    text = format_distance(length)
                textField.text = text
            else:
                textField.text = "Not a Curve"

        elif text_source == 'TEXT_FILE':
            textField.text = ''
            try:
                for line in textField.textFile.lines:
                    textField.text += line.body
                    textField.text += '\n'
            except AttributeError:
                pass

        elif text_source == 'PROJECT_NAME':
            textField.text = ''
            sceneProps = bpy.context.scene.MeasureItArchProps
            textField.text = sceneProps.project_name

        elif text_source == 'PROJECT_NUMBER':
            textField.text = ''
            sceneProps = bpy.context.scene.MeasureItArchProps
            textField.text = sceneProps.project_number

        elif text_source == 'PROJECT_ADDRESS':
            textField.text = ''
            sceneProps = bpy.context.scene.MeasureItArchProps
            textField.text = sceneProps.project_address

        # CUSTOM PROP
        elif text_source == 'RNAPROP':
            if textField.rnaProp != '':
                try:
                    # TODO: `eval` is evil
                    data = eval(
                        'bpy.data.objects[\'' + obj.name + '\']' + textField.rnaProp)
                    text = str(data)
                    if "location" in textField.rnaProp:
                        text = format_distance(data)

                    textField.text = text
                except:
                    textField.text = 'Bad Data Path'

        if old_text == textField.text:
            textField.text_updated = False

    if style != None and style.all_caps and (style.text_updated or bpy.context.scene.MeasureItArchProps.is_render_draw):
        textField.text = textField.text.upper()


# This is a one off for a project where I need to preview the
# "create dual mesh" Operator from Alessandro Zomparelli's tissue addon.
# Keeping it here untill I can create a pull request for tissue to discuss adding it in there.
def preview_dual(context):
    objs = context.selected_objects
    for myobj in objs:
        if myobj.type == 'MESH':
            mat = myobj.matrix_world
            mesh = myobj.data
            bm = bmesh.new()
            if myobj.mode == 'OBJECT':
                bm.from_object(myobj, bpy.context.view_layer.depsgraph)
            else:
                bm = bmesh.from_edit_mesh(mesh)

            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            edges = bm.edges

            coords = []
            with OpenGL_Settings(None):
                for edge in edges:
                    faces = edge.link_faces
                    for face in faces:
                        center = face.calc_center_median()
                        coords.append(mat @ center)

                draw_lines(3, (0, 0, 0, 0.7), coords, twoPass=True, offset=-0.0005)

def draw_text_3D(context, textobj, textprops, myobj, card):
    # get props

    sceneProps = context.scene.MeasureItArchProps

    if sceneProps.is_vector_draw:
        return

    card[0] = Vector(card[0])
    card[1] = Vector(card[1])
    card[2] = Vector(card[2])
    card[3] = Vector(card[3])
    uvVal = 1.0
    normalizedDeviceUVs = [(-uvVal, -uvVal), (-uvVal, uvVal),
                           (uvVal, uvVal), (uvVal, -uvVal)]

    # i,j,k Basis Vectors
    i = Vector((1, 0, 0))
    j = Vector((0, 1, 0))
    k = Vector((0, 0, 1))

    # Get View rotation
    debug_camera = False
    if sceneProps.is_render_draw or debug_camera:
        viewRot = context.scene.camera.rotation_euler.to_quaternion()
    else:
        viewRot = context.area.spaces[0].region_3d.view_rotation

    # Define Flip Matrix's
    flipMatrixX = Matrix([
        [-1, 0],
        [0, 1]
    ])

    flipMatrixY = Matrix([
        [1, 0],
        [0, -1]
    ])

    # Check Text Cards Direction Relative to view Vector
    # Card Indices:
    #
    #     1----------------2
    #     |                |
    #     |                |
    #     0----------------3

    cardDirX = (card[3] - card[0]).normalized()
    cardDirY = (card[1] - card[0]).normalized()
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
    rot = Quaternion(viewAxisZ, radians(0.01))
    viewAxisX.rotate(rot)
    viewAxisY.rotate(rot)

    if cardDirZ.dot(viewAxisZ) > 0:
        viewDif = viewAxisZ.rotation_difference(cardDirZ)
    else:
        viewAxisZ.negate()
        viewDif = viewAxisZ.rotation_difference(cardDirZ)

    viewAxisX.rotate(viewDif)
    viewAxisY.rotate(viewDif)

    if cardDirX.dot(viewAxisX) < 0:
        flippedUVs = []
        for uv in normalizedDeviceUVs:
            uv = flipMatrixX @ Vector(uv)
            flippedUVs.append(uv)
        normalizedDeviceUVs = flippedUVs

    if cardDirY.dot(viewAxisY) < 0:
        flippedUVs = []
        for uv in normalizedDeviceUVs:
            uv = flipMatrixY @ Vector(uv)
            flippedUVs.append(uv)
        normalizedDeviceUVs = flippedUVs

    # Draw View Axis in Red and Card Axis in Green for debug
    autoflipdebug = sceneProps.debug_flip_text
    if autoflipdebug:
        viewport = [context.area.width, context.area.height]
        lineShader.bind()
        lineShader.uniform_float("Viewport", viewport)
        lineShader.uniform_float("thickness", 4)
        lineShader.uniform_float("finalColor", (1, 0, 0, 1))
        lineShader.uniform_float("offset", 0)

        zero = Vector((0, 0, 0))
        coords = [zero, viewAxisX / 2, zero, viewAxisY]
        batch = batch_for_shader(lineShader, 'LINES', {"pos": coords})
        batch.program_set(lineShader)
        batch.draw()

        lineShader.uniform_float("finalColor", (0, 1, 0, 1))
        coords = [zero, cardDirX / 2, zero, cardDirY]
        batch = batch_for_shader(lineShader, 'LINES', {"pos": coords})
        batch.program_set(lineShader)
        batch.draw()

        print("X dot: " + str(cardDirX.dot(viewAxisX)))
        print("Y dot: " + str(cardDirY.dot(viewAxisY)))

    uvs = []
    for normUV in normalizedDeviceUVs:
        uv = (Vector(normUV) + Vector((1, 1))) * 0.5
        uvs.append(uv)

    # Gets Texture from Object
    width = textobj.textWidth
    height = textobj.textHeight
    dim = width * height * 4

    # Draw Text card for debug
    if sceneProps.show_text_cards:
        coords = [card[0], card[1], card[1], card[2],
                  card[2], card[3], card[3], card[0]]
        draw_lines(1.0, (0.0, 1.0, 0.0, 1.0), coords)



    if 'texture' in textobj and textobj.text != "":
        # np.asarray takes advantage of the buffer protocol and solves the bottleneck here!!!
        texArray = bgl.Buffer(bgl.GL_INT, [1])
        bgl.glGenTextures(1, texArray)

        bgl.glActiveTexture(bgl.GL_TEXTURE0)
        bgl.glBindTexture(bgl.GL_TEXTURE_2D, texArray[0])

        bgl.glTexParameteri(bgl.GL_TEXTURE_2D,
                            bgl.GL_TEXTURE_WRAP_S, bgl.GL_CLAMP_TO_BORDER)
        bgl.glTexParameteri(bgl.GL_TEXTURE_2D,
                            bgl.GL_TEXTURE_WRAP_T, bgl.GL_CLAMP_TO_BORDER)
        bgl.glTexParameteri(bgl.GL_TEXTURE_2D,
                            bgl.GL_TEXTURE_MIN_FILTER, bgl.GL_LINEAR)
        bgl.glTexParameteri(bgl.GL_TEXTURE_2D,
                            bgl.GL_TEXTURE_MAG_FILTER, bgl.GL_LINEAR)
        try:
            tex = bgl.Buffer(bgl.GL_BYTE, dim, np.asarray(
                textobj['texture'], dtype=np.uint8))
            bgl.glTexImage2D(bgl.GL_TEXTURE_2D, 0, bgl.GL_RGBA, width,
                            height, 0, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, tex)
        except AttributeError as atribError:
            print(atribError)
            print("ATTRIBUTE ERROR DRAWING TEXT ON {}".format(myobj.name))
            return

        textobj.texture_updated = False

        # Draw Shader
        textShader.bind()
        textShader.uniform_float("image", 0)

        # Batch Geometry
        batch = batch_for_shader(
            textShader, 'TRI_FAN',
            {
                "pos": card,
                "uv": uvs,
            },
        )

        batch.draw(textShader)
        bgl.glDeleteTextures(1, texArray)
    gpu.shader.unbind()


def generate_end_caps(context, item, capType, capSize, pos, userOffsetVector, midpoint, posflag, flipCaps):
    capCoords = []
    filledCoords = []

    scale = get_scale()

    size = capSize * scale / 1574.804 #FUDGE FACTOR WHYYYY

    distVector = Vector(pos - Vector(midpoint)).normalized()
    norm = distVector.cross(userOffsetVector).normalized()
    line = distVector * size
    arrowAngle = item.endcapArrowAngle

    if flipCaps:
        arrowAngle += radians(180)

    if capType == 99:
        pass

    # Line and Triangle Geometry
    elif capType == 'L' or capType == 'T':
        rotangle = arrowAngle
        line.rotate(Quaternion(norm, rotangle))
        p1 = (pos - line)
        p2 = (pos)
        line.rotate(Quaternion(norm, -(rotangle * 2)))
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

    # Dashed Endcap Geometry
    elif capType == 'D':
        rotangle = radians(-90)
        line = userOffsetVector.copy()
        line.rotate(Quaternion(norm, rotangle))

        # Define Overextension
        capCoords.append(pos)
        capCoords.append(line * size + pos)

        # Define Square
        x = distVector.normalized() * size
        y = userOffsetVector.normalized() * size
        a = 0.35
        b = 0.45

        s1 = (a * x) + (b * y)
        s2 = (b * x) + (a * y)
        s3 = (-a * x) + (-b * y)
        s4 = (-b * x) + (-a * y)

        square = (s1, s2, s3, s4)

        for s in square:
            if posflag < 1:
                s.rotate(Quaternion(norm, rotangle))
            s += pos

        filledCoords.append(square[0])
        filledCoords.append(square[1])
        filledCoords.append(square[2])
        filledCoords.append(square[0])
        filledCoords.append(square[2])
        filledCoords.append(square[3])

    return capCoords, filledCoords


def generate_text_card(
        context, textobj, textProps, rotation=Vector((0, 0, 0)), basePoint=Vector((0, 0, 0)), xDir=Vector((1, 0, 0)),
        yDir=Vector((0, 1, 0)), cardIdx=0):

    """
    Returns a list of 4 Vectors
    """

    width = textobj.textWidth
    height = textobj.textHeight

    scale = get_scale()

    # Define annotation Card Geometry
    resolution = get_resolution()

    # Get font size in pt more stupid fudge factors :(
    size = (textProps.fontSize / 803) * scale

    sx = (width / resolution) * size
    sy = (height / resolution) * size

    cardX = xDir.normalized() * sx
    cardY = yDir.normalized() * sy

    square = [
        basePoint - (cardX / 2),
        basePoint - (cardX / 2) + cardY,
        basePoint + (cardX / 2) + cardY,
        basePoint + (cardX / 2),
    ]

    # pick approprate card based on alignment
    if textProps.textAlignment == 'R':
        aOff = 0.5 * cardX
    elif textProps.textAlignment == 'L':
        aOff = -0.5 * cardX
    else:
        aOff = Vector((0.0, 0.0, 0.0))

    if textProps.textPosition == 'M':
        pOff = 0.5 * cardY
    elif textProps.textPosition == 'B':
        pOff = 1.0 * cardY
    else:
        pOff = Vector((0.0, 0.0, 0.0))

    cardOffset = cardIdx * cardY

    # Define transformation matrices
    rotMat = Matrix.Identity(3)
    rotEuler = Euler(rotation, 'XYZ')
    rotMat.rotate(rotEuler)
    rotMat = rotMat.to_4x4()

    coords = []
    for coord in square:
        coord = Vector(coord) - aOff - pOff - cardOffset
        coord = (rotMat @ (coord - basePoint)) + basePoint
        coords.append(coord)

    return coords


def sortPoints(p1, p2):
    tempDirVec = Vector(p1) - Vector(p2)
    domAxis = get_dom_axis(tempDirVec)

    if p2[domAxis] > p1[domAxis]:
        switchTemp = p1
        p1 = p2
        p2 = switchTemp

    return p1, p2


def get_dom_axis(vector):
    domAxis = 0
    if abs(vector[0]) > abs(vector[1]) and abs(vector[0]) > abs(vector[2]):
        domAxis = 0
    if abs(vector[1]) > abs(vector[0]) and abs(vector[1]) > abs(vector[2]):
        domAxis = 1
    if abs(vector[2]) > abs(vector[0]) and abs(vector[2]) > abs(vector[1]):
        domAxis = 2

    return domAxis


def get_point(v1, mat):
    """
    Get point rotated and relative to parent

    :param v1: point
    :type v1: Vector
    :param mat: matrix to apply
    :type mat: Matrix
    :returns: Vector
    """
    assert isinstance(v1, Vector)

    vt = Vector((v1[0], v1[1], v1[2], 1))
    vt2 = mat @ vt
    return Vector((vt2[0], vt2[1], vt2[2]))


def get_location(mainobject):
    """
    Get location in world space
    """
    # Using World Matrix
    m4 = mainobject.matrix_world
    return [m4[0][3], m4[1][3], m4[2][3]]


def get_arc_data(pointa, pointb, pointc, pointd):
    v1 = Vector((
        pointa[0] - pointb[0],
        pointa[1] - pointb[1],
        pointa[2] - pointb[2]))
    v2 = Vector((
        pointc[0] - pointb[0],
        pointc[1] - pointb[1],
        pointc[2] - pointb[2]))
    v3 = Vector((
        pointd[0] - pointb[0],
        pointd[1] - pointb[1],
        pointd[2] - pointb[2]))

    angle = v1.angle(v2) + v2.angle(v3)

    rclength = pi * 2 * v2.length * (angle / (pi * 2))

    return angle, rclength


def get_mesh_vertices(myobj):
    """ Get vertex data """
    sceneProps = bpy.context.scene.MeasureItArchProps
    try:
        obverts = []
        verts = []
        if myobj.type == 'MESH':
            if myobj.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(myobj.data)
                verts = bm.verts
            else:
                eval_res = sceneProps.eval_mods
                if eval_res or check_mods(myobj):
                    mesh = bpy.data.meshes.new_from_object(myobj, depsgraph =  bpy.context.evaluated_depsgraph_get())
                    verts = mesh.vertices
                else:
                    verts = myobj.data.vertices

            # We're going through every Vertex in the object here
            # probably excessive, should figure out a better way to
            # link dims to verts...

            obverts = [vert.co for vert in verts]

            return obverts
        else:
            return None
    except AttributeError:
        return None


def get_line_vertex(idx, verts):
    """
    A streamlined version of get mesh vertex for line drawing
    """
    try:
        vert = verts[idx].co
    except:
        vert = Vector((0, 0, 0))
    return vert


def archipack_datablock(o):
    """
    Return archipack datablock from object
    """
    try:
        return o.data.archipack_dimension_auto[0]
    except Exception:
        return None


def get_archipack_loc(context, myobj, idx):
    d = archipack_datablock(myobj)
    if d is not None:
        return d.location(context, myobj, idx)
    return None


def get_mesh_vertex(myobj, idx, evalMods, spline_idx=-1):
    context = bpy.context
    coord = get_archipack_loc(context, myobj, idx)
    if coord is not None:
        return coord

    sceneProps = bpy.context.scene.MeasureItArchProps
    verts = []
    coord = Vector((0, 0, 0))


    if myobj.type == 'MESH':
        # Get Vertices
        bm = bmesh.new()
        verts = myobj.data.vertices
        if myobj.mode == 'EDIT':  # From Edit Mesh
            bm = bmesh.from_edit_mesh(myobj.data)
            bm.verts.ensure_lookup_table()
            verts = bm.verts
        else:
            eval_res = sceneProps.eval_mods
            if (eval_res or evalMods) and check_mods(myobj):  # From Evaluated Deps Graph
                bm.from_object(
                    myobj, bpy.context.view_layer.depsgraph)
                bm.verts.ensure_lookup_table()
                verts = bm.verts
        # Get Co-ordinate for Index in Vertices
        if idx < len(verts):
            coord = verts[idx].co
        else:
            if idx != 9999999:
                raise IndexError
            coord = Vector((0,0,0))

    if myobj.type == 'CURVE':
        coord = myobj.data.splines[spline_idx].bezier_points[idx].co



    return coord


def check_mods(myobj):
    goodMods = [
        'DATA_TRANSFER', 'NORMAL_EDIT', 'WEIGHTED_NORMAL', 'UV_PROJECT',
        'UV_WARP', 'ARRAY', 'EDGE_SPLIT', 'MASK', 'MIRROR', 'MULTIRES', 'SCREW',
        'SOLIDIFY', 'SUBSURF', 'TRIANGULATE', 'ARMATURE', 'CAST', 'CURVE',
        'DISPLACE', 'HOOK', 'LAPLACIANDEFORM', 'LATTICE', 'MESH_DEFORM',
        'SHRINKWRAP', 'SIMPLE_DEFORM', 'SMOOTH', 'CORRECTIVE_SMOOTH',
        'LAPLACIANSMOOTH', 'SURFACE_DEFORM', 'WARP', 'WAVE', 'CLOTH',
        'COLLISION', 'DYNAMIC_PAINT', 'PARTICLE_INSTANCE', 'PARTICLE_SYSTEM',
        'SMOKE', 'SOFT_BODY', 'SURFACE', 'SOLIDIFY'
    ]
    if myobj.modifiers is None:
        return False
    for mod in myobj.modifiers:
        if mod.type not in goodMods:
            return False
    return True


def check_vis(item, props):
    context = bpy.context
    inView = False
    if (props.visibleInView == "" or
            props.visibleInView == context.window.view_layer.name):
        inView = True

    if item.visible and props.visible and inView:
        return True
    else:
        return False


def rgb_gamma_correct(rawRGB):
    return Vector((
        pow(rawRGB[0], (1 / 2.2)),
        pow(rawRGB[1], (1 / 2.2)),
        pow(rawRGB[2], (1 / 2.2)),
        rawRGB[3]))


def draw_points(lineWeight, rgb, coords, offset=-0.001, depthpass=False):
    viewport = get_viewport()

    pointShader.bind()
    pointShader.uniform_float("thickness", lineWeight)
    pointShader.uniform_float("Viewport", viewport)
    pointShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
    pointShader.uniform_float("offset", offset)
    pointShader.uniform_float("depthPass", False)
    batch = batch_for_shader(pointShader, 'POINTS', {"pos": coords})
    batch.program_set(pointShader)
    batch.draw()
    gpu.shader.unbind()


def draw_filled_coords(filledCoords, rgb, offset=-0.001, polySmooth=True):
    context = bpy.context
    scene = context.scene
    sceneProps = scene.MeasureItArchProps

    bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
    if not polySmooth:
        bgl.glDisable(bgl.GL_POLYGON_SMOOTH)

    if rgb[3] != 1:
        bgl.glDepthMask(False)

    if sceneProps.is_render_draw:
        bgl.glBlendEquation(bgl.GL_MAX)

    triShader.bind()
    triShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
    triShader.uniform_float("offset", offset)

    batch = batch_for_shader(triShader, 'TRIS', {"pos": filledCoords})
    batch.program_set(triShader)
    batch.draw()
    gpu.shader.unbind()

    bgl.glDisable(bgl.GL_POLYGON_SMOOTH)
    bgl.glBlendEquation(bgl.GL_FUNC_ADD)


def draw_lines(lineWeight, rgb, coords, offset=-0.001, twoPass=False,
               pointPass=False, pointCoords=None):
    context = bpy.context
    scene = context.scene
    sceneProps = scene.MeasureItArchProps
    viewport = get_viewport()

    lineShader.bind()
    lineShader.uniform_float("Viewport", viewport)
    lineShader.uniform_float("thickness", lineWeight)
    lineShader.uniform_float("finalColor", (rgb[0], rgb[1], rgb[2], rgb[3]))
    lineShader.uniform_float("offset", offset)
    gpu.shader.unbind()

    # batch & Draw Shader
    batch3d = batch_for_shader(lineShader, 'LINES', {"pos": coords})

    if rgb[3] == 1 and twoPass:

        bgl.glDepthMask(True)
        lineShader.uniform_float("depthPass", True)
        batch3d.program_set(lineShader)
        batch3d.draw()

    if sceneProps.is_render_draw:
        bgl.glBlendEquation(bgl.GL_MAX)

    bgl.glDepthMask(False)
    lineShader.uniform_float("depthPass", False)
    batch3d.program_set(lineShader)
    batch3d.draw()
    gpu.shader.unbind()

    if pointPass:
        if pointCoords is None:
            pointCoords = coords
        draw_points(lineWeight, rgb, pointCoords, offset)

    bgl.glBlendEquation(bgl.GL_FUNC_ADD)


def cap_extension(dirVec, capSize, capAngle):
    scale = get_scale()
    return dirVec.normalized() / 1000 * capSize * sin(capAngle) * scale

def draw_dim_leaders(myobj, dim, dimProps, points, rotationMatrix, normal):
    pass

def dim_line_extension(capSize):
    scale = get_scale()
    return (capSize / 1000 * scale)


def dim_text_placement(dim, dimProps, origin, dist, distVec, offsetDistance, capSize=0, cardIdx = 0, textField=None):
    # Set Text Alignment
    context = bpy.context
    sceneProps = context.scene.MeasureItArchProps
    flipCaps = False
    dimProps.textPosition = 'T'
    dimLineExtension = 0  # add some extension to the line if the dimension is ext
    normDistVector = distVec.normalized()
    dim.fontSize = dimProps.fontSize

    if dim.textAlignment == 'L':
        dim.textPosition = 'M'
        flipCaps = True
        dimLineExtension = dim_line_extension(capSize)
        origin += Vector((dist / 2 + dimLineExtension * 1.2) * normDistVector)

    elif dim.textAlignment == 'R':
        flipCaps = True
        dim.textPosition = 'M'
        dimLineExtension = dim_line_extension(capSize)
        origin -= Vector((dist / 2 + dimLineExtension * 1.2) * normDistVector)

    square = generate_text_card(
        context, textField, dim, basePoint=origin, xDir=normDistVector, yDir=offsetDistance.normalized() ,cardIdx=cardIdx)

    cardX = square[3] - square[0]
    cardY = square[1] - square[0]

    # Flip if smaller than distance
    if (cardX.length) > dist and sceneProps.use_text_autoplacement:
        if dim.textAlignment == 'C':
            flipCaps = True
            dimLineExtension = dim_line_extension(capSize)
            origin += distVec * -0.5 - (dimLineExtension * normDistVector) - cardX / 2 - cardY / 2
            square = generate_text_card(
                context, textField, dim, basePoint=origin, xDir=normDistVector, yDir=offsetDistance.normalized())
    textField['textcard'] = square
    return (flipCaps, dimLineExtension, origin)


def get_viewport():
    context = bpy.context
    sceneProps = context.scene.MeasureItArchProps

    if sceneProps.is_render_draw:
        return [
            context.scene.render.resolution_x,
            context.scene.render.resolution_y,
        ]
    else:
        return [
            context.area.width,
            context.area.height,
        ]



def z_order_objs(obj_list, extMat, multMat):
    scene = bpy.context.scene
    camera = scene.camera.data
    ordered_obj_list = []
    to_sort = []

    for obj in obj_list:
        if type(obj) is bpy.types.DepsgraphObjectInstance:
            obj = obj.object
        bound_box = obj.bound_box
        point_in_camera = False
        dist_sum = 0
        for point in bound_box:
            loc = obj.matrix_world @ Vector(point)
            if extMat is not None:
                if multMat:
                    loc = extMat @ loc
                else:
                    loc = extMat @ Vector(point)

            point_dist = get_camera_z_dist(loc)
            dist_sum += point_dist

            # is this point in front of the camera?
            if point_dist > 0:
                point_in_camera = True

        # If object has no bounds infront of the camera ignore it
        if point_in_camera:
            obj_dist = dist_sum * (1/8)
            to_sort.append(Dist_Sort(obj, obj_dist))
        else:
            print("Bounding Box Not in Camera: {} Culled".format(obj.name))

    to_sort.sort(reverse=True)
    ordered_obj_list = [item.item for item in to_sort]
    return ordered_obj_list


def z_order_faces(face_list, obj):
    ordered_face_list = []
    to_sort = []

    for face in face_list:
        face_dist = get_camera_z_dist(obj.matrix_world @ face.calc_center_median())

        # If the face is behind the camera, and we're culling faces Ignore it
        if face_dist < 0:
            continue

        to_sort.append(Dist_Sort(face, face_dist))

    to_sort.sort(reverse=True)
    ordered_face_list = [item.item for item in to_sort]

    return ordered_face_list


class Dist_Sort(object):
    item = None
    dist = 0

    def __init__(self, item, dist):
        self.item = item
        self.dist = dist

    def __lt__(self, other):
        return self.dist < other.dist
    def __gt__(self,other):
        return self.dist > other.dist
    def __eq__(self,other):
        return self.dist == other.dist

class Inst_Sort(object):
    name = None
    object = None
    matrix_world = None
    is_instance = False
    parent = None
    bound_box = None

    def __init__(self, obj_int):
        self.name = obj_int.object.name + "_Instance"
        self.object = obj_int.object
        self.bound_box = obj_int.object.bound_box
        self.matrix_world = obj_int.matrix_world.copy()
        self.is_instance = obj_int.is_instance
        self.parent = obj_int.parent

def check_obj_vis(myobj,custom_call):
    scene = bpy.context.scene
    sceneProps = scene.MeasureItArchProps

    if not sceneProps.is_render_draw:
        return (myobj.visible_get() or custom_call) and not myobj.hide_get()
    else:
        return custom_call or not myobj.hide_render



def draw3d_loop(context, objlist, svg=None, dxf = None, extMat=None, multMat=False,custom_call=False):
    """
    Generate all OpenGL calls
    """
    scene = context.scene
    sceneProps = scene.MeasureItArchProps

    if sceneProps.is_render_draw:
        startTime = time.time()

    totalobjs = len(objlist)
    #preview_dual(context)
    if sceneProps.is_vector_draw:
        objlist = z_order_objs(objlist, extMat, multMat)



    for idx, myobj in enumerate(objlist, start=1):
        if sceneProps. is_render_draw:
            print("Rendering Object: " + str(idx) + " of: " +
                  str(totalobjs) + " Name: " + safe_name(myobj.name))

        if check_obj_vis(myobj,custom_call):
            mat = myobj.matrix_world
            if extMat is not None:
                if multMat:
                    mat = extMat @ mat
                else:
                    mat = extMat

            # HATCHES
            if (sceneProps.is_vector_draw or sceneProps.is_dxf_draw) and (myobj.type == 'MESH' or myobj.type =="CURVE"):
                draw_material_hatches(context, myobj, mat, svg=svg, dxf=dxf)

            # DIMS ANNO LINES
            if 'LineGenerator' in myobj:
                lineGen = myobj.LineGenerator
                if not sceneProps.hide_linework or sceneProps.is_render_draw:
                    draw_line_group(context, myobj, lineGen, mat, svg=svg, dxf=dxf)

            if 'AnnotationGenerator' in myobj:
                annotationGen = myobj.AnnotationGenerator
                draw_annotation(context, myobj, annotationGen, mat, svg=svg, dxf=dxf)

            if 'TableGenerator' in myobj:
                tableGen = myobj.TableGenerator
                draw_table(context, myobj, tableGen, mat, svg=svg, dxf=dxf)

            if 'DimensionGenerator' in myobj:
                DimGen = myobj.DimensionGenerator

                for alignedDim in DimGen.alignedDimensions:
                    draw_alignedDimension(
                        context, myobj, DimGen, alignedDim, svg=svg, dxf=dxf)

                for angleDim in DimGen.angleDimensions:
                    draw_angleDimension(
                        context, myobj, DimGen, angleDim, mat, svg=svg, dxf=dxf)

                for axisDim in DimGen.axisDimensions:
                    draw_axisDimension(context, myobj, DimGen,
                                       axisDim, mat, svg=svg,dxf=dxf )

                for boundsDim in DimGen.boundsDimensions:
                    draw_boundsDimension(
                        context, myobj, DimGen, boundsDim, mat, svg=svg, dxf=dxf)

                for arcDim in DimGen.arcDimensions:
                    draw_arcDimension(context, myobj, DimGen,
                                      arcDim, mat, svg=svg, dxf=dxf)

                for areaDim in DimGen.areaDimensions:
                    draw_areaDimension(context, myobj, DimGen,
                                       areaDim, mat, svg=svg, dxf=dxf)


    # Draw Instanced Objects
    view = get_view()
    if not custom_call and not view.skip_instances:

        deps = bpy.context.view_layer.depsgraph

        objlist = [Inst_Sort(obj_int) for obj_int in deps.object_instances]
        #obj_inst_list = deps.object_instances

        #if sceneProps.is_vector_draw:
        #    objlist = z_order_objs(objlist, extMat, multMat)
        num_instances = len(objlist)
        for idx,obj_int in enumerate(objlist , start=1):
            #try:
            #    obj_int = obj_inst_list[idx-1]
            #except IndexError:
            #    print('index error for obj: {}'.format(obj.name))
            #    continue
            if obj_int.is_instance:
                myobj = obj_int.object
                parent = obj_int.parent

                if myobj.type == 'MESH' and parent.type == 'CURVE':
                    if sceneProps.is_render_draw:
                        print(f'Skipping: {myobj.name}')
                    continue

                mat = obj_int.matrix_world

                if sceneProps.is_render_draw:
                    try:
                        print("Rendering Instance Object: " + str(idx) + " of: " +
                            str(num_instances) + " Name: " + safe_name(myobj.name + '_Instance'))
                    except UnicodeDecodeError:
                        print("UNICODE ERROR ON OBJECT NAME")

                if (sceneProps.is_vector_draw or sceneProps.is_dxf_draw) and (myobj.type == 'MESH' or myobj.type =="CURVE"):
                    draw_material_hatches(context, myobj, mat, svg=svg, dxf=dxf, is_instance_draw=True)

                if 'LineGenerator' in myobj:
                    lineGen = myobj.LineGenerator
                    draw_line_group(context, myobj, lineGen, mat, svg=svg, dxf=dxf, is_instance_draw=True)

                if 'AnnotationGenerator' in myobj and myobj.AnnotationGenerator.num_annotations != 0:
                    annotationGen = myobj.AnnotationGenerator
                    draw_annotation(
                        context, myobj, annotationGen, mat, svg=svg, dxf=dxf, instance=obj_int)

                if sceneProps.instance_dims:
                    if 'DimensionGenerator' in myobj and myobj.DimensionGenerator.measureit_arch_num != 0:
                        DimGen = myobj.DimensionGenerator
                        mat = obj_int.matrix_world
                        for alignedDim in DimGen.alignedDimensions:
                            draw_alignedDimension(
                                context, myobj, DimGen, alignedDim, mat=mat, svg=svg, dxf=dxf)
                        for angleDim in DimGen.angleDimensions:
                            draw_angleDimension(
                                context, myobj, DimGen, angleDim, mat, svg=svg, dxf=dxf)
                        for axisDim in DimGen.axisDimensions:
                            draw_axisDimension(
                                context, myobj, DimGen, axisDim, mat, svg=svg, dxf=dxf)
    if sceneProps.is_render_draw:
        endTime = time.time()
        print("Draw 3D Loop Time: " + str(endTime - startTime))

def setup_dim_text(myobj,dim,dimProps,dist,origin,distVector,offsetDistance, is_area=False):
    context =bpy.context
    sceneProps = context.scene.MeasureItArchProps
    if len(dim.textFields) == 0:
        dim.textFields.add()

    dimText = dim.textFields[0]

    # format text and update if necessary
    if not dim.use_custom_text:

        distanceText = format_distance(dist,dim=dim)
        if is_area:
            distanceText = format_area(dist, dim=dim)
        if dimText.text != distanceText:
            dimText.text = distanceText
            dimText.text_updated = True

    idx = 0
    flipCaps = None
    dimLineExtension = None
    for textField in dim.textFields:
        set_text(textField, myobj)
        placementResults = dim_text_placement(
            dim, dimProps, origin, dist, distVector, offsetDistance, dimProps.endcapSize, cardIdx=idx, textField=textField)
        if idx == 0:
            flipCaps = placementResults[0]
            dimLineExtension = placementResults[1]
            origin = placementResults[2]
        if sceneProps.show_dim_text:
            draw_text_3D(context, textField, dimProps, myobj, textField['textcard'])
        idx += 1

    return (flipCaps,dimLineExtension,origin)
