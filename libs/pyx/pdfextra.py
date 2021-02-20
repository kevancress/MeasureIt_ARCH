# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2006 Michael Schindler <m-schindler@users.sourceforge.net>
#
# This file is part of PyX (https://pyx-project.org/).
#
# PyX is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# PyX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyX; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

import io, math
from . import baseclasses, bbox, pdfwriter, color, unit
from .font.font import PDFHelvetica, PDFZapfDingbats

# TODO:
# - discuss behaviour under transformations with André and Jörg
# - what about fillstyles here?
# - where should e.g. a font be added to the registry:
#   in processPDF or in __init__ of the PDF-item?
# - test for double occurrance of field names:
#   this leads to wrong/no display
#
# TODO horizontal alignment in textfields


# flags for annotations:
PDFannotflags = [("invisible", 0), ("hidden", 1), ("printable", 2),
    ("nozoom", 3), ("norotate", 4), ("noview", 5), ("readonly", 6)]

# flags for form fields
PDFformflags = [("readonly", 0), ("required", 1), ("noexport", 2),
    # flags for the button field
    ("notoggletooff", 14), ("radio", 15), ("pushbutton", 16),
    # flags for the choice list field
    ("combo", 17), ("edit", 18), ("sort", 19), ("multiselect", 21),
    # flags for the text field
    ("multiline", 12), ("password", 13), ("fileselect", 20), ("donotspellcheck", 22),
    ("donotscroll", 23)]


class flag: # <<<
    """A helper class for handling flags in pdf forms and annotations"""

    def __init__(self, value=None):
        self.value = value

    def is_set(self, bit):
        return self.value is not None and (self.value & 1<<bit) == 1<<bit

    def set(self, bit):
        if self.value is None:
            self.value = 1<<bit
        else:
            self.value = self.value | 1<<bit

    def unset(self, bit):
        if self.value is not None:
            self.value = self.value & ~(1<<bit)

    def __int__(self):
        return self.value

    def __str__(self):
        return self.value.__str__()
# >>>
def _pdfflags(flags): # <<<
    """Splits flags into annotation/form part
     the flag for the annotation dictionary
     the flag for the form (field) dictionary

    All flags are handled equally here, independent of their use
    for the specific form field.
    """

    # we initialize with 0 and set only those flags which are not 0
    annotflag = flag(value=0)
    formflag = flag(value=0)

    for key, value in PDFannotflags:
        if key in flags and flags[key]:
            annotflag.set(value)

    for key, value in PDFformflags:
        if key in flags and flags[key]:
            formflag.set(value)

    return int(annotflag), int(formflag)
# >>>
def _pdfalignment(string): # <<<
    alignflag = 0
    if string == "c":
        alignflag = 1
    elif string == "r":
        alignflag = 2
    return alignflag
# >>>
def _topt(value, type="u", un="cm"): # <<<
    if isinstance(value, unit.length):
        return unit.topt(value)
    else:
        return unit.topt(unit.length(value, type, un))
# >>>
def _simplestring(text): # <<<
    result = ""
    for x in text:
        if x.isalnum():
            result += x
    return result
# >>>
def _sizetrafo(s, tr): # <<<
    x1, y1 = tr.apply_pt(s, s)
    x0, y0 = tr.apply_pt(0, 0)
    return math.hypot(x1 - x0, y1 - y0) * math.sqrt(0.5)
# >>>


class formfield(baseclasses.canvasitem): # <<<
    """Base class for acroforms"""

    defaultflags = dict()

    def selectflags(self, flags):
        newflags = dict(**self.defaultflags)
        # overwrite the default flags with given values:
        for key, value in list(flags.items()):
            if key in newflags:
                newflags[key] = value
            else:
                raise RuntimeError("unknown argument \"%s\" to formfield" % key)
        return newflags

    def bbox(self):
        return bbox.bbox_pt(self.llx_pt, self.lly_pt, self.urx_pt, self.ury_pt)

    def processPS(self, file, writer, context, registry, bbox):
        raise RuntimeError("postscript output of forms is not supported")
# >>>


