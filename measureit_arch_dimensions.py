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
# File: measureit_arch_dimensions.py
# Main panel for different MeasureitArch general actions
# Author: Antonio Vazquez (antonioya), Kevan Cress
#
# ----------------------------------------------------------
import bpy
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D, UIList
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, BoolProperty, StringProperty, \
                      FloatProperty, EnumProperty, PointerProperty
from .measureit_arch_main import *
from .measureit_arch_baseclass import BaseWithText

# ------------------------------------------------------------------
# Define property group class for measureit_arch faces index
# ------------------------------------------------------------------
class MeasureitArchIndex(PropertyGroup):
    glidx = IntProperty(name="index",
                        description="vertex index")

bpy.utils.register_class(MeasureitArchIndex)

# ------------------------------------------------------------------
# Define property group class for measureit_arch faces
# ------------------------------------------------------------------
class MeasureitArchFaces(PropertyGroup):
    glface = IntProperty(name="glface",
                         description="Face number")
    # Array of index
    measureit_arch_index: CollectionProperty(type=MeasureitArchIndex)

bpy.utils.register_class(MeasureitArchFaces)

class AlignedDimensionProperties(BaseWithText,PropertyGroup):
    dimPointA: IntProperty(name='dimPointA',
                    description="Dimension Start Vertex Index")

    dimObjectA: PointerProperty(type=Object)

    dimPointB: IntProperty(name='dimPointB',
                    description="Dimension End Vertex Index")

    dimObjectB: PointerProperty(type=Object)

    dimOffset: FloatProperty(name='Dimension Offset',
                    description='Offset for Dimension',
                    default= (0.5),
                    subtype='DISTANCE')

    dimLeaderOffset: FloatProperty(name='Dimension Offset',
                    description='Offset for Dimension',
                    default= (0.05),
                    subtype='DISTANCE')
    
    dimVisibleInView: PointerProperty(type= bpy.types.Camera)

    dimFlip: BoolProperty(name='Flip Dimension',
                    description= 'Flip The Dimension Normal',
                    default=False)

    dimViewPlane: EnumProperty(
                    items=(('99', "None", "None",'EMPTY_AXIS',0),
                           ('XY', "XY Plane", "Optimize Dimension for XY Plane (Plan)",'AXIS_TOP',1),
                           ('YZ', "YZ Plane", "Optimize Dimension for YZ Plane (Elevation)",'AXIS_FRONT',2),
                           ('XZ', "XZ Plane", "Optimize Dimension for XZ Plane (Elevation)",'AXIS_SIDE',3)),
                    name="B end",
                    description="Add arrows to point A")   

    endcapA: EnumProperty(
                    items=(('99', "--", "No Cap"),
                           ('L', "Arrow", "Arrow"),
                           ('T', "Triangle", "Triangle"),
                           ('D', "Dashed", "Dashed")),
                    name="A end",
                    description="Add arrows to point A")

    endcapB: EnumProperty(
                    items=(('99', "--", "No Cap"),
                           ('L', "Arrow", "Arrow"),
                           ('T', "Triangle", "Triangle"),
                           ('D', "Dashed", "Dashed")),
                    name="B end",
                    description="Add arrows to point A")     

    dimRotation:FloatProperty(name='annotationOffset',
                            description='Rotation for Annotation',
                            default= 0.0,
                            subtype='ANGLE')

bpy.utils.register_class(AlignedDimensionProperties)

class AxisDimensionProperties(BaseWithText,PropertyGroup):
    dimPointA: IntProperty(name='dimPointA',
                    description="Dimension Start Vertex Index")

    dimObjectA: PointerProperty(type=Object)

    dimPointB: IntProperty(name='dimPointB',
                    description="Dimension End Vertex Index")

    dimObjectB: PointerProperty(type=Object)

    dimOffset: FloatProperty(name='Dimension Offset',
                    description='Offset for Dimension',
                    default= (0.5),
                    subtype='DISTANCE')

    dimLeaderOffset: FloatProperty(name='Dimension Offset',
                    description='Offset for Dimension',
                    default= (0.05),
                    subtype='DISTANCE')
    
    dimVisibleInView: PointerProperty(type= bpy.types.Camera)

    dimFlip: BoolProperty(name='Flip Dimension',
                    description= 'Flip The Dimension Normal',
                    default=False)

    dimViewPlane: EnumProperty(
                    items=(('99', "None", "None",'EMPTY_AXIS',0),
                           ('XY', "XY Plane", "Optimize Dimension for XY Plane (Plan)",'AXIS_TOP',1),
                           ('YZ', "YZ Plane", "Optimize Dimension for YZ Plane (Elevation)",'AXIS_FRONT',2),
                           ('XZ', "XZ Plane", "Optimize Dimension for XZ Plane (Elevation)",'AXIS_SIDE',3)),
                    name="B end",
                    description="Add arrows to point A")   

    dimAxis: EnumProperty(
                    items=(('X', "X Axis", "Measure only the X Axis"),
                           ('Y', "Y Axis", "Measure only the Y Axis"),
                           ('Z', "Z Axis", "Measure only the Z Axis")),
                    name="Measurement Axis",
                    description="Measurement Axis")   

    endcapA: EnumProperty(
                    items=(('99', "--", "No Cap"),
                           ('L', "Arrow", "Arrow"),
                           ('T', "Triangle", "Triangle"),
                           ('D', "Dashed", "Dashed")),
                    name="A end",
                    description="Add arrows to point A")

    endcapB: EnumProperty(
                    items=(('99', "--", "No Cap"),
                           ('L', "Arrow", "Arrow"),
                           ('T', "Triangle", "Triangle"),
                           ('D', "Dashed", "Dashed")),
                    name="B end",
                    description="Add arrows to point A")     

    dimRotation:FloatProperty(name='annotationOffset',
                            description='Rotation for Annotation',
                            default= 0.0,
                            subtype='ANGLE')

