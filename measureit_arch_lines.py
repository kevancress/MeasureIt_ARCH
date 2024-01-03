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
# File: measureit_arch_main.py
# Main panel for different MeasureitArch general actions
# Author: Kevan Cress
#
# ----------------------------------------------------------

from email.policy import default
import bpy
import bmesh
import math

from bpy.types import PropertyGroup, Panel, Operator, UIList
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, \
    BoolProperty, StringProperty, FloatProperty, PointerProperty, EnumProperty
from mathutils import Vector

from datetime import datetime
from .measureit_arch_baseclass import BaseProp
from .measureit_arch_utils import get_smart_selected, get_selected_vertex, get_selected_vertex_history

def mark_invalid(self,context):
    self.is_invalid = True

class LineProperties(BaseProp, PropertyGroup):
    pointPass: BoolProperty(
        name="Draw Round Caps",
        description="Draw Round Caps",
        default=True)

    lineDrawHidden: BoolProperty(
        name="Draw Hidden Lines",
        description="Draw Hidden Lines",
        default=False)

    lineDrawDashed: BoolProperty(
        name="Draw Dashed",
        description="Force Line Group to Draw Dashed",
        default=False)

    screenSpaceDashes: BoolProperty(
        name="Screen Space Dashed",
        description="Draw Dashes in Screen Space",
        default=False)

    lineHiddenColor: FloatVectorProperty(
        name="Hidden Line Color",
        description="Color for Hidden Lines",
        default=(0.2, 0.2, 0.2, 1.0),
        min=0.0,
        max=1,
        subtype='COLOR',
        size=4,
        update = mark_invalid)

    lineHiddenWeight: FloatProperty(
        name="Hidden Line Lineweight",
        description="Hidden Line Lineweight",
        default=1.0,
        soft_min=1.0,
        step=25,
        min=0,
        update = mark_invalid)

    lineWeightGroup: StringProperty(name='Line Weight Group',
        update= mark_invalid)

    filterGroup: StringProperty(name='Filter by Group')

    invertGroupFilter: BoolProperty(default = False)

    weightGroupInfluence: FloatProperty(
        name='Group Influence',
        min=0,
        soft_max=1.0,
        max=10,
        default=0.0,
        subtype='FACTOR')

    lineHiddenDashScale: IntProperty(
        name="Hidden Line Dash Scale",
        description="Hidden Line Dash Scale",
        default=10,
        min=0)

    lineDashSpace: FloatProperty(
        name="Dash Spacing",
        description="Dash Spacing",
        default=0.5,
        min=0,
        max=1)

    lineTexture: PointerProperty(type=bpy.types.Texture)

    useLineTexture: BoolProperty(
        name="Use Line Texture",
        description='Use Line Texture',
        default=False)

    lineDepthOffset: FloatProperty(
        name="Line Depth Offset",
        description="Z buffer Offset tweak for clean rendering, TEMP",
        default=0.0)

    lineOverExtension: FloatProperty(
        name="Line Over Extension",
        default=0.0)
    randomSeed: IntProperty()

    useDynamicCrease: BoolProperty(
        name="Use Dynamic Crease",
        description='Dynamically update LineGroup by Crease (accounting for modifiers)\n'
                    'WARNING: This can be quite slow for large meshes \n or complex modifier stacks',
        default=False)

    creaseAngle: FloatProperty(
        name='Crease Angle',
        min=0,
        default=math.radians(30),
        subtype='ANGLE')

    dynamic_sil: BoolProperty(
        name="Dynamic silhouette",
        description='Dynamically add lines to silhouette edges on vector render \n'
                    'WARNING: This can be quite slow for large meshes \n or complex modifier stacks',
        default=False)

    chain: BoolProperty(
        name="Chain lines",
        description='Try to draw a line chain rather than line segments \n'
        'WARNING: EXPERIMENTAL, will likely break things, works best on single spline curves',
        default=False)

    endcapA: EnumProperty(
        items=(('NONE', "--", "No Cap"),
               ('D', "Dot", "Dot"),
               ('T', "Triangle", "Triangle")),
        name="A end",
        description="Add arrows to point A")
    
    endcapB: EnumProperty(
        items=(('NONE', "--", "No Cap"),
               ('D', "Dot", "Dot"),
               ('T', "Triangle", "Triangle")),
        name="B end",
        description="Add arrows to point B",
        default = 'NONE')

    num_dashes: IntProperty(
        name= "Num Dashes",
        description = 'Number of Dash Segments (1 - 4)',
        default = 1,
        min=1,
        max=4,
    )

    d1_length: IntProperty(
        name= "Dash 1 Length",
        description = 'Dash 1 Length in pixels',
        default = 5,
        min = 0,
        subtype='PIXEL'
    )

    d2_length: IntProperty(
        name= "Dash 2 Length",
        description = 'Dash 3 Length in pixels',
        default = 5,
        min = 0,
        subtype='PIXEL'
    )

    d3_length: IntProperty(
        name= "Dash 3 Length",
        description = 'Dash 3 Length in pixels',
        default = 5,
        min = 0,
        subtype='PIXEL'
    )

    d4_length: IntProperty(
        name= "Dash 4 Length",
        description = 'Dash 4 Length in pixels',
        default = 5,
        min = 0,
        subtype='PIXEL'
    )

    g1_length: IntProperty(
        name= "Gap 1 Length",
        description = 'Gap 1 Length in pixels',
        default = 5,
        min = 0,
        subtype='PIXEL'
    )

    g2_length: IntProperty(
        name= "Gap 2 Length",
        description = 'Gap 2 Length in pixels',
        default = 5,
        min = 0,
        subtype='PIXEL'
    )

    g3_length: IntProperty(
        name= "Gap 3 Length",
        description = 'Gap 3 Length in pixels',
        default = 5,
        min = 0,
        subtype='PIXEL'
    )

    g4_length: IntProperty(
        name= "Gap 3 Length",
        description = 'Gap 3 Length in pixels',
        default = 5,
        min = 0,
        subtype='PIXEL'
    )

