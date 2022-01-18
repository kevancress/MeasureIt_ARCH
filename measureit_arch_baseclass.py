from enum import Enum
import bpy
import math


from bpy.types import PropertyGroup, Operator
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, \
    BoolProperty, StringProperty, FloatProperty, EnumProperty, PointerProperty

def recalc_index(self, context):
    # ensure index's are accurate
    StyleGen = context.scene.StyleGenerator
    wrapper = StyleGen.wrapper
    id_l = 0
    id_a = 0
    id_d = 0
    for style in wrapper:
        if style.itemType == 'line_groups':
            style.itemIndex = id_l
            id_l += 1
        elif style.itemType == 'alignedDimensions':
            style.itemIndex = id_d
            id_d += 1
        elif style.itemType == 'annotations':
            style.itemIndex = id_a
            id_a += 1


class StyleWrapper(PropertyGroup):
    itemType: EnumProperty(
        items=(
            ('line_groups', "Line", ""),
            ('annotations', "Annotation", ""),
            ('alignedDimensions', "Dimension", "")),
        name="Style Item Type",
        update=recalc_index)

    itemIndex: IntProperty(name='Item Index')

def update_flag(self, context):
    self.text_updated = True

def has_dimension_generator(context):
    return context.object is not None and \
        hasattr(context.object, "DimensionGenerator") and \
        len(context.object.DimensionGenerator) > 0

def update_active_dim(self, context):
    dimGen = context.object.DimensionGenerator
    itemType = self.itemType
    idx = 0
    for wrap in dimGen.wrapper:
        if itemType == wrap.itemType:
            if itemType == 'alignedDimensions':
                if self == dimGen.alignedDimensions[wrap.itemIndex]:
                    dimGen.active_index = idx
                    return
            elif itemType == 'axisDimensions':
                if self == dimGen.axisDimensions[wrap.itemIndex]:
                    dimGen.active_index = idx
                    return
        idx += 1

def recalc_dimWrapper_index(self, context):
    for obj in context.selected_objects:
        dimGen = obj.DimensionGenerator
        wrapper = dimGen.wrapper
        id_aligned = 0
        id_angle = 0
        id_axis = 0
        id_arc = 0
        id_area = 0
        for dim in wrapper:
            if dim.itemType == 'alignedDimensions':
                dim.itemIndex = id_aligned
                id_aligned += 1
            elif dim.itemType == 'angleDimensions':
                dim.itemIndex = id_angle
                id_angle += 1
            elif dim.itemType == 'axisDimensions':
                dim.itemIndex = id_axis
                id_axis += 1
            elif dim.itemType == 'arcDimensions':
                dim.itemIndex = id_arc
                id_arc += 1
            elif dim.itemType == 'areaDimensions':
                dim.itemIndex = id_area
                id_area += 1