class textfield(formfield): # <<<
    """An interactive pdf form field for text input.

    The "name" is used for the graphical user interface and for exporing the input data.
    Note that the behaviour under rotations is undefined."""

    defaultflags = dict(invisible=0, hidden=0, printable=1, nozoom=0, norotate=0, noview=0,
        readonly=0, required=0, noexport=0, multiline=0, password=0, fileselect=0,
        donotspellcheck=1, donotscroll=0)

    def __init__(self, x, y, width, height, name, defaultvalue="", fontsize=10, font=PDFHelvetica,
        fontrelleading=1.16, borderwidth=0, align="l", **flags):

        self.llx_pt, self.lly_pt = _topt(x), _topt(y)
        self.urx_pt, self.ury_pt = _topt(x+width), _topt(y+height)
        self.name = name
        self.defaultvalue = defaultvalue
        self.fontsize_pt = _topt(fontsize, "x", "pt")
        self.font = font
        self.fontrelleading = fontrelleading
        self.borderwidth_pt = _topt(borderwidth, "x", "pt")
        self.align = align
        self.flags = self.selectflags(flags)

    def processPDF(self, file, writer, context, registry, bbox):
        # the bounding box is transformed by the canvas
        bbox += self.bbox()

        # the annotation rectangle must be transformed separately:
        llx_pt, lly_pt = context.trafo.apply_pt(self.llx_pt, self.lly_pt)
        urx_pt, ury_pt = context.trafo.apply_pt(self.urx_pt, self.ury_pt)
        fontsize_pt = _sizetrafo(self.fontsize_pt, context.trafo)
        borderwidth_pt = _sizetrafo(self.borderwidth_pt, context.trafo)

        # we create numbers from the flags given
        annotflag, formflag = _pdfflags(self.flags)
        alignflag = _pdfalignment(self.align)

        registry.add(PDFtextfield((llx_pt, lly_pt, urx_pt, ury_pt), self.name, self.defaultvalue,
          fontsize_pt, self.font, self.fontrelleading*fontsize_pt,
          borderwidth_pt, (not self.flags["multiline"]),
          alignflag, annotflag, formflag, context.fillstyles, writer, registry))
# >>>
class PDFtextfield(pdfwriter.PDFobject): # <<<

    def __init__(self, bb_pt, name, defaultvalue, fontsize, font, fontleading,
        borderwidth, vcenter,
        alignflag, annotflag, formflag, fillstyles, writer, registry):

        pdfwriter.PDFobject.__init__(self, "formfield_text")

        # append this formfield to the global document form
        # and to the annotation list of the page:
        self.PDFform = None
        for object in registry.objects:
            if object.type == "form":
                object.append(self)
                self.PDFform = object
            elif object.type == "annotations":
                object.append(self)

        self.name = name
        self.bb_pt = bb_pt
        self.defaultvalue = defaultvalue
        self.fontsize = fontsize
        self.font = font
        if self.font is None:
            self.font = PDFHelvetica
        self.fontleading = fontleading
        self.borderwidth = borderwidth
        self.alignflag = alignflag
        self.formflag = formflag
        self.annotflag = annotflag

        self.registry = pdfwriter.PDFregistry()
        self.registry.addresource("Font", self.font.name, self.font, procset="Text")
        self.registry.add(self.font)

        if self.defaultvalue:
            text = self.defaultvalue.split("\n")
            self.defaulttext = PDFdefaulttext(writer, registry, self.fontsize, self.font,
                self.fontleading, text, self.bb_pt, self.borderwidth, vcenter)
            self.registry.add(self.defaulttext)
        else:
            self.defaulttext = None

        # process some fillstyles:
        fillstring = io.StringIO()
        for attr in fillstyles:
            if 1:#isinstance(attr, color.color):
                cont = pdfwriter.context()
                cont.fillattr = 1
                cont.strokeattr = 0
                attr.processPDF(fillstring, writer, cont, self.registry, bbox)
        self.fillstyles = fillstring.getvalue()
        fillstring.close()

        registry.mergeregistry(self.registry)

    def write(self, file, writer, registry):
        ### the dictionary entries for the annotation
        file.write("<</Type /Annot\n")
        file.write("/P %d 0 R\n" % registry.getrefno(self.PDFform)) # reference to the page objects
        file.write("/Rect [%f %f %f %f]\n" % self.bb_pt) # the annotation rectangle
        #ile.write("/BS <</W 0 /S /S>>\n") # border style dictionary
        file.write("/Border [0 0 %f]\n" % self.borderwidth) # border style
        file.write("/F %d\n" % self.annotflag)
        ### the dictionary entries for the widget annotations
        file.write("/Subtype /Widget\n")
        file.write("/H /N\n") # highlight behaviour
        if self.defaulttext:
            file.write("/AP <</N %d 0 R >>\n" % registry.getrefno(self.defaulttext)) # appearance dictionary
        ### the dictionary entries for the form field
        file.write("/FT /Tx\n") # type of the form field
        file.write("/T (%s)\n" % self.name) # partial field name
        file.write("/TU (%s)\n" % self.name) # field name for the user-interface
        file.write("/TM (%s)\n" % self.name) # field name for exporting the data
        file.write("/V (%s)\n" % self.defaultvalue) # starting value
        file.write("/DV (%s)\n" % self.defaultvalue) # reset value
        file.write("/Ff %d\n" % self.formflag) # flags for various purposes
        ### the dictionary entries for the text field
        file.write("/DR ")
        self.registry.writeresources(file) # default resources for appearance
        file.write("/DA (%s /%s %f Tf %f TL)\n" % (self.fillstyles, self.font.name, self.fontsize, self.fontleading)) # default appearance string
        file.write("/Q %d\n" % self.alignflag)
        file.write(">>\n")
