# Exporting to .DXF Files

To support exchange with AutoCAD, MeasureIt_ARCH includes an option to render views out as .dxf files.

!!! Warning
    .dxf export is very much a work in progress and will never be perfect. This exporter is meant to be "good enough" to facilitate basic exchange of drawings from MeasureIt_ARCH to AutoCAD.
    
    Until Autodesk decides to meaningfully impliment open exchange file formats and well documented open standards, propper interoperability is nearly impossible to achieve...

    <sub> ...but Autodesk will never do this because their business model relies on monopolistic practices that keep users and entire industries dependant on their software ecosystem... </sub>

## Enabling DXF options:
DXF options can be enabled in the MeasureIt_ARCH settings panel of blender's Scene settings, by ticking the box labled "Show DXF Options"


## Available DXF Options:
Currently enabling Show DXF Options will enable:

* the **"MeasureIt_ARCH to DXF"** render Button
* the **"CAD Color Index"** property in Lines Groups and Line Styles

## Common Pitfalls:

#### Scale Issues:

!!! Danger
    AutoCAD's handling of .dxf units is an absolute mess. Please Read the following:

When opening a .dxf file directly, AutoCAD will ignore the units specified in the .dxf header, and use whatever the users default unit settings happen to be set to. 

I recomend **never opening a .dxf file directly**, but instead using the `CLASSICINSERT` command in AutoCAD. `CLASSICINSERT` does respect the .dxf Unit header, and can be used to insert the .dxf correctly scaled either as a block or exploded.

By default MeasureIt_ARCH currently exports all .dxf files in Meters.

#### Naming Issues:

The following characters are not allowed in dxf file definitions `"'[]{}()!@#$%^&*`. Some of these will throw an error on export, others will not, but will still result in a corrupt .dxf file that will not import into AutoCAD. Ensure that none of your object or style names have any of these characters when exporting.

!!! Danger
    Other special characters may cause issues as well. It's generally best to avoid any and all non-alphanumeric characters in names when exporting to .dxf
