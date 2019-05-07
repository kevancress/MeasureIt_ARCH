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
# File: measureit_arch_main.py
# Main panel for different MeasureitArch general actions
# Author: Antonio Vazquez (antonioya), Kevan Cress
#
# ----------------------------------------------------------

import bpy

class M_ARCH_UL_styles_list(bpy.types.UIList):
    # The draw_item function is called for each item of the collection that is visible in the list.
    #   data is the RNA object containing the collection,
    #   item is the current drawn item of the collection,
    #   icon is the "computed" icon for the item (as an integer, because some objects like materials or textures
    #   have custom icons ID, which are not available as enum items).
    #   active_data is the RNA object containing the active property for the collection (i.e. integer pointing to the
    #   active item of the collection).
    #   active_propname is the name of the active property (use 'getattr(active_data, active_propname)').
    #   index is index of the current item in the collection.
    #   flt_flag is the result of the filtering process for this item.
    #   Note: as index and flt_flag are optional arguments, you do not have to use/declare them here if you don't
    #         need them.
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        gen = data
        # draw_item must handle the three layout types... Usually 'DEFAULT' and 'COMPACT' can share the same code.
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.use_property_decorate = False
            # You should always start your row layout by a label (icon + text), or a non-embossed text field,
            # this will also make the row easily selectable in the list! The later also enables ctrl-click rename.
            # We use icon_value of label, as our given icon is an integer value, not an enum ID.
            # Note "data" names should never be translated!
            row = layout.row(align=True)
            subrow = row.row()
            subrow.prop(item, "name", text="",emboss=False,icon='MESH_CUBE')
            if item.visible:
                visIcon = 'HIDE_OFF'
            else:
                visIcon = 'HIDE_ON'

            if item.isOutline:
                outIcon = 'SEQ_CHROMA_SCOPE'
            else:
                outIcon = 'VOLUME'

            if item.lineDrawHidden:
                hiddenIcon = 'MOD_WIREFRAME'
            else:
                hiddenIcon = 'MESH_CUBE'
            subrow = row.row()
            subrow.scale_x = 0.4
            subrow.prop(item, 'color',emboss=True, text="")
            subrow = row.row(align=True)
            subrow.prop(item, 'isOutline', text="", toggle=True, icon=outIcon,emboss=False)
            subrow.prop(item, 'lineDrawHidden', text="", toggle=True, icon=hiddenIcon)
            subrow.prop(item, "visible", text="", icon = visIcon)
            
            

        # 'GRID' layout type should be as compact as possible (typically a single icon!).
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

class UIStylesList(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "MeasureIt-ARCH Styles"
    bl_idname = "OBJECT_PT_ui_list_example"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        #layout.use_property_decorate = False
        
        obj = context.object
        if 'StyleGenerator' in context.scene:     
            scene = context.scene
            StyleGen = scene.StyleGenerator[0]

            # template_list now takes two new args.
            # The first one is the identifier of the registered UIList to use (if you want only the default list,
            # with no custom draw code, use "UI_UL_list").\
            row = layout.row()
            row.template_list("M_ARCH_UL_styles_list", "", StyleGen, "line_groups", StyleGen, "active_style_index",rows=2, type='DEFAULT')

            col = row.column(align=True)
            col.operator("measureit_arch.addstylebutton", icon='ADD', text="")
            op = col.operator("measureit_arch.deletepropbutton", text="", icon="X")
            op.tag = StyleGen.active_style_index  # saves internal data
            op.item_type = 'L'
            op.is_style = True

            col = layout.column()
            activeLineStyle = StyleGen.line_groups[StyleGen.active_style_index]
            col.prop(activeLineStyle, 'color', text="Color")
            col.prop(activeLineStyle, 'lineWeight', text="Lineweight" )
            col.prop(activeLineStyle, 'lineDepthOffset', text="Z Offset")
            delOp = col.operator("measureit_arch.deleteallitemsbutton", text="Delete All Styles", icon="X")
            delOp.is_style = True
            # The second one can usually be left as an empty string.
            # It's an additional ID used to distinguish lists in case you
            # use the same list several times in a given area.
            #layout.template_list("M_ARCH_UL_measure_list", "compact",  StyleGen, "line_groups",
            #                    StyleGen, "active_style_index", type='COMPACT')