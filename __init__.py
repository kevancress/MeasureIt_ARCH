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
# Author: Antonio Vazquez (antonioya), Kevan Cress
# ----------------------------------------------------------

import os
import site
import bpy

from bpy.types import WindowManager, Scene, Object, Material

# ----------------------------------------------
# Define Addon info
# ----------------------------------------------
bl_info = {
    "name": "MeasureIt_ARCH",
    "author": "Kevan Cress, Antonio Vazquez (antonioya)",
    "location": "View3D > Tools Panel / Properties panel",
    "version": (0, 5, 0),
    "blender": (2, 83, 0),
    "description": "Tools for adding Dimensions, Annotations and Linework to Objects",
    "warning": "",
    "doc_url": "https://github.com/kevancress/MeasureIt_ARCH/",
    "category": "3D View"
}


cwd = os.path.dirname(os.path.realpath(__file__))
site.addsitedir(os.path.join(cwd, "libs"))

if "measureit_arch_main" in locals():
    print("M_ARCH reload modules")
    import importlib
    importlib.reload(measureit_arch_baseclass)
    importlib.reload(measureit_arch_annotations)
    importlib.reload(measureit_arch_dimensions)
    importlib.reload(measureit_arch_gizmos)
    importlib.reload(measureit_arch_material_hatches)
    importlib.reload(measureit_arch_lines)
    importlib.reload(measureit_arch_main)
    importlib.reload(measureit_arch_render)
    importlib.reload(measureit_arch_schedules)
    importlib.reload(measureit_arch_sheets)
    importlib.reload(measureit_arch_styles)
    importlib.reload(measureit_arch_views)
    importlib.reload(measureit_arch_units)
    importlib.reload(measureit_arch_object)
else:
    print("M_ARCH import modules")
    from . import measureit_arch_baseclass
    from . import measureit_arch_annotations
    from . import measureit_arch_dimensions
    from . import measureit_arch_gizmos
    from . import measureit_arch_material_hatches
    from . import measureit_arch_lines
    from . import measureit_arch_units
    from . import measureit_arch_main
    from . import measureit_arch_render
    from . import measureit_arch_schedules
    from . import measureit_arch_sheets
    from . import measureit_arch_styles
    from . import measureit_arch_views
    from . import measureit_arch_object

classes = (
    measureit_arch_main.ShowHideViewportButton,
    measureit_arch_main.MEASUREIT_PT_main_panel,
    measureit_arch_object.OBJECT_PT_Panel,

    #measureit_arch_main.MeasureIt_nav_button,
    
    measureit_arch_units.SCENE_PT_MARCH_units,


    # Base Classes
    measureit_arch_baseclass.TextField,
    measureit_arch_baseclass.ObjProps,
    measureit_arch_baseclass.MeasureItARCHSceneProps,
    measureit_arch_baseclass.DeletePropButton,
    measureit_arch_baseclass.AddTextField,
    measureit_arch_baseclass.MoveItem,
    measureit_arch_baseclass.DeleteAllItemsButton,
    measureit_arch_baseclass.MovePropButton,
    measureit_arch_baseclass.StyleWrapper,

    # Annotations
    measureit_arch_annotations.OBJECT_PT_UIAnnotations,
    measureit_arch_annotations.CustomProperties,
    measureit_arch_annotations.SecondaryLeader,
    measureit_arch_annotations.AnnotationProperties,
    measureit_arch_annotations.AnnotationContainer,
    measureit_arch_annotations.AddAnnotationButton,
    measureit_arch_annotations.TranslateAnnotationOp,
    measureit_arch_annotations.RotateAnnotationOp,
    measureit_arch_annotations.M_ARCH_UL_annotations_list,
    measureit_arch_annotations.OBJECT_MT_annotation_menu,

    # Dimensions
    measureit_arch_dimensions.OBJECT_PT_UIDimensions,
    measureit_arch_dimensions.AreaDimensionProperties,
    measureit_arch_dimensions.AlignedDimensionProperties,
    measureit_arch_dimensions.AxisDimensionProperties,
    measureit_arch_dimensions.BoundsDimensionProperties,
    measureit_arch_dimensions.ArcDimensionProperties,
    measureit_arch_dimensions.AngleDimensionProperties,
    measureit_arch_dimensions.DimensionWrapper,
    measureit_arch_dimensions.DimensionContainer,
    measureit_arch_dimensions.AddAlignedDimensionButton,
    measureit_arch_dimensions.AddBoundingDimensionButton,
    measureit_arch_dimensions.AddAxisDimensionButton,
    measureit_arch_dimensions.AddAreaButton,
    measureit_arch_dimensions.AddAngleButton,
    measureit_arch_dimensions.AddArcButton,
    measureit_arch_dimensions.CursorToArcOrigin,
    measureit_arch_dimensions.AddFaceToArea,
    measureit_arch_dimensions.RemoveFaceFromArea,
    measureit_arch_dimensions.TranslateDimensionOp,
    measureit_arch_dimensions.M_ARCH_UL_dimension_list,
    measureit_arch_dimensions.OBJECT_MT_dimension_menu,

    # Gizmos
    measureit_arch_gizmos.mArchGizmoGroup,

    # Hatches
    measureit_arch_material_hatches.MATERIAL_PT_UIHatch,
    measureit_arch_material_hatches.HatchProperties,

    # Lines
    measureit_arch_lines.OBJECT_PT_UILines,
    measureit_arch_lines.LineProperties,
    measureit_arch_lines.LineContainer,
    measureit_arch_lines.AddLineButton,
    measureit_arch_lines.AddDynamicLineButton,
    measureit_arch_lines.AddToLineGroup,
    measureit_arch_lines.AddLineByProperty,
    measureit_arch_lines.RemoveFromLineGroup,
    measureit_arch_lines.OBJECT_MT_lines_menu,
    measureit_arch_lines.M_ARCH_UL_lines_list,

    # Render
    measureit_arch_render.RENDER_PT_MeasureitArch_Panel,
    measureit_arch_render.RenderImageButton,
    measureit_arch_render.RenderAnimationButton,
    measureit_arch_render.RenderVectorButton,
    measureit_arch_render.RenderDXFButton,

    # Schedules
    measureit_arch_schedules.ColumnProps,
    measureit_arch_schedules.ScheduleProperties,
    measureit_arch_schedules.ScheduleContainer,
    measureit_arch_schedules.AddColumnButton,
    measureit_arch_schedules.DeleteScheduleButton,
    measureit_arch_schedules.GenerateSchedule,
    measureit_arch_schedules.DuplicateScheduleButton,
    measureit_arch_schedules.AddScheduleButton,

    # Sheets
    measureit_arch_sheets.SCENE_PT_Sheet,
    measureit_arch_sheets.SheetViewProperties,
    measureit_arch_sheets.SheetViewContainer,
    measureit_arch_sheets.AddSheetViewButton,
    measureit_arch_sheets.DeleteSheetViewButton,
    measureit_arch_sheets.M_ARCH_UL_Sheets_list,

    # Styles
    measureit_arch_styles.StyleContainer,
    measureit_arch_styles.ListDeletePropButton,
    measureit_arch_styles.AddStyleButton,

    # Views
    measureit_arch_views.ViewProperties,
    measureit_arch_views.ViewContainer,
    measureit_arch_views.DeleteViewButton,
    measureit_arch_views.DuplicateViewButton,
    measureit_arch_views.DuplicateViewWithLayerButton,
    measureit_arch_views.AddViewButton,
    measureit_arch_views.M_ARCH_OP_Render_Preview,
    measureit_arch_views.BatchViewRender,
    measureit_arch_views.OpenInBrowser,


    # Scene UI Panels
    measureit_arch_main.SCENE_PT_Panel,
    measureit_arch_views.SCENE_PT_Views,
    measureit_arch_views.M_ARCH_UL_Views_list,
    measureit_arch_views.SCENE_MT_Views_menu,
    measureit_arch_styles.SCENE_PT_UIStyles,
    measureit_arch_styles.M_ARCH_UL_styles_list,
    measureit_arch_styles.SCENE_MT_styles_menu,
    measureit_arch_schedules.SCENE_PT_Schedules,
    measureit_arch_schedules.M_ARCH_UL_Schedules_list,
    measureit_arch_schedules.SCENE_MT_Schedules_menu,
    measureit_arch_main.SCENE_PT_MARCH_Settings,

    # Object Setting Ui Panel
    measureit_arch_object.OBJECT_PT_UIObjSettings,
)