def update_active(self,context):
    Generator = context.object.LineGenerator

    for item in Generator.line_groups:
        item.is_active = False

    activeItem = Generator.line_groups[Generator.active_index]
    activeItem.is_active = True

class LineContainer(PropertyGroup):
    line_num: IntProperty(
        name='Number of Line Groups', min=0, max=1000, default=0,
        description='Number total of line groups')

    active_index: IntProperty(
        name='Active Line Index',
        update = update_active)

    show_line_settings: BoolProperty(name='Show Line Settings', default=False)

    # Array of segments
    line_groups: CollectionProperty(type=LineProperties)


class AddLineButton(Operator):
    bl_idname = "measureit_arch.addlinebutton"
    bl_label = "Add"
    bl_description = "(EDITMODE) Creates a new Line Group from the selected edges"
    bl_category = 'MeasureitArch'

    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "MESH" and bpy.context.mode == 'EDIT_MESH':
                return True
            else:
                return False

    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # Add properties
            scene = context.scene
            sceneProps = scene.MeasureItArchProps
            mainobject = context.object
            selectionDict, warningStr = get_smart_selected(
                filterObj=mainobject, forceEdges=True)

            if len(selectionDict) >= 2:

                lineGen = mainobject.LineGenerator
                lGroup = lineGen.line_groups.add()

                # Set values
                lGroup.creation_time = str(int(datetime.utcnow().timestamp() * 100)) 
                lGroup.itemType = 'line_groups'
                lGroup.style = sceneProps.default_line_style
                if sceneProps.default_line_style != '':
                    lGroup.uses_style = True
                else:
                    lGroup.uses_style = False
                lGroup.lineWeight = 1
                lGroup.lineColor = sceneProps.default_color
                lGroup.name = 'Line ' + str(len(lineGen.line_groups))

                mylist = []
                for item in selectionDict:
                    mylist.append(item['vert'])
                lGroup['lineBuffer'] = mylist
                lineGen.line_num += 1

                # redraw
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt_ARCH: Select at least two vertices for creating measure segment.")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}


