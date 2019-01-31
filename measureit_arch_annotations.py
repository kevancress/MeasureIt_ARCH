# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


# ----------------------------------------------------------
# File: measureit_arch_annotations.py
# Main panel for different MeasureitArch general actions
# Author:  Kevan Cress
#
# ----------------------------------------------------------
import bpy
import blf
import bgl
import gpu

from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D, Scene

from bpy.props import (
        CollectionProperty,
        FloatVectorProperty,
        IntProperty,
        BoolProperty,
        StringProperty,
        FloatProperty,
        EnumProperty,
        PointerProperty
        )
from .buffer_prop import BufferProperty
from .measureit_arch_main import *
import numpy as np
import math
# ------------------------------------------------------------------
# Define property group class for annotation data
# ------------------------------------------------------------------

def update_text(self, context):

    rawRGB = self.annotationColor
    rgb = (pow(rawRGB[0],(1/2.2)),pow(rawRGB[1],(1/2.2)),pow(rawRGB[2],(1/2.2)),rawRGB[3])
    size = 20
    font_id=0
    blf.color(font_id,rgb[0],rgb[1],rgb[2],rgb[3])
    blf.size(font_id,size,300)
    blf.position(font_id, 5, 5,0)
    
    fwidth, fheight =blf.dimensions(font_id,self.annotationText)
    width = math.ceil(fwidth)
    height = math.ceil(fheight)
    self.annotationHeight = height
    self.annotationWidth = width
    annotationOffscreen = gpu.types.GPUOffScreen(width,height)
    texture_buffer = bgl.Buffer(bgl.GL_BYTE, width * height * 4)
    print (width*height*4)
    with annotationOffscreen.bind():
        bgl.glClear(bgl.GL_COLOR_BUFFER_BIT)

        text = self.annotationText
        
        blf.size(font_id,60,300)
        blf.draw(font_id,text)
        
        bgl.glReadBuffer(bgl.GL_BACK)
        bgl.glReadPixels(0, 0, width, height, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, texture_buffer)
        
        context.object[str(self.annotationAnchor)] = texture_buffer.to_list()
        self.text_updated = True
        annotationOffscreen.free()
   
    if not str(self.annotationAnchor) in bpy.data.images:
        bpy.data.images.new(str(self.annotationAnchor), width, height)
    image = bpy.data.images[str(self.annotationAnchor)]
    image.scale(width, height)
    image.pixels = [v / 255 for v in texture_buffer]
class AnnotationProperties(PropertyGroup):

    annotationText: StringProperty(name="annotationText",
                        description="Text Associated With Annotation ",
                        default="",
                        update= update_text)
    
    annotationAnchor: IntProperty(name="annotationAnchor",
                        description="Index of Vertex that the annotation is Anchored to")

    annotationColor: FloatVectorProperty(name="annotationColor",
                        description="Color for Lines",
                        default=(0.1, 0.1, 0.1, 1.0),
                        min=0.0,
                        max=1,
                        subtype='COLOR',
                        size=4,
                        update=update_text) 

    annotationLineWeight: IntProperty(name="annotationLineWeight",
                        description="Lineweight",
                        min = 1,
                        max = 10)

    annotationVis: BoolProperty(name="annotationVis",
                        description="Line show/hide",
                        default=True)

    annotationFree: BoolProperty(name="annotationFree",
                        description="This annotation is free and can be deleted",
                        default=False)
    
    annotationSettings: BoolProperty(name= "annotationSettings",
                        description= "Show Line Settings",
                        default=False)
    annotationTexture: IntProperty(name= "annotationTexture",
                        description= "Int Array Storing the Annotation Texture Buffer")

    annotationFont: PointerProperty(type= bpy.types.VectorFont)

    text_updated: BoolProperty(name='text_updated',
                        description= 'flag when text texture need to be redrawn',
                        default = False)

    annotationWidth: IntProperty(name='annotationWidth',
                        description= 'Width of annotation')
    
    annotationHeight: IntProperty(name='annotationHeight',
                        description= 'Height of annotation')
# Register
bpy.utils.register_class(AnnotationProperties)



# ------------------------------------------------------------------
# Define object class (container of annotations)
# MeasureitArch
# ------------------------------------------------------------------
class AnnotationContainer(PropertyGroup):
    num_annotations: IntProperty(name='Number of Annotations', min=0, max=1000, default=0,
                                description='Number total of Annotations')
    # Array of segments
    annotations: CollectionProperty(type=AnnotationProperties)