# >>>
class PDFdefaulttext(pdfwriter.PDFobject): # <<<

    def __init__(self, writer, registry, fontsize, font, fontleading, texts, bb, borderwidth, vcenter):

        pdfwriter.PDFobject.__init__(self, "defaulttext")
        self.font = font
        self.fontsize = fontsize
        self.fontleading = fontleading

        self.registry = pdfwriter.PDFregistry()
        self.registry.addresource("Font", self.font.name, self.font, procset="Text")
        self.registry.add(self.font)

        self.bb = (0, 0, bb[2] - bb[0], bb[3] - bb[1])
        self.texts = [t for t in texts if t]

        self.borderwidth = borderwidth
        # try to imitate the shifting of PDF:
        # the font orientation point is on the baseline of the text
        self.hshift = 2*self.borderwidth
        if vcenter:
            baselinevrel = 0.215
            self.vshift = 0.5 * (bb[3] - bb[1]) + (len(self.texts) / 2.0 - 1)*self.fontleading + baselinevrel*self.fontsize
        elif (bb[3] - bb[1]) < self.fontleading + 4*self.borderwidth:
            baselinevrel = 0.215
            self.vshift = 2*self.borderwidth + baselinevrel * self.fontsize
            #self.vshift = 0.5 * (bb[3] - bb[1]) - (0.5 - baselinevrel - 0.5*addrelshift)*self.fontsize
        else:
            baselinevrel = 0.215
            addrelshift = 0.215
            self.vshift = (bb[3] - bb[1]) - 2*self.borderwidth - self.fontleading + (baselinevrel - addrelshift)*self.fontsize

        registry.mergeregistry(self.registry)


    def write(self, file, writer, registry):
        content = "/Tx BMC q BT /%s %f Tf %f TL %f %f Td (%s) Tj" % (self.font.name, self.fontsize, self.fontleading, self.hshift, self.vshift, self.texts[0])
        for text in self.texts[1:]:
            content += " (%s)'" % (text)
        content += " ET Q EMC\n"
        if writer.compress:
            import zlib
            content = zlib.compress(content)

        file.write("<<\n")
        file.write("/Type /XObject\n")
        file.write("/Subtype /Form\n")
        file.write("/BBox [%f %f %f %f]\n" % self.bb)
        #ile.write("/Matrix [0.98 0.17 -0.17 0.98 0 0]\n")
        file.write("/Resources ")
        self.registry.writeresources(file) # default resources for appearance
        file.write("/Length %i\n" % len(content))
        if writer.compress:
            file.write("/Filter /FlateDecode\n")
        file.write(">>\n"
                   "stream\n")
        file.write(content)
        file.write("endstream\n")
# >>>


