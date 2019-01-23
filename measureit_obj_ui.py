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

# <pep8 compliant>

# ----------------------------------------------------------
# File: measureit_main.py
# Main panel for different Measureit general actions
# Author: Kevan Cress
#
# ----------------------------------------------------------
# noinspection PyUnresolvedReferences

import bpy

import bmesh
from bmesh import from_edit_mesh

import bgl
import gpu
from gpu_extras.batch import batch_for_shader

from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, BoolProperty, StringProperty, \
                      FloatProperty, EnumProperty
from bpy.app.handlers import persistent
# noinspection PyUnresolvedReferences
from .measureit_geometry import *
from .measureit_render import *
from .measureit_main import get_smart_selected, get_selected_vertex

class MeasureitObjDimensionsPanel(Panel):
    bl_idname = "obj_dimensions"
    bl_label = "Object Dimensions"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    
        
    def draw(self, context):
         scene = context.scene
         if context.object is not None:
            if 'MeasureGenerator' in context.object:
                layout = self.layout
                layout.use_property_split = True
                layout.use_property_decorate = False
                # -----------------
                # loop
                # -----------------
                
                mp = context.object.MeasureGenerator[0]
                if mp.measureit_num > 0:
                    row = layout.row(align = True)
                    row.operator("measureit.expandallsegmentbutton", text="Expand all", icon="ADD")
                    row.operator("measureit.collapseallsegmentbutton", text="Collapse all", icon="REMOVE")
                    for idx in range(0, mp.measureit_num):
                        if mp.measureit_segments[idx].glfree is False:
                            add_item(layout, idx, mp.measureit_segments[idx])

                    row = layout.row()
                    row.operator("measureit.deleteallsegmentbutton", text="Delete all", icon="X")
                # -----------------
                # Sum loop segments
                # -----------------
                if mp.measureit_num > 0:
                    scale = bpy.context.scene.unit_settings.scale_length
                    tx = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S",
                          "T", "U", "V", "W", "X", "Y", "Z"]
                    tot = [0.0] * len(tx)
                    ac = [False] * len(tx)
                    myobj = context.object
                    obverts = get_mesh_vertices(myobj)
                    viewtot = False
                    for idx in range(0, mp.measureit_num):
                        ms = mp.measureit_segments[idx]
                        if (ms.gltype == 1 or ms.gltype == 12
                            or ms.gltype == 13 or ms.gltype == 14) and ms.gltot != '99' \
                                and ms.glfree is False:  # only segments
                            if bpy.context.mode == "EDIT_MESH":
                                bm = bmesh.from_edit_mesh(bpy.context.edit_object.data)
                                if hasattr(bm.verts, "ensure_lookup_table"):
                                    bm.verts.ensure_lookup_table()
                            if ms.glpointa <= len(obverts) and ms.glpointb <= len(obverts):
                                p1 = get_point(obverts[ms.glpointa].co, myobj)
                                if ms.gltype == 1:
                                    p2 = get_point(obverts[ms.glpointb].co, myobj)
                                elif ms.gltype == 12:
                                    p2 = get_point((0.0,
                                                    obverts[ms.glpointa].co[1],
                                                    obverts[ms.glpointa].co[2]), myobj)
                                elif ms.gltype == 13:
                                    p2 = get_point((obverts[ms.glpointa].co[0],
                                                    0.0,
                                                    obverts[ms.glpointa].co[2]), myobj)
                                else:
                                    p2 = get_point((obverts[ms.glpointa].co[0],
                                                    obverts[ms.glpointa].co[1],
                                                    0.0), myobj)

                                dist, distloc = distance(p1, p2, ms.glocx, ms.glocy, ms.glocz)
                                if dist == distloc:
                                    usedist = dist
                                else:
                                    usedist = distloc
                                usedist *= scale
                                tot[int(ms.gltot)] += usedist
                                ac[int(ms.gltot)] = True
                                viewtot = True
                    # -----------------
                    # Print values
                    # -----------------
                    if viewtot is True:
                        pr = scene.measureit_gl_precision
                        fmt = "%1." + str(pr) + "f"
                        units = scene.measureit_units

                        box = layout.box()
                        box.label(text="Totals", icon='SOLO_ON')
                        final = 0
                        for idx in range(0, len(tot)):
                            if ac[idx] is True:
                                final += tot[idx]
                                tx_dist = format_distance(fmt, units, tot[idx])
                                row = box.row(align = True)
                                row.label(text="Group " + tx[idx] + ":")
                                row.label(text=" ")
                                row.label(text=tx_dist)

                        # Grand total
                        row = box.row(align=True)
                        row.label(text="")
                        row.label(text=" ")
                        row.label(text="-" * 20)
                        tx_dist = format_distance(fmt, units, final)

                        row = box.row(align=True)
                        row.label(text="")
                        row.label(text=" ")
                        row.label(text=tx_dist)
                        # delete all
                        row = box.row()
                        row.operator("measureit.deleteallsumbutton", text="Delete all", icon="X")