bpy.utils.register_class(AxisDimensionProperties)


class AngleDimensionProperties(BaseWithText,PropertyGroup):
    dimPointA: IntProperty(name='dimPointA',
                    description="Angle Start Vertex Index")

    dimPointB: IntProperty(name='dimPointB',
                    description="Angle Middle Vertex Index")
    
    dimPointC: IntProperty(name='dimPointC',
                    description="Angle End Vertex Index")

    dimVisibleInView: PointerProperty(type= bpy.types.Camera)

    dimRadius: FloatProperty(name='Dimension Radius',
                    description='Radius Dimension',
                    default= (0.05),
                    subtype='DISTANCE')

bpy.utils.register_class(AngleDimensionProperties)


def recalc_dimWrapper_index(self,context):
    dimGen = context.object.DimensionGenerator[0]
    wrappedDimensions = dimGen.wrappedDimensions
    id_aligned = 0
    id_angle = 0
    id_axis = 0
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

# A Wrapper object so multiple dimension types can be
# Shown in the same UI List

class DimensionWrapper(PropertyGroup):
    itemType: EnumProperty(
                items=(('D-ALIGNED', "Aligned Dimension", ""),
                        ('D-ANGLE', "Angle Dimension", ""),
                        ('D-AXIS', "Axisi Dimension", "")),
                name="Dimension Item Type",
                update=recalc_dimWrapper_index)

    itemIndex: IntProperty(name='Dimension Index')

bpy.utils.register_class(DimensionWrapper)


class DimensionContainer(PropertyGroup):
    measureit_arch_num: IntProperty(name='Number of measures', min=0, max=1000, default=0,
                                description='Number total of measureit_arch elements')
    
    active_dimension_index: IntProperty(name="Active Dimension Index")

    show_dimension_settings: BoolProperty(name='Show Dimension Settings', default=False)
    
    # Array of segments
    alignedDimensions: CollectionProperty(type=AlignedDimensionProperties)
    angleDimensions: CollectionProperty(type=AngleDimensionProperties)
    axisDimensions: CollectionProperty(type=AxisDimensionProperties)

    wrappedDimensions: CollectionProperty(type=DimensionWrapper)

bpy.utils.register_class(DimensionContainer)
Object.DimensionGenerator = CollectionProperty(type=DimensionContainer)

