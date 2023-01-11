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
from . import vector_utils

from .measureit_arch_utils import get_view, interpolate3d, get_camera_z_dist, recursionlimit, get_resolution, get_scale, pts_to_px


def svg_line_shader(item, itemProps, coords, thickness, color, svg, parent=None, mat=Matrix.Identity(4)):
    weight_scale_fac = 1.3333333333333333 * get_resolution()/96
    if bpy.context.scene.MeasureItArchProps.illustrator_style_svgs:
        weight_scale_fac = 1
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

        

    lines = svg.g(id=idName, stroke=svgColor,fill = 'none',
                  stroke_width="{}".format(thickness*weight_scale_fac), stroke_linecap=cap)
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

    try:
        dash_val = ""
        for i in range(itemProps.num_dashes+1):
            if i == 0: continue
            if i > 1: dash_val += ","
            dash_space = eval('itemProps.d{}_length'.format(i))
            gap_space = eval('itemProps.g{}_length'.format(i))
            dash_val += "{},{}".format(dash_space , gap_space)
    except AttributeError:
        dash_val = "5,5"

    dashed_lines = svg.g(id=dash_id_name, stroke=dash_col,fill = 'none', stroke_width="{}".format(dash_weight * weight_scale_fac),
                    stroke_dasharray=dash_val, stroke_linecap='butt')

    if parent:
        parent.add(dashed_lines)
    else:
        svg.add(dashed_lines)

    # Get Depth Buffer as list and also other common props 
    if dashed:
        lines = dashed_lines
        
    for x in range(0, len(coords) - 1, 2):
        draw_single_line(coords[x],coords[x+1],mat,itemProps,svg,lines,dashed_lines,cap,draw_hidden)
 
 
def draw_single_line(p1,p2,mat,itemProps,svg,lines,dashed_lines,cap,draw_hidden):
    line_segs = vector_utils.depth_test(p1, p2, mat, itemProps)
    for line in line_segs:
        vis = line[0]
        p1 = line[1]
        p2 = line[2]
        if vis == -1:
            continue

        if vis or draw_hidden:
            p1ss = vector_utils.get_render_location(mat @ Vector(p1))
            p2ss = vector_utils.get_render_location(mat @ Vector(p2))
            line_draw = svg.line(start=tuple(p1ss), end=tuple(p2ss),stroke_linecap=cap)
            if vis:
                lines.add(line_draw)
            elif not vis and draw_hidden:
                dashed_lines.add(line_draw)

def svg_fill_shader(item, coords, color, svg, parent=None):
    if vector_utils.camera_cull(coords):
        print("No Points In front of Camera: {} Culled in Fill Shader")
        return
    coords_2d = []
    idName = item.name + "_fills"
    svgColor = svgwrite.rgb(color[0] * 100, color[1] * 100, color[2] * 100, '%')
    fills = svg.g(id=idName, fill=svgColor)
    parent.add(fills)

    for coord in coords:
        coords_2d.append(vector_utils.get_render_location(coord))

    for x in range(0, len(coords_2d) - 1, 3):
        tri = svg.polygon(
            points=[coords_2d[x], coords_2d[x + 1], coords_2d[x + 2]])
        fills.add(tri)

def svg_circle_shader(item, point, rad, color, svg, parent=None):
    if vector_utils.camera_cull([point]):
        print("No Points In front of Camera: {} Culled in Circle Shader")
        return

    idName = item.name + "_fills"
    svgColor = svgwrite.rgb(color[0] * 100, color[1] * 100, color[2] * 100, '%')
    fills = svg.g(id=idName, fill=svgColor)
    parent.add(fills)

    point_2d = vector_utils.get_render_location(point)

    circle = svg.circle(center=point_2d,r=rad)
    fills.add(circle)