class radiobuttons(formfield): # <<<

    """A set of related buttons that can each be on or off.

    Typically, at most one radio button in a set may be on at any
    given time, and selecting any one of the buttons
    automatically deselects all the others.

    Note that the behaviour under rotations is undefined."""

    defaultflags = dict(invisible=0, hidden=0, printable=1, nozoom=0,
        norotate=0, noview=0, readonly=0, required=0, noexport=0, notoggletooff=0)

    def __init__(self, positions, name, values, defaultvalue=None, size=10, baselinerelpos=0.2, **flags):

        self.name = name
        self.size_pt = _topt(size, "x", "pt")
        self.positions_pt = [(_topt(x), _topt(y) - baselinerelpos*self.size_pt) for x, y in positions]
        self.flags = self.selectflags(flags)
        self.flags["radio"] = 1
        self.values = values
        self.defaultvalue = defaultvalue

    def bbox(self):
        llx = min([x[0] for x in self.positions_pt])
        lly = min([x[1] for x in self.positions_pt])
        urx = max([x[0] for x in self.positions_pt]) + self.size_pt
        ury = max([x[1] for x in self.positions_pt]) + self.size_pt
        return bbox.bbox_pt(llx, lly, urx, ury)

    def processPDF(self, file, writer, context, registry, bbox):
        # the bbox is transformed by the canvas
        bbox += self.bbox()

        # the annotation rectangle must be transformed separately:
        positions_pt = [context.trafo.apply_pt(x, y) for x, y in self.positions_pt]
        size_pt = _sizetrafo(self.size_pt, context.trafo)

        # we create numbers from the flags given
        annotflag, formflag = _pdfflags(self.flags)

        onstate = PDFButtonState(writer, registry,
            10, PDFZapfDingbats, bgchar="m", fgchar="8",
            bgscale=1.1, bgrelshift=(0, 0.18), fgrelshift=(0.12, 0.26))
        offstate = PDFButtonState(writer, registry,
            10, PDFZapfDingbats, bgchar="m", fgchar=None,
            bgscale=1.1, bgrelshift=(0, 0.18))
        registry.add(onstate)
        registry.add(offstate)

        registry.add(PDFbuttonlist(positions_pt, self.name, size_pt, self.values, self.defaultvalue,
            annotflag, formflag, onstate, offstate, writer, registry))
# >>>
class checkbox(formfield): # <<<

    """Toggles between two states, on and off

    Note that the behaviour under rotations is undefined."""

    defaultflags = dict(invisible=0, hidden=0, printable=1, nozoom=0,
        norotate=0, noview=0, readonly=0, required=0, noexport=0)

    def __init__(self, x, y, name, defaulton=0, size=10, baselinerelpos=0.2, **flags):

        self.name = name
        self.size_pt = _topt(size, "x", "pt")
        self.llx_pt, self.lly_pt = _topt(x), _topt(y) - baselinerelpos*self.size_pt
        self.urx_pt, self.ury_pt = self.llx_pt + self.size_pt, self.lly_pt + self.size_pt
        self.flags = self.selectflags(flags)
        self.defaulton = defaulton

    def processPDF(self, file, writer, context, registry, bbox):
        # the bbox is transformed by the canvas
        bbox += self.bbox()

        # the annotation rectangle must be transformed separately:
        positions_pt = [context.trafo.apply_pt(self.llx_pt, self.lly_pt)]
        size_pt = _sizetrafo(self.size_pt, context.trafo)

        # we create numbers from the flags given
        annotflag, formflag = _pdfflags(self.flags)

        onstate = PDFButtonState(writer, registry,
            10, PDFZapfDingbats, bgchar="o", fgchar="4",
            bgscale=1.2, bgrelshift=(0, 0.08), fgscale=0.9, fgrelshift=(0.15, 0.25))
        offstate = PDFButtonState(writer, registry,
            10, PDFZapfDingbats, bgchar="o", fgchar=None,
            bgscale=1.2, bgrelshift=(0, 0.08))
        registry.add(onstate)
        registry.add(offstate)

        if self.defaulton:
            default = "Yes"
        else:
            default = "Off"

        registry.add(PDFbuttonlist(positions_pt, self.name, size_pt, ["Yes"], default,
            annotflag, formflag, onstate, offstate, writer, registry))
