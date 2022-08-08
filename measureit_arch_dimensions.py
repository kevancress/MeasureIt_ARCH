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
from typing import List
import bpy
import bmesh
import random

from bpy.types import PropertyGroup, Panel, Object, Operator, UIList, Collection
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, \
    BoolProperty, StringProperty, FloatProperty, EnumProperty, \
    PointerProperty, BoolVectorProperty
from mathutils import Vector

from .measureit_arch_baseclass import BaseDim, recalc_dimWrapper_index
from .measureit_arch_utils import get_smart_selected, \
    get_selected_vertex_history, get_selected_faces
from .measureit_arch_units import BU_TO_FEET


def update_active_dim(self, context):
    Generator = context.object.DimensionGenerator
    activeWraper = Generator.wrapper[Generator.active_index]

    for key in Generator.keys():
        item = Generator.path_resolve(key)
        if 'collection' in str(item):
            typeContainer = item
            for item in typeContainer:
                item.is_active = False

    activeItem = eval('Generator.' + activeWraper.itemType +
                      '[activeWraper.itemIndex]')
    activeItem.is_active = True


class AreaDimensionProperties(BaseDim, PropertyGroup):

    gen_group: StringProperty(
        name="Generator Group",
        description="group in the generator - api property",
        default="areaDimensions")

    dimTextPos: FloatVectorProperty(
        name='Text Position',
        description='Offset for Area Dimension Text',
        default=(0, 0, 0),
        subtype='TRANSLATION')

    originFaceIdx: IntProperty(
        name='Origin Face',
        description='The face whos normal and center are used for text placement')

    showFill: BoolProperty(name='Show Fill')

    showOutline: BoolProperty(name='Show Outline')

    fillAlpha: FloatProperty(
        name='Fill',
        min=0,
        soft_max=1.0,
        max=1,
        default=0.5,
        subtype='FACTOR')

    fillColor: FloatVectorProperty(
        name="Color",
        description="Color for the Item",
        default=(0.0, 0.0, 0.0, 1.0),
        min=0,
        max=1,
        subtype='COLOR',
        size=4)


class AlignedDimensionProperties(BaseDim, PropertyGroup):
    gen_group: StringProperty(
        name="Generator Group",
        description="group in the generator - api property",
        default="alignedDimensions")

    dimObjectA: PointerProperty(type=Object)

    dimObjectB: PointerProperty(type=Object)


class AxisDimensionProperties(BaseDim, PropertyGroup):
    gen_group: StringProperty(
        name="Generator Group",
        description="group in the generator - api property",
        default="axisDimensions")

    dimObjectA: PointerProperty(type=Object)

    dimObjectB: PointerProperty(type=Object)

    dimAxisObject: PointerProperty(type=Object)

    dimAxis: EnumProperty(
        items=(('X', "X Axis", "Measure only the X Axis"),
               ('Y', "Y Axis", "Measure only the Y Axis"),
               ('Z', "Z Axis", "Measure only the Z Axis")),
        name="Measurement Axis",
        description="Measurement Axis")


class BoundsDimensionProperties(BaseDim, PropertyGroup):
    gen_group: StringProperty(
        name="Generator Group",
        description="group in the generator - api property",
        default="boundsDimensions")

    drawAxis: BoolVectorProperty(
        name="Draw Axis",
        description="Axis to Dimension for Bounding Box",
        default=(False, False, False),
        subtype='XYZ')

    dimCollection: PointerProperty(type=Collection)

    calcAxisAligned: BoolProperty()


class ArcDimensionProperties(BaseDim, PropertyGroup):
    gen_group: StringProperty(
        name="Generator Group",
        description="group in the generator - api property",
        default="arcDimensions")

    dimPointC: IntProperty(
        name='dimPointC',
        description="Angle End Vertex Index")

    arcCenter: FloatVectorProperty(name='Arc Center')

    showLength: BoolProperty(
        name='Show Arc Length',
        description='Displays the Arc Length Measurement',
        default=True)

    showRadius: BoolProperty(
        name='Show Arc Radius',
        description='Displays the Arc Radius and Center',
        default=True)

    displayAsAngle: BoolProperty(
        name='Display Arc Length as Angle',
        description='Display the Arc Length as the angle between the two extremes',
        default=False)

    endcapC: EnumProperty(
        items=(('99', "--", "No Cap"),
               ('L', "Arrow", "Arrow"),
               ('T', "Triangle", "Triangle")),
        default='T',
        name="C end",
        description="Add arrows to Radius Leader")


class AngleDimensionProperties(BaseDim, PropertyGroup):
    gen_group: StringProperty(
        name="Generator Group",
        description="group in the generator - api property",
        default="angleDimensions")

    dimPointC: IntProperty(
        name='dimPointC',
        description="Angle End Vertex Index")

    dimRadius: FloatProperty(
        name='Dimension Radius',
        description='Radius Dimension',
        default=(0.05),
        subtype='DISTANCE')

    reflexAngle: BoolProperty(
        name='Show Reflex Angle',
        description='Displays the Reflex Angle (Greater than 180 Degrees)',
        default=False)