# -----------------------------------------------------
# Add segment options to the panel.
# -----------------------------------------------------
def add_item(layout, idx, segment):
    scene = bpy.context.scene
    if segment.gladvance is True:
        box = layout.box()
        row = box.row(align=True)
    else:
        row = layout.row(align=True)


    if segment.glview is True:
        icon = "VISIBLE_IPO_ON"
    else:
        icon = "VISIBLE_IPO_OFF"

    row.prop(segment, 'glview', text="", toggle=True, icon=icon)
    row.prop(segment, 'gladvance', text="", toggle=True, icon="PREFERENCES")
    row.prop(segment, 'style', text="")
    row.prop(segment, 'gltxt', text="")
    op = row.operator("measureit.deletesegmentbutton", text="", icon="X")
    op.tag = idx  # saves internal data

    if segment.gladvance is True:

        col = box.column()

        if segment.gltype == 20:  # Area special
            
            col.prop(segment, 'glcolorarea', text="Area Color")
            col.prop(segment, 'glcolor', text="Color")
        else:
            col.prop(segment, 'glcolor', text="Color")

        if segment.gltype != 9 and segment.gltype != 10 and segment.gltype != 20:
            col.prop(segment, 'gldefault', text="Automatic position")

            col = box.column(align=True)

            col.prop(segment, 'glspace', text="Distance")
            col.prop(segment, 'glwidth', text="Lineweight")
            if segment.gldefault is False:
                col.prop(segment, 'glnormalx', text="X")
                col.prop(segment, 'glnormaly', text="Y")
                col.prop(segment, 'glnormalz', text="Z")
            
            

        col = box.column(align=True)

        col.prop(segment, 'glfont_size', text="Font Size")
        col.prop(segment, 'glfont_rotat', text="Rotate")
        col.prop(segment, 'glfontx', text="X")
        col.prop(segment, 'glfonty', text="Y")
        col.prop(segment, 'glfont_align', text="Align")

        # Arrows
        if segment.gltype != 9 and segment.gltype != 10 and segment.gltype != 20:
            col = box.column(align=True)

            col.prop(segment, 'glarrow_a', text="Arrow Start ")
            col.prop(segment, 'glarrow_b', text="End ")
            if segment.glarrow_a != '99' or segment.glarrow_b != '99':
                col.prop(segment, 'glarrow_s', text="Size")

        if segment.gltype != 2 and segment.gltype != 10:
            col = box.column(align=True)
            if scene.measureit_gl_show_d is True and segment.gltype != 9 and segment.gltype != 21:
                if segment.gldist is True:
                    icon = "VISIBLE_IPO_ON"
                else:
                    icon = "VISIBLE_IPO_OFF"
                col.prop(segment, 'gldist', text="Distance", toggle=True, icon=icon)
            if scene.measureit_gl_show_n is True:
                if segment.glnames is True:
                    icon = "VISIBLE_IPO_ON"
                else:
                    icon = "VISIBLE_IPO_OFF"
                col.prop(segment, 'glnames', text="Text", toggle=True, icon=icon)
            # sum distances

            col = box.column(align=True)

            if segment.gltype == 1 or segment.gltype == 12 or segment.gltype == 13 or segment.gltype == 14:
                col.prop(segment, 'gltot', text="Sum")

        

        # Loc axis
        if segment.gltype != 2 and segment.gltype != 9 and segment.gltype != 10 \
                and segment.gltype != 11 and segment.gltype != 12 and segment.gltype != 13 \
                and segment.gltype != 14 and segment.gltype != 20:
            row = box.row(align = True)
            row.use_property_split = False
            row.prop(segment, 'glocx', text="X", toggle=True)
            row.prop(segment, 'glocy', text="Y", toggle=True)
            row.prop(segment, 'glocz', text="Z", toggle=True)
            if segment.glocx is False or segment.glocy is False or segment.glocz is False:
                row = box.row()
                if segment.gltype == 1:
                    row.prop(segment, 'glorto', text="Orthogonal")
                row.prop(segment, 'glocwarning', text="Warning")
                # ortogonal (only segments)
                if segment.gltype == 1:
                    if segment.glorto != "99":
                        row = box.row(align=True)
                        row.prop(segment, 'glorto_x', text="X", toggle=True)
                        row.prop(segment, 'glorto_y', text="Y", toggle=True)
                        row.prop(segment, 'glorto_z', text="Z", toggle=True)

        # Arc special
        if segment.gltype == 11:
            row = box.row(align = True)
            row.prop(segment, 'glarc_rad', text="Radius")
            row.prop(segment, 'glarc_len', text="Length")
            row.prop(segment, 'glarc_ang', text="Angle")

            row = box.row(align = True)
            row.prop(segment, 'glarc_txradio', text="")
            row.prop(segment, 'glarc_txlen', text="")
            row.prop(segment, 'glarc_txang', text="")
            row = box.row(align = True)
            row.prop(segment, 'glarc_full', text="Full Circle")
            if segment.glarc_rad is True:
                row.prop(segment, 'glarc_extrad', text="Adapt radio")

            row = box.row(align = True)
            row.prop(segment, 'glarc_a', text="")
            row.prop(segment, 'glarc_b', text="")
            if segment.glarc_a != '99' or segment.glarc_b != '99':
                row.prop(segment, 'glarc_s', text="Size")

