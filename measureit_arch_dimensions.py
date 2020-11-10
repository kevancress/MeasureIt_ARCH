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
from .measureit_arch_main import OBJECT_PT_Panel
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D, UIList, Collection
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, BoolProperty, StringProperty, \
                      FloatProperty, EnumProperty, PointerProperty, BoolVectorProperty
from .measureit_arch_main import *
from .measureit_arch_baseclass import BaseWithText , BaseDim, recalc_dimWrapper_index
from mathutils import Vector, Matrix, Euler, Quaternion
import math
import random
# ------------------------------------------------------------------
# Define property group class for measureit_arch faces index
# ------------------------------------------------------------------


def update_active_dim(self,context):
    Generator = context.object.DimensionGenerator
    activeWraper = Generator.wrapper[Generator.active_index]

    for key in Generator.keys():
        item = Generator.path_resolve(key)
        if 'collection' in str(item):
            typeContainer = item
            for item in typeContainer:
                item.is_active = False
    
    activeItem = eval('Generator.' + activeWraper.itemType + '[activeWraper.itemIndex]')
    activeItem.is_active = True
    

class AreaDimensionProperties(BaseDim,PropertyGroup):
    
    gen_group: StringProperty(name="Generator Group",
        description="group in the generator - api property",
        default="areaDimensions",)

    dimTextPos: FloatVectorProperty(name='Text Position',
                            description='Offset for Area Dimension Text',
                            default= (0,0,0),
                            subtype= 'TRANSLATION')

    originFaceIdx: IntProperty(name = 'Origin Face',
                            description='The face whos normal and center are used for text placement',)
    
    showFill: BoolProperty(name='Show Fill')

    showOutline: BoolProperty(name='Show Outline')

    fillAlpha: FloatProperty(name='Fill',
                    min=0,
                    soft_max=1.0,
                    max=1,
                    default=0.5,
                    subtype='FACTOR')

    fillColor: FloatVectorProperty(name="Color",
                description="Color for the Item",
                default= (0.0,0.0,0.0, 1.0),
                min=0,
                max=1,
                subtype='COLOR',
                size=4)

bpy.utils.register_class(AreaDimensionProperties)

class AlignedDimensionProperties(BaseDim, PropertyGroup):

    gen_group: StringProperty(name="Generator Group",
        description="group in the generator - api property",
        default="alignedDimensions",)

    dimObjectA: PointerProperty(type=Object)

    dimObjectB: PointerProperty(type=Object) 

bpy.utils.register_class(AlignedDimensionProperties)


class AxisDimensionProperties(BaseDim, PropertyGroup):

    gen_group: StringProperty(name="Generator Group",
        description="group in the generator - api property",
        default="axisDimensions",)

    dimObjectA: PointerProperty(type=Object)

    dimObjectB: PointerProperty(type=Object)

    dimAxisObject: PointerProperty(type=Object)

    dimAxis: EnumProperty(
                    items=(('X', "X Axis", "Measure only the X Axis"),
                           ('Y', "Y Axis", "Measure only the Y Axis"),
                           ('Z', "Z Axis", "Measure only the Z Axis")),
                    name="Measurement Axis",
                    description="Measurement Axis")       

bpy.utils.register_class(AxisDimensionProperties)


class BoundsDimensionProperties(BaseDim, PropertyGroup):
    gen_group: StringProperty(name="Generator Group",
        description="group in the generator - api property",
        default="boundsDimensions",)

    drawAxis: BoolVectorProperty(name= "Draw Axis",
                description= "Axis to Dimension for Bounding Box",
                default= (False,False,False),
                subtype= 'XYZ')

    dimCollection: PointerProperty(type=Collection)

    calcAxisAligned: BoolProperty()

bpy.utils.register_class(BoundsDimensionProperties)
    

class ArcDimensionProperties(BaseDim, PropertyGroup):
    gen_group: StringProperty(name="Generator Group",
        description="group in the generator - api property",
        default="arcDimensions",)

    dimPointC: IntProperty(name='dimPointC',
                    description="Angle End Vertex Index")

    arcCenter: FloatVectorProperty(name='Arc Center')

    showLength: BoolProperty(name='Show Arc Length',
                    description='Displays the Arc Length Measurement',
                    default = True)

    showRadius: BoolProperty(name='Show Arc Radius',
                    description='Displays the Arc Radius and Center',
                    default = True)

    displayAsAngle: BoolProperty(name='Display Arc Length as Angle',
                    description='Display the Arc Length as the angle between the two extreems',
                    default = False)

    endcapC: EnumProperty(
                items=(('99', "--", "No Cap"),
                        ('L', "Arrow", "Arrow"),
                        ('T', "Triangle", "Triangle")),
                default ='T',
                name="C end",
                description="Add arrows to Radius Leader")
   
