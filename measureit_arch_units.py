# coding=utf-8

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
# File: measureit_arch_units.py
# Author: Matthias Pronk
# Utilities for unit conversions and formatting
# ----------------------------------------------------------

import bpy
import math
import unittest

from typing import Tuple
from bpy.types import Panel


__all__ = (
    'BU_TO_INCHES',
    'format_distance',
    'format_area',
    'format_angle',
)

# Note: one Blender Unit (BU) is 1m
INCH_TO_CM = 2.54
INCHES_PER_FEET = 12
INCHES_PER_MILE = 5280 * INCHES_PER_FEET
THOU_PER_INCH = 1000

INCH_TO_PT = 72

# Conversion factor from Blender Units to Inches / Feet
BU_TO_INCHES = 100.0 / INCH_TO_CM
BU_TO_FEET = 100.0 / (INCH_TO_CM * INCHES_PER_FEET)


# MeasureIt_ARCH Unit settings
class SCENE_PT_MARCH_units(Panel):
    """ MeasureIt_ARCH Unit settings """

    if hasattr(bpy.types, "SCENE_PT_unit"):
        bl_parent_id = 'SCENE_PT_unit'
    bl_idname = "SCENE_PT_MARCH_Units"
    bl_label = "MeasureIt_ARCH Unit Settings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="", icon='SNAP_INCREMENT')

    # -----------------------------------------------------
    # Draw (create UI interface)
    # -----------------------------------------------------
    def draw(self, context):
        scene = context.scene
        sceneProps = scene.MeasureItArchProps

        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        scene = context.scene

        col = layout.column()
        col.label(text='Precision:')
        col.prop(sceneProps, 'metric_precision', text="Metric Precision")
        col.prop(sceneProps, 'mm_precision', text="Milimeter Precision")
        col.prop(sceneProps, 'angle_precision', text="Angle Precision")
        col.prop(sceneProps, 'imperial_precision', text="Imperial Precision")
        col.label(text='Areas:')
        col.prop(sceneProps, 'imperial_area_units')
        col.prop(sceneProps, 'metric_area_units')
        col.prop(sceneProps, 'area_precision')
        col.label(text='Scale:')
        col.prop(sceneProps, 'use_unit_scale')

        col = layout.column(align=True)
        col.prop(sceneProps, 'default_scale', text="Default Scale 1:")



def format_distance(distance: float, dim = None, allow_negative = False) -> str:
    """
    Format a distance (length) for display

    :param area: distance in BU / meters
    :param type: float
    :returns: formatted string
    :return type: string
    """
    scene = bpy.context.scene
    unit_system = bpy.context.scene.unit_settings.system
    unit_length = scene.unit_settings.length_unit
    separate_units = scene.unit_settings.use_separate
    hide_units = scene.MeasureItArchProps.hide_units
    unit_scale = scene.unit_settings.scale_length
    
    unit_system, unit_length = get_dim_unit_override(dim,unit_system,unit_length)
    
    if scene.MeasureItArchProps.use_unit_scale:
        distance *= unit_scale
    if unit_system == 'METRIC':
        precision = scene.MeasureItArchProps.metric_precision
        if not unit_length == 'ADAPTIVE':
            return _format_metric_length(
                distance, precision, unit_length, hide_units)
        # If unit_length is 'Adaptive' or `separate_units` is True, use Blender
        # built-in which means units are always shown (regardless of
        # `hide_units`)
        return bpy.utils.units.to_string(
            'METRIC', 'LENGTH', distance, precision=precision,
            split_unit=separate_units, compatible_unit=False)

    elif unit_system == 'IMPERIAL':
        if not unit_length == 'ADAPTIVE':
            precision = int(scene.MeasureItArchProps.imperial_precision)
            return _format_imperial_length(distance, precision, unit_length)
        return bpy.utils.units.to_string(
            'IMPERIAL', 'LENGTH', distance, split_unit=separate_units,
            compatible_unit=False)

    return bpy.utils.units.to_string(
        'NONE', 'LENGTH', distance, split_unit=separate_units,
        compatible_unit=False)