class DimensionWrapper(PropertyGroup):
    """
    A Wrapper object so multiple dimension types can be shown in the same UI
    list
    """
    itemType: EnumProperty(
        items=(('alignedDimensions', "Aligned Dimension", ""),
               ('angleDimensions', "Angle Dimension", ""),
               ('axisDimensions', "Axis Dimension", ""),
               ('boundsDimensions', "Bounding Box Dimension", ""),
               ('arcDimensions', "Arc Dimension", ""),
               ('areaDimensions', "Area Dimension", "")),
        name="Dimension Item Type",
        update=recalc_dimWrapper_index)

    itemIndex: IntProperty(name='Dimension Index')


class DimensionContainer(PropertyGroup):
    measureit_arch_num: IntProperty(
        name='Number of measures', min=0, max=1000, default=0,
        description='Total number of MeasureIt_Arch elements')
    active_index: IntProperty(
        name="Active Dimension Index",
        update=update_active_dim)
    show_dimension_settings: BoolProperty(
        name='Show Dimension Settings', default=False)
    show_dimension_fields: BoolProperty(
        name='Show Dimension Text Fields', default=False)

    # Collections of each dimension property
    alignedDimensions: CollectionProperty(type=AlignedDimensionProperties)
    angleDimensions: CollectionProperty(type=AngleDimensionProperties)
    axisDimensions: CollectionProperty(type=AxisDimensionProperties)
    boundsDimensions: CollectionProperty(type=BoundsDimensionProperties)
    arcDimensions: CollectionProperty(type=ArcDimensionProperties)
    areaDimensions: CollectionProperty(type=AreaDimensionProperties)

    # Collection of Wrapped dimensions for list UI display
    wrapper: CollectionProperty(type=DimensionWrapper)


class AddAlignedDimensionButton(Operator):
    bl_idname = "measureit_arch.addaligneddimensionbutton"
    bl_label = "Add"
    bl_description = "Add Aligned Dimension (Dimension Properties can be edited in the Object Properties)"
    bl_category = 'MeasureitArch'

    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type in {"MESH", "EMPTY", "CAMERA", "LIGHT"}:
                return True
            else:
                return False

    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # get selected
            scene = context.scene
            sceneProps = scene.MeasureItArchProps

            newDimensions = []

            pointList, warningStr = get_smart_selected()

            if warningStr != '':
                self.report({'ERROR'}, warningStr)

            for idx in range(0, len(pointList) - 1, 2):
                p1 = pointList[idx]
                mainObj = p1['obj']

                # Try To get the next point
                # If it doesn't exist, we're done with the loop
                try:
                    p2 = pointList[idx + 1]
                except IndexError:
                    break

                DimGen = mainObj.DimensionGenerator

                alignedDims = DimGen.alignedDimensions

                newDimension = alignedDims.add()

                newDimension.dimObjectA = p1['obj']
                newDimension.dimObjectB = p2['obj']

                newDimension.dimPointA = p1['vert']
                newDimension.dimPointB = p2['vert']

                newDimension.name = 'Dimension {}'.format(
                    len(DimGen.alignedDimensions))
                newDimensions.append(newDimension)

                newWrapper = DimGen.wrapper.add()
                newWrapper.itemType = 'alignedDimensions'
                recalc_dimWrapper_index(self, context)
                newDimensions.append(newDimension)
                context.area.tag_redraw()
                idx += 1

            # Set Common Values
            for newDimension in newDimensions:
                newDimension.itemType = 'alignedDimensions'
                newDimension.style = sceneProps.default_dimension_style
                if sceneProps.default_dimension_style != '':
                    newDimension.uses_style = True
                else:
                    newDimension.uses_style = False

                newDimension.lineWeight = 1
                newDimension.dimViewPlane = sceneProps.viewPlane

                # text
                newDimension.textAlignment = 'C'

                DimGen.measureit_arch_num += 1
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")

            return {'CANCELLED'}


class AddBoundingDimensionButton(Operator):
    bl_idname = "measureit_arch.addboundingdimensionbutton"
    bl_label = "Bounding"
    bl_description = "Add a Bounding Box Dimension (Dimension Properties can be edited in the Object Properties)"
    bl_category = 'MeasureitArch'

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

    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # get selected
            scene = context.scene
            sceneProps = scene.MeasureItArchProps

            # Object Context
            if bpy.context.mode == 'OBJECT':
                mainobject = context.object
                # Check Generators

                # Basically I dont need to do anything here, I want to handle
                # the measuring and the selection of which bounding box verts
                # to anchor to in the draw method, so that the most visible
                # verts can be selected depending on the current view. all we
                # need to do is to create a  Bounds dimension and set its
                # defualt props. We do the tricky part in the draw.

                # Add Bounds Dim with Axis
                DimGen = mainobject.DimensionGenerator
                newBoundsDimension = DimGen.boundsDimensions.add()

                newBoundsDimension.name = 'Bounding Box Dimension'
                newBoundsDimension.drawAxis[0] = sceneProps.bound_x
                newBoundsDimension.drawAxis[1] = sceneProps.bound_y
                newBoundsDimension.drawAxis[2] = sceneProps.bound_z
                newBoundsDimension.textAlignment = 'C'

                # Add Text Field for each Axis
                newBoundsDimension.textFields.add()
                newBoundsDimension.textFields.add()
                newBoundsDimension.textFields.add()

                newBoundsDimension.style = sceneProps.default_dimension_style
                if sceneProps.default_dimension_style != '':
                    newBoundsDimension.uses_style = True
                else:
                    newBoundsDimension.uses_style = False

                newWrapper = DimGen.wrapper.add()
                newWrapper.itemType = 'boundsDimensions'

                # redraw
                recalc_dimWrapper_index(self, context)
                context.area.tag_redraw()

            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}


