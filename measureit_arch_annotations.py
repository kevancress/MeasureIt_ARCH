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
import math

from bpy_extras import view3d_utils
from bpy.types import PropertyGroup, Panel, Object, Operator, UIList, Collection
from bpy.props import (
    CollectionProperty,
    FloatVectorProperty,
    IntProperty,
    BoolProperty,
    StringProperty,
    FloatProperty,
    EnumProperty,
    PointerProperty,
    BoolVectorProperty
)
from mathutils import Vector

from .measureit_arch_baseclass import BaseWithText
from .measureit_arch_utils import get_smart_selected


def update_active_annotation(self, context):
    Generator = context.object.AnnotationGenerator

    for annotation in Generator.annotations:
        annotation.is_active = False

    activeAnnotation = Generator.annotations[Generator.active_index]
    activeAnnotation.is_active = True


def annotation_update_flag(self, context):
    for textField in self.textFields:
        textField.text_updated = True
        update_custom_props(self, context)


def update_custom_props(self, context):
    ignoredProps = [
        'AnnotationGenerator', 'DimensionGenerator', 'LineGenerator',
        '_RNA_UI', 'cycles', 'cycles_visibility', 'obverts'
    ]
    idx = 0
    for key in context.object.keys():
        if key not in ignoredProps:
            if key not in self.customProperties:
                self.customProperties.add().name = key
    for prop in self.customProperties:
        if prop.name not in context.object.keys():
            self.customProperties.remove(idx)
        idx += 1


class CustomProperties(PropertyGroup):
    name: StringProperty(name='Custom Properties')


def custom_shape_poll(self, collection):
    myobj = self.annotationAnchorObject
    try:
        collection.objects[myobj.name]
    except:
        return collection


class AnnotationProperties(BaseWithText, PropertyGroup):
    customProperties: CollectionProperty(type=CustomProperties)

    customShape: PointerProperty(
        name='Custom Annotation Shape', type=Collection, poll=custom_shape_poll)

    custom_local_transforms: BoolProperty(
        name='Use Local Transforms',
        description='Uses the Local transforms of custom annotation objects',
        default=True)

    custom_fit_text: BoolProperty(
        name='Fit Text',
        description='Scale Custom Shap to Text Length',
        default=True)

    custom_scale: FloatProperty(
        name='Custom Shape Scale',
        description='Scale Custom Shape',
        default=1.0,)

    custom_shape_location: EnumProperty(
        items=(('A', "Anchor", "Anchor"),
               ('T', "Text", "Text")),
        name="Custom Shape Location",
        description="Define Where a custom shape is anchored")

    draw_leader: BoolProperty(
        name='Use Leader',
        description='Draw A Leader Line from the annotation to the anchor',
        default=True)

    shape_to_text: BoolProperty(
        name='Shape to text',
        description='Align the custom annotation shape with the annotation text, '
                    'rather than the anchor point',
        default=False)

    annotationRotation: FloatVectorProperty(
        name='annotationOffset',
        description='Rotation for Annotation',
        default=(0.0, 0.0, 0.0),
        subtype='EULER')

    annotationOffset: FloatVectorProperty(
        name='annotationOffset',
        description='Offset for Annotation',
        default=(1.0, 1.0, 1.0),
        subtype='TRANSLATION')

    leader_length: FloatProperty(
        name='Leader Offset',
        description='Leader Length',
        default=0.0,)

    annotationTextSource: StringProperty(
        name='annotationTextSource',
        description="Text Source",
        update=annotation_update_flag)

    annotationAnchorObject: PointerProperty(type=Object)

    annotationAnchor: IntProperty(
        name="annotationAnchor",
        description="Index of Vertex that the annotation is Anchored to")
    
    annotationAnchorSpline: IntProperty(
        name="annotationAnchorSpline",
        description="Index of Spline that the annotation is Anchored to (Curves)",
        default = -1)

    endcapSize: IntProperty(
        name="dimEndcapSize",
        description="End Cap size",
        default=15, min=1, max=500)

    endcapA: EnumProperty(
        items=(('99', "--", "No Cap"),
               ('D', "Dot", "Dot"),
               ('T', "Triangle", "Triangle")),
        name="A end",
        description="Add arrows to point A")

    align_to_camera: BoolProperty(
        name='Align Text to Camera',
        description='Keeps Anotation Text Aligned to the Active Camera',
        default=False)