def svg_poly_fill_shader(item, coords, color, svg, parent=None, line_color=(0, 0, 0,0), lineWeight=0, fillURL='', itemProps = None, closed=True, mat = Matrix.Identity(4)):
    weight_scale_fac = 1.3333333333333333 * get_resolution()/96
    if bpy.context.scene.MeasureItArchProps.illustrator_style_svgs:
        weight_scale_fac = 1
    
    if vector_utils.camera_cull(coords,mat):
        print("No Points In front of Camera: {} Culled in Poly Fill Shader")
        return


    cap = 'butt'
    try:
        if itemProps.pointPass:
            cap = 'round'
    except AttributeError:
        pass

    coords_2d = []
    idName = item.name + "_fills"
    dashed = False     
    if itemProps==None: itemProps = item
    if  "lineDrawDashed" in itemProps and itemProps.lineDrawDashed:
        dashed = True  

        try:
            dash_val = ""
            for i in range(itemProps.num_dashes+1):
                if i == 0: continue
                if i > 1: dash_val += ","
                dash_space = eval('itemProps.d{}_length'.format(i))
                gap_space = eval('itemProps.g{}_length'.format(i))
                dash_val += "{},{}".format(dash_space , gap_space)
        except AttributeError:
            if "dash_size" in itemProps:
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
                        stroke=lineColor, stroke_width="{}".format(lineWeight*weight_scale_fac), stroke_opacity=lineOpacity,stroke_linejoin="round",  stroke_dasharray=dash_val, stroke_linecap= cap)
    else:
        solidfill = svg.g(id=idName, fill=fill, fill_opacity=fillOpacity,
                        stroke=lineColor, stroke_width="{}".format(lineWeight*weight_scale_fac), stroke_opacity=lineOpacity,stroke_linejoin="round", stroke_linecap= cap)
    if parent:
        parent.add(solidfill)
    else:
        svg.add(solidfill)

    for coord in coords:
        coords_2d.append(vector_utils.get_render_location(mat @ Vector(coord)))

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

    if vector_utils.camera_cull(textCard):
        print("No Points In front of Camera: {} Culled Text Card")
        return

    svgColor = svgwrite.rgb(color[0] * 100, color[1] * 100, color[2] * 100, '%')
    ssp0 = vector_utils.get_render_location(textCard[0])
    ssp1 = vector_utils.get_render_location(textCard[1])
    ssp2 = vector_utils.get_render_location(textCard[2])
    ssp3 = vector_utils.get_render_location(textCard[3])

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

    
    # Get resolution for text size
    view = get_view()
    res = get_resolution()
    scale = get_scale()

    # Try to get font
    font_family = "Open Sans"
    if style.font != None:
        font_file = style.font.filepath
        font_file = bpy.path.abspath(font_file)
        try:
            tt = ttLib.TTFont(font_file, verbose=1)
            font_family = shortName(tt)[0]
        except Exception as e:
            font_family = style.font.name
            print(e)
            print(font_file)

    print(font_family)

    # Get Skew
    #skewX = 90-math.degrees(yDirVec.angle_signed(xDirVec))
    #print("Skew: {}".format(skew))

    lines = text.split('\n')

    # Draw the text
    line_height = cardHeight / len(lines)
    
    # Height Offset to match the raster texture shift
    heightOffsetAmount = cardHeight - line_height * 0.8
    heightOffset = yDirVec.copy().normalized() * heightOffsetAmount
    offset_text_position = text_position + heightOffset


    idx = 0
    for line in lines:
        offset_line_position = offset_text_position + Vector((0,line_height*1.1 * idx))
        svg.add(svg.text(line, insert=tuple(offset_line_position), fill=svgColor, **{
            #'transform-origin': '{}px {}px'.format(offset_text_position[0], offset_text_position[1]),
            'transform': 'rotate({} {} {})'.format(
                rotation,
                offset_text_position[0],
                offset_text_position[1]
            ),
            

            # I wish i could tell you why this fudge factor is necessary, but for some reason
            # spec-ing svg units in inches and using this factor for text size is the only way to get
            # sensible imports in both inkscape and illustrator
            'font-size': '{}px'.format(pts_to_px(style.fontSize)),
            'font-family':  font_family,
            'text-anchor': text_anchor,
            'text-align': text_anchor,
            'xml:space' : "preserve"
        }))

        idx += 1

    ## Debug Draw Text Card for troubleshooting
    if bpy.context.scene.MeasureItArchProps.show_text_cards:

        svg.add(svg.line(start=tuple(ssp0), end=tuple(ssp1), stroke="blue", stroke_width="1pt"))
        svg.add(svg.line(start=tuple(ssp1), end=tuple(ssp2), stroke="blue", stroke_width="1pt"))
        svg.add(svg.line(start=tuple(ssp2), end=tuple(ssp3), stroke="blue", stroke_width="1pt"))
        svg.add(svg.line(start=tuple(ssp0), end=tuple(ssp3), stroke="blue", stroke_width="1pt"))

        svg.add(svg.line(start=tuple(card[0]), end=tuple(card[3]), stroke="red", stroke_width="2pt"))
        svg.add(svg.line(start=tuple(card[0]), end=tuple(card[1]), stroke="green", stroke_width="2pt"))
        svg.add(svg.line(start=tuple(midVec), end=tuple(center), stroke="blue", stroke_width="2pt"))
        svg.add(svg.line(start=tuple(text_position), end=tuple(offset_text_position), stroke="yellow", stroke_width=2))

        svg.add(svg.line(start=tuple((0,0)), end=tuple((50,0)), stroke="red", stroke_width="1pt"))
        svg.add(svg.line(start=tuple((0,0)), end=tuple((0,50)), stroke="green", stroke_width="1pt"))


def svg_line_pattern_shader(pattern, svg, objs, weight, color, size):
    weight_scale_fac = 1.3333333333333333 * get_resolution()/96
    if bpy.context.scene.MeasureItArchProps.illustrator_style_svgs:
        weight_scale_fac = 1
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
                pair[1]), stroke_width="{}".format(weight*weight_scale_fac), stroke=svgColor, stroke_linecap='round'))


def polygon_subtract(source, cut):
    return source





# From https://gist.github.com/pklaus/dce37521579513c574d0
FONT_SPECIFIER_NAME_ID = 4
FONT_SPECIFIER_FAMILY_ID = 1
def shortName(font):
    """Get the short name from the font's names table"""
    name = ""
    family = ""
    
    for record in font['name'].names:
        if record.nameID == FONT_SPECIFIER_NAME_ID and not name:
            if b'\x00' in record.string:
                name_str = record.string.decode('utf-16-be')
            else:
                name_str = record.string.decode('utf-8')
            name = name_str
        elif record.nameID == FONT_SPECIFIER_FAMILY_ID and not family:
            if b'\x00' in record.string:
                name_str = record.string.decode('utf-16-be')
            else:
                name_str = record.string.decode('utf-8')
            family = name_str
       
        if name and family: break
    return name, family


def get_svg_color(color):
    return svgwrite.rgb(color[0] * 100, color[1] * 100, color[2] * 100, '%')