class AddAlignedDimensionButton(Operator):
    bl_idname = "measureit_arch.addaligneddimensionbutton"
    bl_label = "Add"
    bl_description = "Add Aligned Dimension (Dimension Properties can be edited in the Object Properties)"
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
            if o.type == "MESH" or o.type == "EMPTY" or o.type == "CAMERA" or o.type == "LIGHT":
                return True
            else:
                return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # get selected
            scene = context.scene
            
            newDimensions = []

            # Edit Context
            if bpy.context.mode == 'EDIT_MESH':
                for mainobject in context.objects_in_mode:
                    mylist = get_smart_selected(mainobject)
                    if len(mylist) < 2:  # if not selected linked vertex
                        mylist = get_selected_vertex(mainobject)
                    if len(mylist) >= 2:
                        #Check Generators
                        if 'DimensionGenerator' not in mainobject:
                            mainobject.DimensionGenerator.add()
                        if 'StyleGenerator' not in scene:
                            scene.StyleGenerator.add()

                        DimGen = mainobject.DimensionGenerator[0]

                        for x in range(0, len(mylist) - 1, 2):
                            if exist_segment(DimGen, mylist[x], mylist[x + 1]) is False:
                                newDimension = DimGen.alignedDimensions.add()
                                newDimension.dimObjectA = mainobject
                                newDimension.dimObjectB = mainobject
                                newDimension.dimPointB = mylist[x]
                                newDimension.dimPointA = mylist[x + 1]
                                newDimension.name = 'Dimension ' + str(len(DimGen.alignedDimensions))
                                newDimensions.append(newDimension)

                                newWrapper = DimGen.wrappedDimensions.add()
                                newWrapper.itemType = 'D-ALIGNED'


                        # redraw
                        recalc_dimWrapper_index(self,context)
                        context.area.tag_redraw()
                    else:
                        self.report({'ERROR'},
                                    "MeasureIt-ARCH: Select at least two vertices for creating measure segment.")
            
            # Object Context
            elif bpy.context.mode == 'OBJECT':
                mainobject = context.object
                if len(context.selected_objects) != 2:
                    self.report({'ERROR'},
                            "MeasureIt-ARCH: Select two objects only, and optionally 1 vertex or 2 vertices "
                            "(one of each object)")
                    return {'FINISHED'}
                
                linkobject = None
                for obj in context.selected_objects:
                    if obj.name != mainobject.name:
                        linkobject = obj

                 # Verify destination vertex
                mylinkvertex = get_selected_vertex(linkobject)
                if len(mylinkvertex) != 1:
                    if len(mylinkvertex) == 0:
                        mylinkvertex.append(9999999)
                    else:
                        self.report({'ERROR'},
                                    "MeasureIt-ARCH: The destination object has more than one vertex selected. "
                                    "Select only 1")
                        return {'FINISHED'}
                # Verify origin vertex
                myobjvertex = get_selected_vertex(mainobject)
                if len(myobjvertex) != 1:
                    if len(myobjvertex) == 0:
                        myobjvertex.append(9999999)
                    else:
                        self.report({'ERROR'},
                                    "MeasureIt-ARCH: The active object has more than one vertex selected. Select only 1")
                        return {'FINISHED'}

                # -------------------------------
                # Add properties
                # -------------------------------
                flag = False
                if 'DimensionGenerator' not in mainobject:
                    mainobject.DimensionGenerator.add()

                DimGen = mainobject.DimensionGenerator[0]

                # Create all array elements
                newDimension = DimGen.alignedDimensions.add()

                newDimension.dimObjectA = mainobject
                newDimension.dimPointA = myobjvertex[0]
                newDimension.dimObjectB = linkobject
                newDimension.dimPointB = mylinkvertex[0]
                newDimension.name = 'Dimension ' + str(len(DimGen.alignedDimensions))
                newDimensions.append(newDimension)
                newWrapper = DimGen.wrappedDimensions.add()
                newWrapper.itemType = 'D-ALIGNED'
                recalc_dimWrapper_index(self,context)

                context.area.tag_redraw()

            # Set Common Values
            for newDimension in newDimensions:
                newDimension.itemType = 'D-ALIGNED'
                newDimension.style = scene.measureit_arch_default_dimension_style
                if scene.measureit_arch_default_dimension_style is not '':
                    newDimension.uses_style = True
                else:
                    newDimension.uses_style = False
                
                newDimension.lineWeight = 1
                if 'camera' in scene:
                    newDimension.dimVisibleInView = scene.camera.data
                newDimension.dimViewPlane = scene.viewPlane

                newDimension.endcapA= scene.measureit_arch_glarrow_a
                newDimension.endcapB = scene.measureit_arch_glarrow_b
                newDimension.endcapSize= 8
                # color
                newDimension.color = scene.measureit_arch_default_color
                # dist
                newDimension.dimOffset = 0.3
                newDimension.dimLeaderOffset = 0.05
                # text
                newDimension.text = scene.measureit_arch_gl_txt
                newDimension.fontSize = 24
                newDimension.textResolution = 150
                newDimension.textAlignment = 'C'
                # Sum group
                DimGen.measureit_arch_num += 1 
            return{'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

            return {'CANCELLED'}

class AddAxisDimensionButton(Operator):
    bl_idname = "measureit_arch.addaxisdimensionbutton"
    bl_label = "Add"
    bl_description = "Add Single Axis Dimension (Dimension Properties can be edited in the Object Properties)"
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
            if o.type == "MESH" or o.type == "EMPTY" or o.type == "CAMERA" or o.type == "LIGHT":
                return True
            else:
                return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # get selected
            scene = context.scene
            
            newDimensions = []

            # Edit Context
            if bpy.context.mode == 'EDIT_MESH':
                for mainobject in context.objects_in_mode:
                    mylist = get_smart_selected(mainobject)
                    if len(mylist) < 2:  # if not selected linked vertex
                        mylist = get_selected_vertex(mainobject)
                    if len(mylist) >= 2:
                        #Check Generators
                        if 'DimensionGenerator' not in mainobject:
                            mainobject.DimensionGenerator.add()
                        if 'StyleGenerator' not in scene:
                            scene.StyleGenerator.add()

                        DimGen = mainobject.DimensionGenerator[0]

                        for x in range(0, len(mylist) - 1, 2):
                            if exist_segment(DimGen, mylist[x], mylist[x + 1]) is False:
                                newDimension = DimGen.axisDimensions.add()
                                newDimension.dimObjectA = mainobject
                                newDimension.dimObjectB = mainobject
                                newDimension.dimPointB = mylist[x]
                                newDimension.dimPointA = mylist[x + 1]
                                newDimension.name = 'Axis ' + str(len(DimGen.axisDimensions))
                                newDimensions.append(newDimension)

                                newWrapper = DimGen.wrappedDimensions.add()
                                newWrapper.itemType = 'D-AXIS'


                        # redraw
                        recalc_dimWrapper_index(self,context)
                        context.area.tag_redraw()
                    else:
                        self.report({'ERROR'},
                                    "MeasureIt-ARCH: Select at least two vertices for creating measure segment.")
            
            # Object Context
            elif bpy.context.mode == 'OBJECT':
                mainobject = context.object
                if len(context.selected_objects) != 2:
                    self.report({'ERROR'},
                            "MeasureIt-ARCH: Select two objects only, and optionally 1 vertex or 2 vertices "
                            "(one of each object)")
                    return {'FINISHED'}
                
                linkobject = None
                for obj in context.selected_objects:
                    if obj.name != mainobject.name:
                        linkobject = obj

                 # Verify destination vertex
                mylinkvertex = get_selected_vertex(linkobject)
                if len(mylinkvertex) != 1:
                    if len(mylinkvertex) == 0:
                        mylinkvertex.append(9999999)
                    else:
                        self.report({'ERROR'},
                                    "MeasureIt-ARCH: The destination object has more than one vertex selected. "
                                    "Select only 1")
                        return {'FINISHED'}
                # Verify origin vertex
                myobjvertex = get_selected_vertex(mainobject)
                if len(myobjvertex) != 1:
                    if len(myobjvertex) == 0:
                        myobjvertex.append(9999999)
                    else:
                        self.report({'ERROR'},
                                    "MeasureIt-ARCH: The active object has more than one vertex selected. Select only 1")
                        return {'FINISHED'}

                # -------------------------------
                # Add properties
                # -------------------------------
                flag = False
                if 'DimensionGenerator' not in mainobject:
                    mainobject.DimensionGenerator.add()

                DimGen = mainobject.DimensionGenerator[0]

                # Create all array elements
                newDimension = DimGen.axisDimensions.add()

                newDimension.dimObjectA = mainobject
                newDimension.dimPointA = myobjvertex[0]
                newDimension.dimObjectB = linkobject
                newDimension.dimPointB = mylinkvertex[0]
                newDimension.name = 'Axis ' + str(len(DimGen.axisDimensions))
                newDimensions.append(newDimension)
                newWrapper = DimGen.wrappedDimensions.add()
                newWrapper.itemType = 'D-AXIS'
                recalc_dimWrapper_index(self,context)

                context.area.tag_redraw()

            # Set Common Values
            for newDimension in newDimensions:
                newDimension.itemType = 'D-AXIS'
                newDimension.style = scene.measureit_arch_default_dimension_style
                if scene.measureit_arch_default_dimension_style is not '':
                    newDimension.uses_style = True
                else:
                    newDimension.uses_style = False
                
                newDimension.lineWeight = 1
                if 'camera' in scene:
                    newDimension.dimVisibleInView = scene.camera.data
                newDimension.dimViewPlane = scene.viewPlane

                newDimension.endcapA= scene.measureit_arch_glarrow_a
                newDimension.endcapB = scene.measureit_arch_glarrow_b
                newDimension.endcapSize= 8
                newDimension.dimAxis = scene.measureit_arch_dim_axis
                # color
                newDimension.color = scene.measureit_arch_default_color
                # dist
                newDimension.dimOffset = 0.3
                newDimension.dimLeaderOffset = 0.05
                # text
                newDimension.text = scene.measureit_arch_gl_txt
                newDimension.fontSize = 24
                newDimension.textResolution = 150
                newDimension.textAlignment = 'C'
                # Sum group
                DimGen.measureit_arch_num += 1 
            return{'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

            return {'CANCELLED'}

class AddAreaButton(Operator): # LEGACY
    bl_idname = "measureit_arch.addareabutton"
    bl_label = "Area"
    bl_description = "(EDITMODE only) Add a new measure for area (select 1 o more faces)"
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
            scene = context.scene
            mainobject = context.object
            mylist = get_selected_faces(mainobject)
            if len(mylist) >= 1:
                if 'DimensionGenerator' not in mainobject:
                    mainobject.DimensionGenerator.add()

                mp = mainobject.DimensionGenerator[0]
                mp.measureit_arch_segments.add()
                ms = mp.measureit_arch_segments[mp.measureit_arch_num]
                ms.gltype = 20

                f = -1
                for face in mylist:
                    # Create array elements
                    ms.measureit_arch_faces.add()
                    f += 1
                    # Set values
                    mf = ms.measureit_arch_faces[f]
                    mf.glface = f
                    i = 0
                    for v in face:
                        mf.measureit_arch_index.add()
                        mi = mf.measureit_arch_index[i]
                        mi.glidx = v
                        i += 1

                # color
                rgb = scene.measureit_arch_default_color
                ms.glcolor = (rgb[0], rgb[1], rgb[2], 0.4)
                # dist
                ms.glspace = scene.measureit_arch_hint_space
                # text
                ms.gltxt = scene.measureit_arch_gl_txt
                ms.glfont_size = scene.measureit_arch_font_size
                ms.glfont_align = scene.measureit_arch_font_align
                ms.glfont_rotat = scene.measureit_arch_font_rotation
                # Sum group
                ms.gltot = scene.measureit_arch_sum
                # Add index
                mp.measureit_arch_num += 1
                # redraw
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: Select at least one face for creating area measure. ")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}

    bl_idname = "measureit_arch.addsegmentortobutton"
    bl_label = "Add"
    bl_description = "(EDITMODE only) Add a new measure segment from vertex to object origin for one " \
                     "axis (select 1 vertex)"
    bl_category = 'MeasureitArch'
    tag = IntProperty()

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
            scene = context.scene
            mainobject = context.object
            mylist = get_smart_selected(mainobject)

            if len(mylist) < 1:  # if not selected linked vertex
                mylist = get_selected_vertex(mainobject)

            if len(mylist) >= 1:
                if 'DimensionGenerator' not in mainobject:
                    mainobject.DimensionGenerator.add()

                mp = mainobject.DimensionGenerator[0]
                for x in range(0, len(mylist)):
                    # -----------------------
                    # Only if not exist
                    # -----------------------
                    if exist_segment(mp, mylist[x], mylist[x], 12 + int(self.tag)) is False:
                        # Create all array elements
                        for cont in range(len(mp.measureit_arch_segments) - 1, mp.measureit_arch_num):
                            mp.measureit_arch_segments.add()

                        # Set values
                        ms = mp.measureit_arch_segments[mp.measureit_arch_num]
                        ms.gltype = 12 + int(self.tag)
                        ms.glpointa = mylist[x]
                        ms.glpointb = mylist[x]
                        ms.glarrow_a = scene.measureit_arch_glarrow_a
                        ms.glarrow_b = scene.measureit_arch_glarrow_b
                        ms.glarrow_s = scene.measureit_arch_glarrow_s
                        # color
                        ms.glcolor = scene.measureit_arch_default_color
                        # dist
                        ms.glspace = scene.measureit_arch_hint_space
                        # text
                        ms.gltxt = scene.measureit_arch_gl_txt
                        ms.glfont_size = scene.measureit_arch_font_size
                        ms.glfont_align = scene.measureit_arch_font_align
                        ms.glfont_rotat = scene.measureit_arch_font_rotation
                        # Sum group
                        ms.gltot = scene.measureit_arch_sum
                        # Add index
                        mp.measureit_arch_num += 1

                # redraw
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: Select at least one vertex for creating measure segment.")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}

class AddAngleButton(Operator):
    bl_idname = "measureit_arch.addanglebutton"
    bl_label = "Angle"
    bl_description = "(EDITMODE only) Add a new angle measure (select 3 vertices, 2nd is angle vertex)"
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
            scene = context.scene
            mainobject = context.object
            mylist = get_selected_vertex_history(mainobject)
            if len(mylist) == 3:
                #Check Generators
                if 'DimensionGenerator' not in mainobject:
                    mainobject.DimensionGenerator.add()
                if 'StyleGenerator' not in scene:
                    scene.StyleGenerator.add()
                
                DimGen = mainobject.DimensionGenerator[0]

                newDimension = DimGen.angleDimensions.add()
                newDimension.itemType = 'D-ANGLE'
                newDimension.name = 'Angle ' + str(len(DimGen.angleDimensions))
                newWrapper = DimGen.wrappedDimensions.add()
                newWrapper.itemType = 'D-ANGLE'
                recalc_dimWrapper_index(self,context)

                newDimension.dimVisibleInView = scene.camera.data

                newDimension.style = scene.measureit_arch_default_dimension_style
                if scene.measureit_arch_default_dimension_style is not '':
                    newDimension.uses_style = True
                else:
                    newDimension.uses_style = False

                newDimension.dimPointA = mylist[0]
                newDimension.dimPointB = mylist[1]
                newDimension.dimPointC = mylist[2]
                newDimension.dimRadius = 0.25
                newDimension.lineWeight = 1
                newDimension.color = scene.measureit_arch_default_color
                
                # text
                newDimension.text = scene.measureit_arch_gl_txt
                newDimension.fontSize = 7
                newDimension.textResolution = 72
                newDimension.textAlignment = 'C'
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: Select three vertices for creating angle measure")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}

class AddArcButton(Operator): #LEGACY
    bl_idname = "measureit_arch.addarcbutton"
    bl_label = "Angle"
    bl_description = "(EDITMODE only) Add a new arc measure (select 3 vertices of the arc," \
                     " vertices 1st and 3rd are arc extremes)"
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
            scene = context.scene
            mainobject = context.object
            mylist = get_selected_vertex_history(mainobject)
            if len(mylist) == 3:
                if 'DimensionGenerator' not in mainobject:
                    mainobject.DimensionGenerator.add()

                mp = mainobject.DimensionGenerator[0]
                # -----------------------
                # Only if not exist
                # -----------------------
                if exist_segment(mp, mylist[0], mylist[1], 11, mylist[2]) is False:
                    # Create all array elements
                    for cont in range(len(mp.measureit_arch_segments) - 1, mp.measureit_arch_num):
                        mp.measureit_arch_segments.add()

                    # Set values
                    ms = mp.measureit_arch_segments[mp.measureit_arch_num]
                    ms.gltype = 11
                    ms.glpointa = mylist[0]
                    ms.glpointb = mylist[1]
                    ms.glpointc = mylist[2]
                    ms.glarrow_a = scene.measureit_arch_glarrow_a
                    ms.glarrow_b = scene.measureit_arch_glarrow_b
                    ms.glarrow_s = scene.measureit_arch_glarrow_s
                    # color
                    ms.glcolor = scene.measureit_arch_default_color
                    # dist
                    ms.glspace = scene.measureit_arch_hint_space
                    # text
                    ms.gltxt = scene.measureit_arch_gl_txt
                    ms.glfont_size = scene.measureit_arch_font_size
                    ms.glfont_align = scene.measureit_arch_font_align
                    ms.glfont_rotat = scene.measureit_arch_font_rotation
                    # Add index
                    mp.measureit_arch_num += 1

                # redraw
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: Select three vertices for creating arc measure")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}

    bl_idname = "measureit_arch.addoriginbutton"
    bl_label = "Add"
    bl_description = "(OBJECT mode only) Add a new measure to origin (select object and optionally 1 vertex)"
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
            if o.type == "MESH" or o.type == "EMPTY" or o.type == "CAMERA" or o.type == "LAMP":
                if bpy.context.mode == 'OBJECT':
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
            scene = context.scene
            mainobject = context.object
            mylist = get_selected_vertex(mainobject)
            if 'DimensionGenerator' not in mainobject:
                mainobject.DimensionGenerator.add()

            mp = mainobject.DimensionGenerator[0]
            # Create all array elements
            for cont in range(len(mp.measureit_arch_segments) - 1, mp.measureit_arch_num):
                mp.measureit_arch_segments.add()

            # -----------------------
            # Set values
            # -----------------------
            ms = mp.measureit_arch_segments[mp.measureit_arch_num]
            flag = False
            if len(mylist) > 0:
                if len(mylist) == 1:
                    if exist_segment(mp, mylist[0], mylist[0], 6) is False:  # Both equal
                        flag = True
                        # Vertex to origin
                        ms.gltype = 6
                        ms.glpointa = mylist[0]
                        ms.glpointb = mylist[0]
                else:
                    self.report({'ERROR'},
                                "MeasureIt-ARCH: Enter in EDITMODE and select one vertex only for creating "
                                "measure from vertex to origin")
                    return {'FINISHED'}
            else:
                # Object to origin
                if exist_segment(mp, 0, 0, 7) is False:  # Both equal
                    flag = True
                    ms.gltype = 7
                    ms.glpointa = 0
                    ms.glpointb = 0
            # ------------------
            # only if created
            # ------------------
            if flag is True:
                ms.glarrow_a = scene.measureit_arch_glarrow_a
                ms.glarrow_b = scene.measureit_arch_glarrow_b
                ms.glarrow_s = scene.measureit_arch_glarrow_s
                # color
                ms.glcolor = scene.measureit_arch_default_color
                # dist
                ms.glspace = scene.measureit_arch_hint_space
                # text
                ms.gltxt = scene.measureit_arch_gl_txt
                ms.glfont_size = scene.measureit_arch_font_size
                ms.glfont_align = scene.measureit_arch_font_align
                ms.glfont_rotat = scene.measureit_arch_font_rotation
                # Add index
                mp.measureit_arch_num += 1

            # redraw
            context.area.tag_redraw()

            return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}

    bl_idname = "measureit_arch.addnotebutton"
    bl_label = "Note"
    bl_description = "(OBJECT mode only) Add a new note"
    bl_category = 'MeasureitArch'
    tag= IntProperty()

    # ------------------------------
    # Poll
    # ------------------------------
    # noinspection PyUnusedLocal
    @classmethod
    def poll(cls, context):
        if bpy.context.mode == 'OBJECT':
            return True
        else:
            return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            bpy.ops.object.empty_add(type='PLAIN_AXES')
            myempty = bpy.data.objects[bpy.context.active_object.name]
            myempty.location = bpy.context.scene.cursor_location
            myempty.empty_display_size = 0.01
            myempty.name = "Annotation"
            # Add properties
            scene = context.scene
            mainobject = myempty
            if 'DimensionGenerator' not in mainobject:
                mainobject.DimensionGenerator.add()

            mp = mainobject.DimensionGenerator[0]
            # Create all array elements
            for cont in range(len(mp.measureit_arch_segments) - 1, mp.measureit_arch_num):
                mp.measureit_arch_segments.add()

            # Set values
            ms = mp.measureit_arch_segments[mp.measureit_arch_num]
            ms.gltype = 10
            ms.glpointa = 0
            ms.glpointb = 0  # Equal
            # color
            ms.glcolor = scene.measureit_arch_default_color
            # dist
            ms.glspace = scene.measureit_arch_hint_space
            # text
            ms.gltxt = scene.measureit_arch_gl_txt
            ms.glfont_size = scene.measureit_arch_font_size
            ms.glfont_align = scene.measureit_arch_font_align
            ms.glfont_rotat = scene.measureit_arch_font_rotation
            # Add index
            mp.measureit_arch_num += 1

            # redraw
            context.area.tag_redraw()
            return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}