# >>>
class PDFbuttonlist(pdfwriter.PDFobject): # <<<

    def __init__(self, positions_pt, name, size_pt, values, defaultvalue, annotflag, formflag,
        onstate, offstate, writer, registry):

        pdfwriter.PDFobject.__init__(self, "formfield_buttonlist")

        # append this formfield to the global document form
        # but we do not treat this as a fully valid annotation field
        for object in registry.objects:
            if object.type == "form":
                object.append(self)

        self.name = name
        self.formflag = formflag
        self.annotflag = annotflag

        self.size_pt = size_pt
        self.defaultvalue = defaultvalue
        self.onstate = onstate
        self.offstate = offstate

        self.checkboxes = []
        for i, pos_pt, value in zip(list(range(len(values))), positions_pt, values):
            chbox = PDFcheckboxfield(pos_pt, value, size_pt, _simplestring(value), (value == defaultvalue),
                self, self.onstate, self.offstate, self.annotflag, self.formflag, writer, registry)
            self.checkboxes.append(chbox)
            registry.add(chbox)

    def write(self, file, writer, registry):
        ### implementation note: There are some (undocumented) PDF flaws which
        ### do not allow to inherit certain variables:
        ### * The parent button may not have /Ff (otherwise, notoggletooff fails)
        ### * The Kids of a radio button may not have a /T on their own (otherwise, they are not displayed)
        ### * The /BS and /Border do not draw anything.
        ###   Nevertheless, the border width of /Border is used

        ### the dictionary entries for the annotation
        file.write("<<\n")
        ### the dictionary entries for the form field
        file.write("/FT /Btn\n") # type of the form field
        file.write("/Kids [%s]\n" % " ".join(["%d 0 R" % registry.getrefno(x) for x in self.checkboxes]))
        file.write("/T (%s)\n" % self.name) # partial field name
        file.write("/TU (%s)\n" % self.name) # field name for the user-interface
        file.write("/TM (%s)\n" % self.name) # field name for exporting the data
        ### the dictionary entries for the radiobuttons field
        file.write("/V /%s\n" % self.defaultvalue)
        file.write(">>\n")
# >>>
class PDFcheckboxfield(pdfwriter.PDFobject): # <<<

    def __init__(self, pos_pt, name, size_pt, valuename, defaulton, parent, onstate, offstate, annotflag, formflag, writer, registry):

        pdfwriter.PDFobject.__init__(self, "formfield_checkbox")

        # we treat this as an annotation only, since the parent is
        # already in the form field
        self.PDFform = None
        for object in registry.objects:
            if object.type == "form":
                assert self.PDFform is None
                self.PDFform = object
            if object.type == "annotations":
                object.append(self)

        self.bb_pt = (pos_pt[0], pos_pt[1], pos_pt[0] + size_pt, pos_pt[1] + size_pt)
        self.name = name
        self.size_pt = size_pt
        self.valuename = valuename
        if defaulton:
            self.defaultvalue = self.valuename
        else:
            self.defaultvalue = "Off"
        self.parent = parent
        self.onstate = onstate
        self.offstate = offstate
        self.annotflag = annotflag
        self.formflag = formflag

    def write(self, file, writer, registry):
        ### the dictionary entries for the annotation
        file.write("<<\n")
        file.write("/Type /Annot\n")
        file.write("/Subtype /Widget\n")
        file.write("/P %d 0 R\n" % registry.getrefno(self.PDFform)) # reference to the page objects
        file.write("/Rect [%f %f %f %f]\n" % self.bb_pt) # the annotation rectangle
        file.write("/F %d\n" % self.annotflag) # flags
        ### the dictionary entries for the widget annotations
        file.write("/H /N\n") # hightlight behaviour
        ### the dictionary entries for the form field
        file.write("/FT /Btn\n") # type of the form field
        file.write("/Parent %d 0 R\n" % registry.getrefno(self.parent)) # only for hierarchy
        file.write("/AP << /N << /%s %d 0 R /Off %d 0 R >> >>\n" % (self.valuename, registry.getrefno(self.onstate), registry.getrefno(self.offstate)))
        file.write("/AS /%s\n" % self.defaultvalue)
        file.write("/Ff %d\n" % self.formflag) # Ff may not come from parent!
        file.write(">>\n")
