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
import numpy as np

from math import fabs, sqrt
from mathutils import Vector, Matrix
from .measureit_arch_utils import get_view, interpolate3d, get_camera_z_dist
from multiprocessing import Pool

depthbuffer = None
facemap = []
edgemap = []
near_clip = None
far_clip = None
camera_type = None
width = None
height = None

# Gets the Pixel Co-ordinate of a point in 3D Spcae
def get_render_location(mypoint, svg_flip_y = True):
    global width
    global height
    scene = bpy.context.scene

    v1 = Vector(mypoint)

    co_2d = object_utils.world_to_camera_view(scene, scene.camera, v1)
    # Get pixel coords

    return [(co_2d.x * width), height - (co_2d.y * height)]

# Gets 2d worldscale projection using normalized device co-ordinates... loss of precision but handles perspective
def get_worldscale_projection_ndc(mypoint):
    view = get_view()
    scene = bpy.context.scene
    v1 = Vector(mypoint)
    ndc =  object_utils.world_to_camera_view(scene, scene.camera, v1)

    camera_scale = view.model_scale / view.paper_scale
    world_width = view.width * camera_scale
    world_height = view.height * camera_scale

    return [(ndc.x * world_width), (ndc.y * world_height)]

# Gets 2d worldscale projection using camera matrix. falls back to ndc if camera is using perspective projection
# Because dxf's allways seem to import in mm, we'll use this as the default scale factor
def get_worldscale_projection(mypoint, units = 'M', is_2d=True):
    scene = bpy.context.scene
    sceneProps = scene.MeasureItArchProps
    camera = scene.camera

    # Fall back to ndc for perspective
    if camera.data.type == 'PERSPECTIVE':
        return get_worldscale_projection_ndc(mypoint)

    v1 = Vector(mypoint)
    camera_matrix = camera.matrix_world
    camera_rot = camera_matrix.to_quaternion()
    camera_basis = Matrix.Identity(3) 
    camera_basis.rotate(camera_rot)

    proj_point = (v1 - camera.location) @ camera_basis
    
    if units == 'MM':
        proj_point *= 1000
    elif units == 'CM':
        proj_point *= 100
    elif units == 'M':
        pass
    
    if is_2d:

        return proj_point.xy + Vector((sceneProps.offset_x_2d,sceneProps.offset_y_2d))

    return proj_point
    


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
    global edgemap
    depthbuffer = None
    facemap = []
    edgemap = []

def set_globals():
    sceneProps = bpy.context.scene.MeasureItArchProps
    view = get_view()
    global depthbuffer
    global near_clip
    global far_clip
    global camera_type
    global width
    global height
    start_time = time.time()

    scene = bpy.context.scene
    camera = bpy.context.scene.camera.data
    near_clip = camera.clip_start
    far_clip = camera.clip_end
    camera_type = camera.type
    render_scale = scene.render.resolution_percentage / 100
    width = int(scene.render.resolution_x * render_scale)
    height = int(scene.render.resolution_y * render_scale)

    if 'depthbuffer' in sceneProps and depthbuffer is None and view.vector_depthtest:
        #depthbuffer = np.asarray(sceneProps['depthbuffer'], dtype=np.float32) # I feel like this should be faster but its not
        depthbuffer = sceneProps['depthbuffer'].to_list()   
        end_time = time.time()
        print("Reading Depthbuffer to list took: " + str(end_time - start_time))

    if view.vector_depthtest and sceneProps.depth_test_method == 'GEOMETRIC':
        generate_edgemap()
        #generate_facemap()
    

    
# --------------------------------------------------------------------
# Get position in final render image
# (Z < 0 out of camera)
# return 2d position
# --------------------------------------------------------------------


class MapEdge(object):
    start_coord: Vector = Vector((0,0,0))
    end_coord: Vector = Vector((0,1,0))

    ss_start_coord : Vector = Vector((0,0,0))
    ss_end_coord : Vector = Vector((0,0,0))

    def __init__(self, start, end):
        self.start_coord =start
        self.end_coord = end
        self.ss_start_coord = get_ss_point(start)
        self.ss_end_coord = get_ss_point(end)

