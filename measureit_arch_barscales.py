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


# ----------------------------------------------------------
# File: measureit_arch_barscales.py
# MeasureIt_ARCH Tables
# Author:  Kevan Cress
#
# ----------------------------------------------------------



import bpy

from bpy.types import PropertyGroup, Panel, Operator, UIList, Scene, Object
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, \
    BoolProperty, StringProperty, PointerProperty, FloatProperty

from mathutils import Vector, Matrix, Euler, Quaternion
from .measureit_arch_utils import get_smart_selected, get_view
from .measureit_arch_baseclass import BaseWithText, draw_textfield_settings

scale_configs = {

}

def text_file_update(self,context):
    self.text_file_updated = True


class BarScaleProperties(PropertyGroup, BaseWithText):

    anchor: PointerProperty(type=Object)

    height: FloatProperty(
        name="Minimum Row Height",
        description="Minimum Row Height in Paper Space Units",
        subtype = 'DISTANCE',
        min = 0,
        default=0.2)

    max_width: FloatProperty(
        name="Max Width",
        description="Max Width in Paper Space Units",
        subtype = 'DISTANCE',
        min = 0,
        default=0.0)
    
    lineWeight: FloatProperty(
        name="Line Weight",
        description="Line Weight",
        default=1.0)
    
    first_increment: FloatProperty(
        name="First Increment",
        description="First Increment in Model Space units",
        subtype = 'DISTANCE',
        min = 0,
        default= 0.25)
    
    second_increment:FloatProperty(
        name="Second Increment",
        description="Second Increment in Model Space units",
        subtype = 'DISTANCE',
        min = 0,
        default= 0.5)

    third_increment:FloatProperty(
        name="Third Increment",
        description="Third Increment in Model Space units (-1 to skip)",
        subtype = 'DISTANCE',
        soft_min = 0,
        default= -1)
    
    final_increment:FloatProperty(
        name="Final Increment",
        description="Final Increment in Model Space units",
        subtype = 'DISTANCE',
        min = 0,
        default= 1.0)



class BarScaleContainer(PropertyGroup):

    active_index: IntProperty(name='Active Table Index')

    show_settings: BoolProperty(name='Show Sheet View Settings', default=False)

    barScales: CollectionProperty(type=BarScaleProperties)



class AddBarScaleButton(Operator):
    bl_idname = "measureit_arch.addbarscalebutton"
    bl_label = "Add"
    bl_description = "Add a new Bar Scale"
    bl_category = 'MeasureitArch'

    @classmethod
    def poll(cls, context):
        obj = context.object
        if obj is None or len(context.selected_objects) == 0:
            return True
        elif obj.type == "EMPTY":
            return True
        else:
            return False

    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            scene = context.scene
            sceneProps = scene.MeasureItArchProps
            mainobject = context.object

            # If no obj selected, created an empty
            if (bpy.context.mode == 'OBJECT' and
                len(context.selected_objects) == 0):
                cursorLoc = bpy.context.scene.cursor.location
                bpy.ops.object.empty_add(
                    type='SPHERE', radius=0.01, location=cursorLoc)
                context.object.name = 'Bar Scale Empty'

            pointList, warningStr = get_smart_selected(usePairs=False)

            if warningStr != '':
                self.report({'ERROR'}, warningStr)

            print(pointList)

            for point in pointList:
                obj = point['obj']
                anchor = point['vert']
                
                barScaleGen = obj.BarScaleGenerator

                newBarScale = barScaleGen.barScales.add()

                newBarScale.anchor = mainobject
   
                if sceneProps.default_annotation_style != '':
                    newBarScale.uses_style = True
                    newBarScale.style = sceneProps.default_annotation_style
                else:
                    newBarScale.uses_style = False

                newBarScale.name = "Barscale {}".format(len(barScaleGen.barScales))
                newBarScale.textPosition = 'M'

                newBarScale.color = (0, 0, 0, 1)
                newBarScale.fontSize = 12
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")

        return {'CANCELLED'}


class M_ARCH_UL_BarScale_List(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            table = item
            layout.use_property_decorate = False
            row = layout.row(align=True)
            subrow = row.row()
            subrow.prop(table, "name", text="", emboss=False)
            subrow = row.row()
            subrow.scale_x = 0.6
            subrow.prop(table, 'color', text="")


            
class OBJECT_PT_BarScales(Panel):
    """ A panel in the Scene properties window """
    bl_parent_id = 'OBJECT_PT_Panel'
    bl_label = "Bar Scales"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon='SNAP_INCREMENT')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        barScaleGen = context.object.BarScaleGenerator

        row = layout.row()

        # Draw The UI List
        row.template_list(
            "M_ARCH_UL_Tables_List", "", barScaleGen, "barScales", barScaleGen,
            "active_index", rows=2, type='DEFAULT')

        col = row.column(align=True)

        if len(barScaleGen.barScales) > 0 and barScaleGen.active_index < len(barScaleGen.barScales):
            barScale = barScaleGen.barScales[barScaleGen.active_index]

            # Settings Below List
            if barScaleGen.show_settings:
                settingsIcon = 'DISCLOSURE_TRI_DOWN'
            else:
                settingsIcon = 'DISCLOSURE_TRI_RIGHT'

            box = layout.box()
            col = box.column()
            row = col.row()
            row.prop(barScaleGen, 'show_settings', text="",
                     icon=settingsIcon, emboss=False)

            row.label(text=barScale.name + ' Settings:')

            if barScaleGen.show_settings:
                col = box.column()

                col = box.column()
                split = box.split(factor=0.485)
                col = split.column()
                col.alignment = 'RIGHT'

                col.label(text='Font')
                col = split.column(align=True)
                col.template_ID(
                    barScale, "font", open="font.open", unlink="font.unlink")
                
                col = box.column()
                col.prop(barScale,'fontSize')
                col.prop(barScale,'lineWeight')
               
                col = box.column()
                col.prop(barScale,'max_width')
                col.prop(barScale,'height')

                col.prop(barScale,'first_increment')
                col.prop(barScale,'second_increment')
                col.prop(barScale,'third_increment')
                col.prop(barScale,'final_increment')

            box = layout.box()
            col = box.column()
            row = col.row()



    