# >>>
class PDFButtonState(pdfwriter.PDFobject): # <<<

    def __init__(self, writer, registry, fontsize, font, bgchar, fgchar,
        bgscale=None, bgrelshift=None, fgscale=None, fgrelshift=None):

        pdfwriter.PDFobject.__init__(self, "buttonstate", "buttonstate" + "_".join(map(str, list(map(id, [fontsize, font, bgchar, fgchar, bgscale, bgrelshift, fgscale, fgrelshift])))))
        self.font = font
        self.fontsize = fontsize
        registry.addresource("Font", self.font.name, self.font, procset="Text")
        registry.add(self.font)
        self.bb = 0, 0, fontsize, fontsize
        self.bgchar = bgchar
        self.fgchar = fgchar

        if bgscale is None and bgrelshift is not None:
            bgscale = 1
        if bgscale is not None and bgrelshift is None:
            bgrelshift = 0, 0
        if bgscale is not None:
            self.bgtrafo = "%f 0 0 %f %f %f Tm" % (bgscale, bgscale, bgrelshift[0]*self.fontsize, bgrelshift[1]*self.fontsize)
        else:
            self.bgtrafo = ""

        if fgscale is None and fgrelshift is not None:
            fgscale = 1
        if fgscale is not None and fgrelshift is None:
            fgrelshift = 0, 0
        if fgscale is not None:
            self.fgtrafo = "%f 0 0 %f %f %f Tm" % (fgscale, fgscale, fgrelshift[0]*self.fontsize, fgrelshift[1]*self.fontsize)
        else:
            self.fgtrafo = ""

    def write(self, file, writer, registry):
        content = ""
        if self.bgchar:
            content += "q BT /%s %f Tf %s (%s) Tj ET Q\n" % (self.font.name, self.fontsize, self.bgtrafo, self.bgchar)
        if self.fgchar:
            content += "q BT /%s %f Tf %s (%s) Tj ET Q\n" % (self.font.name, self.fontsize, self.fgtrafo, self.fgchar)
        if writer.compress:
            import zlib
            content = zlib.compress(content)

        file.write("<<\n")
        file.write("/Type /XObject\n")
        file.write("/Subtype /Form\n")
        file.write("/BBox [%f %f %f %f]\n" % self.bb)
        #ile.write("/Matrix [0.98 0.17 -0.17 0.98 0 0]\n")
        file.write("/Resources <</Font << /%s %d 0 R >> /ProcSet [/PDF /Text] >>\n" %
                   (self.font.name, registry.getrefno(self.font)))
        file.write("/Length %i\n" % len(content))
        if writer.compress:
            file.write("/Filter /FlateDecode\n")
        file.write(">>\n"
                   "stream\n")
        file.write(content)
        file.write("endstream\n")


## Zapf Dingbats symbols for further buttonstates:
# "3" = thin checkmark
# "4" = thick checkmark
# "5" = thin large cross
# "6" = thick large cross
# "7" = thin small cross
# "8" = thick small cross
# "l" = filled circle
# "m" = empty circle
# "n" = filled rectangle
# "o" = empty rectangle (shadow bottom right)
# "p" = empty rectangle (shadow top right)
# "q" = empty box (to bottom right)
# "r" = empty box (to top right)
# >>>


