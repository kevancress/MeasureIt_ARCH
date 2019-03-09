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

class BaseProp:
    name: StringProperty(name="Item Name",
            description="Item Name",
            default="")

    is_style: BoolProperty(name= "is Style",
                description= "This property Group is a Style",
                default=False)
    
    uses_style: BoolProperty(name= "uses Style",
                description= "This property Group Uses a Style",
                default=False,
                update = update_flag)

    text_updated: BoolProperty(name='text_updated',
                description= 'flag when text need to be redrawn',
                default = False)

    style: StringProperty(name="Item Name",
            description="Item Name",
            default="",
            update = update_flag)

    itemType: EnumProperty(
                items=(('A', "Annotation ", ""),
                        ('L', "Line Style", ""),
                        ('D', "Dimension", "")),
                name="Style Type",
                description="Type of Style to Add")

    color: FloatVectorProperty(name="dimColor",
                description="Color for the Dimension",
                default=(0.0,0.0,0.0, 1.0),
                min=0,
                max=1,
                subtype='COLOR',
                size=4,
                update= update_flag)

    lineWeight: IntProperty(name="lineWeight",
                description="Lineweight",
                min = 1,
                max = 10)

    free: BoolProperty(name="annotationFree",
                description="This annotation is free and can be deleted",
                default=False)
    
    settings: BoolProperty(name= "Settings",
                description= "Show Settings",
                default=False)

    visible: BoolProperty(name="annotationVis",
                description="Line show/hide",
                default=True)

class BaseWithText(BaseProp):  
    text: StringProperty(name="annotationText",
                description="Text Associated With Annotation ",
                default="",
                update= update_flag)

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

    textFlippedX: BoolProperty(name='textFlippedX', 
                description= 'Flip Text X',
                default = False)
    textFlippedY: BoolProperty(name='textFlippedY', 
                description= 'Flip Text Y',
                default = False)
    
    texture_updated: BoolProperty(name='text_updated',
            description= 'flag when text texture need to be redrawn',
            default = False)

    textWidth: IntProperty(name='annotationWidth',
                description= 'Width of annotation')
        
    textHeight: IntProperty(name='annotationHeight',
                description= 'Height of annotation')
    
class DeletePropButton(Operator):

    bl_idname = "measureit_arch.deletepropbutton"
    bl_label = "Delete property"
    bl_description = "Delete a property"
    bl_category = 'MeasureitArch'
    bl_options = {'REGISTER'} 
    tag= IntProperty()
    item_type= StringProperty()
    is_style= BoolProperty()

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        # Add properties
        mainObj = context.object
        
        if self.is_style is True:
            Generator = context.scene.StyleGenerator[0]
        else:
            if self.item_type is 'A':
                Generator = mainObj.AnnotationGenerator[0]
                Generator.num_annotations -= 1
            elif self.item_type is 'L':
                Generator = mainObj.LineGenerator[0]
                Generator.line_num -= 1
            elif self.item_type is 'D':
                Generator = mainObj.MeasureGenerator[0]
                Generator.measureit_arch_num -= 1

        if self.item_type is 'A':
            itemGroup = Generator.annotations
        elif self.item_type is 'L':
            itemGroup = Generator.line_groups
        elif self.item_type is 'D':
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
    bl_label = "Delete All Styles?"
    bl_description = "Delete all Styles"
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
        else:
            
            if self.item_type is 'D':
                for alignedDim in mainobject.MeasureGenerator[0].alignedDimensions:
                    mainobject.MeasureGenerator[0].alignedDimensions.remove(0)
                    mainobject.MeasureGenerator[0].measureit_arch_num = 0
            
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

class ExpandCollapseAllPropButton(Operator):
    bl_idname = "measureit_arch.expandcollapseallpropbutton"
    bl_label = "Expand or Collapse"
    bl_description = "Expand or Collapse all measure properties"
    bl_category = 'MeasureitArch'
    item_type = StringProperty()
    is_style = BoolProperty()
    state = BoolProperty()
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
                alignedDim.settings = self.state
            for line in StyleGen.line_groups:
                line.settings = self.state
            for annotation in StyleGen.annotations:
                annotation.settings = self.state
            return {'FINISHED'}

        if self.item_type is 'D':
            for alignedDim in mainobject.MeasureGenerator[0].alignedDimensions:
                alignedDim.settings = self.state
            return {'FINISHED'}
        if self.item_type is 'L':
            for line in mainobject.LineGenerator[0].line_groups:
                line.settings = self.state
            return {'FINISHED'}
        if self.item_type is 'A': 
            for annotation in mainobject.AnnotationGenerator[0].annotations:
                annotation.settings = self.state
            return {'FINISHED'}
        return {'FINISHED'}
    
