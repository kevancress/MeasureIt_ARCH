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

# <pep8 compliant>

# ----------------------------------------------------------
#
# Collection of SVG "Shaders" for the Various Draw Functions.
# Author: Kevan Cress
#
# ----------------------------------------------------------
import bpy
import bpy_extras.object_utils as object_utils
import math
import svgwrite

from math import fabs, sqrt
from mathutils import Vector, Matrix

from .measureit_arch_utils import get_view


def svg_line_shader(item, coords, thickness, color, svg, parent=None,
                    dashed=False, mat=Matrix.Identity(4)):
    idName = item.name + "_lines"
    svgColor = svgwrite.rgb(color[0] * 100, color[1] * 100, color[2] * 100, '%')

    cap = 'round'
    try:
        if item.pointPass:
            cap = 'round'
        else:
            cap = 'butt'
    except:
        pass

    lines = svg.g(id=idName, stroke=svgColor,
                  stroke_width=thickness, stroke_linecap=cap)
    if dashed:
        lines = svg.g(id=idName, stroke=svgColor, stroke_width=thickness,
                      stroke_dasharray="5,5", stroke_linecap='butt')

    if parent:
        parent.add(lines)
    else:
        svg.add(lines)

    for x in range(0, len(coords) - 1, 2):
        vis, p1, p2 = check_visible(coords[x], coords[x + 1], mat, item)
        if vis:
            p1ss = get_render_location(mat @ Vector(p1))
            p2ss = get_render_location(mat @ Vector(p2))
            line = svg.line(start=tuple(p1ss), end=tuple(p2ss))
            lines.add(line)


def svg_fill_shader(item, coords, color, svg, parent=None):
    coords_2d = []
    idName = item.name + "_fills"
    svgColor = svgwrite.rgb(color[0] * 100, color[1] * 100, color[2] * 100, '%')
    fills = svg.g(id=idName, fill=svgColor)
    parent.add(fills)

    for coord in coords:
        coords_2d.append(get_render_location(coord))

    for x in range(0, len(coords_2d) - 1, 3):
        tri = svg.polygon(
            points=[coords_2d[x], coords_2d[x+1], coords_2d[x+2]])
        fills.add(tri)


def svg_poly_fill_shader(item, coords, color, svg, parent=None, line_color=(0, 0, 0), lineWeight=0, fillURL=''):
    coords_2d = []
    idName = item.name + "_fills"

    fill = svgwrite.rgb(color[0]*100, color[1]*100, color[2]*100, '%')

    fillOpacity = color[3]
    lineColor = svgwrite.rgb(
        line_color[0]*100, line_color[1]*100, line_color[2]*100, '%')
    solidfill = svg.g(id=idName, fill=fill, opacity=fillOpacity,
                      stroke=lineColor, stroke_width=lineWeight)
    parent.add(solidfill)

    for coord in coords:
        coords_2d.append(get_render_location(coord))

    poly = svg.polygon(points=coords_2d)
    solidfill.add(poly)

    if fillURL != '':
        fill = fillURL
        patternfill = svg.g(id=idName, fill=fill, opacity=item.patternOpacity,
                            stroke=lineColor, stroke_width=lineWeight)
        parent.add(patternfill)
        patternfill.add(poly)


