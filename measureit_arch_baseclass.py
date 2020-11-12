import bpy
import bgl
import blf
import gpu
import math
from mathutils import Matrix
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D, Scene
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, BoolProperty, StringProperty, \
                FloatProperty, EnumProperty, PointerProperty


def update_flag(self,context):
    self.text_updated = True

def has_dimension_generator(context):
    return context.object is not None and \
    hasattr(context.object, "DimensionGenerator") and \
    len(context.object.DimensionGenerator) > 0


def update_active_dim(self,context):
    if has_dimension_generator(context):
        dimGen = context.object.DimensionGenerator[0]
        itemType = self.itemType
        idx = 0
        for wrap in dimGen.wrappedDimensions:
            if itemType == wrap.itemType:
                if itemType == 'D-ALIGNED':
                    if self == dimGen.alignedDimensions[wrap.itemIndex]:
                        dimGen.active_dimension_index = idx
                        return
                elif itemType == 'D-AXIS':
                    if self == dimGen.axisDimensions[wrap.itemIndex]:
                        dimGen.active_dimension_index = idx
                        return
            idx += 1


def recalc_dimWrapper_index(self,context):
    if has_dimension_generator(context):
        dimGen = context.object.DimensionGenerator[0]
        wrappedDimensions = dimGen.wrappedDimensions
        id_aligned = 0
        id_angle = 0
        id_axis = 0
        id_arc = 0
        id_area = 0
        for dim in wrappedDimensions:
            if dim.itemType == 'D-ALIGNED':
                dim.itemIndex = id_aligned
                id_aligned += 1
            elif dim.itemType == 'D-ANGLE':
                dim.itemIndex = id_angle
                id_angle += 1
            elif dim.itemType == 'D-AXIS':
                dim.itemIndex = id_axis
                id_axis += 1
            elif dim.itemType == 'D-ARC':
                dim.itemIndex = id_arc
                id_arc += 1
            elif dim.itemType == 'D-AREA':
                dim.itemIndex = id_area
                id_area += 1

                
class BaseProp:
    icon: StringProperty(name = "Icon",
            description = "item icon",
            default = "",)

    generator: StringProperty(name="Generator",
            description="item generator - api property",
            default="",)
    
    gen_group: StringProperty(name="Generator Group",
        description="group in the generator - api property",
        default="",)

    inFront: BoolProperty(name='inFront',
                description= 'Draw this element In front of other objects',
                default = False)

    visibleInView: PointerProperty(type= bpy.types.Camera)

    is_style: BoolProperty(name= "is Style",
                description= "This property Group is a Style",
                default=False)
    
    uses_style: BoolProperty(name= "uses Style",
                description= "This property Group Uses a Style",
                default=False,
                update = update_flag)

    style: StringProperty(name="Style Name",
            description="Item Name",
            default="",
            update = update_flag)

    itemType: StringProperty(name="Item Type",
            description= 'flag for common operators',
            default = '')

    color: FloatVectorProperty(name="Color",
                description="Color for the Item",
                default= (0.0,0.0,0.0, 1.0),
                min=0,
                max=1,
                subtype='COLOR',
                size=4,
                update=update_flag)

    lineWeight: FloatProperty(name="Line Weight",
                description="Lineweight",
                default = 1,
                soft_min = 1.0,
                step = 25,
                min = 0)

    free: BoolProperty(name="Free",
                description="This Item is free and can be deleted",
                default=False)

    evalMods: BoolProperty(name="Evaluate Depsgraph",
            description="This Element will evaluate the Dependency Graph (Modifiers, Shape Keys etc.) before drawing",
            default=False)
    
    settings: BoolProperty(name= "Settings",
                description= "Show Settings",
                default=False)

    visible: BoolProperty(name="Visibility",
                description="how/hide",
                default=True)
    
    gizLoc: FloatVectorProperty(name="Gizmo Location",
                description= "Default Location for item Gizmo",
                subtype='TRANSLATION')
    
    gizRotDir: FloatVectorProperty(name="Gizmo Rotation Direction",
                description= "Default Rot Direction for item Gizmo",
                subtype='TRANSLATION')

