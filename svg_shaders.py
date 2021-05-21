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
from fontTools import ttLib

from math import fabs, sqrt
from mathutils import Vector, Matrix
from sys import getrecursionlimit, setrecursionlimit

from .measureit_arch_utils import get_view, interpolate3d, get_camera_z_dist, recursionlimit

depthbuffer = None

def svg_line_shader(item, itemProps, coords, thickness, color, svg, parent=None,
                    dashed=False, mat=Matrix.Identity(4)):
    idName = item.name + "_lines"
    dash_id_name = idName = item.name + "_dashed_lines"
    svgColor = get_svg_color(color)
    if "pointPass" in item and item.pointPass:
        cap = 'round'
    else:
        cap = 'butt'

    lines = svg.g(id=idName, stroke=svgColor,
                  stroke_width=thickness, stroke_linecap=cap)
    if parent:
        parent.add(lines)
    else:
        svg.add(lines)

    draw_hidden = 'lineDrawHidden' in itemProps and itemProps.lineDrawHidden
    dash_col = svgColor
    dash_weight = thickness
    if draw_hidden:
        dash_col = get_svg_color(itemProps.lineHiddenColor)
        dash_weight = itemProps.lineHiddenWeight

    if "lineHiddenDashScale" in itemProps:
        dash_size = itemProps.lineHiddenDashScale
        dash_space = (itemProps.lineDashSpace *4) - 1
        dash_val = "{},{}".format(dash_size, dash_size*dash_space)
    else:
        dash_val = "5,5"

    dashed_lines = svg.g(id=dash_id_name, stroke=dash_col, stroke_width=dash_weight,
                    stroke_dasharray=dash_val, stroke_linecap='butt')

    if parent:
        parent.add(dashed_lines)
    else:
        svg.add(dashed_lines)

    # Get Depth Buffer as list
    sceneProps = bpy.context.scene.MeasureItArchProps
    global depthbuffer
    if 'depthbuffer' in sceneProps and depthbuffer is None:
        depthbuffer = sceneProps['depthbuffer'].to_list()

    for x in range(0, len(coords) - 1, 2):
        line_segs = depth_test(coords[x], coords[x + 1], mat, itemProps, depthbuffer)
        for line in line_segs:
            vis = line[0]
            p1 = line[1]
            p2 = line[2]
            if vis == -1:
                continue

            if vis or draw_hidden:
                p1ss = get_render_location(mat @ Vector(p1))
                p2ss = get_render_location(mat @ Vector(p2))
                line_draw = svg.line(start=tuple(p1ss), end=tuple(p2ss))
                if vis and not dashed:
                    lines.add(line_draw)
                elif vis and dashed:
                    dashed_lines.add(line_draw)
                elif not vis and draw_hidden:
                    dashed_lines.add(line_draw)



def svg_fill_shader(item, coords, color, svg, parent=None):
    if camera_cull(coords):
        return
    coords_2d = []
    idName = item.name + "_fills"
    svgColor = svgwrite.rgb(color[0] * 100, color[1] * 100, color[2] * 100, '%')
    fills = svg.g(id=idName, fill=svgColor)
    parent.add(fills)

    for coord in coords:
        coords_2d.append(get_render_location(coord))

    for x in range(0, len(coords_2d) - 1, 3):
        tri = svg.polygon(
            points=[coords_2d[x], coords_2d[x + 1], coords_2d[x + 2]])
        fills.add(tri)

def svg_circle_shader(item, point, rad, color, svg, parent=None):
    if camera_cull([point]):
        return

    idName = item.name + "_fills"
    svgColor = svgwrite.rgb(color[0] * 100, color[1] * 100, color[2] * 100, '%')
    fills = svg.g(id=idName, fill=svgColor)
    parent.add(fills)

    point_2d = get_render_location(point)

    circle = svg.circle(center=point_2d,r=rad)
    fills.add(circle)