def svg_text_shader(item, text, mid, textCard, color, svg, parent=None):

    # Card Indicies:
    #
    #     1----------------2
    #     |                |
    #     |                |
    #     0----------------3

    text_position = get_render_location(mid)
    svgColor = svgwrite.rgb(color[0] * 100, color[1] * 100, color[2] * 100, '%')
    ssp0 = get_render_location(textCard[0])
    ssp1 = get_render_location(textCard[1])
    # ssp2 = get_render_location(textCard[2])
    ssp3 = get_render_location(textCard[3])

    cardHeight = Vector(ssp1) - Vector(ssp0)

    dirVec = Vector(ssp3) - Vector(ssp0)

    heightOffsetAmount = 1 / 8 * cardHeight.length
    heightOffset = Vector((dirVec[1], -dirVec[0])).normalized()

    heightOffset *= heightOffsetAmount

    leftVec = Vector(ssp0)
    rightVec = Vector(ssp3)
    midVec = (leftVec + rightVec) / 2

    if dirVec.length == 0:
        return

    text_position = (0, 0)
    text_anchor = 'start'
    if item.textAlignment == 'L':
        text_position = leftVec
        text_anchor = 'start'
        # position_flip = rightVec
        anchor_flip = 'end'

    if item.textAlignment == 'C':
        text_position = midVec
        text_anchor = 'middle'
        # position_flip = midVec
        anchor_flip = 'middle'

    if item.textAlignment == 'R':
        text_position = rightVec
        text_anchor = 'end'
        # position_flip = leftVec
        anchor_flip = 'start'

    rotation = math.degrees(dirVec.angle_signed(Vector((1, 0))))
    if rotation > 90 or rotation < -90:
        rotation += 180
        # text_position = position_flip
        text_anchor = anchor_flip
        heightOffset = -heightOffset
        print('did flip')

    print(heightOffset)
    text_position += heightOffset
    view = get_view()
    res = bpy.context.scene.MeasureItArchProps.default_resolution
    if view is not None:
        res = view.res

    parent.add(svg.text(text, insert=tuple(text_position), fill=svgColor, **{
        'transform': 'rotate({} {} {})'.format(
            rotation,
            text_position[0],
            text_position[1]
        ),

        # I wish i could tell you why this fudge factor is necessary, but for some reason
        # spec-ing svg units in inches and using this factor for text size is the only way to get
        # sensible imports in both inkscape and illustrator
        'font-size': round(item.fontSize * 4.166666667 / (300 / res), 2),
        'font-family': 'Helvetica',
        'text-anchor': text_anchor,
        'text-align': text_anchor
    }))


def svg_line_pattern_shader(pattern, svg, objs, weight, color, size):
    svgColor = svgwrite.rgb(color[0] * 100, color[1] * 100, color[2] * 100, '%')

    for obj in objs:
        mesh = obj.data
        edges = mesh.edges
        for edge in edges:
            pair = []
            for idx in edge.vertices:
                ssp = (mesh.vertices[idx].co[0] * size,
                       mesh.vertices[idx].co[1] * size)
                pair.append(ssp)
            pattern.add(svg.line(start=tuple(pair[0]), end=tuple(
                pair[1]), stroke_width=weight, stroke=svgColor))


# --------------------------------------------------------------------
# Get position in final render image
# (Z < 0 out of camera)
# return 2d position
# --------------------------------------------------------------------
def get_render_location(mypoint):
    scene = bpy.context.scene
    render_scale = scene.render.resolution_percentage / 100

    width = int(scene.render.resolution_x * render_scale)
    height = int(scene.render.resolution_y * render_scale)

    v1 = Vector(mypoint)

    co_2d = object_utils.world_to_camera_view(scene, scene.camera, v1)
    # Get pixel coords

    return [(co_2d.x * width), height - (co_2d.y * height)]


def get_clip_space_coord(mypoint):
    scene = bpy.context.scene

    v1 = Vector(mypoint)
    co_camera_space = object_utils.world_to_camera_view(
        scene, scene.camera, v1)

    co_clip = Vector((co_camera_space.x, co_camera_space.y, co_camera_space.z))

    return co_clip


def true_z_buffer(context, zValue):
    camera = context.scene.camera.data
    if camera.type == 'ORTHO':
        nearClip = camera.clip_start
        farClip = camera.clip_end

        depth = zValue * (farClip - nearClip) + nearClip
        return depth

    elif camera.type == 'PERSP':
        nearClip = camera.clip_start
        farClip = camera.clip_end

        z_ndc = 2.0 * zValue - 1.0
        depth = 2.0 * nearClip * farClip / \
            (farClip + nearClip - z_ndc * (farClip - nearClip))
        return depth

    else:
        return zValue