class TextField(PropertyGroup):
    text_updated: BoolProperty(name='text_updated',
                description= 'flag when text needs to be redrawn',
                default = False)

    text: StringProperty(name="Text",
                description="Text Associated With Item",
                default="",
                update= update_flag)

    autoFillText: BoolProperty(name='Auto Fill Text',
                description= 'Fill This Text Field Automatically from a property',
                default = False)

    textSource: EnumProperty(
                items=(('VIEW', "View", "",'DOCUMENTS',1),
                        ('DATE', "Date", "",'TIME',2),
                        ('RNAPROP', "Custom Property", "",'RNA',99)),
                name="Text Source",
                default = 'RNAPROP',
                description="Set Text Field Source")
    
    rnaProp: StringProperty(name="Custom Prop String",
                description="RNA Prop String",
                default="",
                update= update_flag)

    textAlignment:EnumProperty(
                items=(('L', "Left", "",'ALIGN_LEFT',1),
                        ('C', "Center", "",'ALIGN_CENTER',2),
                        ('R', "Right", "",'ALIGN_RIGHT',3)),
                name="align Font",
                default = 'L',
                description="Set Font alignment")
    
    textPosition:EnumProperty(
                items=(('T', "Top", "",'ALIGN_TOP',1),
                        ('M', "Mid", "",'ALIGN_MIDDLE',2),
                        ('B', "Bottom", "",'ALIGN_BOTTOM',3)),
                name="align Font",
                description="Set Font Position")

    textWidth: IntProperty(name='annotationWidth',
                description= 'Width of annotation')
        
    textHeight: IntProperty(name='annotationHeight',
                description= 'Height of annotation')

    texture_updated: BoolProperty(name='texture_updated',
            description= 'flag when text texture need to be redrawn',
            default = False)

bpy.utils.register_class(TextField)

class BaseWithText(BaseProp):

    text: StringProperty(name='legacy text')

    text_updated: BoolProperty(name='text_updated',
                description= 'flag when text needs to be redrawn',
                default = False)

    textFields: CollectionProperty(type=TextField)

    textAlignment:EnumProperty(
                items=(('L', "Left", "",'ALIGN_LEFT',1),
                        ('C', "Center", "",'ALIGN_CENTER',2),
                        ('R', "Right", "",'ALIGN_RIGHT',3)),
                name="align Font",
                description="Set Font alignment")

    textPosition:EnumProperty(
                items=(('T', "Top", "",'ALIGN_TOP',1),
                        ('M', "Mid", "",'ALIGN_MIDDLE',2),
                        ('B', "Bottom", "",'ALIGN_BOTTOM',3)),
                name="align Font",
                description="Set Font Position")

    fontSize: IntProperty(name='Font Size',
                description="Font Size in pt (1pt = 1/72\") \nNote: Font size is relative to the current scale \nScale is defined in your active view, or in the Scene unit settings ",
                default=18)

    font: PointerProperty(type= bpy.types.VectorFont,
                update = update_flag)

    # endcap properties are defined here to ensure compatiblity but the enumProps are overwritten in child property groups
    endcapSize: IntProperty(name="dimEndcapSize",
                description="End Cap size",
                default=12, min=1, max=500)
    
    endcapArrowAngle: FloatProperty(name="endcapArrowAngle",
                description="End Cap Arrow Angle",
                default = math.radians(15),
                soft_min = math.radians(15),
                soft_max = math.radians(45),
                subtype = 'ANGLE')

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
    