class AddAxisDimensionButton(Operator):
    bl_idname = "measureit_arch.addaxisdimensionbutton"
    bl_label = "Add"
    bl_description = "Add Single Axis Dimension (Dimension Properties can be edited in the Object Properties)"
    bl_category = 'MeasureitArch'

    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type in {"MESH", "EMPTY", "CAMERA", "LIGHT"}:
                return True
            else:
                return False

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
                self.report({'ERROR'}, warningStr)

            for idx in range(0, len(pointList) - 1, 2):
                p1 = pointList[idx]
                mainObj = p1['obj']

                # Try To get the next point
                # If it doesn't exist, we're done with the loop
                try:
                    p2 = pointList[idx + 1]
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

                newDimension.name = 'Dimension {}'.format(
                    len(DimGen.axisDimensions))
                newDimensions.append(newDimension)

                newWrapper = DimGen.wrapper.add()
                newWrapper.itemType = 'axisDimensions'
                idx += 1

            # Set Common Values
            for newDimension in newDimensions:
                newDimension.itemType = 'axisDimensions'
                newDimension.style = sceneProps.default_dimension_style
                if sceneProps.default_dimension_style != '':
                    newDimension.uses_style = True
                else:
                    newDimension.uses_style = False

                newDimension.dimViewPlane = sceneProps.viewPlane

                newDimension.dimAxis = sceneProps.measureit_arch_dim_axis
                newDimension.textAlignment = 'C'

                # Sum group
                DimGen.measureit_arch_num += 1
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}

class PerimeterEdge():
    edge_idx = 0
    vertA_idx = 0
    vertB_idx = 0

    def __init__(self, e_idx, a_idx, b_idx) -> None:
        self.edge_idx = e_idx
        self.vertA_idx = a_idx
        self.vertB_idx = b_idx
        pass

    def is_connected(self,other_edge):
        return other_edge.vertA_idx == self.vertA_idx or other_edge.vertA_idx == self.vertB_idx \
            or other_edge.vertB_idx == self.vertA_idx or other_edge.vertB_idx == self.vertB_idx
    
    def get_other_vert(self,vert_idx):
        if vert_idx == self.vertA_idx:
            return self.vertB_idx
        elif vert_idx == self.vertB_idx:
            return self.vertA_idx
        else:
            return -1
    
    def get_shared_vert(self, other_edge):
        if self.vertA_idx == other_edge.vertA_idx or self.vertA_idx == other_edge.vertB_idx:
            return self.vertA_idx
        elif self.vertB_idx == other_edge.vertA_idx or self.vertB_idx == other_edge.vertB_idx:
            return self.vertB_idx
        else:
            print('No Shared Vert!!!')
            return-1


# Sorts perimeter edges into a continuous loop
def sort_perimeter_edges(perimeter_edges):
    sorted_list = []
    safety_idx = 0
    last_entry = None
    while len(perimeter_edges) > 0:
        item = perimeter_edges.pop(0)
        if last_entry == None:
            sorted_list.append(item)
            last_entry = item

        elif last_entry.is_connected(item):
            last_entry = item
            sorted_list.append(item)
            
        else:
            safety_idx += 1
            perimeter_edges.append(item)

        if safety_idx > 100000:
            print('Something went wrong sorting perimeter edges')
            break

    return sorted_list

def get_perimeter_verts(sorted_perimeter_edges):
    edges = sorted_perimeter_edges.copy()
    sorted_verts = []
    last_vert = None
    first_vert = None
    while len(edges)>0:
        if len(sorted_verts) == 0:
            e1 = edges.pop(0)
            e2 = edges.pop(0)
            first_vert = e1.get_shared_vert(e2)
            last_vert = e1.get_other_vert(first_vert)
            sorted_verts.append(first_vert)
            sorted_verts.append(e2.get_other_vert(first_vert))
        else:
            current_vert = sorted_verts[-1]
            e = edges.pop(0)
            sorted_verts.append(e.get_other_vert(current_vert))

    sorted_verts.append(last_vert)
    sorted_verts.append(first_vert)

    return sorted_verts