class AnnotationContainer(PropertyGroup):
    num_annotations: IntProperty(
        name='Number of Annotations', min=0, max=1000, default=0,
        description='Number total of Annotations')
    active_index: IntProperty(
        name='Active Annotation Index',
        update=update_active_annotation)
    show_annotation_settings: BoolProperty(
        name='Show Annotation Settings', default=False)
    show_annotation_fields: BoolProperty(
        name='Show Annotation Text Fields', default=False)
    # Array of segments
    annotations: CollectionProperty(type=AnnotationProperties)


class AddAnnotationButton(Operator):
    bl_idname = "measureit_arch.addannotationbutton"
    bl_label = "Add"
    bl_description = "Add a new Annotation (For Mesh Objects Select 1 Vertex in Edit Mode)"
    bl_category = 'MeasureitArch'

    @classmethod
    def poll(cls, context):
        obj = context.object
        if obj is None or len(context.selected_objects) == 0:
            return True
        elif obj.type == "EMPTY" or obj.type == "CAMERA" or obj.type == "LIGHT":
            return True
        elif (obj.type == "MESH" or obj.type =="CURVE") and (bpy.context.mode == 'EDIT_MESH' or bpy.context.mode == "EDIT_CURVE"):
            return True
        else:
            return False

    def execute(self, context):
        emptyAnnoFlag = False
        if context.area.type == 'VIEW_3D':
            scene = context.scene
            sceneProps = scene.MeasureItArchProps
            mainobject = context.object

            # If no obj selected, created an empty
            if (bpy.context.mode == 'OBJECT' and
                len(context.selected_objects) == 0):
                cursorLoc = bpy.context.scene.cursor.location
                bpy.ops.object.empty_add(
                    type='SPHERE', radius=0.01, location=cursorLoc)
                context.object.name = 'Annotation Empty'
                emptyAnnoFlag = True

            pointList, warningStr = get_smart_selected(usePairs=False)

            if warningStr != '':
                self.report({'ERROR'}, warningStr)

            print(pointList)

            for point in pointList:
                obj = point['obj']
                anchor = point['vert']
                
                    

                annotationGen = obj.AnnotationGenerator

                annotationGen.num_annotations += 1
                newAnnotation = annotationGen.annotations.add()
                newAnnotation.annotationAnchor = anchor

                newAnnotation.itemType = 'A'
                newAnnotation.annotationAnchorObject = mainobject
                try:
                    newAnnotation.annotationAnchorSpline = point['spline']
                except KeyError:
                    pass

                if sceneProps.default_annotation_style != '':
                    newAnnotation.uses_style = True
                    newAnnotation.style = sceneProps.default_annotation_style
                else:
                    newAnnotation.uses_style = False

                if emptyAnnoFlag:
                    newAnnotation.annotationOffset = (0, 0, 0)
                    newAnnotation.textAlignment = 'C'
                    newAnnotation.lineWeight = 0

                newAnnotation.name = "Annotation {}".format(annotationGen.num_annotations)
                field = newAnnotation.textFields.add()
                field.text = ("Annotation {}".format(annotationGen.num_annotations))
                field2 = newAnnotation.textFields.add()
                field2.text = ("")

                newAnnotation.color = (0, 0, 0, 1)
                newAnnotation.fontSize = 24
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")

        return {'CANCELLED'}


class M_ARCH_UL_annotations_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        scene = bpy.context.scene

        StyleGen = scene.StyleGenerator
        hasGen = True

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            annotation = item
            layout.use_property_decorate = False
            row = layout.row(align=True)
            subrow = row.row()
            subrow.prop(
                annotation, "name", text="", emboss=False, icon='FONT_DATA')

            if annotation.visible:
                visIcon = 'HIDE_OFF'
            else:
                visIcon = 'HIDE_ON'

            if annotation.uses_style:
                styleIcon = 'LINKED'
            else:
                styleIcon = 'UNLINKED'

            subrow = row.row(align=True)
            if not annotation.uses_style:
                subrow = row.row()
                subrow.scale_x = 0.6
                subrow.prop(annotation, 'color', text="")
            else:
                row.prop_search(
                    annotation, 'style', StyleGen, 'annotations',
                    text="", icon='COLOR')
                row.separator()

            if hasGen:
                row = row.row(align=True)
                row.prop(annotation, 'uses_style', text="",
                         toggle=True, icon=styleIcon, emboss=False)

            row.prop(annotation, "visible", text="", icon=visIcon)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')


