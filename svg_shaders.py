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
import math
import bpy_extras.object_utils as object_utils
import svgwrite
import gpu

def svg_line_shader(item, coords,thickness,color,svg,parent=None,mat=Matrix.Identity(4)):
    idName = item.name + "_lines"
    svgColor = svgwrite.rgb(color[0]*255, color[1]*255, color[2]*255, '%')
    lines = svg.g(id=idName,stroke=svgColor, stroke_width=thickness)
    if parent:
        parent.add(lines)
    else:
        svg.add(lines)

    for x in range(0, len(coords) - 1, 2):
        if check_visible(coords[x],coords[x+1],mat,item):
            p1ss = get_render_location(mat@Vector(coords[x]))
            p2ss = get_render_location(mat@Vector(coords[x+1]))
            line = svg.line(start=tuple(p1ss),end=tuple(p2ss))
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


def svg_text_shader(item, text, mid, textCard, color,svg,parent=None):
    text_position = get_render_location(mid)
    svgColor = svgwrite.rgb(color[0]*255, color[1]*255, color[2]*255, '%')
    ssp1 = get_render_location(textCard[0])
    ssp2 = get_render_location(textCard[3])
    ssp3 = get_render_location(textCard[2])

    dirVec = Vector(ssp1) - Vector(ssp2)

    if dirVec.length == 0:
        return

    text_position  = (Vector(ssp1) + Vector(ssp3)) / 2 

    rotation = math.degrees(dirVec.angle_signed(Vector((1, 0))))
  
    parent.add(svg.text(text, insert=tuple(text_position), fill=svgColor, **{
            'transform': 'rotate({} {} {})'.format(
                rotation,
                text_position[0],
                text_position[1]
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
    context = bpy.context
    scene = bpy.context.scene
    camera = scene.camera
    render = scene.render


    clip_end = camera.data.clip_end
    clip_start = camera.data.clip_start

    v1 = Vector(mypoint)
    co_camera_space = object_utils.world_to_camera_view(scene, scene.camera, v1)

    clip_space_z = (co_camera_space.z - clip_start)/ clip_end-clip_start

    co_clip = Vector((co_camera_space.x,co_camera_space.y,co_camera_space.z/100))

    return co_clip

    



    #render_scale = scene.render.resolution_percentage / 100
    #width = int(render.resolution_x * render_scale)
    #height = int(render.resolution_y * render_scale)

    #modelview_matrix = camera.matrix_world.inverted()
    #projection_matrix = camera.calc_matrix_camera(context.evaluated_depsgraph_get(), x=width, y=height)
           
    #return modelview_matrix @ projection_matrix @ Vector((mypoint[0], mypoint[1], mypoint[2], 1))

def check_visible(p1,p2,mat,item):
    scene = bpy.context.scene
    camera = scene.camera
    render = scene.render

    if not scene.MeasureItArchProps.vector_depthtest:
        return True

    print('Drawing: ' + item.name)  
    if 'lineDepthOffset' in item:
        z_offset = 1.0
    else:
        z_offset = 1.0

    p1Visible = True
    p2Visible = True

    sceneProps= bpy.context.scene.MeasureItArchProps
    if 'depthbuffer' in sceneProps:
        depthbuffer = sceneProps['depthbuffer'].to_list()

    render_scale = scene.render.resolution_percentage / 100
    width = int(render.resolution_x * render_scale)
    height = int(render.resolution_y * render_scale)

    # Get Screen Space Points
    p1ss = get_render_location(mat@Vector(p1))
    p1ss = Vector((p1ss[0], height-p1ss[1]))
    p2ss = get_render_location(mat@Vector(p2))
    p2ss = Vector((p2ss[0], height-p2ss[1]))



    ## Get Clip Space Points
    p1clip = get_clip_space_coord(mat@ Vector(p1))
    p2clip = get_clip_space_coord(mat@ Vector(p2))
    
    # Get Buffer Index and depthbuffer value based on SS Point
    p1pxIdx = int((width * (p1ss[1]) + p1ss[0]-1)*4)
    p2pxIdx = int((width * (p2ss[1]) + p2ss[0]-1)*4)

    try:
        p1depth = depthbuffer[p1pxIdx]/255
        p2depth = depthbuffer[p2pxIdx]/255
    except IndexError:
        print('Index not in Depth Buffer ')
        return False
    
    # Get Depth From Clip Space point
    p1vecdepth = (p1clip[2])
    p2vecdepth = (p2clip[2])

    # Check Clip space point against depth buffer value
    print('p1')
    print(p1clip)
    print(str(p1depth) + ' at Coords: ' + str(p1ss[0]) + "," + str(p1ss[1]) + 'Index :' + str(p1pxIdx))
    if p1depth > p1vecdepth-z_offset/100 or p1depth == 0.0:
        p1Visible = True
    else:
        p1Visible = False
        print('p1 not visible')

    print('p2')
    print(p2clip)
    print(str(p2depth) + ' at Coords: ' + str(p2ss[0]) + "," + str(p2ss[1]) + 'Index :' + str(p2pxIdx))
    if p2depth > p2vecdepth-z_offset/100 or p2depth == 0.0:
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
        