class MeasureitObjLinesPanel(Panel):
    bl_idname = "obj_lines"
    bl_label = "Object Lines"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    
        
    def draw(self, context):
         scene = context.scene
         if context.object is not None:
            if 'LineGenerator' in context.object:
                layout = self.layout
                layout.use_property_split = True
                layout.use_property_decorate = False
                # -----------------
                # loop
                # -----------------
                
                mp = context.object.LineGenerator[0]
                if mp.line_num > 0:
                    row = layout.row(align = True)
                    #row.operator("measureit.expandallsegmentbutton", text="Expand all", icon="ADD")
                    #row.operator("measureit.collapseallsegmentbutton", text="Collapse all", icon="REMOVE")
                    for idx in range(0, mp.line_num):
                        add_line_item(layout, idx, mp.line_groups[idx])

                    row = layout.row()
                    #row.operator("measureit.deleteallsegmentbutton", text="Delete all", icon="X")
    
# -----------------------------------------------------
# Add line options to the panel.
# -----------------------------------------------------
def add_line_item(layout, idx, line):
    scene = bpy.context.scene
    if line.lineSettings is True:
        box = layout.box()
        row = box.row(align=True)
    else:
        row = layout.row(align=True)


    if line.lineVis is True:
        icon = "VISIBLE_IPO_ON"
    else:
        icon = "VISIBLE_IPO_OFF"

    row.prop(line, 'lineVis', text="", toggle=True, icon=icon)
    row.prop(line, 'lineSettings', text="",toggle=True, icon='PREFERENCES')
    row.prop(line, 'isOutline', text="", toggle=True, icon='SEQ_CHROMA_SCOPE')
    row.prop(line, 'lineDrawHidden', text="", toggle=True, icon='MOD_WIREFRAME')
    row.prop(line, 'lineColor', text="" )
    row.prop(line, 'lineWeight', text="")
    op = row.operator("measureit.deletelinebutton", text="", icon="X")
    op.tag = idx  # saves internal data
    
    if line.lineSettings is True:
        row = box.row(align=True)
        
        op = row.operator('measureit.addtolinegroup', text="Add Line", icon='ADD')
        op.tag = idx
        op = row.operator('measureit.removefromlinegroup', text="Remove Line", icon='REMOVE')
        op.tag = idx
        col = box.column()
        col.prop(line, 'lineWeight', text="Lineweight" )
        if line.lineDrawHidden is True:
            col = box.column()
            col.prop(line, 'lineHiddenColor', text="Hidden Line Color")
            col.prop(line, 'lineHiddenWeight',text="Hidden Line Weight")
            col.prop(line, 'lineHiddenDashScale',text="Dash Scale")
        



class DeleteLineButton(Operator):

    bl_idname = "measureit.deletelinebutton"
    bl_label = "Delete Line"
    bl_description = "Delete a Line"
    bl_category = 'Measureit'
    tag= IntProperty()

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        # Add properties
        mainObj = context.object
        mp = mainObj.LineGenerator[0]
        ms = mp.line_groups[self.tag]
        ms.lineFree = True
        # Delete element
        mp.line_groups.remove(self.tag)
        mp.line_num -= 1
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

class AddToLineGroup(Operator):   
    bl_idname = "measureit.addtolinegroup"
    bl_label = "Add Selection to Line Group"
    bl_description = "Add Selection to Line Group"
    bl_category = 'Measureit'
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

class RemoveFromLineGroup(Operator):   
    bl_idname = "measureit.removefromlinegroup"
    bl_label = "Remove Selection from Line Group"
    bl_description = "Remove Selection from Line Group"
    bl_category = 'Measureit'
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