class MapPolygon(object):
    edges = []
    depth = None
    center = Vector((0,0,0))
    normal = Vector((0,0,1))

    def __init__(self, edge_array, depth, center, normal):
        self.edges = edge_array
        self.depth = depth
        self.center = center
        self.normal = normal

class IntersectPoint(object):
    point: Vector = Vector((0,0))
    factor = 0.0

    def __init__(self, point, factor) -> None:
        self.point = point
        self.factor = factor
    
    def __lt__(self,other):
        return self.factor < other.factor

class LineSegment(object):
    visible = 1 # 1 visible 0 hidden -1 culled
    start = Vector((0,0,0))
    end = Vector((0,0,0))

    def __init__(self,start,end, visible) -> None:
        self.start = start
        self.end = end
        self.visible = visible

def generate_edgemap():
    deps = bpy.context.view_layer.depsgraph
    for obj_int in deps.object_instances:
        obj = obj_int.object
        parent = obj_int.parent

        ignore = obj.MeasureItArchProps.ignore_in_depth_test
        if parent != None:
            ignore = obj.MeasureItArchProps.ignore_in_depth_test or parent.MeasureItArchProps.ignore_in_depth_test

        if obj.type == 'MESH' and not(obj.hide_render or obj.display_type == "WIRE" or ignore):
            mat = obj.matrix_world
            obj_eval = obj.evaluated_get(deps)
            mesh = obj_eval.to_mesh(
                preserve_all_data_layers=False, depsgraph=bpy.context.view_layer.depsgraph)
            
            for edge in mesh.edges:
                p1 = mat @ mesh.vertices[edge.vertices[0]].co 
                p2 = mat @ mesh.vertices[edge.vertices[1]].co 
                map_edge = MapEdge(p1,p2)
                edgemap.append(map_edge)

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
            center = mat @ face.calc_center_bounds() 
            depth = get_camera_z_dist(center)
            normal = mat @ face.normal 
            edge_array = []
            for edge in face.edges:
                start = mat @ edge.verts[0].co 
                end = mat @ edge.verts[1].co  
                edge_array.append(MapEdge(start,end))
            facemap.append(MapPolygon(edge_array,depth,center,normal))


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

# Calculates the intersection point of line A (p1,p2) and line B (p3,p4)
# returns the intersect point in 2D and factor along the line from p1
def line_segment_intersection_2D(p1,p2,p3,p4):

    denom = (p4.y-p3.y) * (p2.x-p1.x) - (p4.x-p3.x) * (p2.y-p1.y)

    if denom == 0: # parallel
        #print('parallel')
        return None
    
    ua = ((p4.x-p3.x) * (p1.y-p3.y) - (p4.y-p3.y) * (p1.x - p3.x)) / denom
    if ua < 0 or ua > 1: # out of range
        #print('out of range')
        return None

    ub = ((p2.x-p1.x)*(p1.y-p3.y) - (p2.y-p1.y)*(p1.x-p3.x)) / denom
    if ub < 0 or ub > 1: # out of range
        #print('out of range')
        return None
    
    x = p1.x + ua * (p2.x-p1.x)
    y = p1.y + ua * (p2.y-p1.y)

    #print('Intersected')
    intersect = Vector((x,y))
    factor = (intersect-p1).length / (p2-p1).length

    return IntersectPoint(intersect,factor)


def get_line_plane_intersection(p0, p1, p_co, p_no, epsilon=1e-6):

    """
    modified from https://stackoverflow.com/questions/5666222/3d-line-plane-intersection
    p0, p1: Define the line.
    p_co, p_no: define the plane:
        p_co Is a point on the plane (plane coordinate).
        p_no Is a normal vector defining the plane direction;
             (does not need to be normalized).

    Return a Vector or None (when the intersection can't be found).
    """

    u = p1-p0
    dot = p_no.dot(u)

    if abs(dot) > epsilon:
        # The factor of the point between p0 -> p1 (0 - 1)
        # if 'fac' is between (0 - 1) the point intersects with the segment.
        # Otherwise:
        #  < 0.0: behind p0.
        #  > 1.0: infront of p1.
        w = p0 - p_co
        fac = -p_no.dot(w) / dot
        u = u* fac
        intersect = p0 + u
        factor = (intersect-p0).length / (p1-p0).length
        return IntersectPoint(intersect,factor)

    # The segment is parallel to plane.
    return None  


