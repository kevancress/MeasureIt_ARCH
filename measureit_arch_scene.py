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
# File: measureit_arch_main.py
# Main panel for different MeasureitArch general actions
# Author: Antonio Vazquez (antonioya), Kevan Cress
#
# ----------------------------------------------------------

import bpy
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D, Scene
from bpy.props import (
        CollectionProperty,
        FloatVectorProperty,
        IntProperty,
        BoolProperty,
        StringProperty,
        FloatProperty,
        EnumProperty,
        )

###################################
#
#            PANELS
#
###################################

class MeasureitArchDimensionStylesPanel(Panel):
    bl_idname = "measureit_arch.dim_styles"
    bl_label = "Dimension Styles"
    bl_space_type = 'PROPERTIES'
    bl_region_type = "WINDOW"
    bl_context = 'scene'
    bl_options = {'DEFAULT_CLOSED'}

    # ------------------------------
    # Draw UI
    # ------------------------------
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        scene = context.scene
        
        #-------------------
        # Add Styles to Panel
        #--------------------
        col = layout.column()
        col.operator("measureit_arch.adddimstylebutton", text="New Dimension Style", icon="ADD")
        if 'StyleGenerator' in context.scene:
            styleGen = context.scene.StyleGenerator[0]

            if styleGen.style_num > 0:
                for idx in range(0, styleGen.style_num):
                    add_style_item(layout, idx, styleGen.measureit_arch_styles[idx])
       
        col = layout.column()
        col.operator("measureit_arch.deleteallstylesbutton", text="Delete All Styles", icon="X")

class MeasureitArchDimensionSettingsPanel(Panel):
    bl_idname = "measureit_arch.settings_panel"
    bl_label = "Dimension Settings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'

    # -----------------------------------------------------
    # Draw (create UI interface)
    # -----------------------------------------------------
    # noinspection PyUnusedLocal
    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        scene = context.scene

        row = layout.row()

        col = layout.column(align=True)
        col.prop(scene, "measureit_arch_default_style", text="Active Style")

        col = layout.column(align = True)
        col.prop(scene, 'measureit_arch_gl_precision', text="Precision")
        col.prop(scene, 'measureit_arch_units')

        col = layout.column(align=True)
        col.prop(scene, 'measureit_arch_gl_show_d', text="Distances", toggle=True, icon="DRIVER_DISTANCE")
        col.prop(scene, 'measureit_arch_gl_show_n', text="Texts", toggle=True, icon="FONT_DATA")
        #col.prop(scene, 'measureit_arch_hide_units', text="Units", toggle=True, icon="DRIVER_DISTANCE")
        
        # Scale factor
        col = layout.column(align = True)
        col.use_property_split= True
        col.alignment = 'RIGHT'
        col.label(text = 'Override:')
        col.prop(scene, 'measureit_arch_scale', text="Scale",toggle=True,icon="EMPTY_ARROWS")
        col.prop(scene, 'measureit_arch_ovr', text="Style",toggle=True,icon="TRACKING_FORWARDS_SINGLE")

        if scene.measureit_arch_scale is True:
            scaleBox = layout.box()
            scaleBox.label(text='Scale Override')
            col = scaleBox.column(align = True)
            col.prop(scene, 'measureit_arch_scale_color', text="Color")
            col.prop(scene, 'measureit_arch_scale_factor', text="Factor")

            col = scaleBox.column(align = True)
            col.prop(scene, 'measureit_arch_gl_scaletxt', text="Text")
            col.prop(scene, 'measureit_arch_scale_font', text="Font Size")
            col.prop(scene, 'measureit_arch_scale_precision', text="Precision")
            
            col = scaleBox.column(align = True)
            col.prop(scene, 'measureit_arch_scale_pos_x')
            col.prop(scene, 'measureit_arch_scale_pos_y')

        # Override
        
        if scene.measureit_arch_ovr is True:
            styleBox = layout.box()
            styleBox.label(text='Style Override')
            col = styleBox.column(align = True)
            col.prop(scene, 'measureit_arch_ovr_color', text="Colour")
            col.prop(scene, 'measureit_arch_ovr_width', text="Width")
            col = styleBox.column(align = True)
            col.prop(scene, 'measureit_arch_ovr_font', text="Font Size")
            col.prop(scene, 'measureit_arch_ovr_font_align', text="Alignment")
            if scene.measureit_arch_ovr_font_align == 'L':
                col.prop(scene, 'measureit_arch_ovr_font_rotation', text="Rotation")