class AddAreaButton(Operator):
    bl_idname = "measureit_arch.addareabutton"
    bl_label = "Area"
    bl_description = "(EDITMODE only) Add a new measure for area (select 1 or more faces) \n \
        The active face determines text placement"
    bl_category = 'MeasureitArch'

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

    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # Add properties
            myobj = context.object
            scene = context.scene
            sceneProps = scene.MeasureItArchProps

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
                bm.verts.ensure_lookup_table()

                perimeterEdges = []
                for faceIdx in mylist:
                    face = faces[faceIdx]
                    edges = face.edges
                    for edge in edges:
                        adjFaces = edge.link_faces
                        vertA = edge.verts[0].index
                        vertB = edge.verts[1].index
                        if len(adjFaces) > 1:
                            if adjFaces[0].index in mylist and adjFaces[1].index in mylist:
                                pass
                            else:
                                perimeterEdges.append(PerimeterEdge(edge.index,vertA,vertB))
                        else:
                            perimeterEdges.append(PerimeterEdge(edge.index,vertA,vertB))
                
                newDim.originFaceIdx = mylist[0]
                sorted_perimeter_edge_idxs = sort_perimeter_edges(perimeterEdges)
                sorted_perimeter_vert_idxs = get_perimeter_verts(sorted_perimeter_edge_idxs)

                # Add perimeter edges to buffer
                # newDim['perimeterEdgeBuffer'] = sorted_perimeter_edge_idxs
                newDim['perimeterVertBuffer'] = sorted_perimeter_vert_idxs
                newDim.name = 'Area {}'.format(len(dimGen.areaDimensions))
                newDim.fillColor = (
                    random.random(), random.random(), random.random(), 1)

                newDim.style = sceneProps.default_dimension_style
                if sceneProps.default_dimension_style != '':
                    newDim.uses_style = True
                else:
                    newDim.uses_style = False



                newWrapper = dimGen.wrapper.add()
                newWrapper.itemType = 'areaDimensions'

                # redraw
                recalc_dimWrapper_index(self, context)
                context.area.tag_redraw()

                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt_ARCH: Select at least one face for creating area measure. ")
                return {'FINISHED'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")

        return {'CANCELLED'}



class AddAngleButton(Operator):
    bl_idname = "measureit_arch.addanglebutton"
    bl_label = "Angle"
    bl_description = "(EDITMODE only) Add a new angle measure (select 3 vertices, 2nd is angle vertex)"
    bl_category = 'MeasureitArch'

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
                newDimension.name = 'Angle {}'.format(
                    len(DimGen.angleDimensions))
                newWrapper = DimGen.wrapper.add()
                newWrapper.itemType = 'angleDimensions'
                recalc_dimWrapper_index(self, context)

                newDimension.style = sceneProps.default_dimension_style
                if sceneProps.default_dimension_style != '':
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

    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # Add properties
            mainobject = context.object
            mylist = get_selected_vertex_history(mainobject)
            if len(mylist) == 3:

                DimGen = mainobject.DimensionGenerator
                newDimension = DimGen.arcDimensions.add()
                newDimension.itemType = 'arcDimensions'
                newDimension.name = 'Arc {}'.format(len(DimGen.arcDimensions))
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
            self.report({'WARNING'}, "View3D not found, cannot run operator")

        return {'CANCELLED'}


class CursorToArcOrigin(Operator):
    bl_idname = "measureit_arch.cursortoarcorigin"
    bl_label = "Cursor To Arc Origin"
    bl_description = "Move the 3D Cursor to the Arc's Origin"
    bl_category = 'MeasureitArch'

    @classmethod
    def poll(cls, context):
        myobj = context.object
        if myobj is None:
            return False
        else:
            dimGen = myobj.DimensionGenerator
            try:
                activeWrapperItem = dimGen.wrapper[dimGen.active_index]
            except:
                return False

            if activeWrapperItem.itemType == 'arcDimensions':
                return True
            else:
                return False

    def execute(self, context):
        myobj = context.active_object
        dimGen = myobj.DimensionGenerator
        activeWrapperItem = dimGen.wrapper[dimGen.active_index]
        cursor = context.scene.cursor

        if activeWrapperItem.itemType == 'arcDimensions':
            arc = dimGen.arcDimensions[activeWrapperItem.itemIndex]
            center = arc.arcCenter
            cursor.location = center
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Please select an Arc Dimension")
        return {'CANCELLED'}


class AddFaceToArea(Operator):
    bl_idname = "measureit_arch.addfacetoarea"
    bl_label = "Add Selected Faces to Area Dimension"
    bl_description = "(EDIT MODE) Adds the currently selected faces to the active Area Dimension"
    bl_category = 'MeasureitArch'
    tag: IntProperty()

    @classmethod
    def poll(cls, context):
        myobj = context.object
        if myobj is None:
            return False
        else:
            if myobj.type == "MESH":
                if bpy.context.mode == 'EDIT_MESH':
                    dimGen = myobj.DimensionGenerator
                    activeWrapperItem = dimGen.wrapper[dimGen.active_index]

                    if activeWrapperItem.itemType == 'areaDimensions':
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                return False

    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # get selected

                    myobj = context.object
                    mylist = get_selected_faces(myobj)
                    dimGen = myobj.DimensionGenerator
                    activeWrapperItem = dimGen.wrapper[dimGen.active_index]

                    if activeWrapperItem.itemType == 'areaDimensions':
                        dim = dimGen.areaDimensions[activeWrapperItem.itemIndex]
                    else:
                        return {'CANCELLED'}

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
                    return {'FINISHED'}
            return {'CANCELLED'}


class RemoveFaceFromArea(Operator):
    bl_idname = "measureit_arch.removefacefromarea"
    bl_label = "Remove Selected Faces from Area Dimension"
    bl_description = "(EDIT MODE) Removes the currently selected faces from the active Area Dimension"
    bl_category = 'MeasureitArch'

    @classmethod
    def poll(cls, context):
        myobj = context.object
        if myobj is None:
            return False
        else:
            if myobj.type == "MESH":
                if bpy.context.mode == 'EDIT_MESH':
                    dimGen = myobj.DimensionGenerator
                    activeWrapperItem = dimGen.wrapper[dimGen.active_index]

                    if activeWrapperItem.itemType == 'areaDimensions':
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                return False

    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # get selected

                    myobj = context.object
                    mylist = get_selected_faces(myobj)
                    dimGen = myobj.DimensionGenerator
                    activeWrapperItem = dimGen.wrapper[dimGen.active_index]

                    if activeWrapperItem.itemType == 'areaDimensions':
                        dim = dimGen.areaDimensions[activeWrapperItem.itemIndex]
                    else:
                        return {'CANCELLED'}

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
                    return {'FINISHED'}
            return {'CANCELLED'}


class M_ARCH_UL_dimension_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        dimGen = context.object.DimensionGenerator
        angleDim = dimGen.angleDimensions
        alignedDim = dimGen.alignedDimensions
        axisDim = dimGen.axisDimensions
        boundsDim = dimGen.boundsDimensions
        arcDim = dimGen.arcDimensions
        areaDim = dimGen.areaDimensions

        scene = bpy.context.scene

        StyleGen = scene.StyleGenerator
        hasGen = True

        # I should define this in the dimension container itself so that I dont
        # have to edit this each time I define a new dimension type...

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

            subrow.prop(dim, "name", text="", emboss=False, icon=nameIcon)

            if dim.visible:
                visIcon = 'HIDE_OFF'
            else:
                visIcon = 'HIDE_ON'

            if dim.uses_style:
                styleIcon = 'LINKED'
            else:
                styleIcon = 'UNLINKED'

            if not dim.uses_style:
                subrow = row.row(align=True)
                subrow.scale_x = 0.6
                subrow.prop(dim, 'color', text="")
                if item.itemType == 'areaDimensions':
                    subrow.prop(dim, 'fillColor', text="")
            else:
                row.prop_search(dim, 'style', StyleGen,
                                'alignedDimensions', text="", icon='COLOR')
                row.separator()

            if hasGen:
                row = row.row(align=True)
                row.prop(dim, 'uses_style', text="", toggle=True,
                         icon=styleIcon, emboss=False)

            row.prop(dim, "visible", text="", icon=visIcon, emboss=False)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')


class OBJECT_PT_UIDimensions(Panel):
    """ A Panel in the Object properties window """
    bl_parent_id = 'OBJECT_PT_Panel'
    bl_label = "Dimensions"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon='DRIVER_DISTANCE')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        obj = context.object
        if 'DimensionGenerator' in context.object:
            dimGen = obj.DimensionGenerator

            row = layout.row()

            # Draw The UI List
            row.template_list("M_ARCH_UL_dimension_list", "", dimGen,
                              "wrapper", dimGen, "active_index", rows=2, type='DEFAULT')

            # Operators Next to List
            col = row.column(align=True)
            op = col.operator(
                "measureit_arch.listdeletepropbutton", text="", icon="X")
            op.genPath = 'bpy.context.object.DimensionGenerator'
            op.tag = dimGen.active_index  # saves internal data
            op.is_style = False
            op.item_type = 'D'

            col.separator()
            up = col.operator("measureit_arch.movepropbutton", text="", icon="TRIA_UP")
            up.genPath = 'bpy.context.object.DimensionGenerator'
            up.item_type = "wrapper"
            up.upDown = -1

            down = col.operator("measureit_arch.movepropbutton", text="", icon="TRIA_DOWN")
            down.genPath = 'bpy.context.object.DimensionGenerator'
            down.item_type = "wrapper"
            down.upDown = 1

            col.separator()
            col.menu("OBJECT_MT_dimension_menu", icon='DOWNARROW_HLT', text="")

            # Settings Below List
            if len(dimGen.wrapper) > 0 and dimGen.active_index < len(dimGen.wrapper):
                activeWrapperItem = dimGen.wrapper[dimGen.active_index]
                item = eval('dimGen.' + activeWrapperItem.itemType +
                            '[activeWrapperItem.itemIndex]')
                idxString = "bpy.context.active_object.DimensionGenerator.wrapper[bpy.context.active_object.DimensionGenerator.active_index].itemIndex"

                ### TEXT FIELDS
                field_types = ['alignedDimensions','axisDimensions','areaDimensions']
                if activeWrapperItem.itemType in field_types:
                    if dimGen.show_dimension_fields:
                        fieldsIcon = 'DISCLOSURE_TRI_DOWN'
                    else:
                        fieldsIcon = 'DISCLOSURE_TRI_RIGHT'

                    box = layout.box()
                    col = box.column()
                    row = col.row()
                    row.prop(dimGen, 'show_dimension_fields',
                            text="", icon= fieldsIcon, emboss=False)

                    row.label(text=item.name + ' Text Fields:')

                    row.emboss = 'PULLDOWN_MENU'
                    txtAddOp = row.operator(
                        "measureit_arch.addtextfield", text="", icon="ADD")
                    txtAddOp.propPath = 'bpy.context.active_object.DimensionGenerator.{}[{}].textFields'.format(activeWrapperItem.itemType,idxString)
                    txtAddOp.idx = dimGen.active_index
                    txtAddOp.add = True

                    txtRemoveOp = row.operator(
                        "measureit_arch.addtextfield", text="", icon="REMOVE")
                    txtAddOp.propPath = 'bpy.context.active_object.DimensionGenerator.{}[{}].textFields'.format(activeWrapperItem.itemType,idxString)
                    txtRemoveOp.idx = activeWrapperItem.itemIndex
                    txtRemoveOp.add = False

                    if dimGen.show_dimension_fields:
                        col = box.column(align=True)
                        idx = 0

                        col.prop(item,"use_custom_text",text="Use Custom Dimension Text")
                        for textField in item.textFields:
                            if idx == 0 and not item.use_custom_text:
                                idx += 1
                                continue

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
                            idx += 1



                ### SETTINGS
                if dimGen.show_dimension_settings:
                    settingsIcon = 'DISCLOSURE_TRI_DOWN'
                else:
                    settingsIcon = 'DISCLOSURE_TRI_RIGHT'

                box = layout.box()
                col = box.column()
                row = col.row()
                row.prop(dimGen, 'show_dimension_settings',
                         text="", icon=settingsIcon, emboss=False)

                row.label(text=item.name + ' Settings:')
                if dimGen.show_dimension_settings:
                    eval('draw_' + activeWrapperItem.itemType +
                         '_settings(item, box)')



