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
# Shared Utils for both SVG and DXF exports
# Author: Kevan Cress
#
# ----------------------------------------------------------

import bpy
import bmesh
import time
import bpy_extras.object_utils as object_utils
import math

from math import fabs, sqrt
from mathutils import Vector, Matrix
from .measureit_arch_utils import get_view, interpolate3d, get_camera_z_dist

depthbuffer = None
facemap = []
near_clip = None
far_clip = None
camera_type = None
width = None
height = None

def get_render_location(mypoint, svg_flip_y = True):
    global width
    scene = bpy.context.scene

    v1 = Vector(mypoint)

    co_2d = object_utils.world_to_camera_view(scene, scene.camera, v1)
    # Get pixel coords

    return [(co_2d.x * width), height - (co_2d.y * height)]

def get_worldscale_projection(mypoint):
    view = get_view()
    scene = bpy.context.scene
    v1 = Vector(mypoint)
    ndc =  object_utils.world_to_camera_view(scene, scene.camera, v1)

    camera_scale = view.model_scale / view.paper_scale
    world_width = view.width * camera_scale
    world_height = view.height * camera_scale

    return [(ndc.x * world_width), (ndc.y * world_height)]

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


# Clear the depth buffer and facemap
def clear_db():
    global depthbuffer
    global facemap
    depthbuffer = None
    facemap = []

def set_globals():
    sceneProps = bpy.context.scene.MeasureItArchProps
    view = get_view()
    global depthbuffer
    global near_clip
    global far_clip
    global camera_type
    global width
    global height
    if 'depthbuffer' in sceneProps and depthbuffer is None and view.vector_depthtest:
        depthbuffer = sceneProps['depthbuffer'].to_list()
    
    scene = bpy.context.scene
    camera = bpy.context.scene.camera.data
    near_clip = camera.clip_start
    far_clip = camera.clip_end
    camera_type = camera.type
    render_scale = scene.render.resolution_percentage / 100
    width = int(scene.render.resolution_x * render_scale)
    height = int(scene.render.resolution_y * render_scale)
    
# --------------------------------------------------------------------
# Get position in final render image
# (Z < 0 out of camera)
# return 2d position
# --------------------------------------------------------------------


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

    


def get_clip_space_coord(mypoint):
    scene = bpy.context.scene

    v1 = Vector(mypoint)
    co_camera_space = object_utils.world_to_camera_view(
        scene, scene.camera, v1)

    co_clip = Vector((co_camera_space.x, co_camera_space.y, co_camera_space.z))

    return co_clip

def camera_cull(points, mat = Matrix.Identity(4)):
    should_cull = []
    for point in points:
        dist = get_camera_z_dist(mat @ Vector(point))
        if dist < near_clip or dist > far_clip:
            should_cull.append(True)
        else:
            should_cull.append(False)

    if any(cull is False for cull in should_cull):
        return False
    else:
        return True

def true_z_buffer(zValue):
    global near_clip
    global far_clip
    global camera_type
    
    if camera_type == 'ORTHO':
        depth = zValue * (far_clip - near_clip) + near_clip - 0.09 #TODO Why is this fudge factor here
        return depth

    elif camera_type == 'PERSP':
        z_ndc = 2.0 * zValue - 1.0
        depth = 2.0 * near_clip * far_clip / (far_clip + near_clip - z_ndc * (far_clip - near_clip))
        return depth

    else:
        return zValue

def depth_test(p1, p2, mat, item, depthbuffer):
    scene = bpy.context.scene

    # Don't depth test if out of culling
    if camera_cull([mat @ Vector(p1), mat @ Vector(p2)]):
        return [[-1, p1, p2]]

    # Don't Depth test if not enabled
    view = get_view()
    if not view.vector_depthtest or item.inFront:
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
    global height

    # Get Screen Space Points
    p1ss = get_render_location(point)
    p1ss = Vector((p1ss[0], height - p1ss[1]))

    return p1ss

def check_visible(item, point):
    context = bpy.context
    scene = context.scene
    global width
    #Set Z-offset
    z_offset = 0.1

    if 'lineDepthOffset' in item:
        z_offset += item.lineDepthOffset / 10

    dist = get_camera_z_dist(point)
    if dist < 0:
        return -1

    if dist < near_clip or dist > far_clip:
        return -1

    #Get Render info

    point_ss = get_ss_point(point)
    point_clip = get_clip_space_coord(point)

    # Get Depth buffer Pixel Index based on SS Point

    if scene.MeasureItArchProps.depth_samples == 'POINT':
        pxIdx1 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1)
        pxIdx2 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1)
        samples = [pxIdx1,pxIdx2]

    if scene.MeasureItArchProps.depth_samples == 'CROSS':
        pxIdx1 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1)
        pxIdx2 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1)

        pxIdx3 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) + width
        pxIdx4 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) + width

        pxIdx5 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) - width
        pxIdx6 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) - width

        pxIdx7 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) + 1
        pxIdx8 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) + 1

        pxIdx9 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) - 1
        pxIdx10 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) - 1

        samples = [pxIdx1,pxIdx2,pxIdx3,pxIdx4,pxIdx5,pxIdx6,pxIdx7,pxIdx8,pxIdx9,pxIdx10]
    
    if scene.MeasureItArchProps.depth_samples == 'SQUARE':
        pxIdx1 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1)
        pxIdx2 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1)

        pxIdx3 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) + width
        pxIdx4 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) + width

        pxIdx5 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) + width + 1
        pxIdx6 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) + width +1

        pxIdx7 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) + width - 1
        pxIdx8 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) + width -1

        pxIdx9 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) - width
        pxIdx10 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) - width

        pxIdx11 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) - width + 1
        pxIdx12 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) - width + 1

        pxIdx13 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) - width - 1
        pxIdx14 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) - width - 1

        pxIdx15 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) + 1
        pxIdx16 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) + 1

        pxIdx17 = int(((width * math.ceil(point_ss[1])) + math.ceil(point_ss[0])) * 1) - 1
        pxIdx18 = int(((width * math.floor(point_ss[1])) + math.floor(point_ss[0])) * 1) - 1

        samples = [pxIdx1,pxIdx2,pxIdx3,pxIdx4,pxIdx5,pxIdx6,pxIdx7,pxIdx8,pxIdx9,pxIdx10,pxIdx11,pxIdx12,pxIdx13,pxIdx14,pxIdx15,pxIdx16,pxIdx17,pxIdx18]


    true_samples = [get_true_z_at_idx(sample) for sample in samples]
    point_depth = sum(true_samples) / len(true_samples)

    # Get Depth From Clip Space point
    point_vecdepth = (point_clip[2]) - z_offset

    # Check Clip space point against depth buffer value
    pointVisible = point_depth > point_vecdepth

    return pointVisible

def get_true_z_at_idx(idx):
    val = get_bufffer_at_idx(idx)
    true_val = true_z_buffer(val)
    return true_val


def get_bufffer_at_idx(idx):
    # Get Depth Buffer Value buffer value
    try:
        point_depth = depthbuffer[idx]
    except IndexError:
        #print('Index not in Depth Buffer:{}'.format(idx))
        point_depth = 0
    return point_depth