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
# Author: Antonio Vazquez (antonioya), Kevan Cress
# ----------------------------------------------------------

# ----------------------------------------------
# Define Addon info
# ----------------------------------------------
bl_info = {
    "name": "MeasureIt_ARCH",
    "author": "Kevan Cress, Antonio Vazquez (antonioya)",
    "location": "View3D > Tools Panel /Properties panel",
    "version": (0, 4, 6),
    "blender": (2, 83, 0),      
    "description": "Tools for adding Dimensions, Annotations and Linework to Objects",
    "warning": "",
    "doc_url": "https://github.com/kevancress/MeasureIt_ARCH/",
    "category": "3D View"
}

import sys
import os
import site

cwd = os.path.dirname(os.path.realpath(__file__))
site.addsitedir(os.path.join(cwd, "libs"))

# ----------------------------------------------
# Import modules
# ----------------------------------------------
if "bpy" in locals():
    import importlib
    #importlib.reload(measureit_arch_geometry)
    #importlib.reload(measureit_arch_annotations)
    #importlib.reload(measureit_arch_baseclass)
    #importlib.reload(measureit_arch_main)
    #importlib.reload(measureit_arch_lines)
    #importlib.reload(measureit_arch_render)
    #importlib.reload(measureit_arch_styles)
    #importlib.reload(measureit_arch_dimensions)
    print("measureit_arch: Reloaded multifiles")
else:
    #from . import measureit_arch_geometry
    #from . import measureit_arch_annotations
    #from . import measureit_arch_baseclass
    #from . import measureit_arch_main
    #from . import measureit_arch_lines
    #from . import measureit_arch_render
    #from . import measureit_arch_styles
    #from . import measureit_arch_dimensions
    print("measureit_arch: Imported multifiles")

import bpy
from bpy.types import (
        PropertyGroup,
        AddonPreferences,
        Scene,
        WindowManager,
        )
from bpy.props import (
        CollectionProperty,
        FloatVectorProperty,
        IntProperty,
        BoolProperty,
        StringProperty,
        FloatProperty,
        EnumProperty,
        )
from . import auto_load
auto_load.init()

from .measureit_arch_main import precision_ui

# --------------------------------------------------------------
# Register all operators and panels
# --------------------------------------------------------------

panelClasses = [

]

# Define menu
# noinspection PyUnusedLocal
def register():
    for cls in panelClasses:
        bpy.utils.register_class(cls)
    auto_load.register()
    bpy.types.SCENE_PT_unit.append(precision_ui)
    # Define properties\
    wm = WindowManager
    # register internal property
    wm.measureit_arch_run_opengl = BoolProperty(default=False)
    
def unregister():
    auto_load.unregister()
    bpy.types.SCENE_PT_unit.remove(precision_ui)

    # remove OpenGL data
    measureit_arch_main.ShowHideViewportButton.handle_remove(measureit_arch_main.ShowHideViewportButton, bpy.context)
    wm = bpy.context.window_manager
    p = 'measureit_arch_run_opengl'
    if p in wm:
        del wm[p]

if __name__ == '__main__':
    register()