class BaseDim(BaseWithText):
    
    generator: StringProperty(name="Generator",
        description="item generator - api property",
        default="DimensionGenerator[0]",)

    dimPointA: IntProperty(name='dimPointA',
                    description="Dimension Start Vertex Index")
    
    dimPointB: IntProperty(name='dimPointB',
                    description="Dimension End Vertex Index")

    dimOffset: FloatProperty(name='Dimension Offset',
                    description='Offset for Dimension',
                    default= (0.5),
                    subtype='DISTANCE',
                    update= update_active_dim)

    dimLeaderOffset: FloatProperty(name='Dimension Offset',
                    description='Offset for Dimension',
                    default= (0.05),
                    subtype='DISTANCE')

    dimViewPlane: EnumProperty(
                    items=(('99', "None", "None",'EMPTY_AXIS',0),
                           ('XY', "XY Plane", "Optimize Dimension for XY Plane (Plan)",'AXIS_TOP',1),
                           ('YZ', "YZ Plane", "Optimize Dimension for YZ Plane (Elevation)",'AXIS_FRONT',2),
                           ('XZ', "XZ Plane", "Optimize Dimension for XZ Plane (Elevation)",'AXIS_SIDE',3)),
                    name="View Plane",
                    description="Dimension View Plane")   

    endcapA: EnumProperty(
                    items=(('99', "--", "No Cap"),
                           ('L', "Arrow", "Arrow"),
                           ('T', "Triangle", "Triangle"),
                           ('D', "Dashed", "Dashed")),
                    default ='T',
                    name="A end",
                    description="Add arrows to point A")

    endcapB: EnumProperty(
                    items=(('99', "--", "No Cap"),
                           ('L', "Arrow", "Arrow"),
                           ('T', "Triangle", "Triangle"),
                           ('D', "Dashed", "Dashed")),
                    name="B end",
                    default ='T',
                    description="Add arrows to point A")   

    dimRotation:FloatProperty(name='annotationOffset',
                            description='Rotation for Dimension',
                            default= 0.0,
                            subtype='ANGLE')

