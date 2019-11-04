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

import bpy
import bmesh
import bgl
import gpu
from bmesh import from_edit_mesh
from gpu_extras.batch import batch_for_shader
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D, UIList
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, BoolProperty, StringProperty, \
                      FloatProperty, EnumProperty, PointerProperty
from bpy.app.handlers import persistent
from .measureit_arch_geometry import *
from .measureit_arch_render import *
from .measureit_arch_main import get_smart_selected, get_selected_vertex
from .measureit_arch_baseclass import BaseProp

class SingleLineProperties(PropertyGroup):
    pointA: IntProperty(name = "pointA",
                        description = "first vertex index of the line")
                        
    pointB: IntProperty(name = "pointB",
                        description = "Second vertex index of the line")
bpy.utils.register_class(SingleLineProperties)

class LineProperties(BaseProp, PropertyGroup):
    numLines: IntProperty(name="Number of Lines",
                        description="Number Of Single Lines")

    lineDrawHidden: BoolProperty(name= "Draw Hidden Lines",
                        description= "Draw Hidden Lines",
                        default= False)

    lineDrawDashed: BoolProperty(name= "Draw Dashed",
                        description= "Force Line Group to Draw Dashed",
                        default= False)
    
    screenSpaceDashes: BoolProperty(name= "Screen Space Dashed",
                        description= "Draw Dashes in Screen Space",
                        default= False)

    lineHiddenColor: FloatVectorProperty(name="Hidden Line Color",
                        description="Color for Hidden Lines",
                        default=(0.2, 0.2, 0.2, 1.0),
                        min=0.0,
                        max=1,
                        subtype='COLOR',
                        size=4) 

    lineHiddenWeight: IntProperty(name="Hidden Line Lineweight",
                        description="Hidden Line Lineweight",
                        default= 1,
                        min = 0)
    
    lineHiddenDashScale: IntProperty(name="Hidden Line Dash Scale",
                        description="Hidden Line Dash Scale",
                        default= 10,
                        min = 0)

    isOutline: BoolProperty(name= "Is Outline",
                        description= "Line Group Is For Drawing Outlines",
                        default=False)
    
    lineTexture: PointerProperty(type= bpy.types.Texture)

    useLineTexture: BoolProperty(name="Use Line Texture",
                        description='Use Line Texture',
                        default = False)

    lineDepthOffset: FloatProperty(name= "Line Depth Offset",
                        description= "Z buffer Offset tweak for clean rendering, TEMP",
                        default = 0.0)
    #collection of individual line segments                        
    singleLine: CollectionProperty(type=SingleLineProperties)
bpy.utils.register_class(LineProperties)

class LineContainer(PropertyGroup):
    line_num: IntProperty(name='Number of Line Groups', min=0, max=1000, default=0,
                                description='Number total of line groups')
    
    active_line_index: IntProperty(name='Active Line Index')

    show_line_settings: BoolProperty(name='Show Line Settings', default=False)

    # Array of segments
    line_groups: CollectionProperty(type=LineProperties)

bpy.utils.register_class(LineContainer)
Object.LineGenerator = CollectionProperty(type=LineContainer)

class AddLineButton(Operator):
    bl_idname = "measureit_arch.addlinebutton"
    bl_label = "Add"
    bl_description = "(EDITMODE only) Add a new measure segment between 2 vertices (select 2 vertices or more)"
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
            mylist = get_smart_selected(mainobject)
            if len(mylist) < 2:  # if not selected linked vertex
                mylist = get_selected_vertex(mainobject)

            if len(mylist) >= 2:
                if 'LineGenerator' not in mainobject:
                    mainobject.LineGenerator.add()

                lineGen = mainobject.LineGenerator[0]
                lGroup = lineGen.line_groups.add()

                # Set values
                lGroup.itemType = 'L'
                lGroup.style = scene.measureit_arch_default_line_style
                if scene.measureit_arch_default_line_style is not '':
                    lGroup.uses_style = True
                else:
                    lGroup.uses_style = False
                lGroup.lineWeight = 1     
                lGroup.lineColor = scene.measureit_arch_default_color
                lGroup.name = 'Line ' + str(len(lineGen.line_groups))
                
                for x in range (0, len(mylist)-1, 2):
                    sLine = lGroup.singleLine.add()
                    sLine.pointA = mylist[x]
                    sLine.pointB = mylist[x+1]
                    lGroup.numLines +=1

                lineGen.line_num += 1


                # redraw
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: Select at least two vertices for creating measure segment.")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}