def add_style_item(box, idx, style):

    if style.gladvance is True:
        box = box.box()
    row = box.row(align=True)
    if style.glview is True:
        icon = "VISIBLE_IPO_ON"
    else:
        icon = "VISIBLE_IPO_OFF"
    
    row.prop(style, 'glview', text="", toggle=True, icon=icon)
    row.prop(style, 'gladvance', text="", toggle=True, icon="PREFERENCES")

    split = row.split(factor=0.25, align=True)
    split.prop(style, 'glcolor', text="")
    split.prop(style, 'styleName', text="")
    op = row.operator("measureit_arch.deletestylebutton", text="", icon="X")
    op.tag = idx  # saves internal data

    if style.gladvance is True:
        col = box.column()
        #col.prop(style, 'gltxt', text="Text")
        #col.prop(style, 'gldefault', text="Automatic position")

        col = box.column(align=True)

        #col.prop(style, 'glspace', text="Distance")
        col.prop(style, 'glwidth', text="Lineweight")
        #if style.gldefault is False:
        #    col.prop(style, 'glnormalx', text="X")
        #    col.prop(style, 'glnormaly', text="Y")
        #    col.prop(style, 'glnormalz', text="Z")
    
        col = box.column(align=True)

        col.prop(style, 'glfont_size', text="Font Size")
        col.prop(style, 'glfont_rotat', text="Rotate")
        #col.prop(style, 'glfontx', text="X")
        #col.prop(style, 'glfonty', text="Y")
        col.prop(style, 'glfont_align', text="Align")
        
        # Arrows
        
        col = box.column(align=True)

        col.prop(style, 'glarrow_a', text="Arrow Start ")
        col.prop(style, 'glarrow_b', text="End ")
        if style.glarrow_a != '99' or style.glarrow_b != '99':
            col.prop(style, 'glarrow_s', text="Size")


###################################
#
#       Style Properties
#
###################################