bpy.utils.register_class(ArcDimensionProperties)



class AngleDimensionProperties(BaseDim, PropertyGroup):
    gen_group: StringProperty(name="Generator Group",
        description="group in the generator - api property",
        default="angleDimensions",)

    dimPointC: IntProperty(name='dimPointC',
                    description="Angle End Vertex Index")

    dimRadius: FloatProperty(name='Dimension Radius',
                    description='Radius Dimension',
                    default= (0.05),
                    subtype='DISTANCE')

    reflexAngle: BoolProperty(name='Show Reflex Angle',
                    description='Displays the Reflex Angle (Greater then 180 Degrees)',
                    default = False)

bpy.utils.register_class(AngleDimensionProperties)


# A Wrapper object so multiple dimension types can be
# Shown in the same UI List

class DimensionWrapper(PropertyGroup):
    itemType: EnumProperty(
                items=(('alignedDimensions', "Aligned Dimension", ""),
                        ('angleDimensions', "Angle Dimension", ""),
                        ('axisDimensions', "Axis Dimension", ""),
                        ('boundsDimensions', "Bounding Box Dimension",""),
                        ('arcDimensions',"Arc Dimension",""),
                        ('areaDimensions',"Area Dimension","")),
                name="Dimension Item Type",
                update=recalc_dimWrapper_index)

    itemIndex: IntProperty(name='Dimension Index')

bpy.utils.register_class(DimensionWrapper)


class DimensionContainer(PropertyGroup):
    measureit_arch_num: IntProperty(name='Number of measures', min=0, max=1000, default=0,
                                description='Number total of measureit_arch elements')
    active_index: IntProperty(name="Active Dimension Index",
                                update= update_active_dim)
    show_dimension_settings: BoolProperty(name='Show Dimension Settings', default=False)
    
    # Collections of each dimension property
    alignedDimensions: CollectionProperty(type=AlignedDimensionProperties)
    angleDimensions: CollectionProperty(type=AngleDimensionProperties)
    axisDimensions: CollectionProperty(type=AxisDimensionProperties)
    boundsDimensions: CollectionProperty(type=BoundsDimensionProperties)
    arcDimensions: CollectionProperty(type=ArcDimensionProperties)
    areaDimensions: CollectionProperty(type=AreaDimensionProperties)


    # Collection of Wrapped dimensions for list UI display
    wrapper: CollectionProperty(type=DimensionWrapper)