class OBJECT_PT_UIAnnotations(Panel):
    """Creates a Panel in the Object properties window"""
    bl_parent_id = 'OBJECT_PT_Panel'
    bl_label = "Annotations"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon='FONT_DATA')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        if context.object is not None:
            if 'AnnotationGenerator' in context.object:
                annoGen = context.object.AnnotationGenerator

                row = layout.row()

                # Draw The UI List
                row.template_list(
                    "M_ARCH_UL_annotations_list", "", annoGen, "annotations",
                    annoGen, "active_index", rows=2, type='DEFAULT')

                # Operators Next to List
                col = row.column(align=True)
                op = col.operator(
                    "measureit_arch.deletepropbutton", text="", icon="X")
                op.genPath = 'bpy.context.object.AnnotationGenerator'
                op.tag = annoGen.active_index  # saves internal data
                op.item_type = 'annotations'
                op.is_style = False

                col.separator()
                up = col.operator("measureit_arch.movepropbutton", text="", icon="TRIA_UP")
                up.genPath = 'bpy.context.object.AnnotationGenerator'
                up.item_type = 'annotations'
                up.upDown = -1

                down = col.operator("measureit_arch.movepropbutton", text="", icon="TRIA_DOWN")
                down.genPath = 'bpy.context.object.AnnotationGenerator'
                down.item_type = 'annotations'
                down.upDown = 1

                col.separator()
                col.menu("OBJECT_MT_annotation_menu",
                         icon='DOWNARROW_HLT', text="")

                # Settings Below List
                if (len(annoGen.annotations) > 0 and
                    annoGen.active_index < len(annoGen.annotations)):

                    annotation = annoGen.annotations[annoGen.active_index]

                    if annoGen.show_annotation_fields:
                        fieldsIcon = 'DISCLOSURE_TRI_DOWN'
                    else:
                        fieldsIcon = 'DISCLOSURE_TRI_RIGHT'

                    box = layout.box()
                    col = box.column()
                    row = col.row(align=True)
                    row.prop(annoGen, 'show_annotation_fields',
                             text="", icon=fieldsIcon, emboss=False)
                    row.label(text=annotation.name + ' Text Fields:')

                    row.emboss = 'PULLDOWN_MENU'
                    txtAddOp = row.operator(
                        "measureit_arch.addtextfield", text="", icon="ADD")
                    txtAddOp.propPath = 'bpy.context.active_object.AnnotationGenerator.annotations[bpy.context.active_object.AnnotationGenerator.active_index].textFields'
                    txtAddOp.idx = annoGen.active_index
                    txtAddOp.add = True

                    txtRemoveOp = row.operator(
                        "measureit_arch.addtextfield", text="", icon="REMOVE")
                    txtRemoveOp.propPath = 'bpy.context.active_object.AnnotationGenerator.annotations[bpy.context.active_object.AnnotationGenerator.active_index].textFields'
                    txtRemoveOp.idx = annoGen.active_index
                    txtRemoveOp.add = False

                    if annoGen.show_annotation_fields:

                        col = box.column(align=True)
                        idx = 0
                        for textField in annotation.textFields:
                            col = box.column(align=True)

                            row = col.row(align=True)

                            split = row.split(factor=0.2)
                            split.label(text='Text Field ' + str(idx + 1))

                            row = split.row(align=True)
                            row.prop(textField, 'autoFillText',
                                     text="", icon="FILE_TEXT")

                            if textField.autoFillText:
                                row.prop(textField, 'textSource', text="")
                            else:
                                row.prop(textField, 'text', text="")

                            if textField.textSource == 'RNAPROP' and textField.autoFillText:
                                row.prop(textField, 'rnaProp', text="")

                            row.emboss = 'PULLDOWN_MENU'
                            op = row.operator(
                                'measureit_arch.moveitem', text="", icon='TRIA_DOWN')
                            op.propPath = 'bpy.context.active_object.AnnotationGenerator.annotations[bpy.context.active_object.AnnotationGenerator.active_index].textFields'
                            op.upDown = 1
                            op.idx = idx

                            op = row.operator(
                                'measureit_arch.moveitem', text="", icon='TRIA_UP')
                            op.propPath = 'bpy.context.active_object.AnnotationGenerator.annotations[bpy.context.active_object.AnnotationGenerator.active_index].textFields'
                            op.upDown = -1
                            op.idx = idx
                            idx += 1

                    if annoGen.show_annotation_settings:
                        settingsIcon = 'DISCLOSURE_TRI_DOWN'
                    else:
                        settingsIcon = 'DISCLOSURE_TRI_RIGHT'

                    box = layout.box()
                    col = box.column()
                    row = col.row()
                    row.prop(annoGen, 'show_annotation_settings',
                             text="", icon=settingsIcon, emboss=False)
                    row.label(text=annotation.name + ' Settings:')

                    if annoGen.show_annotation_settings:
                        col = box.column(align=True)
                        col.prop_search(
                            annotation, 'customShape', bpy.data, 'collections',
                            text='Custom Shape')
                        col.prop(
                            annotation, 'custom_shape_location',
                            text='Custom Shape Location')
                        col.prop(
                            annotation, 'custom_scale',
                            text='Custom Shape Scale')
                        col.prop(
                            annotation, 'custom_local_transforms',
                            text='Use Local Transforms')
                        # col.prop(annotation, 'custom_fit_text', text = 'Fit Text')

                        if not annotation.uses_style:
                            col = box.column(align=True)
                            col.prop_search(
                                annotation, 'visibleInView', bpy.context.scene, 'view_layers', text='Visible In View')

                            col = box.column(align=True)
                            split = box.split(factor=0.485)
                            col = split.column()
                            col.alignment = 'RIGHT'
                            col.label(text='Font')
                            col = split.column(align=True)
                            col.template_ID(
                                annotation, "font", open="font.open", unlink="font.unlink")

                            col = box.column(align=True)
                            col.prop(annotation, 'fontSize', text="Font Size")
                            col.prop(annotation, 'textAlignment', text='Justification')
                            col.prop(annotation, 'textPosition', text='Position')

                            col = box.column(align=True)
                            col.prop(annotation, 'endcapA', text='End Cap')
                            col.prop(annotation, 'endcapSize', text='Size')
                            col.prop(annotation, 'endcapArrowAngle', text='Arrow Angle')

                            col = box.column(align=True)
                            col.prop(annotation, 'lineWeight', text="Line Weight")
                            col.prop(annotation, 'draw_leader', text='Draw Leader')

                        col = box.column()
                        col.prop(annotation, 'leader_length')

                        col = box.column()
                        col.prop(annotation, 'annotationOffset', text='Offset')

                        col = box.column()
                        col.enabled = not annotation.align_to_camera
                        col.prop(annotation, 'annotationRotation', text='Rotation')

                        col = box.column()
                        col.prop(annotation, 'inFront', text='Draw in Front')
                        col.prop(annotation, 'align_to_camera')

                # Delete Operator (Move to drop down menu next to list)
                col = layout.column()


