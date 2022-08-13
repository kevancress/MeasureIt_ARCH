# Reporting Issues & Bugs

MeasureIt_ARCH is a work in progress, developed mostly by one person, in their spare time. There will be bugs. If you, dear user, are lucky enough to find one of these bugs, please report it so I can attempt to fix it. 

This guide will tell you what to report, where to report it, and what information you should include when reporting.

## What is an Issue / Bug that I should Report?

For MeasureIt_ARCH I consider all of the following to be bugs that should be reported:

- Blender Crashes when using MeasureIt_ARCH
- Blender Reports an Error in the [Info Editor](https://docs.blender.org/manual/en/latest/editors/info_editor.html) when using MeasureIt_ARCH
- A MeasureIt_ARCH tool produces an unexpected or unintutive result (*that isn't clearly described in the docs*) 

    !!! Example
        - an Area Dimension Text isn't centered properly,
        - the Add Dimension Button occaisionally produces a duplicate Dimension

- A MeasureIt_ARCH property behaves in an unexpected way
- You can't find a feature or property where it is described in the docs
- A feature or property isn't documented

Essentially if there's anything that makes you think **_"huh thats not what I expected would happen"_** then I'd like to hear about it.

Anything that make you think **_'I really wish it did <Somthing new\>'_** is a feature request, and I'd like to hear those too, but check out the "Requesting Features" page for Feature Request Guidelines. 

## Where to Report Issues

Issues should be reported in the [GitHub Issue Tracker](https://github.com/kevancress/MeasureIt_ARCH/issues).

!!! Warning
    MeasureIt_ARCH does have a [Youtube page](https://www.youtube.com/c/MeasureItARCH) and a [Twitter account](https://twitter.com/measureit_arch), but the GitHub issue tracker is the only source that I regularly check when working on Issues. If you report an issue to my youtube or twitter account it will likely be lost and forgotten.

## What to Include in an Issue Report

A usefull error report should contain the following:

- A descriptive Title
- A brief description of what you were doing when the error occured
- **The Version of Blender you are using**
- The Operating system you are using
- **The Version of MeasureIt_ARCH you are using**

    !!! Info
        MeasureIt_ARCH now displays detailed version info at the bottom of the "MeasureIt_ARCH Settings" Panel in Blender's Scene Properties. Please include the values for the:

        - "Previous Commit Hash:", and
        - "Previous Commit Date:"

        as listed there when reporting an issue. 

- The severity of the issue (is this an annoyance, or is it preventing you from using the addon)
- **Any error messages that occur with the issue.**

    !!! Info
        Errors should show up in Blender's [Info Editor](https://docs.blender.org/manual/en/latest/editors/info_editor.html) or in the Blender System Console which can be toggled by going to "Window" -> "Toggle System Console"

For issues specifically related to how graphics are drawn in the 3D view the model of your graphics card can also be useful information.