def get_dim_unit_override(dim, unit_system, unit_length = None):
    if dim != None:
        if dim.override_unit_system != 'NONE':
            unit_system = dim.override_unit_system
            if unit_system == 'METRIC' and dim.override_metric_length != 'NONE':
                unit_length = dim.override_metric_length
            elif unit_system == 'IMPERIAL' and dim.override_imperial_length != 'NONE':
                unit_length = dim.override_imperial_length
    
    return unit_system, unit_length

def format_area(area: float, dim) -> str:
    """
    Format an area for display

    :param area: area in square BU / meters
    :param type: float
    :returns: formatted string
    :return type: string
    """
    scene = bpy.context.scene
    sceneProps = scene.MeasureItArchProps
    unit_scale = scene.unit_settings.scale_length

    if scene.MeasureItArchProps.use_unit_scale:
        area *= unit_scale

    unit_system = scene.unit_settings.system
    if unit_system == 'METRIC':
        unit_length = sceneProps.metric_area_units
    else:
        unit_length = sceneProps.imperial_area_units
    separate_units = scene.unit_settings.use_separate
    hide_units = scene.MeasureItArchProps.hide_units

    unit_system, unit_length = get_dim_unit_override(dim,unit_system,unit_length)

    if unit_system == 'METRIC':
        precision = scene.MeasureItArchProps.area_precision
        if not separate_units and not unit_length == 'ADAPTIVE':
            return _format_metric_area(
                area, precision, unit_length, hide_units)
        # If unit_length is 'Adaptive' or `separate_units` is True, use Blender
        # built-in which means units are always shown (regardless of
        # `hide_units`)
        return bpy.utils.units.to_string(
            'METRIC', 'AREA', area, precision=precision,
            split_unit=separate_units, compatible_unit=False)
    
    elif unit_system == 'IMPERIAL':
        precision = scene.MeasureItArchProps.area_precision
        return _format_imperial_area(area, precision, unit_length)

    return bpy.utils.units.to_string(
        'NONE', 'LENGTH', area, split_unit=separate_units,
        compatible_unit=False)


def format_angle(angle: float) -> str:
    """
    Format an angle for display

    :param angle: angle in radians
    :type angle: float
    :returns: formatted string
    :return type: string
    """
    scene = bpy.context.scene
    hide_units = scene.MeasureItArchProps.hide_units
    precision = scene.MeasureItArchProps.angle_precision
    system_rotation = scene.unit_settings.system_rotation

    if system_rotation == 'DEGREES':
        return "{:.{}f}{}".format(
            math.degrees(angle), precision, '' if hide_units else '°')
    elif system_rotation == 'RADIANS':
        return "{:.{}f}{}".format(
            angle, precision, '' if hide_units else ' rad')


def _format_metric_length(
        value: float, precision: int, unit_length: str = 'METERS',
        hide_units: bool = False) -> str:
    """
    (Internal) Format a value in BU/meters as a string
    """
    if unit_length == 'CENTIMETERS':
        value *= 100
        unit = " cm"
    elif unit_length == 'MILLIMETERS':
        precision = bpy.context.scene.MeasureItArchProps.mm_precision
        value *= 1000
        unit = " mm"
    elif unit_length == 'MICROMETERS':
        value *= 1000000
        unit = " µm"
    elif unit_length == 'KILOMETERS':
        value = value / float(1000)
        unit = " km"
    else:
        unit = " m"
    return "{:.{}f}{}".format(value, precision, "" if hide_units else unit)


def _format_metric_area(
        value: float, precision: int, unit_length: str = 'METERS',
        hide_units: bool = False) -> str:
    """
    (Internal) Format a value in square BU/meters as a string
    """
    if unit_length == 'CENTIMETERS':
        value *= 100 ** 2
        unit = " cm²"
    elif unit_length == 'MILLIMETERS':
        value *= 1000 ** 2
        unit = " mm²"
    elif unit_length == 'MICROMETERS':
        value *= 1000000 ** 2
        unit = " µm²"
    elif unit_length == 'KILOMETERS':
        value = value / float(1000 ** 2)
        unit = " km²"
    else:
        unit = " m²"
    return "{:.{}f}{}".format(value, precision, "" if hide_units else unit)