class M_ARCH_UL_dimension_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        dimGen = context.object.DimensionGenerator[0]
        angleDim = dimGen.angleDimensions
        alignedDim = dimGen.alignedDimensions
        axisDim =  dimGen.axisDimensions

        scene = bpy.context.scene
        hasGen = False
        if 'StyleGenerator' in scene:
            StyleGen = scene.StyleGenerator[0]
            hasGen = True
    
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.use_property_decorate = False
            # Get correct item and icon
            if item.itemType == 'D-ALIGNED':
                dim = alignedDim[item.itemIndex]
                nameIcon = 'DRIVER_DISTANCE'
    
            elif item.itemType == 'D-ANGLE':
                dim = angleDim[item.itemIndex]
                nameIcon = 'DRIVER_ROTATIONAL_DIFFERENCE'

            elif item.itemType == 'D-AXIS':
                dim = axisDim[item.itemIndex]
                nameIcon = 'TRACKING_FORWARDS_SINGLE'


            row = layout.row(align=True)
            subrow = row.row()

            subrow.prop(dim, "name", text="",emboss=False,icon=nameIcon)

            if dim.visible: visIcon = 'HIDE_OFF'
            else: visIcon = 'HIDE_ON'
            
            if dim.uses_style: styleIcon = 'LINKED'
            else: styleIcon = 'UNLINKED'
            
            if not dim.uses_style:
                subrow = row.row()
                subrow.scale_x = 0.6
                subrow.prop(dim, 'color', text="" )
            else:
                row.prop_search(dim,'style', StyleGen,'alignedDimensions',text="", icon='COLOR')
                row.separator()

            subrow = row.row(align=True)
            if item.itemType == 'D-ALIGNED' or item.itemType == 'D-AXIS':
                if dim.dimFlip: flipIcon ='BACK'
                else: flipIcon = 'FORWARD'
                subrow.prop(dim, 'dimFlip',text='',toggle=True, icon=flipIcon,emboss=False)
            
            if hasGen:
                row = row.row(align=True)
                row.prop(dim, 'uses_style', text="",toggle=True, icon=styleIcon,emboss=False)
            
            row.prop(dim, "visible", text="", icon = visIcon,emboss=False)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')

