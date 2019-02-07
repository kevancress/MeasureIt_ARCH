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
    style: IntProperty(name="Style",
                    description="Style to use",
                    min=0)

    color: FloatVectorProperty(name="dimColor",
                    description="Color for the Dimension",
                    default=(0.0,0.0,0.0, 1.0),
                    min=0,
                    max=1,
                    subtype='COLOR',
                    size=4)
    
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

    color: FloatVectorProperty(name="dimColor",
                description="Color for the Dimension",
                default=(0.0,0.0,0.0, 1.0),
                min=0,
                max=1,
                subtype='COLOR',
                size=4,
                update= update_flag)
    
    text: StringProperty(name="annotationText",
                description="Text Associated With Annotation ",
                default="",
                update= update_flag)

    textAlignment:EnumProperty(
                items=(('L', "Left", ""),
                        ('C', "Center", ""),
                        ('R', "Right", "")),
                name="align Font",
                description="Set Font alignment")

    textPosition:EnumProperty(
                items=(('T', "Top", ""),
                        ('M', "Mid", ""),
                        ('B', "Bottom", "")),
                name="align Font",
                description="Set Font Position")

    fontSize: IntProperty(name='annotationSize',
                description="Annotation Size",
                default=12)

    textResolution: IntProperty(name="Annotation Resolution",
                description="Annotation Resolution",
                default=150,
                min=50,
                max=1200)

    font: PointerProperty(type= bpy.types.VectorFont,
                update = update_flag)

    text_updated: BoolProperty(name='text_updated',
                description= 'flag when text need to be redrawn',
                default = False)
    
    texture_updated: BoolProperty(name='text_updated',
            description= 'flag when text texture need to be redrawn',
            default = False)

    textWidth: IntProperty(name='annotationWidth',
                description= 'Width of annotation')
        
    textHeight: IntProperty(name='annotationHeight',
                description= 'Height of annotation')
    
