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
from decimal import *

from mathutils import Vector, Matrix

### Use Decimeters for DXF export units, multiplying blender standard Meter units by 10. Why does AutoCAD import these dm files as drawings with mm drawing units scaled correctly, only autodesk knows.
### AutoCADs unit system and dxf support is a disaster... 

hatch_col_id = 10
hatch_col_dict = {}




def quantize_vec2(vec2,precision='1e-6'):
    x = Decimal('{}'.format(vec2.x)).quantize(Decimal(precision))
    y = Decimal('{}'.format(vec2.y)).quantize(Decimal(precision))
    return(x,y)

def dxf_line_shader(lineGroup, itemProps, coords, lineWeight, rgb, dxf, myobj, mat=Matrix.Identity(4), make_block = False):
    view = get_view()
    dashed = False
    line_buffer = []
    model_space = dxf.modelspace()
    ss_origin = vector_utils.get_worldscale_projection(myobj.location)

    #if ss_origin.z < 0:
        #print('Object Origin behind Camera. Skipping')
        #return

    if make_block:
        block = None
        blockname = myobj.name
        if myobj.data != None:
            blockname = myobj.data.name

        dxf_name = safe_name(view.name + '-' + blockname, is_dxf=True)

        try:
            dxf.blocks.get(dxf_name)
            block = dxf.blocks[dxf_name]
        except ezdxf.DXFKeyError:
            block = dxf.blocks.new(name = dxf_name)  
            model_space.add_blockref(dxf_name, (0,0), dxfattribs={"layer": itemProps.name})

    

    dashed = "lineDrawDashed" in itemProps and itemProps.lineDrawDashed
    draw_hidden = 'lineDrawHidden' in itemProps and itemProps.lineDrawHidden

   
    for x in range(0, len(coords) - 1, 2):
        line_segs = vector_utils.depth_test(coords[x], coords[x + 1], mat, itemProps)
        for line in line_segs:
            vis = line[0]
            p1 = line[1]
            p2 = line[2]
            if vis == -1:
                continue

            if vis or draw_hidden:
                p1ss = vector_utils.get_worldscale_projection(mat @ Vector(p1)) 
                p2ss = vector_utils.get_worldscale_projection(mat @ Vector(p2))

                p1_float = quantize_vec2(p1ss)
                p2_float = quantize_vec2(p2ss)
                
                # Check if we've drawn this line before
                check_string_1 = "{}:{}".format(p1_float,p2_float)
                check_string_2 = "{}:{}".format(p2_float,p1_float)

                if p1_float == p2_float: # skip lines that are 0 length when projected
                    continue

                if check_string_1 in line_buffer or check_string_2 in line_buffer:
                    continue
                else:
                    #print("{},{}".format(float(p1_float[0]),float(p2_float[0])))
                    line_buffer.append(check_string_1)
                    if make_block:
                        block.add_line(p1_float, p2_float , dxfattribs={"layer": itemProps.name})
                    else:
                        line = model_space.add_line(p1_float, p2_float, dxfattribs={"layer": itemProps.name})