class BaseProp:
    def get_name(self):
        try:
            return self['name']
        except KeyError:
            return ''

    def set_name(self,value):
        self['previous_name'] = self.name
        self['name'] = value

    name: StringProperty(
        name='Name',
        get = get_name,
        set = set_name
    )

    previous_name: StringProperty(
        name='Previous Name'
    )

    creation_time: StringProperty(
        name='Creation Time',
        description ='Timestamp of elements creation, used as a UID for caching line groups',
        default = '0'
    )

    is_active: BoolProperty(
        name='Is Active',
        description='This item is actively selected',
        default=False)

    icon: StringProperty(
        name="Icon",
        description="item icon",
        default="",)

    generator: StringProperty(
        name="Generator",
        description="item generator - api property",
        default="",)

    gen_group: StringProperty(
        name="Generator Group",
        description="group in the generator - api property",
        default="",)

    inFront: BoolProperty(
        name='inFront',
        description='Draw this element In front of other objects',
        default=False)

    visibleInView: StringProperty(
        name="View Layer",
        description="View Layer that this dimension is visible in",
        default="",)

    is_style: BoolProperty(
        name="is Style",
        description="This property Group is a Style",
        default=False)

    uses_style: BoolProperty(
        name="uses Style",
        description="This property Group Uses a Style",
        default=False,
        update=update_flag)

    style: StringProperty(
        name="Style Name",
        description="Item Name",
        default="",
        update=update_flag)

    style_pointer: PointerProperty(
        type = StyleWrapper
    )

    itemType: StringProperty(
        name="Item Type",
        description='flag for common operators',
        default='')

    color: FloatVectorProperty(
        name="Color",
        description="Color for the Item",
        default=(0.0, 0.0, 0.0, 1.0),
        min=0,
        max=1,
        subtype='COLOR',
        size=4,
        update=update_flag)

    lineWeight: FloatProperty(
        name="Line Weight",
        description="Lineweight",
        default=1,
        soft_min=1.0,
        step=25,
        min=0)

    free: BoolProperty(
        name="Free",
        description="This Item is free and can be deleted",
        default=False)

    evalMods: BoolProperty(
        name="Evaluate Depsgraph",
        description="This Element will evaluate the Dependency Graph "
                    "(Modifiers, Shape Keys etc.) before drawing",
        default=False)

    settings: BoolProperty(
        name="Settings",
        description="Show Settings",
        default=False)

    visible: BoolProperty(
        name="Visibility",
        description="how/hide",
        default=True)

    gizLoc: FloatVectorProperty(
        name="Gizmo Location",
        description="Default Location for item Gizmo",
        subtype='TRANSLATION')

    gizRotDir: FloatVectorProperty(
        name="Gizmo Rotation Direction",
        description="Default Rot Direction for item Gizmo",
        subtype='TRANSLATION')

class ObjProps(PropertyGroup):
    ignore_in_depth_test: BoolProperty(
        name='Ignore in Depth Test',
        description='Ignore this object in Vector Depth Tests',
        default=False)


class TextField(PropertyGroup):
    text_updated: BoolProperty(
        name='text_updated',
        description='flag when text needs to be redrawn',
        default=False)

    text: StringProperty(
        name="Text",
        description="Text Associated With Item",
        default="",
        update=update_flag)

    autoFillText: BoolProperty(
        name='Auto Fill Text',
        description='Fill This Text Field Automatically from a property',
        default=False)

    textSource: EnumProperty(
        items=(('VIEW', "View", "", 'DOCUMENTS', 1),
               ('DATE', "Date", "", 'TIME', 2),
               ('NOTES', "Notes", "", 'LONGDISPLAY', 3),
               ('C_LENGTH', "Curve Length", "", 'OUTLINER_DATA_CURVE', 4),
               ('ELEVATION', "Elevation","",'TRACKING_CLEAR_FORWARDS',5),
               ('SCALE', "Scale", "", 'SNAP_INCREMENT', 6),
               ('VIEWNUM', "Drawing Number", "", 'SORTALPHA', 7),
               ('LENGTH', "Dimension Length", "", 'DRIVER_DISTANCE', 8),
               ('RNAPROP', "Custom Property", "", 'RNA', 99)),
        name="Text Source",
        default='RNAPROP',
        description="Set Text Field Source")

    rnaProp: StringProperty(
        name="Custom Prop String",
        description="RNA Prop String",
        default="",
        update=update_flag)

    textAlignment: EnumProperty(
        items=(('L', "Left", "", 'ALIGN_LEFT', 1),
               ('C', "Center", "", 'ALIGN_CENTER', 2),
               ('R', "Right", "", 'ALIGN_RIGHT', 3)),
        name="align Font",
        default='L',
        description="Set Font alignment")

    textPosition: EnumProperty(
        items=(('T', "Top", "", 'ALIGN_TOP', 1),
               ('M', "Mid", "", 'ALIGN_MIDDLE', 2),
               ('B', "Bottom", "", 'ALIGN_BOTTOM', 3)),
        name="align Font",
        description="Set Font Position")

    textWidth: IntProperty(
        name='annotationWidth',
        description='Width of annotation')

    textHeight: IntProperty(
        name='annotationHeight',
        description='Height of annotation')

    texture_updated: BoolProperty(
        name='texture_updated',
        description='flag when text texture need to be redrawn',
        default=False)