class OBJECT_MT_dimension_menu(bpy.types.Menu):
    bl_label = "Custom Menu"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            'measureit_arch.addfacetoarea',
            text="Add To Area", icon='ADD')
        layout.operator(
            'measureit_arch.removefacefromarea',
            text="Remove From Area", icon='REMOVE')

        layout.separator()

        layout.operator(
            'measureit_arch.cursortoarcorigin',
            text="Cursor to Arc Origin", icon='MOD_THICKNESS')

        layout.separator()

        delOp = layout.operator(
            "measureit_arch.deleteallitemsbutton", text="Delete All Dimensions", icon="X")
        delOp.is_style = False
        delOp.genPath = 'bpy.context.object.DimensionGenerator'


def draw_alignedDimensions_settings(dim, layout):

    if dim.is_style or not dim.uses_style:
        # Text Settings
        col = layout.column(align=True, heading='Text')
        col.template_ID(dim, "font", open="font.open",
                        unlink="font.unlink", text='Font')
        col = layout.column(align=True)
        col.prop(dim, 'fontSize', text='Font Size')
        col.prop(dim, 'textAlignment', text='Alignment')

        # Line Weight
        col = layout.column(align=True)
        col.prop(dim, 'lineWeight', text='Line Weight')

        # View Settings
        col = layout.column(align=True)
        col.prop_search(dim, 'visibleInView', bpy.context.scene, 'view_layers', text='Visible In View')
        col.prop(dim, 'dimViewPlane', text='View Plane')

        # Position Settings
        col = layout.column(align=True)
        col.prop(dim, 'dimOffset', text='Distance')
        col.prop(dim, 'dimLeaderOffset', text='Offset')
        col.prop(dim, 'dimRotation', text='Rotation')

        # Cap Settings
        col = layout.column(align=True)
        col.prop(dim, 'endcapA', text='Arrow Start')
        col.prop(dim, 'endcapB', text='End')
        col.prop(dim, 'endcapSize', text='Arrow Size')
        col.prop(dim, 'endcapArrowAngle', text='Arrow Angle')

        # Toggles
        col = layout.column(align=True)
        col.prop(dim, 'inFront', text='Draw in Front')
        col.prop(dim, 'evalMods')

    else:
        col = layout.column(align=True)
        col.prop(dim, 'dimViewPlane', text='View Plane Overide')

        # Unit Overrides
        col = layout.column(align=True)
        col.prop(dim, 'override_unit_system', text='Unit Override')
        if dim.override_unit_system == 'METRIC':
            col.prop(dim, 'override_metric_length', text='Metric Length Override')
        elif dim.override_unit_system == 'IMPERIAL':
            col.prop(dim, 'override_imperial_length', text='Imperial Length Override')

        col = layout.column(align=True)
        col.prop(dim, 'tweakOffset', text='Tweak Distance')
        col.prop(dim, 'textAlignment', text='Alignment')