# From https://ezdxf.readthedocs.io/en/stable/tutorials/linear_dimension.html
def dxf_aligned_dimension(dim, dimProps, p1, p2, origin, dxf):
    model_space = dxf.modelspace()
    
    layer = dimProps.name


    dist = -(dimProps.dimOffset + dim.tweakOffset) # Dimension distance needs to be flipped for some reason

    if dim.dimFlip:
        dist = -dist

    ssp1 = vector_utils.get_worldscale_projection(Vector(p1)) 
    ssp2 = vector_utils.get_worldscale_projection(Vector(p2))

    ssp1 = quantize_vec2(ssp2)
    ssp2 = quantize_vec2(ssp2)

    ssOrigin = vector_utils.get_worldscale_projection(Vector(origin))

    if (Vector(ssp1) - Vector(ssp2)).length == 0:
        print('zero length ss dim vector, returning')
        return
        

    dim = model_space.add_aligned_dim(
        distance = dist,  # location of the dimension line
        p1=ssp1,  # 1st measurement point
        p2=ssp2,  # 2nd measurement point
        dimstyle="MeasureIt_ARCH",  # Custom MeasureIt_ARCH dim style defined in renderdxf
        dxfattribs={"color":256,"layer": layer}
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

    ssp1 = quantize_vec2(ssp2)
    ssp2 = quantize_vec2(ssp2)

    ssOrigin = vector_utils.get_worldscale_projection(Vector(origin))

    dxf_dim = model_space.add_linear_dim(
        base = ssOrigin,  # location of the dimension line
        p1=ssp1,  # 1st measurement point
        p2=ssp2,  # 2nd measurement point
        angle = rot,
        dimstyle="MeasureIt_ARCH",  # Custom MeasureIt_ARCH dim style defined in renderdxf
        dxfattribs={"layer": layer}
    )

    dxf_dim.render()


def dxf_fill_shader(coords,dxf,layer):
    model_space = dxf.modelspace()
    coords_2d = []
    hatch = model_space.add_hatch(color=256,dxfattribs={"layer": layer})
    for coord in coords:
        c2d = quantize_vec2(vector_utils.get_worldscale_projection(Vector(coord)))
        if c2d not in coords_2d:
            coords_2d.append(c2d)

    most_x = Vector(coords_2d[0])
    most_y = Vector(coords_2d[0])
    least_y = Vector(coords_2d[0])
    least_x = Vector(coords_2d[0])
    for coord in coords_2d:
        coord = Vector(coord)
        if most_x.x < coord.x:
            most_x = coord
        if most_y.y < coord.y:
            most_y = coord
        if least_x.x > coord.x:
            least_x = coord
        if least_y.y> coord.y:
            least_y = coord

    path = [most_x,least_y,least_x,most_y]
    hatch.paths.add_polyline_path(path,is_closed=True)

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

    if annotationProps.draw_leader:
        leader = model_space.add_leader(ssLeaderCoords,dxfattribs={"layer": annotationProps.name})

    for textField in annotation.textFields:
        anno_text.text += textField.text
        anno_text.text += '\n'
    

    
    #MTEXT_TOP_LEFT	1
    #MTEXT_TOP_CENTER	2
    #MTEXT_TOP_RIGHT	3
    #MTEXT_MIDDLE_LEFT	4
    #MTEXT_MIDDLE_CENTER	5
    #MTEXT_MIDDLE_RIGHT	6
    #MTEXT_BOTTOM_LEFT	7
    #MTEXT_BOTTOM_CENTER	8
    #MTEXT_BOTTOM_RIGHT	9
    
    attach_val = 0
    if annotationProps.textPosition =='T':
        attach_val = 0
    elif annotationProps.textPosition =='M':
        attach_val = 3
    elif annotationProps.textPosition =='B':
        attach_val = 6

    if annotationProps.textAlignment =='L':
        attach_val += 1
    elif annotationProps.textAlignment =='C':
        attach_val += 2
    elif annotationProps.textAlignment =='R':
        attach_val += 3
    
    
    anno_text.dxf.attachment_point = attach_val
    anno_text.dxf.char_height = annotationProps.fontSize/72
    anno_text.dxf.insert = ssOrigin


    # Get Text Rotation
    x_vec = Vector((1,0))
    
    ssp0 = vector_utils.get_worldscale_projection(annotation.textFields[0]['textcard'][0])
    ssp1 = vector_utils.get_worldscale_projection(annotation.textFields[0]['textcard'][1])
    ssp2 = vector_utils.get_worldscale_projection(annotation.textFields[0]['textcard'][2])
    ssp3 = vector_utils.get_worldscale_projection(annotation.textFields[0]['textcard'][3])
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

    # Re Calc direction vectors after flips
    xDirVec = card[3] - card[0]
    yDirVec = card[1] - card[0]

    # Get the rotation angle of the text card from horizontal
    rotation = math.degrees(xDirVec.angle_signed(x_vec))

    print(rotation)

    anno_text.dxf.rotation = rotation



def dxf_text_shader(textField,style,coords,origin,dxf):
    model_space = dxf.modelspace()
    anno_text = model_space.add_mtext("", dxfattribs={"layer": style.name})

    ssLeaderCoords = []
    for coord in coords:
        ssPoint = vector_utils.get_worldscale_projection(coord)
        ssLeaderCoords.append(ssPoint)

    ssOrigin = vector_utils.get_worldscale_projection(textField['textcard'][0])

    anno_text.text = textField.text

    

    
    #MTEXT_TOP_LEFT	1
    #MTEXT_TOP_CENTER	2
    #MTEXT_TOP_RIGHT	3
    #MTEXT_MIDDLE_LEFT	4
    #MTEXT_MIDDLE_CENTER	5
    #MTEXT_MIDDLE_RIGHT	6
    #MTEXT_BOTTOM_LEFT	7
    #MTEXT_BOTTOM_CENTER	8
    #MTEXT_BOTTOM_RIGHT	9
    
    attach_val = 0
    if style.textPosition =='T':
        attach_val = 0
    elif style.textPosition =='M':
        attach_val = 3
    elif style.textPosition =='B':
        attach_val = 6

    if style.textAlignment =='L':
        attach_val += 1
    elif style.textAlignment =='C':
        attach_val += 2
    elif style.textAlignment =='R':
        attach_val += 3
    
    
    anno_text.dxf.attachment_point = attach_val
    anno_text.dxf.char_height = style.fontSize/72
    anno_text.dxf.insert = ssOrigin


    # Get Text Rotation

    x_vec = Vector((1,0))
    x_p1 = vector_utils.get_worldscale_projection(textField['textcard'][0])
    x_p2 = vector_utils.get_worldscale_projection(textField['textcard'][3])
    card_x_dir = Vector(x_p2) - Vector(x_p1)
    rot_angle = x_vec.angle(card_x_dir, 45)

    print(rot_angle)

    anno_text.dxf.rotation = math.degrees(rot_angle)
