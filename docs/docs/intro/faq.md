# Frequently Asked Questions

!!! Disclaimer
    No one has actually asked me these questions, but I do ask them to myself. Frequently. 
    
    _(or they're just things I wanted to comment on)_

    If you have questions about MeasureIt_ARCH that you think should be answered here, make a pull request for this page with the "Edit on GitHub" button above.

#### What should I use MeasureIt_ARCH for?
MeasureIt_ARCH is meant for producing Design Documentation and Technical Drawings in Blender. If you've been using Sketch-Up, AutoCAD, Rhino or a similar software for design drawings and documentation, on relativly small scale projects, then MeasureIt_ARCH & Blender could be a good tool for you.

#### Why should I use MeasureIt_ARCH?




#### I'm looking for Building Information Modeling (BIM) tools in Blender?

If you're looking for BIM functionality, the BlenderBIM team has you covered. BlenderBIM adds support for working with BIM data based on the [Industry Foundation Classes (IFC) standard](https://www.buildingsmart.org/standards/bsi-standards/industry-foundation-classes/). Check out the BlenderBIM [website](https://blenderbim.org/) and [documentation](https://blenderbim.org/docs/) for more information.


#### Where can I learn about other tools for Archtectural and Technical drawing with Open Source Software?

Check out the OSArch [wiki](https://wiki.osarch.org/index.php?title=AEC_Free_Software_directory) and [website](https://osarch.org/) for more information on Open Source tools.

#### SVG export is great, but my Clients expect PDF's!

A PDF exporter is a high priority for future development. In the meantime MeasureIt_ARCH comes with a .bat file utility to quickly convert .svg's to .pdf's with the help of [Inkscape](https://inkscape.org/). Check out the ["Batch convert .svg to .pdf"](..\tutorials\svg_to_pdf.md) tutorial to learn how to set-up and use the .bat file.

#### PDF's are great, but my Consultants expect CAD files!

A reality of the Architecture Engineering and Construction (AEC) industry is that we need to share information quickly, often, and in the formats that the rest of the industry expects. Unfortunaly if you're working on a project with many consultants that need to exchange tightly co-ordinated CAD files (or work with centralized BIM information), then MeasureIt_ARCH is likely not a good fit for your project right now.

That said, MeasureIt_ARCH does have a (partially) functioning .dxf exporter, along with some options for configuring CAD layer setting. This is a work in progress, but does allow for drawings to be exported to AutoCAD when needed, although this process is currently far from seamless.

#### MeasureIt_ARCH, is that related to MeasureIt?

Indeed it is! MeasureIt is an addon that is included as part of blender, originally developed by Antonio Vazquez, who is now developing Blender's Grease Pencil tools. MeasureIt_ARCH started off as a fork of the MeasureIt addon in 2019. While the original intent was simply to add an option for line drawings to MeasureIt, MeasureIt_ARCH has since developed into a suite of tools for Dimensioning, Line Drawing, Annotations, View Management, Styles, and Vector Graphics, with a redesigned UI as well.



