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
# File: measureit_arch_tables.py
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
from .measureit_arch_baseclass import BaseWithText


class RowProperties(PropertyGroup,BaseWithText):
    height: FloatProperty(
        name="Height",
        description="Row Height",
        default=1.0)
    

class ColumnProperties(PropertyGroup,):
    width: FloatProperty(
        name="Width",
        description="Column Width",
        default=1.0)

class TableProperties(PropertyGroup, BaseWithText):
    name: StringProperty(name="Table Name")

    anchor: PointerProperty(type=Object)

    rows: CollectionProperty(type=RowProperties)
    columns: CollectionProperty(type=ColumnProperties)
    
    extend_header: BoolProperty(name='Extend Header', default=True)
    extend_short_rows: BoolProperty(name='Extend Short Rows', default=True)

    textFile: PointerProperty(
        name="TextFile",
        type = bpy.types.Text)
    
    wrap_text: BoolProperty(name='Wrap Text', default=False)
    
    lineWeight: FloatProperty(
        name="Line Weight",
        description="Line Weight",
        default=1.0)


class TableContainer(PropertyGroup):

    active_index: IntProperty(name='Active Table Index')
    num_tables: IntProperty(name='number of tables in collection')

    show_settings: BoolProperty(name='Show Sheet View Settings', default=False)

    tables: CollectionProperty(type=TableProperties)



class AddTableButton(Operator):
    bl_idname = "measureit_arch.addtablebutton"
    bl_label = "Add"
    bl_description = "Add a new Table"
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
                context.object.name = 'Table Empty'

            pointList, warningStr = get_smart_selected(usePairs=False)

            if warningStr != '':
                self.report({'ERROR'}, warningStr)

            print(pointList)

            for point in pointList:
                obj = point['obj']
                anchor = point['vert']
                
                tableGen = obj.TableGenerator

                newTable = tableGen.tables.add()

                newTable.anchor = mainobject
                tableGen.num_tables += 1
   
                if sceneProps.default_annotation_style != '':
                    newTable.uses_style = True
                    newTable.style = sceneProps.default_annotation_style
                else:
                    newTable.uses_style = False

                newTable.name = "Table {}".format(tableGen.num_tables)

                newTable.color = (0, 0, 0, 1)
                newTable.fontSize = 24
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")

        return {'CANCELLED'}


class M_ARCH_UL_Tables_List(UIList):
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

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')

            


class OBJECT_PT_Tables(Panel):
    """ A panel in the Scene properties window """
    bl_parent_id = 'OBJECT_PT_Panel'
    bl_label = "Tables"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon='SPREADSHEET')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        tableGen = context.object.TableGenerator

        row = layout.row()

        # Draw The UI List
        row.template_list(
            "M_ARCH_UL_Tables_List", "", tableGen, "tables", tableGen,
            "active_index", rows=2, type='DEFAULT')

        col = row.column(align=True)

        if len(tableGen.tables) > 0 and tableGen.active_index < len(tableGen.tables):
            table = tableGen.tables[tableGen.active_index]

            # Settings Below List
            if tableGen.show_settings:
                settingsIcon = 'DISCLOSURE_TRI_DOWN'
            else:
                settingsIcon = 'DISCLOSURE_TRI_RIGHT'

            box = layout.box()
            col = box.column()
            row = col.row()
            row.prop(tableGen, 'show_settings', text="",
                     icon=settingsIcon, emboss=False)

            row.label(text=table.name + ' Settings:')

            if tableGen.show_settings:
                col = box.column()
                col.prop(table,'extend_short_rows')
                #col.prop(table, 'use_header')
                #col.prop(table, 'wrap_text')
                col.prop(table,'textFile')
                #col.prop(table, 'num_columns')
                col.prop(table,'fontSize')

    
