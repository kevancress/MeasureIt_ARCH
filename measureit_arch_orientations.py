import bpy
import math
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
from bpy.app.handlers import persistent

times_updated = 0

def main_update(self,context):
    scene = bpy.context.scene
    TransGen = scene.TransformGenerator
    transform = TransGen.transform_orientations[TransGen.active_index]

    if transform.basis_definition == 'BASIS_VECTORS':
        update_basis_vectors(self,context)
    elif transform.basis_definition == 'ROTATION':
        update_basis_by_rotation(self,context)
    elif transform.basis_definition == 'OBJECT':
        update_transform_orientation(self,context)

def update_basis_by_rotation(self,context):
    pass

def update_basis_by_object(self,context):
    scene = bpy.context.scene
    TransGen = scene.TransformGenerator
    transform = TransGen.transform_orientations[TransGen.active_index]

    basis_mat = transform.orientation_basis_object.matrix_basis.to_3x3()
    transform.basisX = basis_mat.col[0]
    transform.basisY = basis_mat.col[1]
    transform.basisZ = basis_mat.col[2]

    update_transform_orientation(self,context)

def update_basis_vectors(self,context):
    global times_updated
    #print(f'TIMES UPDATED: {times_updated}')
    if times_updated > 10:
       # print('IN RECURSIVE UPDATE, EXITING')
        times_updated = 0
        return
    
    times_updated += 1

    scene = bpy.context.scene
    TransGen = scene.TransformGenerator
    transform = TransGen.transform_orientations[TransGen.active_index]

    x = Vector(transform.basisX)
    y = Vector(transform.basisY)
    z = Vector(transform.basisZ)

    xNorm = math.isclose(x.length, 1.0,abs_tol=0.001)
    yNorm = math.isclose(y.length, 1.0,abs_tol=0.001)
    zNorm = math.isclose(z.length, 1.0,abs_tol=0.001)
    #print(f"X Normal:{xNorm}, {x.length}, Y Normal:{yNorm}, {y.length}, Z Normal:{zNorm},{z.length}")
    if transform.force_normalized_basis:
        if not xNorm: 
            try:
                x = x.normalized()
                transform.basisX = x
            except:
                return

        if not yNorm:
            try:
                y = y.normalized()
                transform.basisY = y
            except:
                return
        if not zNorm:
            try:
                z = z.normalized()
                transform.basisZ = z
            except:
                return
    if transform.basis_definition != 'OBJECT':
        update_transform_orientation(self,context)

class TransformOrientationProperties(PropertyGroup):
    name: StringProperty(name="Name")

    basis_definition: EnumProperty(
        items=(
            ('OBJECT', "Object", ""),
            ('BASIS_VECTORS', "Basis Vectors", ""),
            ('ROTATION', "Rotation", "")),
        name="Transform Basis Definition",
        update=main_update)

    basisX: FloatVectorProperty(
        name="Transform Orientation X Basis",
        description="X Basis Vector for this transform orientation",
        unit='LENGTH',
        default=Vector((1.0,0.0,0.0)),
        update = update_basis_vectors)

    basisY: FloatVectorProperty(
        name="Transform Orientation Y Basis",
        description="Y Basis Vector for this transform orientation",
        unit='LENGTH',
        default=Vector((0.0,1.0,0.0)),
        update = update_basis_vectors)

    basisZ: FloatVectorProperty(
        name="Transform Orientation Z Basis",
        description="Z Basis Vector for this transform orientation",
        unit='LENGTH',
        default=Vector((0.0,0.0,1.0)),
        update = update_basis_vectors)

    force_normalized_basis: BoolProperty(
        name="Force Normalized Basis",
        description="Forces basis vectors to be Normal (All Unit Length).",
        default=False,
        update = update_basis_vectors)

    orientation_from_object: BoolProperty(
        name="Orientation From Object",
        description="Use an Objects transform as the basis for this transform orientation",
        default=True,
        update = update_basis_vectors)
    
    basis_by_rotation: BoolProperty(
        name="Basis By Rotation",
        description="Define the new transformation as a rotation on the global transformation",
        default=False,
        update = update_basis_by_rotation)
    
    basis_euler_rotation: FloatVectorProperty(
        name="Basis Rotation",
        description="Defines an Euler Rotation around the global axis to define a new transform basis",
        unit='ROTATION',
        subtype = 'EULER',
        default=Vector((0.0,0.0,0.0)),
        update = update_basis_vectors)
    
    is_default: BoolProperty(
        name="Is Default",
        description="this transform represents one of the default Transforms and cant be edited",
        default=False)

    orientation_basis_object: PointerProperty(type=Object, update = update_basis_vectors)