def draw_boundsDimensions_settings(dim, layout):
    col = layout.column()
    col.prop_search(dim, 'dimCollection', bpy.data,
                    'collections', text="Collection", icon='GROUP')

    if not dim.uses_style:
        split = layout.split(factor=0.485)
        col = split.column()
        col.alignment = 'RIGHT'
        col.label(text='Font')
        col = split.column()

        col.template_ID(dim, "font", open="font.open", unlink="font.unlink")

        col = layout.column(align=True)
        col.prop(dim, 'dimViewPlane', text='View Plane')
    else:
        col.prop(dim, 'dimViewPlane', text='View Plane Overide')

    if not dim.uses_style:
        col.prop_search(dim, 'visibleInView', bpy.context.scene, 'view_layers', text='Visible In View')
        col.prop(dim, 'lineWeight', text='Line Weight')

    split = layout.split(factor=0.49)
    row = split.row(align=True)
    row.alignment = 'RIGHT'
    row.label(text='Axis')
    row = split.row(align=True)

    row.prop(dim, "drawAxis", text="", toggle=True)

    col = layout.column(align=True)
    col.prop(dim, 'dimOffset', text='Distance')
    col.prop(dim, 'dimLeaderOffset', text='Offset')
    col.prop(dim, 'dimRotation', text='Rotation')

    if not dim.uses_style:
        col = layout.column(align=True)
        col.prop(dim, 'fontSize', text='Font Size')
        col.prop(dim, 'textAlignment', text='Alignment')
        # col.prop(dim,'textPosition',text='Position')

        col = layout.column(align=True)
        col.prop(dim, 'endcapA', text='Arrow Start')
        col.prop(dim, 'endcapB', text='End')
        col.prop(dim, 'endcapSize', text='Arrow Size')
        col.prop(dim, 'endcapArrowAngle', text='Arrow Angle')

        col = layout.column(align=True)
        col.prop(dim, 'inFront', text='Draw in Front')

    col.prop(dim, 'calcAxisAligned', text='Always Use Axis Aligned Bounds')


