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
# Collection of DXF "Shaders" for the Various Draw Functions.
# For Use exporting Measureit_ARCH drawings to dxf files
# Author: Kevan Cress
#
# ----------------------------------------------------------

from glob import glob
import gpu
import math
import bpy_extras.object_utils as object_utils
from math import degrees
import bpy
import ezdxf
from .measureit_arch_utils import get_view, safe_name
from . import vector_utils

from mathutils import Vector, Matrix

### Use Decimeters for DXF export units, multiplying blender standard Meter units by 10. Why does AutoCAD import these dm files as drawings with mm drawing units scaled correctly, only autodesk knows.
### AutoCADs unit system and dxf support is a disaster... 

hatch_col_id = 10
hatch_col_dict = {}

def dxf_line_shader(lineGroup, itemProps, coords, lineWeight, rgb, dxf, myobj, mat=Matrix.Identity(4)):
    dashed = False
    line_buffer = []
    model_space = dxf.modelspace()
    ss_origin = vector_utils.get_worldscale_projection(myobj.location)

    #if ss_origin.z < 0:
        #print('Object Origin behind Camera. Skipping')
        #return

    block = None

    dxf_name = safe_name(myobj.name, is_dxf=True)

    try:
        dxf.blocks.get(dxf_name)
        block = dxf.blocks[dxf_name]
    except ezdxf.DXFKeyError:
        block = dxf.blocks.new(name = dxf_name)  
        model_space.add_blockref(dxf_name, (0,0), dxfattribs={"layer": itemProps.name})

    

    dashed = "lineDrawDashed" in itemProps and itemProps.lineDrawDashed
    draw_hidden = 'lineDrawHidden' in itemProps and itemProps.lineDrawHidden

   
    for x in range(0, len(coords) - 1, 2):
        line_segs = vector_utils.depth_test(coords[x], coords[x + 1], mat, itemProps, vector_utils.depthbuffer)
        for line in line_segs:
            vis = line[0]
            p1 = line[1]
            p2 = line[2]
            if vis == -1:
                continue

            if vis or draw_hidden:
                p1ss = vector_utils.get_worldscale_projection(mat @ Vector(p1)) 
                p2ss = vector_utils.get_worldscale_projection(mat @ Vector(p2))
                
                # Check if we've drawn this line before
                check_string_1 = "{}:{}".format(p1ss,p2ss)
                check_string_2 = "{}:{}".format(p2ss,p1ss)
                if check_string_1 in line_buffer or check_string_2 in line_buffer:
                    continue
                else:
                    line_buffer.append(check_string_1)
                    #line = model_space.add_line(p1ss, p2ss, dxfattribs={"layer": itemProps.name})
                    block.add_line(p1ss, p2ss, dxfattribs={"layer": itemProps.name})


# From https://ezdxf.readthedocs.io/en/stable/tutorials/linear_dimension.html
def dxf_aligned_dimension(dim, dimProps, p1, p2, origin, dxf):
    model_space = dxf.modelspace()
    
    layer = dimProps.name

    dist = -(dimProps.dimOffset + dim.tweakOffset) # Dimension distance needs to be flipped for some reason

    ssp1 = vector_utils.get_worldscale_projection(Vector(p1)) 
    ssp2 = vector_utils.get_worldscale_projection(Vector(p2))
    ssOrigin = vector_utils.get_worldscale_projection(Vector(origin))

    if (Vector(ssp1) - Vector(ssp2)).length == 0:
        print('zero length ss dim vector, returning')
        return
        

    dim = model_space.add_aligned_dim(
        distance = dist,  # location of the dimension line
        p1=ssp1,  # 1st measurement point
        p2=ssp2,  # 2nd measurement point
        dimstyle="MeasureIt_ARCH",  # Custom MeasureIt_ARCH dim style defined in renderdxf
        dxfattribs={"layer": layer}
    )

    dim.render()

def dxf_axis_dimension(dim, dimProps, p1, p2, origin, dxf):
    model_space = dxf.modelspace()

    layer = dimProps.name
    view = get_view()

    model_view_mat = gpu.matrix.get_model_view_matrix()
    cx4 = Vector((1,0,0,0))

    ndcCamX = cx4 @ model_view_mat
    ssCamX = Vector((ndcCamX.x,ndcCamX.y)).normalized()

    rot = degrees(Vector((1,0)).angle_signed(ssCamX))

    if math.isclose(abs(rot),180,rel_tol=0.001):
        rot = 0

    if dim.dimAxis == 'Y':
        rot -= 90

    dist = -(dimProps.dimOffset + dim.tweakOffset) # Dimension distance needs to be flipped for some reason

    ssp1 = vector_utils.get_worldscale_projection(Vector(p1))
    ssp2 = vector_utils.get_worldscale_projection(Vector(p2))
    ssOrigin = vector_utils.get_worldscale_projection(Vector(origin))

    dim = model_space.add_linear_dim(
        base = ssOrigin,  # location of the dimension line
        p1=ssp1,  # 1st measurement point
        p2=ssp2,  # 2nd measurement point
        angle = rot,
        dimstyle="MeasureIt_ARCH",  # Custom MeasureIt_ARCH dim style defined in renderdxf
        dxfattribs={"layer": layer}
    )

    dim.render()


def dxf_hatch_shader(hatch,coords,dxf,material):
    global hatch_col_id
    global hatch_col_dict

    if material.name not in hatch_col_dict:
        hatch_col_id += 1
        hatch_col_dict[material.name] = hatch_col_id 

    model_space = dxf.modelspace()
    hatch = model_space.add_hatch(color=hatch_col_dict[material.name],dxfattribs={"layer": material.name})


    path = []
    for coord in coords:
        ssPoint = vector_utils.get_worldscale_projection(Vector(coord))
        path.append(ssPoint)

    hatch.paths.add_polyline_path(path,is_closed=True)

def dxf_annotation_shader(annotation,annotationProps,coords,origin,dxf):
    model_space = dxf.modelspace()
    anno_text = model_space.add_mtext("", dxfattribs={"layer": annotationProps.name})

    ssLeaderCoords = []
    for coord in coords:
        ssPoint = vector_utils.get_worldscale_projection(coord)
        ssLeaderCoords.append(ssPoint)

    ssOrigin = vector_utils.get_worldscale_projection(origin)

    leader = model_space.add_leader(ssLeaderCoords,dxfattribs={"layer": annotationProps.name})

    for textField in annotation.textFields:
        anno_text.text += textField.text
        anno_text.text += '\n'
    
    anno_text.dxf.char_height = 0.5
    anno_text.dxf.insert = ssOrigin