def _format_imperial_length(value, precision, unit_length='INCH') -> str:
    """
    (Internal) Format a length as a string using imperial units

    :param value: length in BU/meters
    :param type: float
    :param value: precision expressed as 1/n'th inch
    :param type: int
    :param unit_length: one of 'INCHES', 'FEET', 'MILES' or 'THOU'
    :param type: str
    """
    neg_str = ""
    if value < 0:
        neg_str = "-"
        value = abs(value)

    if unit_length in ('INCHES', 'FEET'):
        value *= BU_TO_INCHES
        (inches, num, denom) = _inches_to_fraction(value, precision)
        if unit_length == 'FEET':
            (feet, inches) = divmod(inches, INCHES_PER_FEET)
        else:
            feet = 0
        if feet > 0 and num > 0:
            return "{}{}′ {}-{}⁄{}″".format(neg_str,feet, inches, num, denom)
        elif feet > 0:
            return "{}{}′ {}″".format(neg_str,feet, inches)
        elif num > 0:
            return "{}{}-{}⁄{}″".format(neg_str,inches, num, denom)
        else:
            return "{}{}″".format(neg_str,inches)
    elif unit_length == 'MILES':
        pass
    elif unit_length == 'THOU':
        pass
    # Adaptive
    return bpy.utils.units.to_string(
        'IMPERIAL', 'LENGTH', value, precision=precision,
        split_unit=False, compatible_unit=False)


def _format_imperial_area(value, precision, unit_length='FEET', hide_units=False) -> str:
    """
    (Internal) Format an area as a string using imperial units

    :param value: area in BU/meters
    :param type: float
    :param value: precision expressed as 1/n'th inch
    :param type: int
    :param unit_length: one of 'FEET', 'ACRE', 'HECTARE
    :param type: str
    """

    areaToInches = 1550
    inPerFoot = 143.999
    feetPerAcre = 43560
    feetPerHectare = 107639

    value *= areaToInches
    value /= inPerFoot

    unit = " ft²"
    if unit_length == 'FEET':
        unit = " ft²"
    elif unit_length == 'ACRE':
        unit = 'Acres'
        value /= feetPerAcre
    elif unit_length == 'HECTARE':
        unit = 'ha'
        value /= feetPerHectare

    return "{:.{}f}{}".format(value, precision, "" if hide_units else unit)

def _inches_to_fraction(inches: float, precision: int) -> Tuple[int, int, int]:
    """
    (Internal) Returns the integer and fractional part as a tuple of integer
    part, numerator and denominator (all integers), rounded to precision
    (expressed as 1/n'th of an inch).
    """

    # TODO: I Shouldnt need this check, has to do with an eval depsgraph issue
    if inches == float('inf'):
        print ("Inf Inches")
        return (inches,0,0)

    inches_ = round(inches * precision) / float(precision)
    frac, int_ = math.modf(inches_)
    num, denom = frac.as_integer_ratio()
    return (int(int_), num, denom)


class ImperialConversionTests(unittest.TestCase):
    """ Test conversion from BU to imperial units """

    PRECISION = 5

    def test_inches(self):
        self.assertAlmostEqual(2.3 * BU_TO_INCHES, 90.55118, self.PRECISION)


class FormatImperialTests(unittest.TestCase):
    """ Test formatting of imperial units """

    def test_imperial_length_inch(self):
        str = _format_imperial_length(2.3, 64, 'INCH')
        self.assertEqual(str, "2-19⁄64″")

        str = _format_imperial_length(2.3, 32, 'INCH')
        self.assertEqual(str, "2-5⁄16″")

        str = _format_imperial_length(2.3, 8, 'INCH')
        self.assertEqual(str, "2-1⁄4″")

        str = _format_imperial_length(2.3, 2, 'INCH')
        self.assertEqual(str, "2-1⁄2″")

        str = _format_imperial_length(2.3, 1, 'INCH')
        self.assertEqual(str, "2″")


if __name__ == '__main__':
    # Run with: blender -P measureit_arch_units.py
    unittest.main(argv=['blender'])
