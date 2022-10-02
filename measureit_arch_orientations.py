import bpy
from mathutils import Vector, Matrix


from bpy.props import (
    CollectionProperty,
    IntProperty,
    BoolProperty,
    StringProperty,
    FloatProperty,
    FloatVectorProperty,
    EnumProperty,
    PointerProperty
)

from bpy.types import PropertyGroup, Panel, Operator, UIList, Scene, Object



class TransformOrientationProperties(PropertyGroup):

    basisX: FloatVectorProperty(
        name="Transform Orientation X Basis",
        description="X Basis Vector for this transform orientation",
        unit='LENGTH',
        default=Vector((1.0,0.0,0.0)))

    basisY: FloatVectorProperty(
        name="Transform Orientation Y Basis",
        description="Y Basis Vector for this transform orientation",
        unit='LENGTH',
        default=Vector((0.0,1.0,0.0)))

    basisZ: FloatVectorProperty(
        name="Transform Orientation Z Basis",
        description="Z Basis Vector for this transform orientation",
        unit='LENGTH',
        default=Vector((0.0,0.0,1.0)))

    force_orthonormalized_basis: BoolProperty(
        name="Forces Orthonormalized Basis",
        description="Forces basis vectors to be Orthogonal to eachother and normal",
        default=False)

    orientation_from_object: BoolProperty(
        name="Orientation From Object",
        description="Use an Objects transform as the basis for this transform orientation",
        default=True)

    orientation_basis_object: PointerProperty(type=Object)

def update_transform_orientation(self,context):
    pass

class TransformOrientationContainer(PropertyGroup):
    active_index: IntProperty(
        name='Active Transform Index', min=0, max=1000, default=0,
        description='Index of the current Transform Orientation',
        update=update_transform_orientation)

    show_settings: BoolProperty(name='Show View Settings', default=False)

    # Array of views
    transform_orientations: CollectionProperty(type=TransformOrientationProperties)



class M_ARCH_UL_Transform_Orientation_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            transform = item
            layout.use_property_decorate = False
            row = layout.row(align=True)
            split = row.split(factor=0.3)
            split.prop(transform, "name", text="", emboss=False)
            row.prop(transform, 'orientation_basis_object', text="", icon='OBJECT_DATA')


class SCENE_PT_Transform(Panel):
    """ A panel in the Object properties window """
    bl_parent_id = 'SCENE_PT_Panel'
    bl_label = "Transforms"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon='OBJECT_ORIGIN')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        scene = context.scene
        TransGen = scene.TransformGenerator

        row = layout.row()

        # Draw The UI List
        row.template_list(" M_ARCH_UL_Transform_Orientation_list", "", TransGen,
                          "transform_orientations", TransGen, "active_index", rows=2, type='DEFAULT')

        # Operators Next to List
        #col = row.column(align=True)
        #col.operator("measureit_arch.addviewbutton", icon='ADD', text="")
        #op = col.operator("measureit_arch.deleteviewbutton", text="", icon="X")

        #col.separator()
        up = col.operator("measureit_arch.movepropbutton", text="", icon="TRIA_UP")
        up.genPath = "bpy.context.scene.TransformGenerator"
        up.item_type = "transform_orientations"
        up.upDown = -1

        down = col.operator("measureit_arch.movepropbutton", text="", icon="TRIA_DOWN")
        down.genPath = "bpy.context.scene.TransformGenerator"
        down.item_type = "transform_orientations"
        down.upDown = 1

        #op.tag = TransGen.active_index  # saves internal data

        #col.separator()
        #col.menu("SCENE_MT_Views_menu", icon='DOWNARROW_HLT', text="")

        if len(TransGen.transform_orientations) > 0 and TransGen.active_index < len(TransGen.transform_orientations):
            transform = TransGen.transform_orientations[TransGen.active_index]

            # Settings Below List
            if TransGen.show_settings:
                settingsIcon = 'DISCLOSURE_TRI_DOWN'
            else:
                settingsIcon = 'DISCLOSURE_TRI_RIGHT'

            box = layout.box()
            col = box.column()
            row = col.row()
            row.prop(TransGen, 'show_settings', text="",
                     icon=settingsIcon, emboss=False)

            row.label(text=transform.name + ' Settings:')

            if TransGen.show_settings:
                col = box.column()
                box = box.column()

                col = box.column(align=True)
                col.prop(transform, "transform_basis_object")
                col.prop(transform, "transform_basis_from_object")
                col.prop(transform, "basisX")
                col.prop(transform, "basisZ")
                col.prop(transform, "basisY")
                col.prop(transform, "force_orthonormalized_basis")
