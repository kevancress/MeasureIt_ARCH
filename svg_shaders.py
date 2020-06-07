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
from mathutils import Vector, Matrix, Euler, Quaternion
import bpy_extras.object_utils as object_utils
import svgwrite
import gpu

def svg_line_shader(item, coords,thickness,color,svg,parent=None):
    coords_2d = []
    idName = item.name + "_lines"
    svgColor = svgwrite.rgb(color[0]*255, color[1]*255, color[2]*255, '%')
    lines = svg.g(id=idName,stroke=svgColor, stroke_width=thickness)
    parent.add(lines)

    for coord in coords:
        coords_2d.append(get_render_location(coord))
    
    for x in range(0, len(coords_2d) - 1, 2):
        line = svg.line(start=tuple(coords_2d[x]),end=tuple(coords_2d[x+1]))
        lines.add(line)
    

def svg_fill_shader(item, coords,color,svg,parent=None):
    coords_2d = []
    idName = item.name + "_fills"
    svgColor = svgwrite.rgb(color[0]*255, color[1]*255, color[2]*255, '%')
    fills = svg.g(id=idName,fill=svgColor)
    parent.add(fills)

    for coord in coords:
        coords_2d.append(get_render_location(coord))

    for x in range(0, len(coords_2d) - 1, 3):
        tri = svg.polygon(points=[coords_2d[x],coords_2d[x+1],coords_2d[x+2]])
        fills.add(tri)

def svg_line_group_shader(item,coords,thickness,color,mat,svg):
    idName = item.name
    svgColor = svgwrite.rgb(color[0]*255, color[1]*255, color[2]*255, '%')
    lines = svg.add(svg.g(id=idName,stroke=svgColor, stroke_width=thickness))

    for x in range(0, len(coords) - 1, 2):
        if check_visible(coords[x],coords[x+1],mat):
            p1ss = get_render_location(mat@Vector(coords[x]))
            p2ss = get_render_location(mat@Vector(coords[x+1]))
            line = svg.line(start=tuple(p1ss),end=tuple(p2ss))
            lines.add(line)

def svg_text_shader(item, text, mid ,color,svg,parent=None):
    text_position = get_render_location(mid)
    svgColor = svgwrite.rgb(color[0]*255, color[1]*255, color[2]*255, '%')
  
    parent.add(svg.text(text, insert=tuple(text_position), fill=svgColor, **{
            'transform': 'rotate({} {} {})'.format(
                0,
                0,
                0
            ),
            'font-size': 12,
            'font-family': 'OpenGost Type B TT',
            'text-anchor': 'middle'
        }))


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
    render_scale = scene.render.resolution_percentage / 100
    render_size = (int(scene.render.resolution_x * render_scale),
                   int(scene.render.resolution_y * render_scale))

    return [round(co_2d.x * render_size[0]), height-round(co_2d.y * render_size[1])]


def get_clip_space_coord(mypoint):
    scene = bpy.context.scene
    camera = scene.camera
    render = scene.render

    render_scale = scene.render.resolution_percentage / 100
    width = int(render.resolution_x * render_scale)
    height = int(render.resolution_y * render_scale)

    modelview_matrix = gpu.matrix.get_model_view_matrix()
    projection_matrix = gpu.matrix.get_projection_matrix()
           
    return modelview_matrix @ projection_matrix @ Vector((mypoint[0], mypoint[1], mypoint[2], 1))

def check_visible(p1,p2,mat):
    scene = bpy.context.scene
    camera = scene.camera
    render = scene.render

    p1Visible = True
    p2Visible = True

    sceneProps= bpy.context.scene.MeasureItArchProps
    if 'depthbuffer' in sceneProps:
        depthbuffer = sceneProps['depthbuffer'].to_list()

    render_scale = scene.render.resolution_percentage / 100
    width = int(render.resolution_x * render_scale)
    height = int(render.resolution_y * render_scale)

    p1ss = get_render_location(mat@Vector(p1))
    p1ss = Vector((p1ss[0], height-p1ss[1]))
    p2ss = get_render_location(mat@Vector(p2))
    p1ss = Vector((p2ss[0], height-p2ss[1]))

    p1clip = get_clip_space_coord(mat@ Vector(p1))
    p2clip = get_clip_space_coord(mat@ Vector(p2))
    
    p1pxIdx = int((p1ss[0] * (p1ss[1]-1) + p1ss[1])*4)
    p1vecdepth = (abs(p1clip[2])/100) +.01
    p1depth = depthbuffer[p1pxIdx]/255
    if p1depth > p1vecdepth:
        p1Visible = True
    else:
        p1Visible = False
        print('p1 not visible')


    p2pxIdx = int((p2ss[0] * (p2ss[1]-1) + p2ss[1])*4)
    p2vecdepth = (abs(p2clip[2])/100) +.01
    p2depth = depthbuffer[p2pxIdx]/255
    if p2depth > p2vecdepth:
        p2Visible = True
    else:
        p2Visible = False
        print('p2 not visible')


    if p1Visible and p2Visible:
        print('vis test passed')
        return True
    else:
        print('vis test failed')
        return False
        