def get_clip_space_coord(mypoint):
    scene = bpy.context.scene

    v1 = Vector(mypoint)
    co_camera_space = object_utils.world_to_camera_view(
        scene, scene.camera, v1)

    co_clip = Vector((co_camera_space.x, co_camera_space.y, co_camera_space.z))

    return co_clip

# Culls points if they are beyond the camera near or far clip distance
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
        depth = zValue * (far_clip - near_clip) + near_clip
        return depth

    elif camera_type == 'PERSP':
        z_ndc = 2.0 * zValue - 1.0
        depth = 2.0 * near_clip * far_clip / (far_clip + near_clip - z_ndc * (far_clip - near_clip))
        return depth

    else:
        return zValue


def depth_test(p1, p2, mat, item):
    scene = bpy.context.scene
    sceneProps = bpy.context.scene.MeasureItArchProps
    # Don't depth test if out of culling
    if camera_cull([mat @ Vector(p1), mat @ Vector(p2)]):
        return [[-1, p1, p2]]

    # Don't Depth test if not enabled
    view = get_view()
    if not view.vector_depthtest or item.inFront:
        return [[True, p1, p2]]

    method = sceneProps.depth_test_method
    if item.depth_test_override != 'NONE':
        method = item.depth_test_override
    # a line segment is a list [intiger visibility, start point, end point]
    if method == 'DEPTH_BUFFER':
        line_segs = vis_sampling(p1, p2, mat, item,)
    elif method == 'GEOMETRIC':
        line_segs = geometric_vis_calc(p1,p2,mat,item)

    return line_segs

def geometric_vis_calc(p1,p2,mat,item):
    p1Global = mat @ Vector(p1)
    p2Global = mat @ Vector(p2)

    # Get Screen Space Points
    p1ss = get_ss_point(p1Global)
    p2ss = get_ss_point(p2Global)

    # Get ss normal vectorsP
    dir_vec = p1ss - p2ss
    n1ss = Vector((dir_vec.y, -dir_vec.x))
    n2ss = Vector((-dir_vec.y, dir_vec.x))

    ss_norms = [n1ss,n2ss]


    intersect_points = []

    # Get all 2D edge intersections
    #loop_st = time.time()
    #loop_count = 0
    for edge in edgemap:
        p3ss = edge.ss_start_coord
        p4ss = edge.ss_end_coord

        #aloop_count += 1
        intersection = line_segment_intersection_2D(p1ss,p2ss,p3ss,p4ss)
        if intersection != None:
            intersect_points.append(intersection)
    
    #loop_et = time.time()
    #print("loop time: " + str(loop_et - loop_st) + '. loop count: ' + str(loop_count))

    # Get all 3D face intersections     
    for face in facemap:
        intersection = get_line_plane_intersection(p1Global,p2Global,face.center,face.normal)
        if intersection != None and intersection.factor < 1.0 and intersection.factor > 0.0:
            intersect_points.append(intersection)

    # Check vis of each segment defined by the intersect points
    line_segs = []
    if len(intersect_points) > 0:
        intersect_points.sort() # Sorts by distance from p1

        last_point = Vector(p1)
        for ip in intersect_points: 
            dist = (Vector(p2)-Vector(p1)).length * ip.factor
            point = interpolate3d(Vector(p1),Vector(p2),dist) 

            vis_sample_point = (last_point + point) / 2
            visible = check_visible(item, mat @ vis_sample_point,ss_norms)

            segment = [visible,last_point, point]
            line_segs.append(segment)
            last_point = Vector(point)

        # Last segment
        vis_sample_point = (last_point + Vector(p2)) / 2
        visible = check_visible(item, mat @ vis_sample_point, ss_norms)
        
        line_segs.append([visible,last_point,p2])           

    else:   
        vis_sample_point = (Vector(p1) + Vector(p2)) / 2
        visible = check_visible(item, mat @ vis_sample_point, ss_norms)
        
        line_segs.append([visible,p1,p2])

    # Join segments where no visibility change occurs

    joined_line_segs=[]
    idx = 0
    start_point = line_segs[idx][1]
    prv_seg_vis = line_segs[idx][0]
    while idx + 1 < len(line_segs):
        idx += 1
        seg_vis = line_segs[idx][0]
        if seg_vis != prv_seg_vis:
            segment = [prv_seg_vis,start_point,line_segs[idx][1]]
            prv_seg_vis = line_segs[idx][0]
            start_point = line_segs[idx][1]
            joined_line_segs.append(segment)

    final_segment = [prv_seg_vis,start_point, line_segs[-1][2]]
    joined_line_segs.append(final_segment)

    return joined_line_segs