class OBJECT_MT_annotation_menu(bpy.types.Menu):
    bl_label = "Custom Menu"

    def draw(self, context):
        layout = self.layout

        delOp = layout.operator(
            "measureit_arch.deleteallitemsbutton", text="Delete All Annotations", icon="X")
        delOp.is_style = False
        delOp.genPath = 'bpy.context.object.AnnotationGenerator'
        # if 'AnnotationGenerator' in context.object:
        #     scene = context.scene
        #     annoGen = context.object.AnnotationGenerator


class TranslateAnnotationOp(bpy.types.Operator):
    """ Move Annotation """
    bl_idname = "measureit_arch.translate_annotation"
    bl_label = "Translate Annotation"
    bl_options = {'GRAB_CURSOR', 'INTERNAL', 'BLOCKING', 'UNDO'}

    idx: IntProperty()
    constrainAxis: BoolVectorProperty(name="Constrain Axis", size=3, subtype='XYZ')
    offset: FloatVectorProperty(name="Offset", size=3)
    objIndex: IntProperty()

    def modal(self, context, event):
        myobj = context.selected_objects[self.objIndex]
        annotation = myobj.AnnotationGenerator.annotations[self.idx]
        # Set Tweak Flags
        if event.ctrl:
            tweak_snap = True
        else:
            tweak_snap = False
        if event.shift:
            tweak_precise = True
        else:
            tweak_precise = False

        if event.type == 'MOUSEMOVE':
            sensitivity = 0.01
            vecDelta = Vector(((event.mouse_x - self.init_mouse_x) * sensitivity,
                               (event.mouse_y - self.init_mouse_y) * sensitivity, 0))
            viewRot = context.area.spaces[0].region_3d.view_rotation
            vecDelta.rotate(viewRot)
            mat = myobj.matrix_world
            rot = mat.to_quaternion()
            i = Vector((-1, 0, 0))
            j = Vector((0, -1, 0))
            k = Vector((0, 0, -1))

            axis = 0
            axisInd = 0
            if self.constrainAxis[0]:
                init = self.init_x
                axis = i
                axisInd = 0
                axisText = 'X: '
            if self.constrainAxis[1]:
                init = self.init_y
                axis = j
                axisInd = 1
                axisText = 'Y: '
            if self.constrainAxis[2]:
                init = self.init_z
                axis = k
                axisInd = 2
                axisText = 'Z: '

            axis.rotate(rot)
            delta = vecDelta.project(axis)
            delta = delta.magnitude
            if axis.dot(vecDelta) > 0:
                delta = -delta

            if tweak_snap:
                delta = round(delta)
            if tweak_precise:
                delta /= 10.0

            annotation.annotationOffset[axisInd] = init + delta
            context.area.header_text_set("Move " + axisText + "%.4f" % delta)

        elif event.type == 'LEFTMOUSE':
            # Setting hide_viewport is a stupid hack to force Gizmos to update
            # after operator completes
            context.object.hide_viewport = False
            context.area.header_text_set(None)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            # Setting hide_viewport is a stupid hack to force Gizmos to update
            # after operator completes
            context.object.hide_viewport = False
            context.area.header_text_set(None)
            annotation.annotationOffset[0] = self.init_x
            annotation.annotationOffset[1] = self.init_y
            annotation.annotationOffset[2] = self.init_z
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        myobj = context.selected_objects[self.objIndex]
        annotation = myobj.AnnotationGenerator.annotations[self.idx]
        self.init_mouse_x = event.mouse_x
        self.init_mouse_y = event.mouse_y

        self.init_x = annotation.annotationOffset[0]
        self.init_y = annotation.annotationOffset[1]
        self.init_z = annotation.annotationOffset[2]

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class RotateAnnotationOp(bpy.types.Operator):
    """Rotate Annotation"""
    bl_idname = "measureit_arch.rotate_annotation"
    bl_label = "Rotate Annotation"
    bl_options = {'INTERNAL', 'BLOCKING', 'UNDO'}

    idx: IntProperty()

    constrainAxis: BoolVectorProperty(
        name="Constrain Axis",
        size=3,
        subtype='XYZ')

    offset: FloatVectorProperty(
        name="Offset",
        size=3)

    objIndex: IntProperty()

    def modal(self, context, event):
        context.area.tag_redraw()
        myobj = context.selected_objects[self.objIndex]
        annotation = myobj.AnnotationGenerator.annotations[self.idx]
        center = annotation.gizLoc
        region = bpy.context.region
        rv3d = bpy.context.space_data.region_3d
        center = view3d_utils.location_3d_to_region_2d(region, rv3d, center)
        # For some reason the value returned by view3d utils is 100px off in the y axis
        center += Vector((0, 100))
        vecLast = Vector((self.init_mouse_x, self.init_mouse_y))
        vecLast -= center
        delta = 0
        # Set Tweak Flags
        if event.ctrl:
            tweak_snap = True
        else:
            tweak_snap = False
        # if event.shift:
        #     tweak_precise = True
        # else:
        #     tweak_precise = False

        if event.type == 'MOUSEMOVE':
            sensitivity = 1

            vecDelta = Vector((event.mouse_x, event.mouse_y))
            vecDelta -= center
            delta += vecDelta.angle_signed(vecLast) * sensitivity

            delta = math.degrees(delta)
            if tweak_snap:
                delta = 5 * round(delta / 5)

            if self.constrainAxis[0]:
                annotation.annotationRotation[0] = self.init_x - \
                    math.radians(delta)
                axisText = 'X: '
            if self.constrainAxis[1]:
                annotation.annotationRotation[1] = self.init_y + \
                    math.radians(delta)
                axisText = 'Y: '
            if self.constrainAxis[2]:
                annotation.annotationRotation[2] = self.init_z - \
                    math.radians(delta)
                axisText = 'Z: '

            vecLast = vecDelta
            context.area.header_text_set(
                "Rotate " + axisText + "%.4f" % delta + "\u00b0")

        elif event.type == 'LEFTMOUSE':
            # Setting hide_viewport is a stupid hack to force Gizmos to update after operator completes
            context.area.header_text_set(None)
            bpy.context.window.cursor_modal_restore()
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            # Setting hide_viewport is a stupid hack to force Gizmos to update after operator completes
            context.area.header_text_set(None)
            bpy.context.window.cursor_modal_restore()
            annotation.annotationRotation[0] = self.init_x
            annotation.annotationRotation[1] = self.init_y
            annotation.annotationRotation[2] = self.init_z
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        myobj = context.selected_objects[self.objIndex]
        annotation = myobj.AnnotationGenerator.annotations[self.idx]
        self.init_mouse_x = event.mouse_x
        self.init_mouse_y = event.mouse_y

        self.init_x = annotation.annotationRotation[0]
        self.init_y = annotation.annotationRotation[1]
        self.init_z = annotation.annotationRotation[2]
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