def svg_poly_fill_shader(item, coords, color, svg, parent=None, line_color=(0, 0, 0,0), lineWeight=0, fillURL=''):
    if camera_cull(coords):
        return

    coords_2d = []
    idName = item.name + "_fills"

    fill = svgwrite.rgb(color[0] * 100, color[1] * 100, color[2] * 100, '%')

    fillOpacity = color[3]
    lineColor = svgwrite.rgb(
        line_color[0] * 100, line_color[1] * 100, line_color[2] * 100, '%')
    lineOpacity = lineColor[3]
    solidfill = svg.g(id=idName, fill=fill, fill_opacity=fillOpacity,
                      stroke=lineColor, stroke_width=lineWeight, stroke_opacity=lineOpacity,stroke_linejoin="round")
    parent.add(solidfill)

    for coord in coords:
        coords_2d.append(get_render_location(coord))

    poly = svg.polygon(points=coords_2d)
    solidfill.add(poly)

    if fillURL != '':
        fill = fillURL
        patternfill = svg.g(id=idName, fill=fill, fill_opacity=item.patternOpacity,
                            stroke=lineColor, stroke_width=lineWeight, stroke_opacity=lineOpacity,stroke_linejoin="round")
        parent.add(patternfill)
        patternfill.add(poly)


def svg_text_shader(item, style, text, mid, textCard, color, svg, parent=None):

    # Card Indicies:
    #
    #     1----------------2
    #     |                |
    #     |                |
    #     0----------------3

    if camera_cull(textCard):
        return

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
    if style.textAlignment == 'L':
        text_position = leftVec
        text_anchor = 'start'
        # position_flip = rightVec
        anchor_flip = 'end'

    if style.textAlignment == 'C':
        text_position = midVec
        text_anchor = 'middle'
        # position_flip = midVec
        anchor_flip = 'middle'

    if style.textAlignment == 'R':
        text_position = rightVec
        text_anchor = 'end'
        # position_flip = leftVec
        anchor_flip = 'start'

    xvec = Vector((999, 1)).normalized() #again we need to make this slightly off axis to make rotation consistent for orthogonal views
    rotation = math.degrees(dirVec.angle_signed(xvec))
    print("{} Rotation: {}".format(item.name, rotation))
    badrot_1 = rotation < -90 and rotation > -180
    badrot_2 = rotation > 90 and rotation < 180
    if badrot_1 or badrot_2:
        rotation += 180
        # text_position = position_flip
        text_anchor = anchor_flip
        heightOffset = -heightOffset
        print('{} did flip'.format(item.name))

    #print(heightOffset)
    text_position += heightOffset
    view = get_view()
    res = bpy.context.scene.MeasureItArchProps.default_resolution
    if view is not None:
        res = view.res

    try:
        font_file = style.font.filepath
        tt = ttLib.TTFont(font_file, verbose=1)
        font_family = shortName(tt)[0]
    except:
        font_family = "Open Sans"

    parent.add(svg.text(text, insert=tuple(text_position), fill=svgColor, **{
        'transform': 'rotate({} {} {})'.format(
            rotation,
            text_position[0],
            text_position[1]
        ),

        # I wish i could tell you why this fudge factor is necessary, but for some reason
        # spec-ing svg units in inches and using this factor for text size is the only way to get
        # sensible imports in both inkscape and illustrator
        'font-size': round(style.fontSize * 4.166666667 / (300 / res), 2),
        'font-family':  font_family,
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


def clear_db():
    global depthbuffer
    depthbuffer = None
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

def camera_cull(points):
    camera = bpy.context.scene.camera.data
    should_cull = []
    for point in points:
        dist = get_camera_z_dist(point)
        if dist < camera.clip_start or dist > camera.clip_end:
            should_cull.append(True)
        else:
            should_cull.append(False)

    if any(cull is False for cull in should_cull):
        return False
    else:
        return True

def true_z_buffer(context, zValue):
    camera = context.scene.camera.data
    if camera.type == 'ORTHO':
        nearClip = camera.clip_start
        farClip = camera.clip_end

        depth = zValue * (farClip - nearClip) + nearClip - 0.09
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

def depth_test(p1, p2, mat, item, depthbuffer):
    scene = bpy.context.scene

    # Don't depth test if out of culling
    if camera_cull([mat @ Vector(p1), mat @ Vector(p2)]):
        return [[-1, p1, p2]]

    # Don't Depth test if not enabled
    if not scene.MeasureItArchProps.vector_depthtest or item.inFront:
        return [[True, p1, p2]]

    p1Local = mat @ Vector(p1)
    p2Local = mat @ Vector(p2)

    # Get Screen Space Points
    p1ss = get_ss_point(p1Local)
    p2ss = get_ss_point(p2Local)

    # Length in ss is ~number of pixels. use for num of visibility samples
    ss_length_vec = p1ss-p2ss
    ss_samples = math.ceil(ss_length_vec.length/2)
    if ss_samples < 1: ss_samples = 1

    last_vis_state = check_visible(item, p1Local)
    line_segs = []
    seg_start = p1
    distVector = Vector(p1) - Vector(p2)
    dist = distVector.length
    iter_dist = fabs((dist / ss_samples))

    for i in range(1,ss_samples):
        p_check = interpolate3d(Vector(p1), Vector(p2), iter_dist * i)
        p_check_vis = check_visible(item, mat @ Vector(p_check))

        line = [last_vis_state, seg_start, p_check]

        if last_vis_state is not p_check_vis:
            line_segs.append(line)
            seg_start = p_check
            last_vis_state = p_check_vis

    line_segs.append([last_vis_state, seg_start, p2])

    return line_segs


def clamp(minimum, x, maximum):
    return max(minimum, min(x, maximum))

# For getting the depthbuffer ss point
def get_ss_point(point):
    context = bpy.context
    scene = bpy.context.scene
    render = scene.render

    #Get Render info
    render_scale = scene.render.resolution_percentage / 100
    width = int(render.resolution_x * render_scale)
    height = int(render.resolution_y * render_scale)

    # Get Screen Space Points
    p1ss = get_render_location(point)
    p1ss = Vector((p1ss[0], height - p1ss[1]))

    return p1ss

def check_visible(item, point):
    context = bpy.context
    scene = context.scene
    camera = scene.camera.data
    render = scene.render
    #Set Z-offset
    z_offset = 0.1
    if 'lineDepthOffset' in item:
        z_offset += item.lineDepthOffset / 10

    dist = get_camera_z_dist(point)
    if dist < 0:
        return -1

    if dist < camera.clip_start or dist > camera.clip_end:
        return -1

    #Get Render info
    render_scale = scene.render.resolution_percentage / 100
    width = int(render.resolution_x * render_scale)

    point_ss = get_ss_point(point)
    point_clip = get_clip_space_coord(point)

    # Get Depth buffer Pixel Index based on SS Point
    pxIdx1 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1)
    pxIdx2 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1)

    #pxIdx3 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) + width
    #pxIdx4 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) + width

    #pxIdx5 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) - width
    #pxIdx6 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) - width

    #pxIdx7 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) + 1
    #pxIdx8 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) + 1

    #pxIdx9 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) - 1
    #pxIdx10 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) - 1

    #samples = [pxIdx1,pxIdx2,pxIdx3,pxIdx4,pxIdx5,pxIdx6,pxIdx7,pxIdx8,pxIdx9,pxIdx10]

    samples = [pxIdx1,pxIdx2]

    point_depth = 0
    for sample in samples:
        val = get_bufffer_at_idx(pxIdx1)
        val = true_z_buffer(context, val)
        point_depth += val

    point_depth /= len(samples)

    # Get Depth From Clip Space point
    point_vecdepth = (point_clip[2]) - z_offset

    # Check Clip space point against depth buffer value
    pointVisible = point_depth > point_vecdepth

    return pointVisible

def get_bufffer_at_idx(idx):
    # Get Depth Buffer Value buffer value
    try:
        point_depth = depthbuffer[idx]
    except IndexError:
        #print('Index not in Depth Buffer:{}'.format(idx))
        point_depth = 0
    return point_depth


# From https://gist.github.com/pklaus/dce37521579513c574d0
FONT_SPECIFIER_NAME_ID = 4
FONT_SPECIFIER_FAMILY_ID = 1
def shortName(font):
    """Get the short name from the font's names table"""
    name = ""
    family = ""
    for record in font['name'].names:
        if b'\x00' in record.string:
            name_str = record.string.decode('utf-16-be')
        else:
            name_str = record.string.decode('utf-8')
        if record.nameID == FONT_SPECIFIER_NAME_ID and not name:
            name = name_str
        elif record.nameID == FONT_SPECIFIER_FAMILY_ID and not family:
            family = name_str
        if name and family: break
    return name, family


def get_svg_color(color):
    return svgwrite.rgb(color[0] * 100, color[1] * 100, color[2] * 100, '%')
