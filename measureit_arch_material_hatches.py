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
        HatchGen = context.material.HatchGenerator
        if len(HatchGen.hatches) != 0:
            hatch = HatchGen.hatches[0]
            row.prop(hatch, "visible", text="",)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        HatchGen = context.material.HatchGenerator
        main_col = layout.column()
        col = main_col.column()

        if len(HatchGen.hatches) == 0:
            main_col.operator("measureit_arch.addmaterialhatchbutton", icon='ADD', text="Use Hatch")
        else:
            hatch = HatchGen.hatches[0]
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



class AddMaterialHatchButton(Operator):
    bl_idname = "measureit_arch.addmaterialhatchbutton"
    bl_label = "Add"
    bl_description = "Create A New Hatch"
    bl_category = 'MeasureitArch'

    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # Add properties

                    HatchGen = context.material.HatchGenerator

                    newHatch = HatchGen.hatches.add()
                    newHatch.name = 'Hatch ' + str(len(HatchGen.hatches))

                    context.area.tag_redraw()
                    return {'FINISHED'}
        return {'FINISHED'}


class DeleteMaterialHatchButton(Operator):
    bl_idname = "measureit_arch.deletematerialhatchbutton"
    bl_label = "Delete Hatch"
    bl_description = "Delete a Hatch"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'}
    tag: IntProperty()

    def execute(self, context):
        # Add properties

        Generator = context.material.HatchGenerator
        Generator.hatches.remove(0)

        return {'FINISHED'}