class M_ARCH_UL_lines_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):    
        scene = bpy.context.scene
        hasGen = False
        if 'StyleGenerator' in scene:
            StyleGen = scene.StyleGenerator[0]
            hasGen = True
            
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            line = item
            layout.use_property_decorate = False
            row = layout.row(align=True)
            subrow = row.row()
            subrow.prop(line, "name", text="",emboss=False,icon='MESH_CUBE')
            
            if line.visible: visIcon = 'HIDE_OFF'
            else: visIcon = 'HIDE_ON'

            if line.isOutline: outIcon = 'SEQ_CHROMA_SCOPE' 
            else: outIcon = 'FILE_3D'

            if line.lineDrawHidden: hiddenIcon = 'MOD_WIREFRAME'
            else: hiddenIcon = 'MESH_CUBE'

            if line.uses_style: styleIcon = 'LINKED'
            else: styleIcon = 'UNLINKED'
            
            subrow = row.row(align=True)
            if not line.uses_style:
                subrow.scale_x = 0.5
                subrow.prop(line, 'color',emboss=True, text="")
                subrow.separator()
                row.prop(line, 'isOutline', text="", toggle=True, icon=outIcon,emboss=False)
                row.prop(line, 'lineDrawHidden', text="", toggle=True, icon=hiddenIcon)
            else:
                row.prop_search(line,'style', StyleGen,'line_groups',text="", icon='COLOR')
                row.separator()

            if hasGen:
                row = row.row(align=True)
                row.prop(line, 'uses_style', text="",toggle=True, icon=styleIcon,emboss=False)
            
            row.prop(line, "visible", text="", icon = visIcon)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')

class OBJECT_PT_UILines(Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "MeasureIt-ARCH Lines"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        obj = context.object
        if context.object is not None:
            if 'LineGenerator' in context.object:     
                scene = context.scene
                lineGen = context.object.LineGenerator[0]

                row = layout.row()
                
                # Draw The UI List
                row.template_list("M_ARCH_UL_lines_list", "", lineGen, "line_groups", lineGen, "active_line_index",rows=2, type='DEFAULT')
                
                # Operators Next to List
                col = row.column(align=True)
                op = col.operator("measureit_arch.deletepropbutton", text="", icon="X")
                op.tag = lineGen.active_line_index  # saves internal data
                op.item_type = 'L'
                op.is_style = False
                col.separator()

                col.menu("OBJECT_MT_lines_menu", icon='DOWNARROW_HLT', text="")


                
                # Settings Below List
                if len(lineGen.line_groups) > 0 and  lineGen.active_line_index < len(lineGen.line_groups):
                         
                    line = lineGen.line_groups[lineGen.active_line_index]
                    if lineGen.show_line_settings: settingsIcon = 'DISCLOSURE_TRI_DOWN'
                    else: settingsIcon = 'DISCLOSURE_TRI_RIGHT'
                    if line.uses_style: settingsIcon = 'DOT'
                        
                    box = layout.box()
                    col = box.column() 
                    row = col.row()
                    row.prop(lineGen, 'show_line_settings', text="", icon=settingsIcon,emboss=False)
                    if not line.uses_style: row.label(text= line.name + ' Settings:')
                    else: row.label(text= line.name + ' Uses Style Settings')

                    if lineGen.show_line_settings:
                        if not line.uses_style:
                            col.prop(line, 'lineWeight', text="Lineweight" )
                            col.prop(line, 'lineDepthOffset', text="Z Offset")
                        
                            col = box.column(align=True)
                            if line.lineDrawHidden: col.enabled = True
                            else: col.enabled = False
                            col.prop(line, 'lineHiddenColor', text="Hidden Line Color")
                            col.prop(line, 'lineHiddenWeight',text="Hidden Line Weight")

                            col = box.column(align=True)
                            if line.lineDrawDashed or line.lineDrawHidden: col.enabled = True
                            else: col.enabled = False
                            col.prop(line, 'lineHiddenDashScale',text="Dash Scale")

                            col = box.column(align=True)
                            col.prop(line, 'lineDrawDashed', text="Draw Dashed")
                            col.prop(line, 'screenSpaceDashes', text="Screen Space Dashes")

class OBJECT_MT_lines_menu(bpy.types.Menu):
    bl_label = "Custom Menu"

    def draw(self,context):
        layout = self.layout
        scene = context.scene
        lineGen = context.object.LineGenerator[0]

        op = layout.operator('measureit_arch.addtolinegroup', text="Add To Line Group", icon='ADD')
        op.tag = lineGen.active_line_index  # saves internal data
        op = layout.operator('measureit_arch.removefromlinegroup', text="Remove From Line Group", icon='REMOVE')
        op.tag = lineGen.active_line_index  # saves internal data

        layout.separator()

        delOp = layout.operator("measureit_arch.deleteallitemsbutton", text="Delete All Lines", icon="X")
        delOp.is_style = False
        delOp.item_type = 'L'

class AddToLineGroup(Operator):   
    bl_idname = "measureit_arch.addtolinegroup"
    bl_label = "Add Selection to Line Group"
    bl_description = "(EDIT MODE) Adds the current selection to the active Line Group"
    bl_category = 'MeasureitArch'
    tag= IntProperty()

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
         for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # get selected

                    mainobject = context.object
                    mylist = get_smart_selected(mainobject)
                    if len(mylist) < 2:  # if not selected linked vertex
                        mylist = get_selected_vertex(mainobject)

                    if len(mylist) >= 2:

                        lineGen = mainobject.LineGenerator[0]
                        lGroup = lineGen.line_groups[self.tag]
                        

                        for x in range (0, len(mylist)-1, 2):
                            if lineExists(lGroup,mylist[x],mylist[x+1]) is False:

                                sLine = lGroup.singleLine.add()
                                sLine.pointA = mylist[x]
                                sLine.pointB = mylist[x+1]
                                lGroup.numLines +=1
                                #print("line made" + str(sLine.pointA) + ", " +str(sLine.pointB))

                                # redraw
                                context.area.tag_redraw()
                        return {'FINISHED'}

class AddLineByProperty(Operator):   
    bl_idname = "measureit_arch.addlinebyproperty"
    bl_label = "Add Lines By Crease"
    bl_description = "Add Lines to Edges sharper than the specified angle (uses Autosmooth Angle) OBJECT MODE ONLY"
    bl_category = 'MeasureitArch'
    tag= IntProperty()
    calledFromGroup= BoolProperty(default=False)

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
         for window in bpy.context.window_manager.windows:
            screen = window.screen
            scene = context.scene
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # get selected
                    selObjects = context.view_layer.objects.selected
                    for obj in selObjects:
                        if 'LineGenerator' not in obj:
                            obj.LineGenerator.add()

                        lineGen = obj.LineGenerator[0]
                        lGroup = lineGen.line_groups.add()
                        
                        # Set values
                        lGroup.itemType = 'L'
                        lGroup.style = scene.measureit_arch_default_line_style
                        if scene.measureit_arch_default_line_style is not '':
                            lGroup.uses_style = True
                        else:
                            lGroup.uses_style = False
                        lGroup.lineWeight = 1     
                        lGroup.lineColor = scene.measureit_arch_default_color
                        lGroup.name = 'Line ' + str(len(lineGen.line_groups))
                        angle = obj.data.auto_smooth_angle
                        edgesToAdd = []

                        for edge in obj.data.edges:
                            pointA = edge.vertices[0]
                            pointB = edge.vertices[1]
                            adjacentFaces =[]
                            for face in obj.data.polygons:
                                if pointA in face.vertices and pointB in face.vertices:
                                    adjacentFaces.append(face)
                            if len(adjacentFaces) == 2:
                                normalA = Vector(adjacentFaces[0].normal)
                                normalB = Vector(adjacentFaces[1].normal)
                                dotProd = (normalA.dot(normalB))
                                #print (str(adjacentFaces[0].index) + ' dot(' + str(adjacentFaces[1].index) + ') = ' + str(dotProd))
                                if dotProd >= -1 and dotProd <= 1:
                                    creaseAngle = math.acos(dotProd)
                                    if creaseAngle > angle:
                                        edgesToAdd.append(edge)
                            else:
                                edgesToAdd.append(edge)
                        
                        for edge in edgesToAdd:
                            sLine = lGroup.singleLine.add()
                            sLine.pointA = edge.vertices[0]
                            sLine.pointB = edge.vertices[1]
                            lGroup.numLines +=1

                        lineGen.line_num += 1

                    return {'FINISHED'}
    
    def invoke(self, context, event):
        wm = context.window_manager
        if not context.object.data.use_auto_smooth:
            context.object.data.use_auto_smooth = True
            bpy.ops.object.shade_smooth()
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)
    
    def draw(self,context):
        mesh = context.object.data
        layout = self.layout
        col = layout.column()
        col.prop(mesh,'auto_smooth_angle', text= 'Set Crease Angle')