class StyleProperties(PropertyGroup):
    styleName: StringProperty(name="styleName",
                            description="Name of The Dimension Style")
    gltype: IntProperty(name="gltype",
                         description="Measure type (1-Segment, 2-Label, etc..)", default=1)
    glpointa: IntProperty(name="glpointa",
                           description="Hidden property for opengl")
    glpointb: IntProperty(name="glpointb",
                           description="Hidden property for opengl")
    glpointc: IntProperty(name="glpointc",
                           description="Hidden property for opengl")
    glcolor: FloatVectorProperty(name="glcolor",
                                  description="Color for the measure",
                                  default=(0.173, 0.545, 1.0, 1.0),
                                  min=0.1,
                                  max=1,
                                  subtype='COLOR',
                                  size=4)
    glview: BoolProperty(name="glview",
                          description="Measure visible/hide",
                          default=True)
    glspace: FloatProperty(name='glspace', min=-100, max=100, default=0.1,
                            precision=3,
                            description='Distance to display measure')
    glwidth: IntProperty(name='glwidth', min=1, max=20, default=1,
                          description='line width')
    glfree: BoolProperty(name="glfree",
                          description="This measure is free and can be deleted",
                          default=False)
    gltxt: StringProperty(name="gltxt", maxlen=256,
                           description="Short description (use | for line break)")
    gladvance: BoolProperty(name="gladvance",
                             description="Advanced options as line width or position",
                             default=False)
    gldefault: BoolProperty(name="gldefault",
                             description="Display measure in position calculated by default",
                             default=True)
    glnormalx: FloatProperty(name="glnormalx",
                              description="Change orientation in X axis",
                              default=1, min=-1, max=1, precision=2)
    glnormaly: FloatProperty(name="glnormaly",
                              description="Change orientation in Y axis",
                              default=0, min=-1, max=1, precision=2)
    glnormalz: FloatProperty(name="glnormalz",
                              description="Change orientation in Z axis",
                              default=0, min=-1, max=1, precision=2)
    glfont_size: IntProperty(name="Text Size",
                              description="Text size",
                              default=14, min=6, max=150)
    glfont_align: EnumProperty(items=(('L', "Left align", ""),
                                       ('C', "Center align", ""),
                                       ('R', "Right align", "")),
                                name="align Font",
                                description="Set Font alignment")
    glfont_rotat: IntProperty(name='Rotate', min=0, max=360, default=0,
                                description="Text rotation in degrees")
    gllink: StringProperty(name="gllink",
                            description="linked object for linked measures")
    glocwarning: BoolProperty(name="glocwarning",
                               description="Display a warning if some axis is not used in distance",
                               default=True)
    glocx: BoolProperty(name="glocx",
                         description="Include changes in X axis for calculating the distance",
                         default=True)
    glocy: BoolProperty(name="glocy",
                         description="Include changes in Y axis for calculating the distance",
                         default=True)
    glocz: BoolProperty(name="glocz",
                         description="Include changes in Z axis for calculating the distance",
                         default=True)
    glfontx: IntProperty(name="glfontx",
                          description="Change font position in X axis",
                          default=0, min=-3000, max=3000)
    glfonty: IntProperty(name="glfonty",
                          description="Change font position in Y axis",
                          default=0, min=-3000, max=3000)
    gldist: BoolProperty(name="gldist",
                          description="Display distance for this measure",
                          default=True)
    glnames: BoolProperty(name="glnames",
                           description="Display text for this measure",
                           default=True)
    gltot: EnumProperty(items=(('99', "-", "Select a group for sum"),
                                ('0', "A", ""),
                                ('1', "B", ""),
                                ('2', "C", ""),
                                ('3', "D", ""),
                                ('4', "E", ""),
                                ('5', "F", ""),
                                ('6', "G", ""),
                                ('7', "H", ""),
                                ('8', "I", ""),
                                ('9', "J", ""),
                                ('10', "K", ""),
                                ('11', "L", ""),
                                ('12', "M", ""),
                                ('13', "N", ""),
                                ('14', "O", ""),
                                ('15', "P", ""),
                                ('16', "Q", ""),
                                ('17', "R", ""),
                                ('18', "S", ""),
                                ('19', "T", ""),
                                ('20', "U", ""),
                                ('21', "V", ""),
                                ('22', "W", ""),
                                ('23', "X", ""),
                                ('24', "Y", ""),
                                ('25', "Z", "")),
                         name="Sum in Group",
                         description="Add segment length in selected group")
    glorto: EnumProperty(items=(('99', "None", ""),
                                 ('0', "A", "Point A must use selected point B location"),
                                 ('1', "B", "Point B must use selected point A location")),
                          name="Orthogonal",
                          description="Display point selected as orthogonal (select axis to copy)")
    glorto_x: BoolProperty(name="ox",
                            description="Copy X location",
                            default=False)
    glorto_y: BoolProperty(name="oy",
                            description="Copy Y location",
                            default=False)
    glorto_z: BoolProperty(name="oz",
                            description="Copy Z location",
                            default=False)
    glarrow_a: EnumProperty(items=(('99', "--", "No arrow"),
                                    ('1', "Line", "The point of the arrow are lines"),
                                    ('2', "Triangle", "The point of the arrow is triangle"),
                                    ('3', "TShape", "The point of the arrow is a T")),
                             name="A end",
                             description="Add arrows to point A")
    glarrow_b: EnumProperty(items=(('99', "--", "No arrow"),
                                    ('1', "Line", "The point of the arrow are lines"),
                                    ('2', "Triangle", "The point of the arrow is triangle"),
                                    ('3', "TShape", "The point of the arrow is a T")),
                             name="B end",
                             description="Add arrows to point B")
    glarrow_s: IntProperty(name="Size",
                            description="Arrow size",
                            default=15, min=6, max=500)

    glarc_full: BoolProperty(name="arcfull",
                              description="Create full circunference",
                              default=False)
    glarc_extrad: BoolProperty(name="arcextrad",
                                description="Adapt radio lengh to arc line",
                                default=True)
    glarc_rad: BoolProperty(name="arc rad",
                             description="Show arc radius",
                             default=True)
    glarc_len: BoolProperty(name="arc len",
                             description="Show arc length",
                             default=True)
    glarc_ang: BoolProperty(name="arc ang",
                             description="Show arc angle",
                             default=True)

    glarc_a: EnumProperty(items=(('99', "--", "No arrow"),
                                  ('1', "Line", "The point of the arrow are lines"),
                                  ('2', "Triangle", "The point of the arrow is triangle"),
                                  ('3', "TShape", "The point of the arrow is a T")),
                           name="Ar end",
                           description="Add arrows to point A")
    glarc_b: EnumProperty(items=(('99', "--", "No arrow"),
                                  ('1', "Line", "The point of the arrow are lines"),
                                  ('2', "Triangle", "The point of the arrow is triangle"),
                                  ('3', "TShape", "The point of the arrow is a T")),
                           name="Br end",
                           description="Add arrows to point B")
    glarc_s: IntProperty(name="Size",
                          description="Arrow size",
                          default=15, min=6, max=500)
    glarc_txradio: StringProperty(name="txradio",
                                   description="Text for radius", default="r=")
    glarc_txlen: StringProperty(name="txlen",
                                 description="Text for length", default="L=")
    glarc_txang: StringProperty(name="txang",
                                 description="Text for angle", default="A=")
    glcolorarea: FloatVectorProperty(name="glcolorarea",
                                      description="Color for the measure of area",
                                      default=(0.1, 0.1, 0.1, 1.0),
                                      min=0.1,
                                      max=1,
                                      subtype='COLOR',
                                      size=4)