class BaseWithText(BaseProp):

    text: StringProperty(name='legacy text')

    text_updated: BoolProperty(
        name='text_updated',
        description='flag when text needs to be redrawn',
        default=False)

    textFields: CollectionProperty(type=TextField)

    textAlignment: EnumProperty(
        items=(('L', "Left", "", 'ALIGN_LEFT', 1),
               ('C', "Center", "", 'ALIGN_CENTER', 2),
               ('R', "Right", "", 'ALIGN_RIGHT', 3)),
        name="align Font",
        description="Set Font alignment")

    textPosition: EnumProperty(
        items=(('T', "Top", "", 'ALIGN_TOP', 1),
               ('M', "Mid", "", 'ALIGN_MIDDLE', 2),
               ('B', "Bottom", "", 'ALIGN_BOTTOM', 3)),
        name="align Font",
        description="Set Font Position")

    fontSize: FloatProperty(
        name='Font Size',
        description="Font Size in pt (1pt = 1/72\")\n"
                    "Note: Font size is relative to the current scale\n"
                    "Scale is defined in your active view, or in the Scene unit settings",
        default=10, soft_min = 1, step=100, precision=0)

    font: PointerProperty(
        type=bpy.types.VectorFont,
        update=update_flag)

    # Endcap properties are defined here to ensure compatiblity but the
    # enumProps are overwritten in child property groups
    endcapSize: FloatProperty(
        name="dimEndcapSize",
        description="End Cap size",
        default=4, min=0, max=500,step=100,precision=0)

    endcapArrowAngle: FloatProperty(
        name="endcapArrowAngle",
        description="End Cap Arrow Angle",
        default=math.radians(15),
        soft_min=math.radians(15),
        soft_max=math.radians(45),
        subtype='ANGLE')

    endcapA: EnumProperty(
        items=(('99', "--", "No arrow"),
               ('1', "Line", "The point of the arrow are lines")),
        name="A end",
        description="Add arrows to point A")

    endcapB: EnumProperty(
        items=(('99', "--", "No arrow"),
               ('1', "Line", "The point of the arrow are lines")),
        name="B end",
        description="Add arrows to point A")
    
    all_caps: BoolProperty(
        name='All Caps',
        description='Make Text All Caps',
        default=False,
        update=update_flag)