def vis_sampling(p1, p2, mat, item,):
    p1Local = mat @ Vector(p1)
    p2Local = mat @ Vector(p2)

    # Get Screen Space Points
    p1ss = get_ss_point(p1Local)
    p2ss = get_ss_point(p2Local)

    # Get ss normal vectorsP
    dir_vec = p1ss - p2ss
    n1ss = Vector((dir_vec.y, -dir_vec.x))
    n2ss = Vector((-dir_vec.y, dir_vec.x))

    ss_norms = [n1ss,n2ss]

    # Length in ss is ~number of pixels. use for num of visibility samples
    ss_length_vec = p1ss-p2ss
    ss_samples = math.floor(ss_length_vec.length)
    if ss_samples < 1: ss_samples = 1

    last_vis_state = check_visible(item, p1Local, ss_norms)
    line_segs = []
    seg_start = p1
    distVector = Vector(p1) - Vector(p2)
    dist = distVector.length
    iter_dist = fabs((dist / ss_samples))

    for i in range(1,ss_samples):
        p_check = interpolate3d(Vector(p1), Vector(p2), iter_dist * i) # interpolate line to get point to check
        p_check_vis = check_visible(item, mat @ Vector(p_check), ss_norms) # Check the visibility of that point

        if last_vis_state is not p_check_vis:
            line = [last_vis_state, seg_start, p_check] 
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


def check_visible(item, point, ss_norms):
    epsilon = 0.0001
    context = bpy.context
    scene = context.scene
    global width

    #Set Z-offset
    z_offset = 0.0
    if item != None:
        if 'lineDepthOffset' in item:
            z_offset += item.lineDepthOffset / 10

    dist = get_camera_z_dist(point)
    if dist < 0:
        return -1

    if dist < near_clip or dist > far_clip:
        return -1

    #Get Render info

    # Get ss_point and adjacent normal points
    point_ss = get_ss_point(point)
    ss2 = point_ss + ss_norms[0].normalized()
    ss3 = point_ss + ss_norms[1].normalized()

    # Get Clip space depth
    point_clip = get_clip_space_coord(point)

    # Get Depth buffer Pixel Index based on SS Point    
    db_idx1 = int(((width * math.floor(point_ss[1]))+1 + math.floor(point_ss[0])) -1)
    db_idx2 = int(((width * math.floor(ss2[1]))+1 + math.floor(ss2[0])) -1)
    db_idx3 = int(((width * math.floor(ss3[1]))+1 + math.floor(ss3[0])) -1)
    
    # Get 3 points depths
    bd1 = get_true_z_at_idx(db_idx1)
    bd2 = get_true_z_at_idx(db_idx2)
    bd3 = get_true_z_at_idx(db_idx3)

    # Get Depth From Clip Space point
    point_vecdepth = (point_clip[2]) - z_offset

    # Check Clip space point against depth buffer value
    check1 = (bd1 - point_vecdepth) > -epsilon
    check2 = (bd2 - point_vecdepth) > -epsilon
    check3 = (bd3 - point_vecdepth) > -epsilon

    pointVisible = check1 or check2 or check3

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