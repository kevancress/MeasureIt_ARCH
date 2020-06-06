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

def svg_line_shader(coords,thickness,color,svg):
    coords_2d = []
    lines = svg.add(svg.g(id='lines',stroke='black', stroke_width=thickness))
    for coord in coords:
        coords_2d.append(get_render_location(coord))
    for x in range(0, len(coords_2d) - 1, 2):
        line = svg.line(start=tuple(coords_2d[x]),end=tuple(coords_2d[x+1]))
        lines.add(line)

def svg_line_group_shader(coords,thickness,color,mat,svg):
    coords_2d = []
    lines = svg.add(svg.g(id='lines',stroke='red', stroke_width=thickness))
    for coord in coords:
        coords_2d.append(get_render_location(mat@Vector(coord)))
    for x in range(0, len(coords_2d) - 1, 2):
        line = svg.line(start=tuple(coords_2d[x]),end=tuple(coords_2d[x+1]))
        lines.add(line)




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