class AddDynamicLineButton(Operator):
    bl_idname = "measureit_arch.adddynamiclinebutton"
    bl_label = "Add"
    bl_description = "(EDITMODE) Creates a new Dynamic Line Group"
    bl_category = 'MeasureitArch'

    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if (o.type == "MESH" or o.type == "CURVE") and  bpy.context.mode == 'OBJECT':
                return True
            else:
                return False

    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # Add properties
            scene = context.scene
            sceneProps = scene.MeasureItArchProps

            for obj in context.selected_objects:
                lineGen = obj.LineGenerator
                lGroup = lineGen.line_groups.add()

                # Set values
                lGroup.creation_time = str(int(datetime.utcnow().timestamp() * 100))
                lGroup.itemType = 'line_groups'
                lGroup.style = sceneProps.default_line_style
                if sceneProps.default_line_style != '':
                    lGroup.uses_style = True
                else:
                    lGroup.uses_style = False
                lGroup.lineWeight = 1
                lGroup.lineColor = sceneProps.default_color
                lGroup.name = 'Line ' + str(len(lineGen.line_groups))

                lGroup.useDynamicCrease = True

                # redraw
                context.area.tag_redraw()
            return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}

class M_ARCH_UL_lines_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        scene = bpy.context.scene
        StyleGen = scene.StyleGenerator
        hasGen = True

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            line = item
            layout.use_property_decorate = False
            row = layout.row(align=True)
            subrow = row.row()
            subrow.prop(line, "name", text="", emboss=False, icon='MESH_CUBE')

            if line.visible:
                visIcon = 'HIDE_OFF'
            else:
                visIcon = 'HIDE_ON'

            if line.lineDrawHidden:
                hiddenIcon = 'MOD_WIREFRAME'
            else:
                hiddenIcon = 'MESH_CUBE'

            if line.uses_style:
                styleIcon = 'LINKED'
            else:
                styleIcon = 'UNLINKED'

            subrow = row.row(align=True)
            if not line.uses_style:
                subrow.scale_x = 0.5
                subrow.prop(line, 'color', emboss=True, text="")
                subrow.separator()
                row.prop(
                    line, 'lineDrawHidden', text="", toggle=True,
                    icon=hiddenIcon, emboss=False)
            else:
                row.prop_search(
                    line, 'style', StyleGen, 'line_groups', text="", icon='COLOR')
                
                row.separator()

            if hasGen:
                row = row.row(align=True)
                row.prop(line, 'uses_style', text="", toggle=True,
                         icon=styleIcon, emboss=False)

            row.prop(line, "visible", text="", icon=visIcon)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')