class choicefield(formfield): # <<<
    """An interactive pdf form field for text input.

    The name is used for the graphical user interface and for exporing the input data.
    Note that the behaviour under rotations is undefined."""

    defaultflags = dict(invisible=0, hidden=0, printable=1, nozoom=0,
        norotate=0, noview=0, readonly=0, required=0, noexport=0, combo=1,
        edit=0, sort=0, multiselect=0, donotspellcheck=1)

    def __init__(self, x, y, width, height, name, values, defaultvalue=None, fontsize=10, font=None,
        borderwidth=0, align="l", **flags):

        self.llx_pt, self.lly_pt = _topt(x), _topt(y)
        self.urx_pt, self.ury_pt = _topt(x+width), _topt(y+height)
        self.name = name
        self.values = values
        self.defaultvalue = defaultvalue
        self.fontsize_pt = _topt(fontsize, "x", "pt")
        self.font = font # TODO: add the generic fonts
        self.borderwidth_pt = _topt(borderwidth, "x", "pt")
        self.flags = self.selectflags(flags)
        self.align = align

    def processPDF(self, file, writer, context, registry, bbox):
        # the bounding box is transformed by the canvas
        bbox += self.bbox()

        # the annotation rectangle must be transformed separately:
        llx_pt, lly_pt = context.trafo.apply_pt(self.llx_pt, self.lly_pt)
        urx_pt, ury_pt = context.trafo.apply_pt(self.urx_pt, self.ury_pt)
        fontsize_pt = _sizetrafo(self.fontsize_pt, context.trafo)
        borderwidth_pt = _sizetrafo(self.borderwidth_pt, context.trafo)

        # we create numbers from the flags given
        annotflag, formflag = _pdfflags(self.flags)
        alignflag = _pdfalignment(self.align)

        registry.add(PDFchoicefield((llx_pt, lly_pt, urx_pt, ury_pt),
            self.name, self.values, self.defaultvalue, fontsize_pt, self.font,
            borderwidth_pt, alignflag, annotflag, formflag, writer, registry))
# >>>
class PDFchoicefield(pdfwriter.PDFobject): # <<<

    def __init__(self, bb_pt, name, values, defaultvalue, fontsize, font,
        borderwidth_pt, alignflag, annotflag, formflag, writer, registry):

        pdfwriter.PDFobject.__init__(self, "formfield_choice")

        # append this formfield to the global document form
        # and to the annotation list of the page:
        self.PDFform = None
        for object in registry.objects:
            if object.type == "form":
                object.append(self)
                self.PDFform = object
            elif object.type == "annotations":
                object.append(self)

        self.name = name
        self.bb_pt = bb_pt
        self.values = values
        self.defaultvalue = defaultvalue
        self.fontsize = fontsize
        self.font = font
        if self.font is None:
            self.font = PDFHelvetica
        registry.addresource("Font", self.font.name, self.font, procset="Text")
        registry.add(self.font)
        self.borderwidth_pt = borderwidth_pt
        self.alignflag = alignflag
        self.formflag = formflag
        self.annotflag = annotflag

    def write(self, file, writer, registry):
        ### the dictionary entries for the annotation
        file.write("<</Type /Annot\n")
        file.write("/P %d 0 R\n" % registry.getrefno(self.PDFform)) # reference to the page objects
        file.write("/Rect [%f %f %f %f]\n" % self.bb_pt) # the annotation rectangle
        #ile.write("/BS << ... >>\n" # border style dictionary
        file.write("/Border [0 0 %f]\n" % self.borderwidth_pt) # border style
        file.write("/F %d\n" % self.annotflag)
        ### the dictionary entries for the widget annotations
        file.write("/Subtype /Widget\n")
        file.write("/H /N\n") # highlight behaviour
        #ile.write("/AP <</N  >>\n") # appearance dictionary TODO
        ### the dictionary entries for the form field
        file.write("/FT /Ch\n") # type of the form field
        file.write("/T (%s)\n" % self.name) # partial field name
        file.write("/TU (%s)\n" % self.name) # field name for the user-interface
        file.write("/TM (%s)\n" % self.name) # field name for exporting the data
        if self.defaultvalue in self.values:
            file.write("/V (%s)\n" % self.defaultvalue) # starting value
        file.write("/Ff %d\n" % self.formflag) # flags for various purposes
        ### the dictionary entries for the text field
        file.write("/DR <</Font <</%s %d 0 R >> >>\n" % (self.font.name, registry.getrefno(self.font))) # default resources for appearance
        file.write("/DA (/%s %f Tf)\n" % (self.font.name, self.fontsize)) # default appearance string
        file.write("/Q %d\n" % self.alignflag)
        file.write("/Opt [")
        for value in self.values:
            file.write(" (%s)" % value)
        file.write(" ]\n")
        file.write(">>\n")
# >>>


# vim:foldmethod=marker:foldmarker=<<<,>>>

