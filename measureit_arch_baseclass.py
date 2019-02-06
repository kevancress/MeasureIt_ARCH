import bpy
import bgl
import blf
import gpu
import math
from mathutils import Matrix
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, BoolProperty, StringProperty, \
                      FloatProperty, EnumProperty, PointerProperty

def update_text(self, context):

    #Get textitem Properties
    rawRGB = self.color
    rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])
    size = 20
    resolution = self.textResolution

    
    #Get Font Id
    badfonts=[None]
    if 'Bfont' in bpy.data.fonts:
        badfonts.append(bpy.data.fonts['Bfont'])

    if self.font not in badfonts:
        vecFont = self.font
        fontPath = vecFont.filepath
        font_id= blf.load(fontPath)
    else:
        font_id=0

    # Get Text
    if 'annotationTextSource' in self:
        if self.annotationTextSource is not '':
            text = str(context.object[self.annotationTextSource])
    else:
        text = self.text


    # Set BLF font Properties
    blf.color(font_id,rgb[0],rgb[1],rgb[2],rgb[3])
    blf.size(font_id,size,resolution)
    
    
    #Calculate Optimal Dimensions for Text Texture.
    fheight = blf.dimensions(font_id,'fp')[1]
    fwidth = blf.dimensions(font_id,text)[0]
    width = math.ceil(fwidth)
    height = math.ceil(fheight+4)
    blf.position(font_id,0,height/4,0)
    #Save Texture size to Annotation Properties
    self.textHeight = height
    self.textWidth = width

    # Start Offscreen Draw
    textOffscreen = gpu.types.GPUOffScreen(width,height)
    texture_buffer = bgl.Buffer(bgl.GL_BYTE, width * height * 4)
    with textOffscreen.bind():
        # Clear Past Draw and Set 2D View matrix
        bgl.glClear(bgl.GL_COLOR_BUFFER_BIT)
        
        view_matrix = Matrix([
        [2 / width, 0, 0, -1],
        [0, 2 / height, 0, -1],
        [0, 0, 1, 0],
        [0, 0, 0, 1]])
        
        gpu.matrix.reset()
        gpu.matrix.load_matrix(view_matrix)
        gpu.matrix.load_projection_matrix(Matrix.Identity(4))

        
        blf.draw(font_id,text)
        
        # Read Offscreen To Texture Buffer
        bgl.glReadBuffer(bgl.GL_BACK)
        bgl.glReadPixels(0, 0, width, height, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, texture_buffer)
        
        # Write Texture Buffer to Annotation ID Property as List
        self['texture'] = texture_buffer.to_list()
        self.text_updated = True

        textOffscreen.free()

    #generate image datablock from buffer for debug preview
    #ONLY USE IF NECESSARY. SERIOUSLY SLOWS PREFORMANCE
    #if not str(self.annotationAnchor) in bpy.data.images:
    #    bpy.data.images.new(str(self.annotationAnchor), width, height)
    #image = bpy.data.images[str(self.annotationAnchor)]
    #image.scale(width, height)
    #image.pixels = [v / 255 for v in texture_buffer]

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
                update = update_text)
    
    text: StringProperty(name="annotationText",
                description="Text Associated With Annotation ",
                default="",
                update= update_text)

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
                max=1200,
                update=update_text)

    font: PointerProperty(type= bpy.types.VectorFont,
                update=update_text)

    text_updated: BoolProperty(name='text_updated',
                description= 'flag when text texture need to be redrawn',
                default = False)

    textWidth: IntProperty(name='annotationWidth',
                description= 'Width of annotation')
        
    textHeight: IntProperty(name='annotationHeight',
                description= 'Height of annotation')
    