class OBJECT_PT_UILines(Panel):
    """ A panel in the Object properties window """
    bl_parent_id = 'OBJECT_PT_Panel'
    bl_label = "Line Groups"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon='MATCUBE')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        if context.object is not None:
            if 'LineGenerator' in context.object:
                lineGen = context.object.LineGenerator

                row = layout.row()

                # Draw The UI List
                row.template_list("M_ARCH_UL_lines_list", "", lineGen, "line_groups",
                                  lineGen, "active_index", rows=2, type='DEFAULT')

                # Operators Next to List
                col = row.column(align=True)
                op = col.operator(
                    "measureit_arch.deletepropbutton", text="", icon="X")
                op.genPath = 'bpy.context.object.LineGenerator'
                op.tag = lineGen.active_index  # saves internal data
                op.item_type = 'line_groups'
                op.is_style = False

                col.separator()
                up = col.operator("measureit_arch.movepropbutton", text="", icon="TRIA_UP")
                up.genPath = 'bpy.context.object.LineGenerator'
                up.item_type = 'line_groups'
                up.upDown = -1

                down = col.operator("measureit_arch.movepropbutton", text="", icon="TRIA_DOWN")
                down.genPath = 'bpy.context.object.LineGenerator'
                down.item_type = 'line_groups'
                down.upDown = 1


                col.separator()

                col.menu("OBJECT_MT_lines_menu", icon='DOWNARROW_HLT', text="")

                # Settings Below List
                if (len(lineGen.line_groups) > 0 and
                    lineGen.active_index < len(lineGen.line_groups)):

                    line = lineGen.line_groups[lineGen.active_index]
                    if lineGen.show_line_settings:
                        settingsIcon = 'DISCLOSURE_TRI_DOWN'
                    else:
                        settingsIcon = 'DISCLOSURE_TRI_RIGHT'
                    if line.uses_style:
                        settingsIcon = 'DOT'

                    box = layout.box()
                    col = box.column()
                    row = col.row()
                    row.prop(lineGen, 'show_line_settings', text="",
                             icon=settingsIcon, emboss=False)
                    if not line.uses_style:
                        row.label(text=line.name + ' Settings:')
                    else:
                        row.label(text=line.name + ' Uses Style Settings')

                    if lineGen.show_line_settings:
                        col = box.column(align=True)
                        StyleGen = context.scene.StyleGenerator
                        #col.prop_search(line, 'style_pointer', StyleGen, 'line_groups', text="", icon='COLOR')
                        if bpy.context.scene.MeasureItArchProps.show_dxf_props:
                            col.prop(line, 'cad_col_idx')
                        
                        col.prop(line, 'useDynamicCrease',
                                 text="Dynamic Crease")
                        col.prop(line, 'dynamic_sil', text = "Dynamic Silhouette")
                        if line.useDynamicCrease:
                            col.prop(line, 'creaseAngle',
                                     text="Crease Threshold")

                        col = box.column(align=True)
                        row = col.row(align=True)
                        row.prop_search(line, "filterGroup", context.active_object, "vertex_groups")
                        row.prop(line, "invertGroupFilter")

                        col.prop_search(line, "lineWeightGroup", context.active_object, "vertex_groups")
                        #col.prop(line, "weightGroupInfluence")
                        
                        if not line.uses_style:

                            col = box.column(align=True)
                            col.prop(line, 'lineWeight', text="Lineweight")


                            col = box.column(align=True)
                            col.prop_search(
                                line, 'visibleInView', bpy.context.scene,
                                'view_layers', text='Visible In View')

                            col = box.column(align=True)
                            col.prop(line, 'lineDepthOffset', text="Z Offset")

                            col = box.column(align=True)
                            #col.prop(line, 'lineOverExtension',
                            #         text="Extension")
                            # col.prop(line, 'randomSeed', text="Seed" )

                            col = box.column(align=True)
                            col.enabled = line.lineDrawHidden
                            col.prop(line, 'lineHiddenColor',
                                     text="Hidden Line Color")
                            col.prop(line, 'lineHiddenWeight',
                                     text="Hidden Line Weight")

                            col = box.column(align=True)
                            if line.lineDrawDashed or line.lineDrawHidden:
                                col.enabled = True
                            else:
                                col.enabled = False
                            #col.prop(line, 'lineHiddenDashScale',
                            #         text="Dash Scale")
                            #col.prop(line, 'lineDashSpace', text="Dash Spacing")
                            col.prop(line, 'num_dashes')

                            for i in range(line.num_dashes+1):
                                if i == 0: continue
                                c = col.column(align=True)
                                r = c.row(align = True)
                                r.prop(line, 'd{}_length'.format(i))
                                r.prop(line, 'g{}_length'.format(i), text="")

             

                            col = box.column(align=True)

                            col.prop(line, 'lineDrawDashed', text="Draw Dashed")
                            col.prop(line, 'screenSpaceDashes',
                                     text="Screen Space Dashes")
                            col.prop(line, 'inFront', text="Draw In Front")
                            col.prop(line, 'evalMods')
                        col.prop(line, 'pointPass', text="Round Caps")
                        col.prop(line, 'chain', text="Chain line")

                        col.prop(line, 'endcapA', text='Start Marker')
                        col.prop(line, 'endcapB', text='End Marker')
                        col.prop(line, 'endcapSize', text='End Marker')


