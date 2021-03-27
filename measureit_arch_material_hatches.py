import bpy

from bpy.props import (
    CollectionProperty,
    FloatVectorProperty,
    IntProperty,
    BoolProperty,
    FloatProperty,
    PointerProperty)

from bpy.types import PropertyGroup, Panel, Operator, UIList, Collection
from .measureit_arch_hatches import HatchProperties


class MATERIAL_PT_UIHatch(Panel):
    """ A Panel in the Material properties window """
    #bl_parent_id = 'MATERIAL_PT_Panel'
    bl_label = "Hatch"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"


    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        hatch = context.material.Hatch
        row.prop(hatch, "visible", text="",)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        hatch = context.material.Hatch
        main_col = layout.column()
        col = main_col.column()



        main_col.enabled = hatch.visible
        col = main_col.column()
        col.prop(hatch, 'fill_color', text="Fill Color",)
        col.prop(hatch, 'line_color', text="Line Color",)
        col.prop(hatch, 'lineWeight', text="Line Weight",)
        col = main_col.column()
        col.prop(hatch, 'pattern', text="Pattern",)
        col.prop(hatch, 'patternWeight', text="Pattern Weight",)
        col.prop(hatch, 'patternSize', text="Pattern Size",)
        col.prop(hatch, 'patternRot', text="Pattern Rotation",)
        col.prop(hatch, 'patternOpacity', text="Pattern Opacity",)