# Define menu
# noinspection PyUnusedLocal
def register():
    print("M_ARCH register")
    # Register classes
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.app.handlers.load_post.append(measureit_arch_main.load_handler)
    bpy.app.handlers.load_post.append(measureit_arch_styles.create_preset_styles)
    bpy.app.handlers.load_post.append(measureit_arch_views.create_preset_view)
    bpy.app.handlers.save_pre.append(measureit_arch_main.save_handler)

    # Register pointer properties
    Scene.MeasureItArchProps = bpy.props.PointerProperty(
        type=measureit_arch_baseclass.MeasureItARCHSceneProps)
    Scene.ScheduleGenerator = bpy.props.PointerProperty(
        type=measureit_arch_schedules.ScheduleContainer)
    Scene.StyleGenerator = bpy.props.PointerProperty(
        type=measureit_arch_styles.StyleContainer)
    Scene.ViewGenerator = bpy.props.PointerProperty(
        type=measureit_arch_views.ViewContainer)
    Object.SheetGenerator = bpy.props.PointerProperty(
        type=measureit_arch_sheets.SheetViewContainer)

    # Register collection properties
    Object.MeasureItArchProps = bpy.props.PointerProperty(
        type=measureit_arch_baseclass.ObjProps
    )
    Object.DimensionGenerator = bpy.props.PointerProperty(
        type=measureit_arch_dimensions.DimensionContainer)
    Object.LineGenerator = bpy.props.PointerProperty(
        type=measureit_arch_lines.LineContainer)
    Object.AnnotationGenerator = bpy.props.PointerProperty(
        type=measureit_arch_annotations.AnnotationContainer)
    Material.Hatch = bpy.props.PointerProperty(
        type=measureit_arch_material_hatches.HatchProperties)

    # Property on the WM that indicates if we want to draw the measurements in the viewport
    WindowManager.measureit_arch_run_opengl = bpy.props.BoolProperty(default=False)


def unregister():
    print("M_ARCH unregister")
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.app.handlers.load_post.remove(measureit_arch_main.load_handler)
    bpy.app.handlers.save_pre.remove(measureit_arch_main.save_handler)

    # remove OpenGL data
    measureit_arch_main.ShowHideViewportButton.handle_remove(
        measureit_arch_main.ShowHideViewportButton, bpy.context)

    wm = bpy.context.window_manager
    if 'measureit_arch_run_opengl' in wm:
        del wm['measureit_arch_run_opengl']


if __name__ == '__main__':
    register()