class BaseDim(BaseWithText):

    generator: StringProperty(
        name="Generator",
        description="item generator - api property",
        default="DimensionGenerator[0]",)

    dimPointA: IntProperty(
        name='dimPointA',
        description="Dimension Start Vertex Index")

    dimPointB: IntProperty(
        name='dimPointB',
        description="Dimension End Vertex Index")

    dimFlip: BoolProperty(
        name= 'dimFlip',
        description= "Flip Dimension",
        default= False
    )

    dimOffset: FloatProperty(
        name='Dimension Offset',
        description='Offset for Dimension',
        default=(0.5),
        min = 0.001,
        subtype='DISTANCE',
        update=update_active_dim)

    tweakOffset: FloatProperty(
        name='Dimension Offset',
        description='Offset for Dimension',
        default=(0.0),
        subtype='DISTANCE',
        update=update_active_dim)

    dimLeaderOffset: FloatProperty(
        name='Dimension Offset',
        description='Offset for Dimension',
        default=(0.05),
        min = 0,
        subtype='DISTANCE')

    dimViewPlane: EnumProperty(
        items=(('99', "None", "None", 'EMPTY_AXIS', 0),
               ('XY', "XY Plane",
                "Optimize Dimension for XY Plane (Plan)", 'AXIS_TOP', 1),
               ('YZ', "YZ Plane",
                "Optimize Dimension for YZ Plane (Elevation)", 'AXIS_FRONT', 2),
               ('XZ', "XZ Plane", "Optimize Dimension for XZ Plane (Elevation)", 'AXIS_SIDE', 3)),
        name="View Plane",
        description="Dimension View Plane")

    endcapA: EnumProperty(
        items=(('99', "--", "No Cap"),
               ('L', "Arrow", "Arrow"),
               ('T', "Triangle", "Triangle"),
               ('D', "Dashed", "Dashed")),
        default='T',
        name="A end",
        description="Add arrows to point A")

    endcapB: EnumProperty(
        items=(('99', "--", "No Cap"),
               ('L', "Arrow", "Arrow"),
               ('T', "Triangle", "Triangle"),
               ('D', "Dashed", "Dashed")),
        name="B end",
        default='T',
        description="Add arrows to point A")

    dimRotation: FloatProperty(
        name='annotationOffset',
        description='Rotation for Dimension',
        default=0.0,
        subtype='ANGLE')

    use_custom_text: BoolProperty(
        name = "Use Custom Text",
        description = "Use Custom Text",
        default=False
    )

    use_secondary_units: BoolProperty(
        name = "Use Secondary Units",
        description = "Show dimension in both unit systems",
        default = False
    )

    override_unit_system: EnumProperty(
        items = (('NONE', '--', "None"),
                 ('METRIC', 'Metric', "Metric"),
                 ('IMPERIAL', 'Imperial', 'Imperial')
        ),
        name = "Override Unit System",
        description = "Override Scene Unit System for this Dimension",
        default = 'NONE'
    )