class MeasureItARCHSceneProps(PropertyGroup):
    bound_x: BoolProperty()
    bound_y: BoolProperty()
    bound_z: BoolProperty()

    viewPlane: EnumProperty(
                    items=(('99', "None", "No View Plane Selected",'EMPTY_AXIS',0),
                           ('XY', "XY Plane", "Optimize Dimension for XY Plane (Plan)",'AXIS_TOP',1),
                           ('YZ', "YZ Plane", "Optimize Dimension for YZ Plane (Elevation)",'AXIS_FRONT',2),
                           ('XZ', "XZ Plane", "Optimize Dimension for XZ Plane (Elevation)",'AXIS_SIDE',3)),
                    name="View Plane",
                    description="View Plane")   

    default_color: FloatVectorProperty(
        name="Default color",
        description="Default Color",
        default=(0.0, 0.0, 0.0, 1.0),
        min=0.1,
        max=1,
        subtype='COLOR',
        size=4)

    default_dimension_style: StringProperty(name="Default Style",
                                            description="Dimension Style to Use")   


    default_annotation_style: StringProperty(name="Default Style",
                                            description="Annotation Style to Use")  


    default_line_style: StringProperty(name="Default Style",
                                            description="Line Style to Use") 
                                     

    show_all: BoolProperty(name="Show All",
                                            description="Display measures for all objects,"
                                                        " not only selected",
                                            default=True)

    show_dim_text: BoolProperty(name="Show Dimension Text",
                                             description="Display Dimension Text",
                                             default=True)

    hide_units: BoolProperty(name="Hide Units",
                                              description="Do not display unit of measurement on viewport",
                                              default=False)

    measureit_arch_dim_axis: EnumProperty(
                items=(('X', "X", "X Axis"),
                        ('Y', "Y", "Y Axis"),
                        ('Z', "Z", "Z Axis")),
                name="Axis",
                description="Axis")

    measureit_arch_debug_text: BoolProperty(name="Debug Text",
                                        description="(DEBUG) Draw Debug Info For Text",
                                        default=False)

    highlight_selected: BoolProperty(name='Show Selected',
                description= 'Highlight Selected MeasureIt_ARCH Elements',
                default = True)

    text_updated: BoolProperty(name='text_updated',
                description= 'flag when text needs to be redrawn',
                default = False)
    
    debug_flip_text: BoolProperty(name="Debug Text Flip Vectors",
                                description="Displys Text Card and View Vectors used to Flip Text",
                                default=False)

    default_color: FloatVectorProperty(name="Default Color",
                description="Default Color for new Items",
                default= (0.0,0.0,0.0, 1.0),
                min=0,
                max=1,
                subtype='COLOR',
                size=4,
                update=update_flag)

    instance_dims: BoolProperty(name="Instance Dimensions",
                                description="WARNING: Only the most recent Instance's Dimension text will adapt to local changes in scale or rotation",
                                default=False)

    eval_mods: BoolProperty(name="Evaluate Depsgraph",
                                description="All MeasureIt_ARCH elements will attempt to evaluate the dependency graph (Modifiers, Shape Keys, etc.) before drawing, May make dimensions and linework unstable",
                                default=False)

    is_render_draw: BoolProperty(name="Is Render",
                                description="Flag to use render size for draw aspect ratio",
                                default=False)
    
    is_vector_draw: BoolProperty(name="Is Vector Render",
                                description="Flag to use svg draw code",
                                default=False)
    
    vector_depthtest: BoolProperty(name="Use Vector Depth Test",
                                description="Check for Occlusion when rending to SVG \n WARNING: SLOW, open system console before rendering to view progress",
                                default=False)

    show_gizmos: BoolProperty(name="Show Gizmos",
                                description="Display MeasureIt_ARCH Gizmos",
                                default=False)

    show_text_cards: BoolProperty(name="Debug Text Cards",
                            description="Display MeasureIt_ARCH Text Cards",
                            default=False)

    enable_experimental: BoolProperty(name="Enable Experimental",
                                description="Enable Experimental Features like SVG Rendering",
                                default=False)
    
    enable_experimental: BoolProperty(name="Enable Experimental",
                                description="Enable Experimental Features like SVG Rendering",
                                default=False)

    use_text_autoplacement: BoolProperty(name="Use Text Autoplacement",
                                description="Adjust Dimension Text Placement Automatically",
                                default=True)

    embed_scene_render: BoolProperty(name="Embed Scene Render",
                            description="Render the scene and automatically combine the rendered image with the Measureit-ARCH render pass",
                            default=False)

    default_scale: IntProperty(name='Default Paper Scale', min=1, default=25,
                                description="Default Paper Scale (used for font sizing)")
    
    default_resolution:  IntProperty(name='Default Resolution ', min=1,
                                default=150,
                                soft_min=50,
                                soft_max=1200,
                                description="Default Resolution (used for font sizing)",
                                update= update_flag)
    
    metric_precision: IntProperty(name='Precision', min=0, max=5, default=2,
                                               description="Metric decimal precision")
    
    angle_precision: IntProperty(name='Angle Precision', min=0, max=5, default=0,
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


bpy.utils.register_class(MeasureItARCHSceneProps)
Scene.MeasureItArchProps = bpy.props.PointerProperty(type=MeasureItARCHSceneProps)


class DeletePropButton(Operator):
    bl_idname = "measureit_arch.deletepropbutton"
    bl_label = "Delete property"
    bl_description = "Delete a property"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'} 
    tag: IntProperty()
    item_type: StringProperty()
    is_style: BoolProperty()

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        # Add properties
        mainObj = context.object
        
        if self.is_style is True:
            Generator = context.scene.StyleGenerator
        else:
            if self.item_type == 'A':
                Generator = mainObj.AnnotationGenerator[0]
                Generator.num_annotations -= 1
            elif self.item_type == 'L':
                Generator = mainObj.LineGenerator[0]
                Generator.line_num -= 1
            elif 'D-' in self.item_type:
                Generator = mainObj.DimensionGenerator[0]
                Generator.measureit_arch_num -= 1

        if self.item_type == 'A':
            itemGroup = Generator.annotations
        elif self.item_type == 'L':
            itemGroup = Generator.line_groups
        elif self.item_type == 'D-ALIGNED':
            itemGroup = Generator.alignedDimensions
        elif self.item_type == 'D-ANGLE':
            itemGroup = Generator.angleDimensions
        elif self.item_type == 'D-AXIS':
            itemGroup = Generator.axisDimensions
        elif self.item_type == 'D-BOUNDS':
            itemGroup = Generator.boundsDimensions
        elif self.item_type == 'D-ARC':
            itemGroup = Generator.arcDimensions
        elif self.item_type == 'D-AREA':
            itemGroup = Generator.areaDimensions
        elif 'D' in self.item_type:
            itemGroup = Generator.alignedDimensions
            
        # Delete element
        itemGroup[self.tag].free = True
        itemGroup.remove(self.tag)
        # redraw
        context.area.tag_redraw()

        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
                    context.area.tag_redraw()
                    return {'FINISHED'}
                
        return {'FINISHED'}
   

class AddTextField(Operator):
    bl_idname = "measureit_arch.addtextfield"
    bl_label = "Add Text Field"
    bl_description = "Add or Remove a new field"
    bl_category = 'MeasureitArch'
    idx: IntProperty()
    add: BoolProperty()

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        mainobject = context.object
        if 'AnnotationGenerator' in mainobject:
            textFields = mainobject.AnnotationGenerator[0].annotations[self.idx].textFields
            if self.add:
                textFields.add()
            else:
                textFields.remove(len(textFields)-1)
            return {'FINISHED'}
        return {'FINISHED'}

class MoveItem(Operator):
    bl_idname = "measureit_arch.moveitem"
    bl_label = "Move Item"
    bl_description = "Move Item Up or Down in a list"
    bl_category = 'MeasureitArch'
    propPath : StringProperty()
    idx: IntProperty()
    upDown: BoolProperty()

    def copyKeys(self,source,destination):
        for key in source.__annotations__.keys():
            try:
                destination[key] = source[key]
            except KeyError:
                self.report({'WARNING'}, "Key: " + key + " not moved" )
                


    def execute (self, context):
        collectionProp = eval(self.propPath)

       
        source = collectionProp[self.idx]
        
        try:
            if self.upDown:
                destination = collectionProp[self.idx - 1]
            else:
                destination = collectionProp[self.idx + 1]
        except IndexError:
            self.report({'WARNING'}, "End of stack")
            return {'FINISHED'}

        temp = collectionProp.add()  

        self.copyKeys(destination,temp)
        self.copyKeys(source,destination)
        self.copyKeys(temp,source)

        collectionProp.remove(len(collectionProp)-1)
           
        
        return {'FINISHED'}


class DeleteAllItemsButton(Operator):
    bl_idname = "measureit_arch.deleteallitemsbutton"
    bl_label = "Delete All Items?"
    bl_description = "Delete all Items"
    bl_category = 'MeasureitArch'
    item_type: StringProperty()
    is_style: BoolProperty()
    passedItem: PointerProperty(type=PropertyGroup)
    # -----------------------
    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        # Add properties
        mainobject = context.object
        scene = context.scene

        if self.is_style:
            StyleGen = scene.StyleGenerator

            for alignedDim in StyleGen.alignedDimensions:
                StyleGen.alignedDimensions.remove(0)
            for line in StyleGen.line_groups:
                StyleGen.line_groups.remove(0)
            for annotation in StyleGen.annotations:
                StyleGen.annotations.remove(0)
            for wrapper in StyleGen.wrappedStyles:
                StyleGen.wrappedStyles.remove(0)

        else:
            if self.item_type is 'D':
                for key in mainobject.DimensionGenerator[0].keys():
                    item = mainobject.DimensionGenerator[0].path_resolve(key)
                    if 'collection' in str(item):
                        typeContainer = item
                        for dim in typeContainer:
                            mainobject.DimensionGenerator[0].measureit_arch_num = 0
                            typeContainer.remove(0)

            elif self.item_type is 'L':
                for line in mainobject.LineGenerator[0].line_groups:
                    mainobject.LineGenerator[0].line_groups.remove(0)
                    mainobject.LineGenerator[0].line_num = 0
            
            elif self.item_type is 'A': 
                for annotation in mainobject.AnnotationGenerator[0].annotations:
                    mainobject.AnnotationGenerator[0].annotations.remove(0)
                    mainobject.AnnotationGenerator[0].num_annotations = 0
    
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
    
    def draw(self,context):
        layout = self.layout