class OBJECT_PT_UIDimensions(Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "MeasureIt-ARCH Dimensions"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        obj = context.object
        if 'DimensionGenerator' in context.object:     
            scene = context.scene
            dimGen = obj.DimensionGenerator[0]

            row = layout.row()
            
            # Draw The UI List
            row.template_list("M_ARCH_UL_dimension_list", "", dimGen, "wrappedDimensions", dimGen, "active_dimension_index",rows=2, type='DEFAULT')
            
            # Operators Next to List
            col = row.column(align=True)
            op = col.operator("measureit_arch.listdeletepropbutton", text="", icon="X")
            op.tag = dimGen.active_dimension_index  # saves internal data
            op.is_style = False
            op.item_type = 'D'

            col.separator()
            col.menu("OBJECT_MT_dimension_menu", icon='DOWNARROW_HLT', text="")

            # Settings Below List
            if len(dimGen.wrappedDimensions) > 0 and  dimGen.active_dimension_index < len(dimGen.wrappedDimensions):
                activeWrapperItem = dimGen.wrappedDimensions[dimGen.active_dimension_index ]

                if activeWrapperItem.itemType == 'D-ALIGNED':
                    item = dimGen.alignedDimensions[activeWrapperItem.itemIndex]
                if activeWrapperItem.itemType == 'D-ANGLE':
                    item = dimGen.angleDimensions[activeWrapperItem.itemIndex]
                if activeWrapperItem.itemType == 'D-AXIS':
                    item = dimGen.axisDimensions[activeWrapperItem.itemIndex]

                if dimGen.show_dimension_settings: settingsIcon = 'DISCLOSURE_TRI_DOWN'
                else: settingsIcon = 'DISCLOSURE_TRI_RIGHT'
                
                box = layout.box()
                col = box.column()
                row = col.row()
                row.prop(dimGen, 'show_dimension_settings', text="", icon=settingsIcon,emboss=False)

                row.label(text= item.name + ' Settings:')
                if dimGen.show_dimension_settings:
                    if activeWrapperItem.itemType == 'D-ALIGNED':
                        draw_aligned_dimension_settings(item,box)
                    if activeWrapperItem.itemType == 'D-ANGLE':
                        draw_angle_dimension_settings(item,box)
                    if activeWrapperItem.itemType == 'D-AXIS':
                        draw_axis_dimension_settings(item,box)

class OBJECT_MT_dimension_menu(bpy.types.Menu):
    bl_label = "Custom Menu"

    def draw(self,context):
        layout = self.layout

        delOp = layout.operator("measureit_arch.deleteallitemsbutton", text="Delete All Dimensions", icon="X")
        delOp.is_style = False
        delOp.item_type = 'D'

def draw_aligned_dimension_settings(dim,layout):
    col = layout.column()    

    if dim.uses_style is False:
        split = layout.split(factor=0.485)
        col = split.column()
        col.alignment ='RIGHT'
        col.label(text='Font')
        col = split.column()

        col.template_ID(dim, "font", open="font.open", unlink="font.unlink")

        col = layout.column(align=True)
        col.prop(dim,'dimViewPlane', text='View Plane')
    else:
        col.prop(dim,'dimViewPlane', text='View Plane Overide')

    if dim.uses_style is False:
        col.prop_search(dim,'dimVisibleInView', bpy.data, 'cameras',text='Visible In View')
        col.prop(dim,'lineWeight',text='Line Weight')

    col = layout.column(align=True)
    col.prop(dim,'dimOffset',text='Distance')
    col.prop(dim,'dimLeaderOffset',text='Offset')
    col.prop(dim, 'dimRotation', text='Rotation')
    
    if dim.uses_style is False:
        col = layout.column(align=True)
        col.prop(dim,'fontSize',text='Font Size')
        col.prop(dim,'textResolution',text='Resolution')
        col.prop(dim,'textAlignment',text='Alignment')
        #col.prop(dim,'textPosition',text='Position')

        col = layout.column(align=True)
        col.prop(dim,'endcapA', text='Arrow Start')
        col.prop(dim,'endcapB', text='End')
        col.prop(dim,'endcapSize', text='Arrow Size')
        col.prop(dim,'endcapArrowAngle', text='Arrow Angle')


    col.prop(dim,'textFlippedX',text='Flip Text X')
    col.prop(dim,'textFlippedY',text='Flip Text Y')

def draw_axis_dimension_settings(dim,layout):
    col = layout.column()    

    if dim.uses_style is False:
        split = layout.split(factor=0.485)
        col = split.column()
        col.alignment ='RIGHT'
        col.label(text='Font')
        col = split.column()

        col.template_ID(dim, "font", open="font.open", unlink="font.unlink")

        col = layout.column(align=True)
        col.prop(dim,'dimViewPlane', text='View Plane')
    else:
        col.prop(dim,'dimViewPlane', text='View Plane Overide')
    col.prop(dim,'dimAxis', text='Measurement Axis')
    
    if dim.uses_style is False:
        col.prop_search(dim,'dimVisibleInView', bpy.data, 'cameras',text='Visible In View')
        col.prop(dim,'lineWeight',text='Line Weight')

    col = layout.column(align=True)
    col.prop(dim,'dimOffset',text='Distance')
    col.prop(dim,'dimLeaderOffset',text='Offset')
    col.prop(dim, 'dimRotation', text='Rotation')
    
    if dim.uses_style is False:
        col = layout.column(align=True)
        col.prop(dim,'fontSize',text='Font Size')
        col.prop(dim,'textResolution',text='Resolution')
        col.prop(dim,'textAlignment',text='Alignment')
        #col.prop(dim,'textPosition',text='Position')

        col = layout.column(align=True)
        col.prop(dim,'endcapA', text='Arrow Start')
        col.prop(dim,'endcapB', text='End')
        col.prop(dim,'endcapSize', text='Arrow Size')
        col.prop(dim,'endcapArrowAngle', text='Arrow Angle')

    col.prop(dim,'textFlippedX',text='Flip Text X')
    col.prop(dim,'textFlippedY',text='Flip Text Y')

def draw_angle_dimension_settings(dim,layout):
        col = layout.column()
        if dim.uses_style is False:
            split = layout.split(factor=0.485)
            col = split.column()
            col.alignment ='RIGHT'
            col.label(text='Font')
            col = split.column()

            col.template_ID(dim, "font", open="font.open", unlink="font.unlink")

            col = layout.column()

        col.prop_search(dim,'dimVisibleInView', bpy.data, 'cameras',text='Visible In View')
        if dim.uses_style is False:
            col = layout.column(align=True)
            col.prop(dim,'lineWeight',text='Line Weight')

        col.prop(dim,'dimRadius',text='Radius')

        if dim.uses_style is False:
            col = layout.column(align=True)
            col.prop(dim,'fontSize',text='Font Size')
            col.prop(dim,'textResolution',text='Resolution')
            col.prop(dim,'textAlignment',text='Alignment')
            #col.prop(dim,'textPosition',text='Position')

        col = layout.column(align=True)
        col.prop(dim,'textFlippedX',text='Flip Text X')
        col.prop(dim,'textFlippedY',text='Flip Text Y')