class OBJECT_MT_lines_menu(bpy.types.Menu):
    bl_label = "Custom Menu"

    def draw(self, context):
        layout = self.layout
        lineGen = context.object.LineGenerator

        op = layout.operator(
            'measureit_arch.addtolinegroup',
            text="Add To Line Group", icon='ADD')
        op.tag = lineGen.active_index  # saves internal data
        op = layout.operator(
            'measureit_arch.removefromlinegroup',
            text="Remove From Line Group", icon='REMOVE')
        op.tag = lineGen.active_index  # saves internal data

        layout.separator()

        delOp = layout.operator(
            "measureit_arch.deleteallitemsbutton",
            text="Delete All Lines", icon="X")
        delOp.is_style = False
        delOp.genPath = 'bpy.context.object.LineGenerator'


class AddToLineGroup(Operator):
    bl_idname = "measureit_arch.addtolinegroup"
    bl_label = "Add Selection to Line Group"
    bl_description = "(EDIT MODE) Adds the current selection to the active Line Group"
    bl_category = 'MeasureitArch'
    tag: IntProperty()

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
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # get selected

                    mainobject = context.object
                    selectionDict, warningStr = get_smart_selected(
                        filterObj=mainobject, forceEdges=True)

                    if len(selectionDict) >= 2:

                        lineGen = mainobject.LineGenerator
                        lGroup = lineGen.line_groups[self.tag]

                        mylist = []
                        for item in selectionDict:
                            mylist.append(item['vert'])

                        bufferList = lGroup['lineBuffer'].to_list()
                        for x in range(0, len(mylist) - 1, 2):
                            bufferList.append(mylist[x])
                            bufferList.append(mylist[x + 1])

                        # redraw
                        lGroup['lineBuffer'] = bufferList
                        context.area.tag_redraw()
                    return {'FINISHED'}


class AddLineByProperty(Operator):
    bl_idname = "measureit_arch.addlinebyproperty"
    bl_label = "Add Lines By Crease"
    bl_description = "(OBJECT MODE) Creates a Line Group from edges with a crease greater than the specified angle"
    bl_category = 'MeasureitArch'
    tag: IntProperty()
    calledFromGroup: BoolProperty(default=False)
    includeNonManifold: BoolProperty(default=True)
    creaseAngle: FloatProperty(default=math.radians(30), subtype='ANGLE')

    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "MESH":
                if bpy.context.mode == 'OBJECT':
                    return True
                else:
                    return False
            else:
                return False

    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen
            scene = context.scene
            sceneProps = scene.MeasureItArchProps
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # get selected
                    selObjects = context.view_layer.objects.selected
                    for obj in selObjects:

                        lineGen = obj.LineGenerator
                        lGroup = lineGen.line_groups.add()

                        # Set values
                        lGroup.creation_time = str(int(datetime.utcnow().timestamp() * 100))
                        lGroup.itemType = 'line_groups'
                        lGroup.style = sceneProps.default_line_style
                        if sceneProps.default_line_style != '':
                            lGroup.uses_style = True
                        else:
                            lGroup.uses_style = False
                        lGroup.lineWeight = 1
                        lGroup.lineColor = sceneProps.default_color
                        lGroup.name = 'Line ' + str(len(lineGen.line_groups))
                        angle = self.creaseAngle
                        vertsToAdd = []

                        # Create a Bmesh Instance from the selected object
                        bm = bmesh.new()
                        bm.from_mesh(obj.data)
                        bm.edges.ensure_lookup_table()

                        # For each edge get its linked faces and vertex indicies
                        for edge in bm.edges:
                            linked_faces = edge.link_faces
                            pointA = edge.verts[0].index
                            pointB = edge.verts[1].index
                            if len(linked_faces) == 2:
                                normalA = Vector(
                                    linked_faces[0].normal).normalized()
                                normalB = Vector(
                                    linked_faces[1].normal).normalized()
                                dotProd = (normalA.dot(normalB))

                                if dotProd >= -1 and dotProd <= 1:
                                    creaseAngle = math.acos(dotProd)
                                    if creaseAngle > angle:
                                        vertsToAdd.append(pointA)
                                        vertsToAdd.append(pointB)

                            # Any edge with greater or less
                            # than 2 linked faces is non manifold
                            else:
                                if self.includeNonManifold:
                                    vertsToAdd.append(pointA)
                                    vertsToAdd.append(pointB)

                        # Free the Bmesh instance and add the
                        # vertex indices to the line groups line buffer
                        bm.free()
                        lGroup['lineBuffer'] = vertsToAdd
                        lineGen.line_num += 1
                    return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        mesh = context.object.data
        layout = self.layout
        col = layout.column()
        col.prop(self, 'creaseAngle', text='Set Crease Angle')
        col.prop(self, 'includeNonManifold',
                 text='Add Lines to Non-Manifold Edges?')


