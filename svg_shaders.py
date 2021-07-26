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
import bmesh
import time
import bpy_extras.object_utils as object_utils
import math
import svgwrite
from fontTools import ttLib

from math import fabs, sqrt
from mathutils import Vector, Matrix
from sys import getrecursionlimit, setrecursionlimit

from .measureit_arch_utils import get_view, interpolate3d, get_camera_z_dist, recursionlimit

depthbuffer = None
facemap = []

def svg_line_shader(item, itemProps, coords, thickness, color, svg, parent=None, mat=Matrix.Identity(4)):
    idName = item.name + "_lines"
    dash_id_name = idName = item.name + "_dashed_lines"
    dashed = False

    if "lineDrawDashed" in itemProps and itemProps.lineDrawDashed:
        dashed = True

    svgColor = get_svg_color(color)
    
    cap = 'butt'
    try:
        if itemProps.pointPass:
            cap = 'round'
    except AttributeError:
        pass

        

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

    if "num_dashes" in itemProps:
        dash_val = ""
        for i in range(itemProps.num_dashes+1):
            if i == 0: continue
            if i > 1: dash_val += ","
            dash_space = eval('itemProps.d{}_length'.format(i))
            gap_space = eval('itemProps.g{}_length'.format(i))
            dash_val += "{},{}".format(dash_space , gap_space)
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
    if 'depthbuffer' in sceneProps and depthbuffer is None and sceneProps.vector_depthtest:
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
                line_draw = svg.line(start=tuple(p1ss), end=tuple(p2ss),stroke_linecap=cap)
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

def svg_poly_fill_shader(item, coords, color, svg, parent=None, line_color=(0, 0, 0,0), lineWeight=0, fillURL='', itemProps = None, closed=True, mat = Matrix.Identity(4)):
    if camera_cull(coords):
        return

    coords_2d = []
    idName = item.name + "_fills"
    dashed = False     
    if itemProps==None: itemProps = item
    if  "lineDrawDashed" in itemProps and itemProps.lineDrawDashed:
        dashed = True  

        if "num_dashes" in itemProps:
            dash_val = ""
            for i in range(itemProps.num_dashes+1):
                if i == 0: continue
                if i > 1: dash_val += ","
                dash_space = eval('itemProps.d{}_length'.format(i))
                gap_space = eval('itemProps.g{}_length'.format(i))
                dash_val += "{},{}".format(dash_space , gap_space)
        elif "dash_size" in itemProps:
            dash_val = "{},{}".format(itemProps.dash_size, itemProps.gap_size)
        else:
            dash_val = "5,5"

    fill = svgwrite.rgb(color[0] * 100, color[1] * 100, color[2] * 100, '%')

    fillOpacity = color[3]
    lineColor = svgwrite.rgb(
        line_color[0] * 100, line_color[1] * 100, line_color[2] * 100, '%')
    lineOpacity = lineColor[3]
    if dashed:
        solidfill = svg.g(id=idName, fill=fill, fill_opacity=fillOpacity,
                        stroke=lineColor, stroke_width=lineWeight, stroke_opacity=lineOpacity,stroke_linejoin="round",  stroke_dasharray=dash_val, stroke_linecap='butt')
    else:
        solidfill = svg.g(id=idName, fill=fill, fill_opacity=fillOpacity,
                        stroke=lineColor, stroke_width=lineWeight, stroke_opacity=lineOpacity,stroke_linejoin="round")
    if parent:
        parent.add(solidfill)
    else:
        svg.add(solidfill)

    for coord in coords:
        coords_2d.append(get_render_location(mat @ Vector(coord)))

    if False:
        coords_2d = polygon_occlusion(coords_2d)



    if closed:
        poly = svg.polygon(points=coords_2d)
    else:
        poly = svg.polyline(points=coords_2d)

    solidfill.add(poly)

    if fillURL != '':
        fill = fillURL
        patternfill = svg.g(id=idName, fill=fill, fill_opacity=item.patternOpacity,
                            stroke=0)
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

    svgColor = svgwrite.rgb(color[0] * 100, color[1] * 100, color[2] * 100, '%')
    ssp0 = get_render_location(textCard[0])
    ssp1 = get_render_location(textCard[1])
    ssp2 = get_render_location(textCard[2])
    ssp3 = get_render_location(textCard[3])

    card = [Vector(ssp0),Vector(ssp1),Vector(ssp2),Vector(ssp3)]
    
    xDirVec = card[3] - card[0]
    yDirVec = card[1] - card[0]

    # If either card direction is 0, don't draw any text
    if xDirVec.length == 0 or yDirVec.length == 0:
        return

    # If the card is not ordered correctly on the page flip it
    if yDirVec.dot(Vector((1,1000))) > 0:
        card[0] = Vector(ssp1)
        card[3] = Vector(ssp2)
        card[1] = Vector(ssp0)
        card[2] = Vector(ssp3)

    if xDirVec.dot(Vector((10000,-1))) < 0:
        temp = card[0]
        card[0] = card[3]
        card[3] = temp
        temp2 = card[1]
        card[1] = card[2]
        card[2] = temp2

    # Re Calc direction vectors aftor flips
    xDirVec = card[3] - card[0]
    yDirVec = card[1] - card[0]
    center = card[0] + ((card[2] - card[0])/2)

    cardHeight = yDirVec.length

    # Get the rotation angle of the text card from horizontal
    xvec = Vector((9999, -1)).normalized() #again we need to make this slightly off axis to make rotation consistent for orthogonal views
    rotation = math.degrees(xDirVec.angle_signed(xvec))

    # Define Anchor Points
    leftVec = card[0]
    rightVec = card[3]
    midVec =card[0] + ((card[3]-card[0])/2)

    # Set anchor point and positon
    if style.textAlignment == 'L':
        text_position = leftVec
        text_anchor = 'start'

    if style.textAlignment == 'C':
        text_position = midVec
        text_anchor = 'middle'

    if style.textAlignment == 'R':
        text_position = rightVec
        text_anchor = 'end'

    # Height Offset to match the raster texture shift
    heightOffsetAmount = 0.3 * cardHeight
    heightOffset = yDirVec.copy().normalized() * heightOffsetAmount
    offset_text_position = text_position + heightOffset
    
    # Get resolution for text size
    view = get_view()
    res = bpy.context.scene.MeasureItArchProps.default_resolution
    if view is not None:
        res = view.res

    # Try to get font
    try:
        font_file = style.font.filepath
        tt = ttLib.TTFont(font_file, verbose=1)
        font_family = shortName(tt)[0]
    except:
        font_family = "Open Sans"

    # Get Skew
    #skewX = 90-math.degrees(yDirVec.angle_signed(xDirVec))
    #print("Skew: {}".format(skew))


    # Draw the text
    parent.add(svg.text(text, insert=tuple(offset_text_position), fill=svgColor, **{
        'transform-origin': '{} {}'.format(offset_text_position[0], offset_text_position[1]),
        'transform': 'rotate({})'.format(
            rotation,
        ),
        

        # I wish i could tell you why this fudge factor is necessary, but for some reason
        # spec-ing svg units in inches and using this factor for text size is the only way to get
        # sensible imports in both inkscape and illustrator
        'font-size': round(style.fontSize * 4.166666667 / (300 / res), 2),
        'font-family':  font_family,
        'text-anchor': text_anchor,
        'text-align': text_anchor
    }))

    ## Debug Draw Text Card for troubleshooting
    if bpy.context.scene.MeasureItArchProps.show_text_cards:

        svg.add(svg.line(start=tuple(ssp0), end=tuple(ssp1), stroke="blue", stroke_width=1))
        svg.add(svg.line(start=tuple(ssp1), end=tuple(ssp2), stroke="blue", stroke_width=1))
        svg.add(svg.line(start=tuple(ssp2), end=tuple(ssp3), stroke="blue", stroke_width=1))
        svg.add(svg.line(start=tuple(ssp0), end=tuple(ssp3), stroke="blue", stroke_width=1))

        svg.add(svg.line(start=tuple(card[0]), end=tuple(card[3]), stroke="red", stroke_width=2))
        svg.add(svg.line(start=tuple(card[0]), end=tuple(card[1]), stroke="green", stroke_width=2))
        svg.add(svg.line(start=tuple(midVec), end=tuple(center), stroke="blue", stroke_width=2))
        svg.add(svg.line(start=tuple(text_position), end=tuple(offset_text_position), stroke="yellow", stroke_width=2))

        svg.add(svg.line(start=tuple((0,0)), end=tuple((50,0)), stroke="red", stroke_width=1))
        svg.add(svg.line(start=tuple((0,0)), end=tuple((0,50)), stroke="green", stroke_width=1))


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
                pair[1]), stroke_width=weight, stroke=svgColor, stroke_linecap='round'))