class RemoveFromLineGroup(Operator):   
    bl_idname = "measureit_arch.removefromlinegroup"
    bl_label = "Remove Selection from Line Group"
    bl_description = "(EDIT MODE) Removes the current selection from the active Line Group"
    bl_category = 'MeasureitArch'
    tag= IntProperty()

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
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # get selected

                    mainobject = context.object
                    mylist = get_smart_selected(mainobject)

                    if len(mylist) < 2:  # if not selected linked vertex
                        mylist = get_selected_vertex(mainobject)

                    if len(mylist) >= 2:

                        lineGen = mainobject.LineGenerator[0]
                        lGroup = lineGen.line_groups[self.tag]
                        idx = 0
                        for sLine in lGroup.singleLine:
                            for x in range (0, len(mylist), 2):
                                if sLineExists(sLine,mylist[x],mylist[x+1]):
                                    #print("checked Pair: (" + str(mylist[x]) +   "," + str(mylist[x+1]) + ")" )
                                    #print("A:" + str(sLine.pointA) + "B:" + str(sLine.pointB) ) 
                                    lGroup.singleLine.remove(idx) 
                                    lGroup.numLines -= 1     
                            idx +=1
  
                        # redraw
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

#         if self.is_style is True:
#             Generator = context.scene.StyleGenerator[0]
#         else:
#             Generator = mainObj.LineGenerator[0]
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

def sLineExists(sLine,a,b):
    if (sLine.pointA == a and sLine.pointB == b):
        return True
    elif (sLine.pointA == b and sLine.pointB == a):
        return True
    else:
        return False

def lineExists(lGroup,a,b):
    for sLine in lGroup.singleLine:
        if (sLine.pointA == a and sLine.pointB == b):
            return True
        elif (sLine.pointA == b and sLine.pointB == a):
            return True
    return False