def update_transform_orientation(self,context):
    scene = bpy.context.scene
    TransGen = scene.TransformGenerator
    transform = TransGen.transform_orientations[TransGen.active_index]

    # If its one of the defaults, just set it
    default_names = ['GLOBAL', 'LOCAL', 'NORMAL', 'GIMBAL', 'VIEW', 'CURSOR']
    if transform.name in default_names:
        scene.transform_orientation_slots[0].type = transform.name
        return
    
    # If not check if we've made our custom slot
    slot = scene.transform_orientation_slots[0]
    try:
        slot.type = 'M_ARCH_CUSTOM'
    except:
        bpy.ops.transform.create_orientation(name='M_ARCH_CUSTOM', overwrite=True)
        slot.type = 'M_ARCH_CUSTOM'


    else:
        basis_mat = Matrix.Identity(3)
        x = Vector(transform.basisX)
        y = Vector(transform.basisY)
        z = Vector(transform.basisZ)
       
        basis_mat.col[0] = x
        basis_mat.col[1] = y
        basis_mat.col[2] = z
        slot.custom_orientation.matrix = basis_mat
    
    slot.custom_orientation.matrix = basis_mat

@persistent
def create_preset_transforms(dummy):
    """ Handler called when a Blend file is loaded to create a default view. """
    context = bpy.context
    scene = context.scene
    TransGen = scene.TransformGenerator

    if len(TransGen.transform_orientations)<1:
        global_trans = TransGen.transform_orientations.add()
        global_trans.is_default = True
        global_trans.name = 'GLOBAL'

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
            if transform.is_default: layout.enabled = False
            row.prop(transform, "name", text="", emboss=False)
            row = layout.row(align=True)
            row.prop(transform, 'orientation_basis_object', text="", icon='OBJECT_DATA', emboss = True)
        
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')


class SCENE_PT_Transform(Panel):
    """ A panel in the Object properties window """
    bl_parent_id = 'SCENE_PT_Panel'
    bl_label = "Transforms"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    tempx = FloatVectorProperty(default = Vector((1.0,0.0,0.0)))
    tempy: FloatVectorProperty()
    tempz: FloatVectorProperty()

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
        row.template_list("M_ARCH_UL_Transform_Orientation_list", "", TransGen,
                          "transform_orientations", TransGen, "active_index", rows=2, type='DEFAULT')

        # Operators Next to List
        col = row.column(align=True)

        AddOp = col.operator("measureit_arch.additem", text="", icon="ADD")
        AddOp.propPath = 'bpy.context.scene.TransformGenerator.transform_orientations'
        AddOp.add = True
        AddOp.name = 'Transform'

        RemoveOp = col.operator("measureit_arch.additem", text="", icon="REMOVE")
        RemoveOp.propPath = 'bpy.context.scene.TransformGenerator.transform_orientations'
        RemoveOp.add = False
        if TransGen.active_index < len(TransGen.transform_orientations):
            transform = TransGen.transform_orientations[TransGen.active_index]
            RemoveOp.can_delete = not transform.is_default
            RemoveOp.cant_delete_msg = 'This Transform is a Default Transform and cannot be deleted'

        col.separator()
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

                if transform.is_default:
                    box.enabled = False
                    col.label(text='This is a Default Transform, Create a custom Transform to Edit Settings')
                    return

                col = box.column(align=True)
                col.prop(transform, "basis_definition")
                col = box.column(align=True)
                
                if transform.basis_definition == 'OBJECT':
                    col.prop(transform, "orientation_basis_object", text = 'Basis Object')
                    col.separator()
                    col = box.column(align=True)

                    col.enabled = False
                    obj = transform.orientation_basis_object
                    basis = obj.matrix_basis.to_3x3()
                    col.emboss = 'NORMAL'
                    
                    box = col.box()
                    row = box.row()
                    row.label(text = " Basis X:")
                    subcol = row.column()
                    subcol.label(text = f"X: {basis[0][0]:.2f}")
                    subcol.label(text = f"Y: {basis[1][0]:.2f}")
                    subcol.label(text = f"Z: {basis[2][0]:.2f}")

                    col.separator()
                    box = col.box()
                    row = box.row()
                    row.label(text = " Basis Y:")
                    subcol = row.column()
                    subcol.label(text = f"X: {basis[0][1]:.2f}")
                    subcol.label(text = f"Y: {basis[1][1]:.2f}")
                    subcol.label(text = f"Z: {basis[2][1]:.2f}")

                    col.separator()
                    box = col.box()
                    row = box.row()
                    row.label(text = " Basis Z:")
                    subcol = row.column()
                    subcol.label(text = f"X: {basis[0][2]}")
                    subcol.label(text = f"Y: {basis[1][2]}")
                    subcol.label(text = f"Z: {basis[2][2]}")
                    #col.label(text = f" Basis Y : {basis[1]}")
                    #col.label(text = f" Basis Z : {basis[2]}")
                
                # If were not using an object, show the manual Basis
                elif transform.basis_definition == 'BASIS_VECTORS':
                    col = box.column(align=False)
                    col.prop(transform, "basisX", text = "Basis X")
                    col.prop(transform, "basisY", text = "Basis Y")
                    col.prop(transform, "basisZ", text = "Basis Z")
                    col.prop(transform, "force_normalized_basis")
                
                elif transform.basis_definition == 'ROTATION':
                    col.prop(transform, "basis_euler_rotation", text = "Rotation")


