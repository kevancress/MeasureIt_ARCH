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
#  GNU General Public License for more details.a
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


# ----------------------------------------------------------
# Methods for Text Drawing and Font Atlases
# Author: Kevan Cress
#
# ----------------------------------------------------------

import bpy
import blf
import math
import gpu

from mathutils import Vector, Matrix

from fontTools import ttLib

from bpy.types import PropertyGroup, Operator, Collection
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, BoolProperty, StringProperty, FloatProperty, EnumProperty, PointerProperty


all_font_data = {}

def draw_font_atlas(font, context):
    scene = context.scene
    sceneProps = scene.MeasureItArchProps
    global all_font_data
    
    if font == None:
        font_key = 'bfont'
    else:
        font_key = font.name

    if font == None:
        font_path = '//bfont.ttf'
    else:
        font_path = font.filepath

    if not font_key in all_font_data:
        all_font_data[font_key] = {
            'regen':True,
            'glyph_positions': {}
        }

    resolution = sceneProps.preview_resolution

    font_file = bpy.path.abspath(font_path)
    font_id = blf.load(font_file)
   

    # Set BLF font Properties
    blf.color(font_id, 1.0,1.0,1.0,1.0)
    blf.size(font_id,  12.0 * resolution/72.0)

    
    tt = None
    try:
        tt = ttLib.TTFont(font_file, verbose=1)
    except Exception as e:
        print('Problem loading font!')
        return
    
    glyphs = ''
    num_glyphs = 0
    for key, value in tt['cmap'].getBestCmap().items():
        #print(chr(key))
        num_glyphs += 1
        glyphs += chr(key)
    
    
    sq_size = math.ceil(math.sqrt(num_glyphs))
    text = glyphs


    # Calculate Optimal Dimensions for Text Texture.
    
    fheight = blf.dimensions(font_id, 'Tpg')[1] *1.2
    fwidth = blf.dimensions(font_id, '—')[0] * 1.2

    char_width = math.ceil(fwidth)
    
    biggest_dim = fwidth
    if fheight > fwidth:
        biggest_dim = fheight

    width = math.ceil(biggest_dim) * sq_size
    height = math.ceil(biggest_dim) * sq_size
    line_height = math.ceil(fheight)


    # Start Offscreen Draw
    if width != 0 and height != 0:
        textOffscreen = gpu.types.GPUOffScreen(width, height)

        with textOffscreen.bind():
            fb = gpu.state.active_framebuffer_get()
            fb.clear(color=(0.0, 0.0, 0.0, 0.0))

            view_matrix = Matrix([
                [2 / width, 0, 0, -1],
                [0, 2 / height, 0, -1],
                [0, 0, 1, 0],
                [0, 0, 0, 1]])

            gpu.matrix.reset()
            gpu.matrix.load_matrix(view_matrix)
            gpu.matrix.load_projection_matrix(Matrix.Identity(4))
            
            for i in range(sq_size):
                for j in range(sq_size):
                    x_pos = char_width * j
                    y_pos = line_height * i 
                    blf.position(font_id, x_pos ,y_pos + 0.2*line_height, 0)
                    current_glyph_idx = i*sq_size + j
                    if current_glyph_idx < len(glyphs):
                        current_glyph = glyphs[current_glyph_idx]
                        uv_x = x_pos/height
                        uv_y = y_pos/width
                        all_font_data[font_key]['glyph_positions'][current_glyph] = [uv_x,uv_y]
                        blf.draw(font_id, current_glyph)

        # Write Texture Buffer to ID Property as List
        texture_buffer =  fb.read_color(0, 0, width, height, 4, 0, 'FLOAT')
        texture_buffer.dimensions = width*height*4

        # ONLY USE FOR DEBUG. SERIOUSLY SLOWS PREFORMANCE
        if sceneProps.measureit_arch_debug_text and text != "":
            if not 'atlas_debug' in bpy.data.images:
                bpy.data.images.new('atlas_debug', width, height)
            image = bpy.data.images['atlas_debug']
            image.scale(width, height)
            image.pixels = [v for v in texture_buffer]
        
        all_font_data[font_key]['regen'] = False
        all_font_data[font_key]['texture_buffer'] = gpu.types.GPUTexture([width,height], layers=0, data=texture_buffer)

        del texture_buffer
        textOffscreen.free()