def draw_axisDimensions_settings(dim, layout):
    col = layout.column()

    if not dim.uses_style:
        # Text Settings
        col = layout.column(align=True, heading='Text')
        col.template_ID(dim, "font", open="font.open",
                        unlink="font.unlink", text='Font')
        col = layout.column(align=True)
        col.prop(dim, 'fontSize', text='Font Size')


        # Line Weight
        col = layout.column(align=True)
        col.prop(dim, 'lineWeight', text='Line Weight')

        # View Settings
        col = layout.column(align=True)
        col.prop_search(dim, 'visibleInView', bpy.context.scene, 'view_layers', text='Visible In View')
        col.prop(dim, 'dimViewPlane', text='View Plane')

        # Axis Settings
        col = layout.column(align=True)
        col.prop(dim, 'dimAxis', text='Measurement Axis')
        col.prop_search(dim, 'dimAxisObject', bpy.data,
                        'objects', text='Custom Axis Object')

        # Position Settings
        col = layout.column(align=True)
        col.prop(dim, 'dimOffset', text='Distance')
        col.prop(dim, 'dimLeaderOffset', text='Offset')
        col.prop(dim, 'dimRotation', text='Rotation')

        # Cap Settings
        col = layout.column(align=True)
        col.prop(dim, 'endcapA', text='Arrow Start')
        col.prop(dim, 'endcapB', text='End')
        col.prop(dim, 'endcapSize', text='Arrow Size')
        col.prop(dim, 'endcapArrowAngle', text='Arrow Angle')

        # Toggles
        col = layout.column(align=True)
        col.prop(dim, 'inFront', text='Draw in Front')
        col.prop(dim, 'evalMods')

    else:
        col = layout.column(align=True)
        col.prop(dim, 'dimViewPlane', text='View Plane Overide')

        col = layout.column(align=True)
        col.prop(dim, 'dimAxis', text='Measurement Axis')
        col.prop_search(dim, 'dimAxisObject', bpy.data,
                        'objects', text='Custom Axis Object')

        col = layout.column(align=True)
        col.prop(dim, 'tweakOffset', text='Tweak Distance')
        col.prop(dim, 'textAlignment', text='Alignment')


def draw_angleDimensions_settings(dim, layout):
    col = layout.column()
    if not dim.uses_style:
        split = layout.split(factor=0.485)
        col = split.column()
        col.alignment = 'RIGHT'
        col.label(text='Font')
        col = split.column()

        col.template_ID(dim, "font", open="font.open", unlink="font.unlink")

        col = layout.column()

    col.prop_search(dim, 'visibleInView', bpy.context.scene, 'view_layers', text='Visible In View')

    if not dim.uses_style:
        col = layout.column(align=True)
        col.prop(dim, 'lineWeight', text='Line Weight')

    col.prop(dim, 'dimRadius', text='Radius')

    if not dim.uses_style:
        col = layout.column(align=True)
        col.prop(dim, 'fontSize', text='Font Size')
        col.prop(dim, 'textAlignment', text='Alignment')

        col.prop(dim, 'endcapA', text='Arrow Start')
        col.prop(dim, 'endcapB', text='End')
        col.prop(dim, 'endcapSize', text='Arrow Size')
        col.prop(dim, 'endcapArrowAngle', text='Arrow Angle')
        col.prop(dim, 'inFront', text='Draw in Front')
    col.prop(dim, 'reflexAngle', text='Use Reflex Angle')
    col.prop(dim, 'evalMods')
    # col.prop(dim, 'textPosition', text='Position')

    col = layout.column(align=True)


def draw_arcDimensions_settings(dim, layout):
    col = layout.column()

    if not dim.uses_style:
        split = layout.split(factor=0.485)
        col = split.column()
        col.alignment = 'RIGHT'
        col.label(text='Font')
        col = split.column()

        col.template_ID(dim, "font", open="font.open", unlink="font.unlink")

        col = layout.column()

    col.prop_search(dim, 'visibleInView', bpy.context.scene, 'view_layers', text='Visible In View')

    if not dim.uses_style:
        col = layout.column(align=True)
        col.prop(dim, 'lineWeight', text='Line Weight')

    col.prop(dim, 'dimOffset', text='Radius')

    if not dim.uses_style:
        col = layout.column(align=True)
        col.prop(dim, 'fontSize', text='Font Size')
        col = layout.column(align=True)
        col.prop(dim, 'endcapA', text='Arrow Start')
        col.prop(dim, 'endcapB', text='End')
        col.prop(dim, 'endcapC', text='Radius')
        col.prop(dim, 'endcapSize', text='Arrow Size')
        col.prop(dim, 'endcapArrowAngle', text='Arrow Angle')
        # col.prop(dim,'textPosition',text='Position')
    col = layout.column(align=True)
    col.prop(dim, 'displayAsAngle')
    col.prop(dim, 'showRadius')
    col.prop(dim, 'inFront', text='Draw in Front')

    col = layout.column(align=True)