def check_visible(p1, p2, mat, item, numIterations=0):
    context = bpy.context
    scene = bpy.context.scene
    render = scene.render

    if not scene.MeasureItArchProps.vector_depthtest:
        return True, p1, p2

    # print('Drawing: ' + item.name)
    z_offset = 0.1
    if 'lineDepthOffset' in item:
        z_offset += item.lineDepthOffset / 10

    p1Visible = True
    p2Visible = True

    sceneProps = bpy.context.scene.MeasureItArchProps
    if 'depthbuffer' in sceneProps:
        depthbuffer = sceneProps['depthbuffer'].to_list()

    render_scale = scene.render.resolution_percentage / 100
    width = int(render.resolution_x * render_scale)
    height = int(render.resolution_y * render_scale)

    # Get Screen Space Points
    p1ss = get_render_location(mat @ Vector(p1))
    p1ss = Vector((p1ss[0], height - p1ss[1]))
    p2ss = get_render_location(mat @ Vector(p2))
    p2ss = Vector((p2ss[0], height - p2ss[1]))

    # Get Clip Space Points
    p1clip = get_clip_space_coord(mat @ Vector(p1))
    p2clip = get_clip_space_coord(mat @ Vector(p2))

    # Get Buffer Index and depthbuffer value based on SS Point
    p1pxIdx = int(((width * round(p1ss[1])) + round(p1ss[0]) - 1) * 1)
    p2pxIdx = int(((width * round(p2ss[1])) + round(p2ss[0]) - 1) * 1)

    try:
        p1depth = depthbuffer[p1pxIdx]
    except IndexError:
        print('Index not in Depth Buffer: ' + str(p1pxIdx) + ', ' + str(p2pxIdx))
        p1Visible = True
        p1depth = 0

    try:
        p2depth = depthbuffer[p2pxIdx]
    except IndexError:
        print('Index not in Depth Buffer: ' + str(p1pxIdx) + ', ' + str(p2pxIdx))
        p2Visible = True
        p2depth = 0

    p1depth = true_z_buffer(context, p1depth)
    p2depth = true_z_buffer(context, p2depth)

    # Get Depth From Clip Space point
    p1vecdepth = (p1clip[2]) - z_offset
    p2vecdepth = (p2clip[2]) - z_offset

    # Check Clip space point against depth buffer value
    # print('')
    # print('p1')
    # print(p1clip)
    # print(str(p1depth) + ' vs ' + str(p1vecdepth) + ' at Coords: ' + str(p1ss[0]) + "," + str(p1ss[1]) + 'Index: ' + str(p1pxIdx))
    if p1depth > p1vecdepth:
        p1Visible = True
    else:
        p1Visible = False
        # print('p1 not visible')

    # print('')

    # print('p2')
    # print(p2clip)
    # print(str(p2depth) + ' vs ' + str(p2vecdepth) + ' at Coords: ' + str(p2ss[0]) + "," + str(p2ss[1]) + 'Index: ' + str(p2pxIdx))
    if p2depth > p2vecdepth:
        p2Visible = True
    else:
        p2Visible = False
        # print('p2 not visible')

    if p1Visible and p2Visible:
        # print('vis test passed')
        return True, p1, p2
    elif not p1Visible and not p2Visible:
        # print('vis test failed')
        return False, p1, p2
    else:
        vis = False
        maxIter = 3

        if p1Visible and not p2Visible:
            pass
        else:
            temp = p1
            p1 = p2
            p2 = temp

        if numIterations <= maxIter:
            numIterations += 1
            distVector = Vector(p1) - Vector(p2)
            dist = distVector.length
            p3 = interpolate3d(p1, p2, fabs(dist - (dist / maxIter) * numIterations))
            vis, p1, p2 = check_visible(p1, p3, mat, item, numIterations=numIterations)
        return vis, p1, p2


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
# Distance between 2 points in 3D space
# v1: first point
# v2: second point
# locx/y/z: Use this axis
# return: distance
# --------------------------------------------------------------------
def distance(v1, v2, locx=True, locy=True, locz=True):
    x = sqrt((v2[0] - v1[0]) ** 2 + (v2[1] - v1[1])
             ** 2 + (v2[2] - v1[2]) ** 2)

    # If axis is not used, make equal both (no distance)
    v1b = [v1[0], v1[1], v1[2]]
    v2b = [v2[0], v2[1], v2[2]]
    if not locx:
        v2b[0] = v1b[0]
    if not locy:
        v2b[1] = v1b[1]
    if not locz:
        v2b[2] = v1b[2]

    xloc = sqrt((v2b[0] - v1b[0]) ** 2 + (v2b[1] - v1b[1])
                ** 2 + (v2b[2] - v1b[2]) ** 2)

    return x, xloc


def get_view():
    scene = bpy.context.scene
    ViewGen = scene.ViewGenerator
    view = None

    try:
        view = ViewGen.views[ViewGen.active_index]
    except:
        view = None

    return view