def polygon_occlusion(coords):
    polygon = coords
    global facemap
    #Generate Face Map if none exists
    if len(facemap) == 0:
        start_time = time.time()
        generate_facemap()
        end_time = time.time()
        print("Facemap Generation took: " + str(end_time - start_time))
    
    for face in facemap:
        cut_coords = []
        for edge in face.edges:
            cut_coords.append(edge.start_coord)
        polygon = polygon_subtract(polygon,cut_coords)

    return coords

def polygon_subtract(source, cut):
    return source


class FacemapEdge(object):
    start_coord: Vector = Vector((0,0))
    end_coord: Vector = Vector((0,1))

    def __init__(self, start, end):
        self.start_coord =start
        self.end_coord = end

class FacemapPolygon(object):
    edges = []
    depth = None

    def __init__(self, edge_array, depth):
        self.edges = edge_array
        self.depth = depth

def generate_facemap():
    
    context = bpy.context
    scene = context.scene
    sceneProps = scene.MeasureItArchProps
    global facemap
    objlist = context.view_layer.objects

    for obj in objlist:
        if obj.type != 'MESH':
            continue
        mat = obj.matrix_world
        bm = bmesh.new()
        bm.from_object(obj, bpy.context.view_layer.depsgraph)
        faces = bm.faces
        for face in faces:
            center = face.calc_center_bounds()
            depth = get_camera_z_dist(center)
            edge_array = []
            for edge in face.edges:
                start = get_render_location(edge.verts[0].co @ mat)
                end = get_render_location(edge.verts[1].co @ mat)
                edge_array.append(FacemapEdge(start,end))
            facemap.append(FacemapPolygon(edge_array,depth))

    

# Clear the depth buffer and facemap
def clear_db():
    global depthbuffer
    global facemap
    depthbuffer = None
    facemap = []
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
    scene = bpy.context.scene
    render = scene.render

    #Get Render info
    render_scale = scene.render.resolution_percentage / 100
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