class MeasureItARCHSceneProps(PropertyGroup):
    bound_x: BoolProperty()
    bound_y: BoolProperty()
    bound_z: BoolProperty()

    depth_samples: EnumProperty(
        items=(
            ('POINT', 'Point (2x)', ''),
            ('CROSS', 'Cross (10x)', ''),
            ('SQUARE', 'Square (18x)', ''),
        ),
        name="Depth Test",
        description="Numer and Shape of Samples for Vector Depth Testing",
        default='CROSS')

    viewPlane: EnumProperty(
        items=(('99', "None", "No View Plane Selected", 'EMPTY_AXIS', 0),
               ('XY', "XY Plane",
                "Optimize Dimension for XY Plane (Plan)", 'AXIS_TOP', 1),
               ('YZ', "YZ Plane",
                "Optimize Dimension for YZ Plane (Elevation)", 'AXIS_FRONT', 2),
               ('XZ', "XZ Plane", "Optimize Dimension for XZ Plane (Elevation)", 'AXIS_SIDE', 3)),
        name="View Plane",
        description="View Plane")

    default_dimension_style: StringProperty(
        name="Default Style",
        description="Dimension Style to Use")

    default_annotation_style: StringProperty(
        name="Default Style",
        description="Annotation Style to Use")

    default_line_style: StringProperty(
        name="Default Style",
        description="Line Style to Use")

    show_all: BoolProperty(
        name="Show All",
        description="Display measures for all objects,"
        " not only selected",
        default=True)

    show_dim_text: BoolProperty(
        name="Show Dimension Text",
        description="Display Dimension Text",
        default=True)

    hide_units: BoolProperty(
        name="Hide Units",
        description="Do not display unit of measurement on viewport",
        default=False)

    measureit_arch_dim_axis: EnumProperty(
        items=(('X', "X", "X Axis"),
               ('Y', "Y", "Y Axis"),
               ('Z', "Z", "Z Axis")),
        name="Axis",
        description="Axis")

    measureit_arch_debug_text: BoolProperty(
        name="Debug Text",
        description="(DEBUG) Draw Debug Info For Text",
        default=False)

    highlight_selected: BoolProperty(
        name='Highlight Active',
        description='Highlight Selected MeasureIt_ARCH Elements',
        default=True)

    use_unit_scale: BoolProperty(
        name='Use Unit Scale',
        description='',
        default=False)

    text_updated: BoolProperty(
        name='text_updated',
        description='flag when text needs to be redrawn',
        default=False)

    debug_flip_text: BoolProperty(
        name="Debug Text Flip Vectors",
        description="Displys Text Card and View Vectors used to Flip Text",
        default=False)

    default_color: FloatVectorProperty(
        name="Default Color",
        description="Default Color for new Items",
        default=(0.0, 0.0, 0.0, 1.0),
        min=0,
        max=1,
        subtype='COLOR',
        size=4,
        update=update_flag)

    instance_dims: BoolProperty(
        name="Instance Dimensions",
        description="WARNING: Only the most recent Instance's Dimension text "
                    "will adapt to local changes in scale or rotation",
        default=False)

    eval_mods: BoolProperty(
        name="Evaluate Depsgraph",
        description="All MeasureIt_ARCH elements will attempt to evaluate the "
                    "dependency graph (Modifiers, Shape Keys, etc.) before drawing, "
                    "may make dimensions and linework unstable",
        default=False)

    is_render_draw: BoolProperty(
        name="Is Render",
        description="Flag to use render size for draw aspect ratio",
        default=False)

    is_vector_draw: BoolProperty(
        name="Is Vector Render",
        description="Flag to use svg draw code",
        default=False)

    show_gizmos: BoolProperty(
        name="Show Gizmos",
        description="Display MeasureIt_ARCH Gizmos",
        default=False)

    show_text_cards: BoolProperty(
        name="Debug Text Cards",
        description="Display MeasureIt_ARCH Text Cards",
        default=False)

    enable_experimental: BoolProperty(
        name="Enable Experimental",
        description="Enable Experimental Features like SVG Rendering",
        default=False)

    default_scale: IntProperty(
        name='Default Paper Scale', min=1, default=25,
        description="Default Paper Scale (used for font sizing)")

    angle_precision: IntProperty(
        name='Angle Precision', min=0, max=5, default=0,
        description="Angle decimal precision")

    imperial_precision: EnumProperty(
        items=(('1', "1\"", "1 Inch"),
               ('2', "1/2\"", "1/2 Inch"),
               ('4', "1/4\"", "1/4 Inch"),
               ('8', "1/8\"", "1/8th Inch"),
               ('16', "1/16\"", "1/16th Inch"),
               ('32', "1/32\"", "1/32th Inch"),
               ('64', "1/64\"", "1/64th Inch")),
        name="Imperial Precision",
        description="Measurement Precision for Imperial Units")

    metric_area_units: EnumProperty(
        items = (('KILOMETERS', 'Kilometers', 'Kilometers'),
                ('METERS', 'Meters', 'Meters'),
                ('CENTEMETERS', 'Centimeters', 'Centimeters'),
                ('MILLIMETERS', 'Millimeters', 'Millimeters')
        ),
        name = 'Metric Area Units',
        description = 'Units to Use for Metric Area Dimensions',
        default = 'METERS'
    )

    imperial_area_units: EnumProperty(
        items = (('HECTARE', 'Hectare', 'Hectare'),
                ('ACRE', 'Acre', 'Acre'),
                ('FEET', 'Feet', 'Feet'),
        ),
        name = 'Imperial Area Units',
        description = 'Units to Use for Imperial Area Dimensions',
        default = 'FEET'
    )

    use_text_autoplacement: BoolProperty(
        name="Use Text Autoplacement",
        description="Adjust Dimension Text Placement Automatically",
        default=True)

    keep_freestyle_svg: BoolProperty(
        name="Keep Freestyle SVG",
        description="When Embeding a Freestyle SVG, keep the generated Freestyle SVG as a seperate file as well",
        default=False,)

    default_resolution: IntProperty(
        name='Default Resolution ', min=1,
        default=150,
        soft_min=50,
        soft_max=1200,
        description="Default Resolution (used for font sizing)",
        update=update_flag)

    metric_precision: IntProperty(
        name='Precision', min=0, max=5, default=2,
        description="Metric decimal precision")

    hide_titleblock: BoolProperty(
        name="Hide Titleblock",
        description="Hide TitleBlock",
        default=False,)

    hide_linework: BoolProperty(
        name="Hide Linework",
        description="Hide Linework",
        default=False,)

    source_scene: PointerProperty(type = bpy.types.Scene)

