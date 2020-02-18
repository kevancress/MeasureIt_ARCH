import bpy
import bgl
import blf
import gpu
import math
from mathutils import Matrix
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, BoolProperty, StringProperty, \
                FloatProperty, EnumProperty, PointerProperty

def update_flag(self,context):
    self.text_updated = True

def update_active_dim(self,context):
    dimGen = context.object.DimensionGenerator[0]
    print(self)
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
    

class BaseProp:
    inFront: BoolProperty(name='inFront',
                description= 'Draw this element In front of other objects',
                default = False)


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
                update = update_flag)

    lineWeight: IntProperty(name="Line Weight",
                description="Lineweight",
                default = 1,
                min = 1)

    free: BoolProperty(name="Free",
                description="This Item is free and can be deleted",
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

    textSource: StringProperty(name='annotationTextSource',
                description="Text Source",
                update=update_flag)

    textWidth: IntProperty(name='annotationWidth',
                description= 'Width of annotation')
        
    textHeight: IntProperty(name='annotationHeight',
                description= 'Height of annotation')

    texture_updated: BoolProperty(name='text_updated',
            description= 'flag when text texture need to be redrawn',
            default = False)

bpy.utils.register_class(TextField)

class BaseWithText(BaseProp):

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

    fontSize: IntProperty(name='annotationSize',
                description="Annotation Size",
                default=12)

    textResolution: IntProperty(name="Annotation Resolution",
                description="Annotation Resolution",
                default=150,
                min=50,
                max=1200,
                update = update_flag)

    font: PointerProperty(type= bpy.types.VectorFont,
                update = update_flag)

    # endcap properties are defined here to ensure compatiblity but the enumProps are overwritten in child property groups
    endcapSize: IntProperty(name="dimEndcapSize",
                description="End Cap size",
                default=15, min=1, max=500)
    
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

    dimVisibleInView: PointerProperty(type= bpy.types.Camera)

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
            Generator = context.scene.StyleGenerator[0]
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

class DeleteAllItemsButton(Operator):
    bl_idname = "measureit_arch.deleteallitemsbutton"
    bl_label = "Delete All Items?"
    bl_description = "Delete all Items"
    bl_category = 'MeasureitArch'
    item_type: StringProperty()
    is_style: BoolProperty()
    # -----------------------
    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        # Add properties
        mainobject = context.object
        scene = context.scene

        if self.is_style:
            StyleGen = scene.StyleGenerator[0]

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
                for alignedDim in mainobject.DimensionGenerator[0].alignedDimensions:
                    mainobject.DimensionGenerator[0].alignedDimensions.remove(0)
                    mainobject.DimensionGenerator[0].measureit_arch_num = 0
                for angleDim in mainobject.DimensionGenerator[0].angleDimensions:
                    mainobject.DimensionGenerator[0].angleDimensions.remove(0)
                    mainobject.DimensionGenerator[0].measureit_arch_num = 0
                for axisDim in mainobject.DimensionGenerator[0].axisDimensions:
                    mainobject.DimensionGenerator[0].axisDimensions.remove(0)
                    mainobject.DimensionGenerator[0].measureit_arch_num = 0
                for boundsDim in mainobject.DimensionGenerator[0].boundsDimensions:
                    mainobject.DimensionGenerator[0].boundsDimensions.remove(0)
                    mainobject.DimensionGenerator[0].measureit_arch_num = 0
                for wrapper in mainobject.DimensionGenerator[0].wrappedDimensions:
                    mainobject.DimensionGenerator[0].wrappedDimensions.remove(0)

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