bpy.utils.register_class(DimensionContainer)
Object.DimensionGenerator = PointerProperty(type=DimensionContainer)


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
            sceneProps = scene.MeasureItArchProps
            
            newDimensions = []

            pointList, warningStr = get_smart_selected()

            if warningStr != '':
                self.report({'ERROR'},warningStr)

            for idx in range(0, len(pointList) - 1, 2):
                p1 = pointList[idx]
                mainObj = p1['obj']

                # Try To get the next point
                # If it doesn't exist, we're done with the loop
                try:
                    p2 = pointList[idx+1]
                except IndexError:
                    break
                
                # Note: We won't need this try except block for v0.5
                
                DimGen = mainObj.DimensionGenerator


                alignedDims = DimGen.alignedDimensions
                
                newDimension = alignedDims.add()

                newDimension.dimObjectA = p1['obj']
                newDimension.dimObjectB = p2['obj']
                
                newDimension.dimPointA = p1['vert']
                newDimension.dimPointB = p2['vert']

                newDimension.name = 'Dimension ' + str(len(DimGen.alignedDimensions))
                newDimensions.append(newDimension)

                newWrapper = DimGen.wrapper.add()
                newWrapper.itemType = 'alignedDimensions'
                recalc_dimWrapper_index(self,context)
                newDimensions.append(newDimension)
                context.area.tag_redraw()
                idx += 1

            # Set Common Values
            for newDimension in newDimensions:
                newDimension.itemType = 'alignedDimensions'
                newDimension.style = sceneProps.default_dimension_style
                if sceneProps.default_dimension_style is not '':
                    newDimension.uses_style = True
                else:
                    newDimension.uses_style = False
                
                newDimension.lineWeight = 1
                if 'camera' in scene:
                    newDimension.visibleInView = scene.camera.data
                newDimension.dimViewPlane = sceneProps.viewPlane

                # text
                newDimension.textAlignment = 'C'

                DimGen.measureit_arch_num += 1 
            return{'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

            return {'CANCELLED'}

class AddBoundingDimensionButton(Operator):
    bl_idname = "measureit_arch.addboundingdimensionbutton"
    bl_label = "Bounding"
    bl_description = "Add a Bounding Box Dimension (Dimension Properties can be edited in the Object Properties)"
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
            sceneProps = scene.MeasureItArchProps
        
            newDimensions = []

            # Object Context
            if bpy.context.mode == 'OBJECT':
                mainobject = context.object
                # Check Generators

                # Basically I dont need to do anything here, I want to handle the measureing and the selection of which bounding box
                # verts to anchor to in the draw method, so that the most visible verts can be selected depending on the current view.
                # all we need to do is to create a  Bounds dimension and set its defualt props. We do the tricky part in the draw.

                # Add Bounds Dim with Axis
                DimGen = mainobject.DimensionGenerator
                newBoundsDimension = DimGen.boundsDimensions.add()

                newBoundsDimension.name = 'Bounding Box Dimension'
                newBoundsDimension.drawAxis[0] = sceneProps.bound_x
                newBoundsDimension.drawAxis[1] = sceneProps.bound_y
                newBoundsDimension.drawAxis[2] = sceneProps.bound_z
                newBoundsDimension.textAlignment = 'C'

                #Add Text Field for each Axis
                newBoundsDimension.textFields.add()
                newBoundsDimension.textFields.add()
                newBoundsDimension.textFields.add()

                newBoundsDimension.style = sceneProps.default_dimension_style
                if sceneProps.default_dimension_style is not '':
                    newBoundsDimension.uses_style = True
                else:
                    newBoundsDimension.uses_style = False


                newWrapper = DimGen.wrapper.add()
                newWrapper.itemType = 'boundsDimensions'


                # redraw
                recalc_dimWrapper_index(self,context)
                context.area.tag_redraw()

            
                
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
            sceneProps = scene.MeasureItArchProps
            
            newDimensions = []

            # get selected
            scene = context.scene
            sceneProps = scene.MeasureItArchProps
            
            newDimensions = []

            pointList, warningStr = get_smart_selected()

            if warningStr != '':
                self.report({'ERROR'},warningStr)

            for idx in range(0, len(pointList) - 1, 2):
                p1 = pointList[idx]
                mainObj = p1['obj']

                # Try To get the next point
                # If it doesn't exist, we're done with the loop
                try:
                    p2 = pointList[idx+1]
                except IndexError:
                    break
                
                # Note: We won't need this try except block for v0.5

                DimGen = mainObj.DimensionGenerator


                axisDims = DimGen.axisDimensions
                
                newDimension = axisDims.add()

                newDimension.dimObjectA = p1['obj']
                newDimension.dimObjectB = p2['obj']
                
                newDimension.dimPointA = p1['vert']
                newDimension.dimPointB = p2['vert']

                newDimension.name = 'Dimension ' + str(len(DimGen.axisDimensions))
                newDimensions.append(newDimension)

                newWrapper = DimGen.wrapper.add()
                newWrapper.itemType = 'axisDimensions'
                idx += 1

            # Set Common Values
            for newDimension in newDimensions:
                newDimension.itemType = 'axisDimensions'
                newDimension.style = sceneProps.default_dimension_style
                if sceneProps.default_dimension_style is not '':
                    newDimension.uses_style = True
                else:
                    newDimension.uses_style = False

                if 'camera' in scene:
                    newDimension.visibleInView = scene.camera.data
                newDimension.dimViewPlane = sceneProps.viewPlane

                newDimension.dimAxis = sceneProps.measureit_arch_dim_axis
                newDimension.textAlignment = 'C'
                
                # Sum group
                DimGen.measureit_arch_num += 1 
            return{'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

            return {'CANCELLED'}

class AddAreaButton(Operator):
    bl_idname = "measureit_arch.addareabutton"
    bl_label = "Area"
    bl_description = "(EDITMODE only) Add a new measure for area (select 1 or more faces) \n \
        The active face determines text placement"
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
            sceneProps = scene.MeasureItArchProps
            myobj = context.object
            
            # Get all selected faces
            mylist = get_selected_faces(myobj)
            if len(mylist) >= 1:

                # Create Area Dim
                dimGen = myobj.DimensionGenerator
                areaDims = dimGen.areaDimensions
                newDim = areaDims.add()

                # add faces to buffer
                newDim['facebuffer'] = mylist


                # Calc Perimeter edges
                bm = bmesh.from_edit_mesh(myobj.data)
                faces = bm.faces

                bm.faces.ensure_lookup_table()

                perimiterEdges = []
                for faceIdx in mylist:
                    face = faces[faceIdx]
                    edges = face.edges
                    for edge in edges:
                        adjFaces = edge.link_faces
                        if len(adjFaces)>1:
                            if adjFaces[0].index in mylist and adjFaces[1].index in mylist:
                                pass
                        else:
                            perimiterEdges.append(edge.index)

                # Add perimeter edges to buffer
                newDim['perimeterEdgeBuffer'] = perimiterEdges 
                newDim.name = 'Area ' + str(len(dimGen.areaDimensions))
                newDim.fillColor = (random.random(),random.random(),random.random(),1)

                # User last Selected face as text origin
                try:
                    lastIdx = len(mylist)-1
                    newDim.originFaceIdx = bm.select_history[-1].index
                except IndexError:
                    newDim.originFaceIdx = mylist[len(mylist)-1]

                newWrapper = dimGen.wrapper.add()
                newWrapper.itemType = 'areaDimensions'

                # redraw
                recalc_dimWrapper_index(self,context)
                context.area.tag_redraw()

                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt_ARCH: Select at least one face for creating area measure. ")
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
            sceneProps = scene.MeasureItArchProps
            mainobject = context.object
            mylist = get_selected_vertex_history(mainobject)
            if len(mylist) == 3:
                
                DimGen = mainobject.DimensionGenerator

                newDimension = DimGen.angleDimensions.add()
                newDimension.itemType = 'angleDimensions'
                newDimension.name = 'Angle ' + str(len(DimGen.angleDimensions))
                newWrapper = DimGen.wrapper.add()
                newWrapper.itemType = 'angleDimensions'
                recalc_dimWrapper_index(self,context)

                newDimension.visibleInView = scene.camera.data

                newDimension.style = sceneProps.default_dimension_style
                if sceneProps.default_dimension_style is not '':
                    newDimension.uses_style = True
                else:
                    newDimension.uses_style = False

                newDimension.dimPointA = mylist[0]
                newDimension.dimPointB = mylist[1]
                newDimension.dimPointC = mylist[2]
                newDimension.dimRadius = 0.25
                newDimension.lineWeight = 1
                
                # text

                newDimension.textAlignment = 'C'
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt_ARCH: Select three vertices for creating angle measure")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}

class AddArcButton(Operator):

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
            sceneProps = scene.MeasureItArchProps
            mainobject = context.object
            mylist = get_selected_vertex_history(mainobject)
            if len(mylist) == 3:

                DimGen = mainobject.DimensionGenerator
                newDimension = DimGen.arcDimensions.add()
                newDimension.itemType = 'arcDimensions'
                newDimension.name = 'Arc ' + str(len(DimGen.arcDimensions))
                newDimension.lineWeight = 2
                newWrapper = DimGen.wrapper.add()
                newWrapper.itemType = 'arcDimensions'
            

                # Set values
                newDimension.dimPointA = mylist[0]
                newDimension.dimPointB = mylist[1]
                newDimension.dimPointC = mylist[2]


                # redraw
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt_ARCH: Select three vertices for creating arc measure")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}

class CursorToArcOrigin(Operator):
    bl_idname = "measureit_arch.cursortoarcorigin"
    bl_label = "Cursor To Arc Origin"
    bl_description = "Move the 3D Cursor to the Arc's Origin"
    bl_category = 'MeasureitArch'

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        myobj = context.object
        if myobj is None:
            return False
        else:
            dimGen = myobj.DimensionGenerator
            activeIndex = dimGen.active_index
            activeWrapperItem = dimGen.wrapper[dimGen.active_index]

            if activeWrapperItem.itemType == 'arcDimensions':
                return True
            else:
                return False
                

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        myobj = context.active_object
        dimGen = myobj.DimensionGenerator
        activeIndex = dimGen.active_index
        activeWrapperItem = dimGen.wrapper[dimGen.active_index]
        cursor = context.scene.cursor
        
        if activeWrapperItem.itemType == 'arcDimensions':
            arc = dimGen.arcDimensions[activeWrapperItem.itemIndex]
            center = arc.arcCenter
            cursor.location = center
            return {'FINISHED'}
        else:
             self.report({'ERROR'},
            "Please Select an Arc Dimension")
        return {'CANCELLED'}

class AddFaceToArea(Operator):   
    bl_idname = "measureit_arch.addfacetoarea"
    bl_label = "Add Selected Faces to Area Dimension"
    bl_description = "(EDIT MODE) Adds the currently selected faces to the active Area Dimension"
    bl_category = 'MeasureitArch'
    tag: IntProperty()

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        myobj = context.object
        if myobj is None:
            return False
        else:
            if myobj.type == "MESH":
                if bpy.context.mode == 'EDIT_MESH':
                    dimGen = myobj.DimensionGenerator
                    activeIndex = dimGen.active_index
                    activeWrapperItem = dimGen.wrapper[dimGen.active_index]

                    if activeWrapperItem.itemType == 'areaDimensions':
                        return True
                    else:
                       return False
                else:
                    return False
            else:
                return False


    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
         for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # get selected

                    myobj = context.object
                    mylist =  get_selected_faces(myobj)
                    dimGen = myobj.DimensionGenerator
                    activeIndex = dimGen.active_index
                    activeWrapperItem = dimGen.wrapper[dimGen.active_index]
                    
                    if activeWrapperItem.itemType == 'areaDimensions':
                        dim = dimGen.areaDimensions[activeWrapperItem.itemIndex]
                    else:
                        return{'CANCLED'}

                    # add faces to buffer
                    templist = dim['facebuffer'].to_list()
                    for idx in mylist:
                        templist.append(idx)
                    dim['facebuffer'] = templist


                    # Calc Perimeter edges
                    bm = bmesh.from_edit_mesh(myobj.data)
                    faces = bm.faces

                    bm.faces.ensure_lookup_table()

                    perimiterEdges = []
                    dim['perimeterEdgeBuffer'] = perimiterEdges 
                    for faceIdx in templist:
                        face = faces[faceIdx]
                        edges = face.edges
                        for edge in edges:
                            adjFaces = edge.link_faces
                            if adjFaces[0].index in templist and adjFaces[1].index in templist:
                                pass
                            else:
                                perimiterEdges.append(edge.index)

                    # Add perimeter edges to buffer
                    dim['perimeterEdgeBuffer'] = perimiterEdges 
                    return{'FINISHED'}
            return{'CANCLED'}

class RemoveFaceFromArea(Operator):   
    bl_idname = "measureit_arch.removefacefromarea"
    bl_label = "Remove Selected Faces from Area Dimension"
    bl_description = "(EDIT MODE) Removes the currently selected faces from the active Area Dimension"
    bl_category = 'MeasureitArch'

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        myobj = context.object
        if myobj is None:
            return False
        else:
            if myobj.type == "MESH":
                if bpy.context.mode == 'EDIT_MESH':
                    dimGen = myobj.DimensionGenerator
                    activeIndex = dimGen.active_index
                    activeWrapperItem = dimGen.wrapper[dimGen.active_index]

                    if activeWrapperItem.itemType == 'areaDimensions':
                        return True
                    else:
                       return False
                else:
                    return False
            else:
                return False


    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
         for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # get selected

                    myobj = context.object
                    mylist =  get_selected_faces(myobj)
                    dimGen = myobj.DimensionGenerator
                    activeIndex = dimGen.active_index
                    activeWrapperItem = dimGen.wrapper[dimGen.active_index]
                    
                    if activeWrapperItem.itemType == 'areaDimensions':
                        dim = dimGen.areaDimensions[activeWrapperItem.itemIndex]
                    else:
                        return{'CANCLED'}

                    # remove faces from buffer
                    templist = dim['facebuffer'].to_list()
                    for idx in mylist:
                        if idx in templist:
                            idxToRemove = templist.index(idx)
                            del templist[idxToRemove]

                    dim['facebuffer'] = templist


                    # reCalc Perimeter edges
                    bm = bmesh.from_edit_mesh(myobj.data)
                    faces = bm.faces

                    bm.faces.ensure_lookup_table()

                    perimiterEdges = []
                    dim['perimeterEdgeBuffer'] = perimiterEdges 
                    for faceIdx in templist:
                        face = faces[faceIdx]
                        edges = face.edges
                        for edge in edges:
                            adjFaces = edge.link_faces
                            if adjFaces[0].index in templist and adjFaces[1].index in templist:
                                pass
                            else:
                                perimiterEdges.append(edge.index)

                    # Add perimeter edges to buffer
                    dim['perimeterEdgeBuffer'] = perimiterEdges 
                    return{'FINISHED'}
            return{'CANCLED'}

class M_ARCH_UL_dimension_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        dimGen = context.object.DimensionGenerator
        angleDim = dimGen.angleDimensions
        alignedDim = dimGen.alignedDimensions
        axisDim =  dimGen.axisDimensions
        boundsDim = dimGen.boundsDimensions
        arcDim = dimGen.arcDimensions
        areaDim = dimGen.areaDimensions

        scene = bpy.context.scene

        StyleGen = scene.StyleGenerator
        hasGen = True
        
        # I should define this in the dimension container itself so that I dont have to edit this each time I define a new dimension type...
        #

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.use_property_decorate = False
            # Get correct item and icon
            if item.itemType == 'alignedDimensions':
                dim = alignedDim[item.itemIndex]
                nameIcon = 'DRIVER_DISTANCE'
    
            elif item.itemType == 'angleDimensions':
                dim = angleDim[item.itemIndex]
                nameIcon = 'DRIVER_ROTATIONAL_DIFFERENCE'

            elif item.itemType == 'axisDimensions':
                dim = axisDim[item.itemIndex]
                nameIcon = 'TRACKING_FORWARDS_SINGLE'
            
            elif item.itemType == 'boundsDimensions':
                dim = boundsDim[item.itemIndex]
                nameIcon = 'SHADING_BBOX'
            
            elif item.itemType == 'arcDimensions':
                dim = arcDim[item.itemIndex]
                nameIcon = 'MOD_THICKNESS'

            elif item.itemType == 'areaDimensions':
                dim = areaDim[item.itemIndex]
                nameIcon = 'MESH_GRID'


            row = layout.row()
            subrow = row.row()

            subrow.prop(dim, "name", text="",emboss=False,icon=nameIcon)

            if dim.visible: visIcon = 'HIDE_OFF'
            else: visIcon = 'HIDE_ON'
            
            if dim.uses_style: styleIcon = 'LINKED'
            else: styleIcon = 'UNLINKED'
            
            if not dim.uses_style:
                subrow = row.row(align=True)
                subrow.scale_x = 0.6
                subrow.prop(dim, 'color', text="" )
                if item.itemType == 'areaDimensions':
                    subrow.prop(dim,'fillColor',text="")
            else:
                row.prop_search(dim,'style', StyleGen,'alignedDimensions',text="", icon='COLOR')
                row.separator()

            
            if hasGen:
                row = row.row(align=True)
                row.prop(dim, 'uses_style', text="",toggle=True, icon=styleIcon,emboss=False)
            
            row.prop(dim, "visible", text="", icon = visIcon,emboss=False)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')

class OBJECT_PT_UIDimensions(Panel):
    """Creates a Panel in the Object properties window"""
    bl_parent_id = 'OBJECT_PT_Panel'
    bl_label = "Dimensions"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon= 'DRIVER_DISTANCE')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        obj = context.object
        if 'DimensionGenerator' in context.object:     
            scene = context.scene
            dimGen = obj.DimensionGenerator



            row = layout.row()
            
            # Draw The UI List
            row.template_list("M_ARCH_UL_dimension_list", "", dimGen, "wrapper", dimGen, "active_index",rows=2, type='DEFAULT')
            
            # Operators Next to List
            col = row.column(align=True)
            op = col.operator("measureit_arch.listdeletepropbutton", text="", icon="X")
            op.genPath = 'bpy.context.object.DimensionGenerator'
            op.tag = dimGen.active_index  # saves internal data
            op.is_style = False
            op.item_type = 'D'

            col.separator()
            col.menu("OBJECT_MT_dimension_menu", icon='DOWNARROW_HLT', text="")

            # Settings Below List
            if len(dimGen.wrapper) > 0 and  dimGen.active_index < len(dimGen.wrapper):
                activeWrapperItem = dimGen.wrapper[dimGen.active_index]
                item = eval('dimGen.' + activeWrapperItem.itemType + '[activeWrapperItem.itemIndex]')

                if dimGen.show_dimension_settings: settingsIcon = 'DISCLOSURE_TRI_DOWN'
                else: settingsIcon = 'DISCLOSURE_TRI_RIGHT'
                
                box = layout.box()
                col = box.column()
                row = col.row()
                row.prop(dimGen, 'show_dimension_settings', text="", icon=settingsIcon,emboss=False)

                row.label(text= item.name + ' Settings:')
                if dimGen.show_dimension_settings:
                    eval('draw_' + activeWrapperItem.itemType + '_settings(item,box)' )
                    
                    
class OBJECT_MT_dimension_menu(bpy.types.Menu):
    bl_label = "Custom Menu"

    def draw(self,context):
        layout = self.layout
        
        op = layout.operator('measureit_arch.addfacetoarea', text="Add To Area", icon='ADD')
        op = layout.operator('measureit_arch.removefacefromarea', text="Remove From Area", icon='REMOVE')

        layout.separator()

        op = layout.operator('measureit_arch.cursortoarcorigin',text="Cursor to Arc Origin", icon='MOD_THICKNESS')

        layout.separator()

        delOp = layout.operator("measureit_arch.deleteallitemsbutton", text="Delete All Dimensions", icon="X")
        delOp.is_style = False
        delOp.genPath = 'bpy.context.object.DimensionGenerator'


def draw_alignedDimensions_settings(dim,layout):
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
        col.prop_search(dim,'visibleInView', bpy.data, 'cameras',text='Visible In View')
        col.prop(dim,'lineWeight',text='Line Weight')

    col = layout.column(align=True)
    col.prop(dim,'dimOffset',text='Distance')
    col.prop(dim,'dimLeaderOffset',text='Offset')
    col.prop(dim, 'dimRotation', text='Rotation')
    
    if dim.uses_style is False:
        col = layout.column(align=True)
        col.prop(dim,'fontSize',text='Font Size')
    col.prop(dim,'textAlignment',text='Alignment')
        #col.prop(dim,'textPosition',text='Position')

    if dim.uses_style is False:
        col = layout.column(align=True)
        col.prop(dim,'endcapA', text='Arrow Start')
        col.prop(dim,'endcapB', text='End')
        col.prop(dim,'endcapSize', text='Arrow Size')
        col.prop(dim,'endcapArrowAngle', text='Arrow Angle')
        col.prop(dim,'inFront', text='Draw in Front')
        col.prop(dim,'evalMods')

def draw_boundsDimensions_settings(dim,layout):
    col = layout.column()    
    col.prop_search(dim,'dimCollection', bpy.data,'collections',text="Collection", icon='GROUP')
    
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
        col.prop_search(dim,'visibleInView', bpy.data, 'cameras',text='Visible In View')
        col.prop(dim,'lineWeight',text='Line Weight')


    split = layout.split(factor=0.49)
    row = split.row(align=True)
    row.alignment ='RIGHT'
    row.label(text='Axis')
    row = split.row(align=True)

    row.prop(dim, "drawAxis", text="", toggle=True)


    col = layout.column(align=True)
    col.prop(dim,'dimOffset',text='Distance')
    col.prop(dim,'dimLeaderOffset',text='Offset')
    col.prop(dim, 'dimRotation', text='Rotation')
    
    
    if dim.uses_style is False:
        col = layout.column(align=True)
        col.prop(dim,'fontSize',text='Font Size')
        col.prop(dim,'textAlignment',text='Alignment')
        #col.prop(dim,'textPosition',text='Position')

        col = layout.column(align=True)
        col.prop(dim,'endcapA', text='Arrow Start')
        col.prop(dim,'endcapB', text='End')
        col.prop(dim,'endcapSize', text='Arrow Size')
        col.prop(dim,'endcapArrowAngle', text='Arrow Angle')
        
        col = layout.column(align=True) 
        col.prop(dim,'inFront', text='Draw in Front')

      
    col.prop(dim,'calcAxisAligned', text='Always Use Axis Aligned Bounds')
 
def draw_axisDimensions_settings(dim,layout):
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
    col.prop_search(dim,'dimAxisObject', bpy.data, 'objects',text='Custom Axis Object')
    
    col = layout.column(align=True)
    if dim.uses_style is False:
        col.prop_search(dim,'visibleInView', bpy.data, 'cameras',text='Visible In View')
        
        col.prop(dim,'lineWeight',text='Line Weight')

    col = layout.column(align=True)
    col.prop(dim,'dimOffset',text='Distance')
    col.prop(dim,'dimLeaderOffset',text='Offset')
    
    if dim.uses_style is False:
        col = layout.column(align=True)
        col.prop(dim,'fontSize',text='Font Size')
        col.prop(dim,'textAlignment',text='Alignment')
        #col.prop(dim,'textPosition',text='Position')

        col = layout.column(align=True)
        col.prop(dim,'endcapA', text='Arrow Start')
        col.prop(dim,'endcapB', text='End')
        col.prop(dim,'endcapSize', text='Arrow Size')
        col.prop(dim,'endcapArrowAngle', text='Arrow Angle')
        col.prop(dim,'inFront', text='Draw in Front')
    col.prop(dim,'evalMods')

def draw_angleDimensions_settings(dim,layout):
        col = layout.column()
        if dim.uses_style is False:
            split = layout.split(factor=0.485)
            col = split.column()
            col.alignment ='RIGHT'
            col.label(text='Font')
            col = split.column()

            col.template_ID(dim, "font", open="font.open", unlink="font.unlink")

            col = layout.column()

        col.prop_search(dim,'visibleInView', bpy.data, 'cameras',text='Visible In View')
        if dim.uses_style is False:
            col = layout.column(align=True)
            col.prop(dim,'lineWeight',text='Line Weight')

        col.prop(dim,'dimRadius',text='Radius')

        if dim.uses_style is False:
            col = layout.column(align=True)
            col.prop(dim,'fontSize',text='Font Size')
            col.prop(dim,'textAlignment',text='Alignment')
           
            col.prop(dim,'endcapA', text='Arrow Start')
            col.prop(dim,'endcapB', text='End')
            col.prop(dim,'endcapSize', text='Arrow Size')
            col.prop(dim,'endcapArrowAngle', text='Arrow Angle')
            col.prop(dim,'inFront', text='Draw in Front')
        col.prop(dim,'reflexAngle', text='Use Reflex Angle')
        col.prop(dim,'evalMods')
            #col.prop(dim,'textPosition',text='Position')

        col = layout.column(align=True)

def draw_arcDimensions_settings(dim,layout):
    col = layout.column()

    if dim.uses_style is False:
        split = layout.split(factor=0.485)
        col = split.column()
        col.alignment ='RIGHT'
        col.label(text='Font')
        col = split.column()

        col.template_ID(dim, "font", open="font.open", unlink="font.unlink")

        col = layout.column()

    col.prop_search(dim,'visibleInView', bpy.data, 'cameras',text='Visible In View')
    if dim.uses_style is False:
        col = layout.column(align=True)
        col.prop(dim,'lineWeight',text='Line Weight')

    col.prop(dim,'dimOffset',text='Radius')

    if dim.uses_style is False:
        col = layout.column(align=True)
        col.prop(dim,'fontSize',text='Font Size')
        col = layout.column(align=True)
        col.prop(dim,'endcapA', text='Arrow Start')
        col.prop(dim,'endcapB', text='End')
        col.prop(dim,'endcapC', text='Radius')
        col.prop(dim,'endcapSize', text='Arrow Size')
        col.prop(dim,'endcapArrowAngle', text='Arrow Angle')
        #col.prop(dim,'textPosition',text='Position')
    col = layout.column(align=True)
    col.prop(dim,'displayAsAngle')
    col.prop(dim,'showRadius')
    col.prop(dim,'inFront', text='Draw in Front')
    

    col = layout.column(align=True)

def draw_areaDimensions_settings(dim,layout):
    col = layout.column(align=True)    
    
    col.prop(dim,"fillColor", text='Fill Color')
    col.prop(dim,'fillAlpha', text='Fill Amount')

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
        col.prop_search(dim,'visibleInView', bpy.data, 'cameras',text='Visible In View')
        col.prop(dim,'lineWeight',text='Line Weight')

    col = layout.column(align=True)
    col.prop(dim,'dimTextPos',text='Text Position')
    col.prop(dim,'dimRotation',text='Text Rotation')
    
    if dim.uses_style is False:
        col = layout.column(align=True)
        col.prop(dim,'fontSize',text='Font Size')
        col.prop(dim,'textAlignment',text='Alignment')
        #col.prop(dim,'textPosition',text='Position')

        col = layout.column(align=True)
        col.prop(dim,'inFront', text='Draw in Front')
        col.prop(dim,'evalMods')



class TranlateAnnotationOp(bpy.types.Operator):
    """Move Annotation"""
    bl_idname = "measureit_arch.dimesnion_offset"
    bl_label = "Adjust Dimension Offset"
    bl_options = {'GRAB_CURSOR','INTERNAL','BLOCKING','UNDO'}
    
    idx: IntProperty()

    dimType: StringProperty()

    offset: FloatProperty(
        name="Offset",
    )

    objIndex: IntProperty()

    def modal(self, context, event):
        myobj = context.selected_objects[self.objIndex]
        dimension = eval('myobj.' + self.dimType)
        unit_system = bpy.context.scene.unit_settings.system
        unit_length = bpy.context.scene.unit_settings.length_unit\
        
        toFeet = 3.28084
        toInches = 39.3700787401574887

        # Set Tweak Flags
        if event.ctrl:
            tweak_snap = True
        else: tweak_snap = False
        if event.shift:
            tweak_precise = True
        else: tweak_precise= False
        
        if event.type == 'MOUSEMOVE':
            sensitivity = 0.01
            vecDelta = Vector(((event.mouse_x - self.init_mouse_x)* sensitivity,(event.mouse_y - self.init_mouse_y)* sensitivity,0))
            vecDelta = Vector(((event.mouse_x - self.init_mouse_x)* sensitivity,(event.mouse_y - self.init_mouse_y)* sensitivity,0))
            viewRot = context.area.spaces[0].region_3d.view_rotation
            vecDelta.rotate(viewRot)
            delta = (event.mouse_x - self.init_mouse_x)* sensitivity
            mat = myobj.matrix_world
            rot = mat.to_quaternion()

            axis =  Vector((-1,-1,-1))
            axis.rotate(rot)
            
            delta = vecDelta.project(axis)
            delta = delta.magnitude
            if axis.dot(vecDelta) > 0:
                delta = -delta

            resultInit = self.init
            precise_factor = 10

            if unit_system == 'IMPERIAL':
                resultInit *= toFeet
                delta *= toFeet
                precise_factor = 12

            if tweak_snap:
                delta = round(delta)
                resultInit = round(self.init,0)
                
            if tweak_precise:
                delta /= precise_factor
                resultInit = round(self.init,1)

            if unit_system == 'IMPERIAL':
                resultInit /= toFeet
                delta /= toFeet

            dimension.dimOffset = resultInit +  delta
            context.area.header_text_set("Dimension Offset = " + "%.4f" % (resultInit +  delta))

        elif event.type == 'LEFTMOUSE':
            #Setting hide_viewport is a stupid hack to force Gizmos to update after operator completes
            context.object.hide_viewport = False
            context.area.header_text_set(None)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            #Setting hide_viewport is a stupid hack to force Gizmos to update after operator completes
            context.object.hide_viewport = False 
            context.area.header_text_set(None)
            dimension.dimOffset= self.init

            return {'CANCELLED'}
        
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        myobj = context.selected_objects[self.objIndex]
        dimension = myobj.DimensionGenerator.alignedDimensions[self.idx]
        self.init_mouse_x = event.mouse_x
        self.init_mouse_y = event.mouse_y

        self.init = dimension.dimOffset

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}