class DeletePropButton(Operator):
    bl_idname = "measureit_arch.deletepropbutton"
    bl_label = "Delete property"
    bl_description = "Delete a property"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'}
    genPath: StringProperty()
    tag: IntProperty()
    item_type: StringProperty()
    is_style: BoolProperty()

    def execute(self, context):
        # Add properties

        Generator = eval(self.genPath)
        itemGroup = eval('Generator.' + self.item_type)
        print(self.genPath)
        # Delete element
        itemGroup[self.tag].free = True
        itemGroup.remove(self.tag)

        # Redraw
        context.area.tag_redraw()

        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
                    context.area.tag_redraw()
                    return {'FINISHED'}

        return {'FINISHED'}

class MovePropButton(Operator):
    bl_idname = "measureit_arch.movepropbutton"
    bl_label = "Move View"
    bl_description = "Move a View up or down"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'}
    genPath: StringProperty()
    item_type: StringProperty()
    upDown: IntProperty()  # 1 or -1 for direction

    def execute(self, context):
        # Add properties

        Generator = eval(self.genPath)
        itemGroup = eval('Generator.' + self.item_type)
        idx = Generator.active_index
        itemGroup.move(idx, idx + self.upDown)
        Generator.active_index = idx + self.upDown

        return {'FINISHED'}

class HideAllButton(Operator):
    bl_idname = "measureit_arch.hideallbutton"
    bl_label = "Hide All"
    bl_description = "Hide All"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'}
    item_path: StringProperty()

    def execute(self, context):
        # Add properties

        col_prop = eval(item_path)

        for item in col_prop:
            item.visible = not item.visible

        return {'FINISHED'}

class AddTextField(Operator):
    bl_idname = "measureit_arch.addtextfield"
    bl_label = "Add Text Field"
    bl_description = "Add or Remove a new field"
    bl_category = 'MeasureitArch'

    propPath: StringProperty()
    idx: IntProperty()
    add: BoolProperty()

    def execute(self, context):
        mainobject = context.object
        textFields = eval(self.propPath)
        if self.add:
            textFields.add()
        else:
            textFields.remove(len(textFields) - 1)
        return {'FINISHED'}

class MoveItem(Operator):
    bl_idname = "measureit_arch.moveitem"
    bl_label = "Move Item"
    bl_description = "Move Item Up or Down in a list"
    bl_category = 'MeasureitArch'
    propPath: StringProperty()
    idx: IntProperty()
    upDown: IntProperty()

    def execute(self, context):
        # TODO: `eval` is evil
        collectionProp = eval(self.propPath)

        idx = self.idx
        collectionProp.move(idx, idx + self.upDown)

        return {'FINISHED'}

class DeleteAllItemsButton(Operator):
    bl_idname = "measureit_arch.deleteallitemsbutton"
    bl_label = "Delete All Items?"
    bl_description = "Delete all Items"
    bl_category = 'MeasureitArch'
    genPath: StringProperty()
    is_style: BoolProperty()
    passedItem: PointerProperty(type=PropertyGroup)

    def execute(self, context):
        # Add properties

        Generator = eval(self.genPath)
        for key in Generator.keys():
            item = Generator.path_resolve(key)
            if 'collection' in str(item):
                typeContainer = item
                for item in typeContainer:
                    typeContainer.remove(0)

        for window in bpy.context.window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
                    context.area.tag_redraw()
                    return {'FINISHED'}
            return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