bpy.utils.register_class(AnnotationContainer)
Object.AnnotationGenerator = CollectionProperty(type=AnnotationContainer)


class AddAnnotationButton(Operator):
    bl_idname = "measureit_arch.addannotationbutton"
    bl_label = "Add"
    bl_description = "(EDITMODE only) Add a new measure label (select 1 vertex)"
    bl_category = 'MeasureitArch'

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "MESH":
                if bpy.context.mode == 'EDIT_MESH':
                    return True
                else:
                    return False
            else:
                return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # Add properties
            mainobject = context.object
            mylist = get_selected_vertex(mainobject)
            if len(mylist) == 1:
                if 'AnnotationGenerator' not in mainobject:
                    mainobject.AnnotationGenerator.add()
                
                numVerts = len(mainobject.data.vertices)  
                if 'tex_buffer' not in mainobject:
                    tex_buffer = bgl.Buffer(bgl.GL_INT, numVerts)
                    bgl.glGenTextures(numVerts, tex_buffer)
                    mainobject['tex_buffer'] = tex_buffer.to_list()
                annotationGen = mainobject.AnnotationGenerator[0]
                annotationGen.num_annotations +=1
                newAnnotation = annotationGen.annotations.add()

                          

                
                # Set values
                newAnnotation.annotationText = ("Annotation " + str(annotationGen.num_annotations))
                newAnnotation.annotationAnchor = mylist[0]
                newAnnotation.annotationColor = (0,0,0,1)
                newAnnotation.annotationLineWeight = (2)
                update_text(newAnnotation,context)
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: Select one vertex for creating measure label")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},   
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}


class MeasureitArchAnnotationsPanel(Panel):
    bl_idname = "annotations"
    bl_label = "Annotations"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    
    @classmethod
    def poll(cls, context):
        if 'AnnotationGenerator' in bpy.context.object:
            return True
        else:
            return False


    def draw(self, context):
         if context.object is not None:
            if 'AnnotationGenerator' in context.object:
                layout = self.layout
                layout.use_property_split = True
                layout.use_property_decorate = False
                # -----------------
                # loop
                # -----------------
                
                annotationGen = context.object.AnnotationGenerator[0]
                if annotationGen.num_annotations> 0:
                    #row = layout.row(align = True)
                    #row.operator("measureit_arch.expandallsegmentbutton", text="Expand all", icon="ADD")
                    #row.operator("measureit_arch.collapseallsegmentbutton", text="Collapse all", icon="REMOVE")
                    for idx in range(0, annotationGen.num_annotations):
                        add_annotation_item(layout, idx, annotationGen.annotations[idx])

                    #row = layout.row()
                    #row.operator("measureit_arch.deleteallsegmentbutton", text="Delete all", icon="X")
    
# -----------------------------------------------------
# Add annotation options to the panel.
# -----------------------------------------------------
def add_annotation_item(layout, idx, annotation):
    if annotation.annotationSettings is True:
        box = layout.box()
        row = box.row(align=True)
    else:
        row = layout.row(align=True)


    if annotation.annotationVis is True:
        icon = "VISIBLE_IPO_ON"
    else:
        icon = "VISIBLE_IPO_OFF"

    row.prop(annotation, 'annotationVis', text="", toggle=True, icon=icon)
    row.prop(annotation, 'annotationSettings', text="",toggle=True, icon='PREFERENCES')
    row.prop(annotation, 'annotationColor', text="" )
    row.prop(annotation, 'annotationText', text="")
    op = row.operator("measureit_arch.deleteannotationbutton", text="", icon="X")
    op.tag = idx  # saves internal data
    
    if annotation.annotationSettings is True:
        
        col = box.column()
        col.template_ID(annotation, "annotationFont", open="font.open", unlink="font.unlink")
        col = box.column()
        col.prop(annotation, 'annotationLineWeight', text="Line Weight" )
        
        

class DeleteAnnotationButton(Operator):

    bl_idname = "measureit_arch.deleteannotationbutton"
    bl_label = "Delete Line"
    bl_description = "Delete an Annotation"
    bl_category = 'MeasureitArch'
    tag= IntProperty()

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        # Add properties
        mainObj = context.object
        annotationGen = mainObj.AnnotationGenerator[0]
        annotation = annotationGen.annotations[self.tag]
        annotation.lineFree = True
        # Delete element
        annotationGen.annotations.remove(self.tag)
        annotationGen.num_annotations -= 1
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