def draw_areaDimensions_settings(dim, layout):
    col = layout.column(align=True)

    col.prop(dim, "fillColor", text='Fill Color')
    col.prop(dim, 'fillAlpha', text='Fill Amount')

    if not dim.uses_style:
        split = layout.split(factor=0.485)
        col = split.column()
        col.alignment = 'RIGHT'
        col.label(text='Font')
        col = split.column()

        col.template_ID(dim, "font", open="font.open", unlink="font.unlink")

        col = layout.column(align=True)
        col.prop(dim, 'dimViewPlane', text='View Plane')
    else:
        col.prop(dim, 'dimViewPlane', text='View Plane Overide')

    if not dim.uses_style:
        col.prop_search(dim, 'visibleInView', bpy.context.scene, 'view_layers', text='Visible In View')
        col.prop(dim, 'lineWeight', text='Line Weight')

    col = layout.column(align=True)
    col.prop(dim, 'dimTextPos', text='Text Position')
    col.prop(dim, 'dimRotation', text='Text Rotation')

    if not dim.uses_style:
        col = layout.column(align=True)
        col.prop(dim, 'fontSize', text='Font Size')
        col.prop(dim, 'textAlignment', text='Alignment')
        # col.prop(dim,'textPosition',text='Position')

        col = layout.column(align=True)
        col.prop(dim, 'inFront', text='Draw in Front')
        col.prop(dim, 'evalMods')


class TranslateDimensionOp(bpy.types.Operator):
    """ Move Dimension """
    bl_idname = "measureit_arch.dimension_offset"
    bl_label = "Adjust Dimension Offset"
    bl_options = {'GRAB_CURSOR', 'INTERNAL', 'BLOCKING', 'UNDO'}

    idx: IntProperty()
    dimType: StringProperty()
    offset: FloatProperty(name="Offset")
    objIndex: IntProperty()

    def modal(self, context, event):
        myobj = context.selected_objects[self.objIndex]
        dimension = eval('myobj.' + self.dimType)
        unit_system = bpy.context.scene.unit_settings.system

        # Set Tweak Flags
        tweak_snap = event.ctrl
        tweak_precise = event.shift
        styleOffset = event.alt
        

        if event.type == 'MOUSEMOVE':
            sensitivity = 0.01
            vecDelta = Vector(((event.mouse_x - self.init_mouse_x) * sensitivity,
                               (event.mouse_y - self.init_mouse_y) * sensitivity, 0))
            vecDelta = Vector(((event.mouse_x - self.init_mouse_x) * sensitivity,
                               (event.mouse_y - self.init_mouse_y) * sensitivity, 0))
            viewRot = context.area.spaces[0].region_3d.view_rotation
            vecDelta.rotate(viewRot)
            delta = (event.mouse_x - self.init_mouse_x) * sensitivity
            mat = myobj.matrix_world
            rot = mat.to_quaternion()

            axis = Vector((-1, -1, -1))
            axis.rotate(rot)

            delta = vecDelta.project(axis)
            delta = delta.magnitude
            if axis.dot(vecDelta) > 0:
                delta = -delta

            resultInit = self.init
            precise_factor = 10

            if unit_system == 'IMPERIAL':
                resultInit *= BU_TO_FEET
                delta *= BU_TO_FEET
                precise_factor = 12

            if tweak_snap:
                delta = round(delta)
                resultInit = round(self.init, 0)

            if tweak_precise:
                delta /= precise_factor
                resultInit = round(self.init, 1)

            if unit_system == 'IMPERIAL':
                resultInit /= BU_TO_FEET
                delta /= BU_TO_FEET

            value = resultInit + delta

            if dimension.uses_style and not styleOffset:
                dimension.tweakOffset = value
            elif dimension.uses_style and styleOffset:
                dimension.tweakOffset = self.init
                for alignedDimStyle in context.scene.StyleGenerator.alignedDimensions:
                    if alignedDimStyle.name == dimension.style:
                        alignedDimStyle.dimOffset = value
            else:
                dimension.dimOffset = value

            context.area.header_text_set(
                "Dimension Offset = {:.4f}".format(resultInit + delta))

        elif event.type == 'LEFTMOUSE':
            # Setting hide_viewport is a stupid hack to force Gizmos to update
            # after operator completes
            context.object.hide_viewport = False
            context.area.header_text_set(None)
            return {'FINISHED'}

        elif event.type == 'TAB' and event.value == 'PRESS':
            dimension.dimFlip = not dimension.dimFlip



        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            # Setting hide_viewport is a stupid hack to force Gizmos to update
            # after operator completes
            context.object.hide_viewport = False
            context.area.header_text_set(None)
            dimension.dimOffset = self.init

            return {'CANCELLED'}
        
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        myobj = context.selected_objects[self.objIndex]

        dimension = eval('myobj.' + self.dimType)
        self.init_mouse_x = event.mouse_x
        self.init_mouse_y = event.mouse_y
        self.init_flip = dimension.dimFlip

        self.init = dimension.dimOffset
        if dimension.uses_style:
            self.init = dimension.tweakOffset

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