bpy.utils.register_class(StyleProperties)

class StyleContainer(PropertyGroup):
    style_num = IntProperty(name='Number of styles', min=0, max=1000, default=0,
                                description='Number total of measureit_arch Dimension Styles')
    # Array of styles
    measureit_arch_styles = CollectionProperty(type=StyleProperties)

bpy.utils.register_class(StyleContainer)
Scene.StyleGenerator = CollectionProperty(type=StyleContainer)

###################################
#
#       Style Operators
#
###################################

class AddDimStyleButton(Operator):
    bl_idname = "measureit_arch.adddimstylebutton"
    bl_label = "Add"
    bl_description = "Create A New Dimension Style"
    bl_category = 'MeasureitArch'

    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # Add properties
                    scene = context.scene

                    if 'StyleGenerator' not in scene:
                        scene.StyleGenerator.add()

                    styleGen = scene.StyleGenerator[0]
                    styleGen.measureit_arch_styles.add()

                    newStyle = styleGen.measureit_arch_styles[styleGen.style_num]

                    #Style Properties
                    newStyle.styleName = 'Style ' + str(styleGen.style_num + 1)
                    newStyle.glcolor = scene.measureit_arch_default_color
                    
                    newStyle.glwidth = scene.measureit_arch_gl_width
                    newStyle.glarrow_a = scene.measureit_arch_glarrow_a
                    newStyle.glarrow_b = scene.measureit_arch_glarrow_b
                    newStyle.glarrow_s = scene.measureit_arch_glarrow_s
                    # dist
                    newStyle.glspace = scene.measureit_arch_hint_space
                    # text
                    newStyle.gltxt = scene.measureit_arch_gl_txt
                    newStyle.glfont_size = scene.measureit_arch_font_size
                    newStyle.glfont_align = scene.measureit_arch_font_align
                    newStyle.glfont_rotat = scene.measureit_arch_font_rotation
                    

                    styleGen.style_num += 1
                    context.area.tag_redraw()
                    return {'FINISHED'}
        return {'FINISHED'}

class DeleteStyleButton(Operator):
    bl_idname = "measureit_arch.deletestylebutton"
    bl_label = "Delete Style"
    bl_description = "Delete a Style"
    bl_category = 'MeasureitArch'
    tag= IntProperty()

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # Add properties
                    mp = context.scene.StyleGenerator[0]
                    ms = mp.measureit_arch_styles[self.tag]
                    ms.glfree = True
                    # Delete element
                    mp.measureit_arch_styles.remove(self.tag)
                    mp.style_num -= 1
                    # redraw
                    context.area.tag_redraw()
                    return {'FINISHED'}
        return {'FINISHED'}

class DeleteAllStylesButton(Operator):
    bl_idname = "measureit_arch.deleteallstylesbutton"
    bl_label = "Delete All Styles?"
    bl_description = "Delete all Styles (it cannot be undone)"
    bl_category = 'MeasureitArch'

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # Add properties
                    scene =bpy.context.scene
                    mainobject = context.object
                    styleGen = scene.StyleGenerator[0]

                    while len(styleGen.measureit_arch_styles) > 0:
                        styleGen.measureit_arch_styles.remove(0)

                    # reset size
                    styleGen.style_num = len(styleGen.measureit_arch_styles)
                    # redraw
                    context.area.tag_redraw()
                    return {'FINISHED'}
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