class RemoveFromLineGroup(Operator):
    bl_idname = "measureit_arch.removefromlinegroup"
    bl_label = "Remove Selection from Line Group"
    bl_description = "(EDIT MODE) Removes the current selection from the active Line Group"
    bl_category = 'MeasureitArch'
    tag: IntProperty()

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
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # get selected

                    mainobject = context.object
                    selectionDict, warningStr = get_smart_selected(
                        filterObj=mainobject, forceEdges=True)
                    
                    if len(selectionDict) >= 2:
                        
                        mylist = []
                        for item in selectionDict:
                            mylist.append(item['vert'])

                        lineGen = mainobject.LineGenerator
                        lGroup = lineGen.line_groups[self.tag]

                        bufferList = lGroup['lineBuffer'].to_list()
                        for x in range(0, len(lGroup['lineBuffer']), 2):
                            pointA = lGroup['lineBuffer'][x]
                            pointB = lGroup['lineBuffer'][x + 1]
                            for y in range(0, len(mylist), 2):
                                if sLineExists(pointA, pointB, mylist[y], mylist[y + 1]):
                                    # print("checked Pair: (" + str(mylist[y]) +   "," + str(mylist[y+1]) + ")" )
                                    # print("A:" + str(pointA) + "B:" + str(pointB) )
                                    del bufferList[x]
                                    del bufferList[x]

                        # redraw
                        lGroup['lineBuffer'] = bufferList
                        context.area.tag_redraw()
                        return {'FINISHED'}

# class UseLineTexture(Operator):
#     bl_idname = "measureit_arch.uselinetexture"
#     bl_label = "Create a Line Texture to Use"
#     bl_description = "Create a Line Texture to Use"
#     bl_category = 'MeasureitArch'
#     tag = IntProperty()
#     is_style= BoolProperty()
#     # ------------------------------
#     # Execute button action
#     # ------------------------------
#     def execute(self, context):
#         mainObj = context.object

#         if self.is_style:
#             Generator = context.scene.StyleGenerator
#         else:
#             Generator = mainObj.LineGenerator
#         line = Generator.line_groups[self.tag]

#         if 'Line Texture' not in bpy.data.textures:
#             texture = bpy.data.textures.new("Line Texture", type='NONE')
#             texture.use_nodes = True
#             nodes = texture.node_tree.nodes
#             nodes.clear()
#             node = nodes.new('TextureNodeCurveTime')
#             node.location = (100,100)
#         line.useLineTexture = True

#         return {'FINISHED'}


def sLineExists(pointA, pointB, a, b):
    if (pointA == a and pointB == b):
        return True
    elif (pointA == b and pointB == a):
        return True
    else:
        return False


def lineExists(lGroup, a, b):
    for x in range(0, len(lGroup['lineBuffer']), 2):
        pointA = lGroup['lineBuffer'][x]
        pointB = lGroup['lineBuffer'][x + 1]
        if (pointA == a and pointB == b):
            return True
        elif (pointA == b and pointB == a):
            return True
    return False
