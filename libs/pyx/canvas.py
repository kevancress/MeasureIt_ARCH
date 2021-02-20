# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2002-2012 Jörg Lehmann <joerg@pyx-project.org>
# Copyright (C) 2002-2012 André Wobst <wobsta@pyx-project.org>
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

"""The canvas module provides a PostScript canvas class and related classes

A canvas holds a collection of all elements and corresponding attributes to be
displayed. """

import io, logging, os, sys, string, tempfile
from . import attr, baseclasses, config, document, style, trafo, svgwriter, unit
from . import bbox as bboxmodule

logger = logging.getLogger("pyx")

def _wrappedindocument(method):
    def wrappedindocument(self, file=None, **kwargs):
        page_kwargs = {}
        write_kwargs = {}
        for name, value in list(kwargs.items()):
            if name.startswith("page_"):
                page_kwargs[name[5:]] = value
            elif name.startswith("write_"):
                write_kwargs[name[6:]] = value
            else:
                logger.warning("implicit page keyword argument passing is deprecated; keyword argument '%s' of %s method should be changed to 'page_%s'" %
                               (name, method.__name__, name))
                page_kwargs[name] = value
        d = document.document([document.page(self, **page_kwargs)])
        self.__name__ = method.__name__
        self.__doc__ = method.__doc__
        return method(d, file, **write_kwargs)
    return wrappedindocument

#
# clipping class
#

class SVGclippath(svgwriter.SVGresource):

    def __init__(self, path):
        self.svgid = "clippath%d" % id(path)
        super().__init__("clip-path", self.svgid)
        self.path = path

    def output(self, xml, writer, registry):
        xml.startSVGElement("clipPath", {"id": self.svgid})
        # TODO: clip-rule missing (defaults to nonzero)
        xml.startSVGElement("path", {"d": self.path.returnSVGdata()})
        xml.endSVGElement("path")
        xml.endSVGElement("clipPath")


class clip(attr.attr):

    """class for use in canvas constructor which clips to a path"""

    def __init__(self, path):
        """construct a clip instance for a given path"""
        self.path = path

    def processPS(self, file, writer, context, registry):
        file.write("newpath\n")
        self.path.outputPS(file, writer)
        file.write("clip\n")

    def processPDF(self, file, writer, context, registry):
        self.path.outputPDF(file, writer)
        file.write("W n\n")

    def processSVGattrs(self, attrs, writer, context, registry):
        clippath = SVGclippath(self.path)
        registry.add(clippath)
        attrs["clip-path"] = "url(#%s)" % clippath.svgid


#
# general canvas class
#

class canvas(baseclasses.canvasitem):

    """a canvas holds a collection of canvasitems"""

    def __init__(self, attrs=None, textengine=None, ipython_bboxenlarge=1*unit.t_pt):

        """construct a canvas

        The canvas can be modfied by supplying a list of attrs, which have
        to be instances of one of the following classes:
         - trafo.trafo (leading to a global transformation of the canvas)
         - canvas.clip (clips the canvas)
         - style.strokestyle, style.fillstyle (sets some global attributes of the canvas)

        Note that, while the first two properties are fixed for the
        whole canvas, the last one can be changed via canvas.set().

        The textengine instance used for the text method can be specified
        using the textengine argument. It defaults to text.defaulttextengine

        """

        self.items = []
        self.trafo = trafo.identity
        self.clip = None
        self.layers = {}
        if attrs is None:
            attrs = []
        if textengine is not None:
            self.textengine = textengine
        else:
            # prevent cyclic imports
            from . import text
            self.textengine = text.defaulttextengine
        self.ipython_bboxenlarge = ipython_bboxenlarge

        attr.checkattrs(attrs, [trafo.trafo_pt, clip, style.style])
        attrs = attr.mergeattrs(attrs)
        self.modifies_state = bool(attrs)

        self.styles = attr.getattrs(attrs, [style.style])

        # trafos (and one possible clip operation) are applied from left to
        # right in the attrs list -> reverse for calculating total trafo
        for aattr in reversed(attr.getattrs(attrs, [trafo.trafo_pt, clip])):
            if isinstance(aattr, trafo.trafo_pt):
                self.trafo = self.trafo * aattr
            else:
                if self.clip is not None:
                    raise ValueError("single clipping allowed only")
                self.clip = clip(aattr.path.transformed(self.trafo))

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]

    def _repr_png_(self):
        """
        Automatically represent as PNG graphic when evaluated in IPython notebook.
        """
        return self.pipeGS(device="png16m", page_bboxenlarge=self.ipython_bboxenlarge).getvalue()

    def _repr_svg_(self):
        """
        Automatically represent as SVG graphic when evaluated in IPython notebook.
        """
        f = io.BytesIO()
        self.writeSVGfile(f, page_bboxenlarge=self.ipython_bboxenlarge)
        return f.getvalue().decode("utf-8")

    def bbox(self):
        """returns bounding box of canvas

        Note that this bounding box doesn't take into account the linewidths, so
        is less accurate than the one used when writing the output to a file.
        """
        obbox = bboxmodule.empty()
        for cmd in self.items:
            obbox += cmd.bbox()

        # transform according to our global transformation and
        # intersect with clipping bounding box (which has already been
        # transformed in canvas.__init__())
        obbox.transform(self.trafo)
        if self.clip is not None:
            obbox *= self.clip.path.bbox()
        return obbox

    def processPS(self, file, writer, context, registry, bbox):
        context = context()
        if self.items:
            if self.modifies_state:
                file.write("gsave\n")
                for attr in self.styles:
                    attr.processPS(file, writer, context, registry)
                if self.clip is not None:
                    self.clip.processPS(file, writer, context, registry)
                if self.trafo is not trafo.identity:
                    self.trafo.processPS(file, writer, context, registry)
            nbbox = bboxmodule.empty()
            for item in self.items:
                item.processPS(file, writer, context, registry, nbbox)
            # update bounding bbox
            nbbox.transform(self.trafo)
            if self.clip is not None:
                nbbox *= self.clip.path.bbox()
            bbox += nbbox
            if self.modifies_state:
                file.write("grestore\n")

    def processPDF(self, file, writer, context, registry, bbox):
        context = context()
        textregion = False
        context.trafo = context.trafo * self.trafo
        if self.items:
            if self.modifies_state:
                file.write("q\n") # gsave
                for attr in self.styles:
                    if isinstance(attr, style.fillstyle):
                        context.fillstyles.append(attr)
                    attr.processPDF(file, writer, context, registry)
                if self.clip is not None:
                    self.clip.processPDF(file, writer, context, registry)
                if self.trafo is not trafo.identity:
                    self.trafo.processPDF(file, writer, context, registry)
            nbbox = bboxmodule.empty()
            for item in self.items:
                if not writer.textaspath:
                    if item.requiretextregion():
                        if not textregion:
                            file.write("BT\n")
                            textregion = True
                    else:
                        if textregion:
                            file.write("ET\n")
                            textregion = False
                            context.selectedfont = None
                item.processPDF(file, writer, context, registry, nbbox)
            if textregion:
                file.write("ET\n")
                textregion = False
                context.selectedfont = None
            # update bounding bbox
            nbbox.transform(self.trafo)
            if self.clip is not None:
                nbbox *= self.clip.path.bbox()
            bbox += nbbox
            if self.modifies_state:
                file.write("Q\n") # grestore

    def processSVG(self, xml, writer, context, registry, bbox):
        if self.items:
            if self.modifies_state:
                context = context()
                attrs = {}
                for attr in self.styles:
                    attr.processSVGattrs(attrs, writer, context, registry)
                if self.clip is not None:
                    self.clip.processSVGattrs(attrs, writer, context, registry)
                    if self.trafo is not trafo.identity:
                        # trafo needs to be applied after clipping
                        # thus write g and start anew
                        xml.startSVGElement("g", attrs)
                        attrs = {}
                        self.trafo.processSVGattrs(attrs, writer, context, registry)
                elif self.trafo is not trafo.identity:
                    self.trafo.processSVGattrs(attrs, writer, context, registry)
                xml.startSVGElement("g", attrs)
            nbbox = bboxmodule.empty()
            for item in self.items:
                item.processSVG(xml, writer, context, registry, nbbox)
            # update bounding bbox
            nbbox.transform(self.trafo)
            if self.clip is not None:
                nbbox *= self.clip.path.bbox()
            bbox += nbbox
            if self.modifies_state:
                xml.endSVGElement("g")
                if self.clip is not None and self.trafo is not trafo.identity:
                    xml.endSVGElement("g")

    def layer(self, name, above=None, below=None):
        """create or get a layer with name

        A layer is a canvas itself and can be used to combine drawing
        operations for ordering purposes, i.e., what is above and below each
        other. The layer name is a dotted string, where dots are used to form
        a hierarchy of layer groups. When inserting a layer, it is put on top
        of its layer group except when another layer of this group is specified
        by means of the parameters above or below.

        """
        if above is not None and below is not None:
            raise ValueError("above and below cannot be specified at the same time")
        try:
            group, layer = name.split(".", 1)
        except ValueError:
            if name in self.layers:
                if above is not None or below is not None:
                    # remove for repositioning
                    self.items.remove(self.layers[name])
            else:
                # create new layer
                self.layers[name] = canvas(textengine=self.textengine)
                if above is None and below is None:
                    self.items.append(self.layers[name])

            # (re)position layer
            if above is not None:
                self.items.insert(self.items.index(self.layers[above])+1, self.layers[name])
            elif below is not None:
                self.items.insert(self.items.index(self.layers[below]), self.layers[name])

            return self.layers[name]
        else:
            if not group in self.layers:
                self.layers[group] = self.insert(canvas(textengine=self.textengine))
            if above is not None:
                abovegroup, above = above.split(".", 1)
                assert abovegroup == group
            if below is not None:
                belowgroup, below = below.split(".", 1)
                assert belowgroup == group
            return self.layers[group].layer(layer, above=above, below=below)

    def insert(self, item, attrs=None):
        """insert item in the canvas.

        If attrs are passed, a canvas containing the item is inserted applying
        attrs. If replace is not None, the new item is
        positioned accordingly in the canvas.

        returns the item, possibly wrapped in a canvas

        """

        if not isinstance(item, baseclasses.canvasitem):
            raise ValueError("only instances of baseclasses.canvasitem can be inserted into a canvas")

        if attrs:
            sc = canvas(attrs)
            sc.insert(item)
            item = sc

        self.items.append(item)
        return item

    def draw(self, path, attrs):
        """draw path on canvas using the style given by args

        The argument attrs consists of PathStyles, which modify
        the appearance of the path, PathDecos, which add some new
        visual elements to the path, or trafos, which are applied
        before drawing the path.

        """
        from . import deco
        attrs = attr.mergeattrs(attrs)
        attr.checkattrs(attrs, [deco.deco, baseclasses.deformer, style.style])

        for adeformer in attr.getattrs(attrs, [baseclasses.deformer]):
            path = adeformer.deform(path)

        styles = attr.getattrs(attrs, [style.style])
        dp = deco.decoratedpath(path, styles=styles)

        # add path decorations and modify path accordingly
        for adeco in attr.getattrs(attrs, [deco.deco]):
            adeco.decorate(dp, self.textengine)

        self.insert(dp)

    def stroke(self, path, attrs=[]):
        """stroke path on canvas using the style given by args

        The argument attrs consists of PathStyles, which modify
        the appearance of the path, PathDecos, which add some new
        visual elements to the path, or trafos, which are applied
        before drawing the path.

        """
        from . import deco
        self.draw(path, [deco.stroked]+list(attrs))

    def fill(self, path, attrs=[]):
        """fill path on canvas using the style given by args

        The argument attrs consists of PathStyles, which modify
        the appearance of the path, PathDecos, which add some new
        visual elements to the path, or trafos, which are applied
        before drawing the path.

        """
        from . import deco
        self.draw(path, [deco.filled]+list(attrs))

    def settextengine(self, textengine):
        """sets the textengine to be used to within the text and text_pt methods"""

        self.textengine = textengine

    def text(self, x, y, atext, *args, **kwargs):
        """insert a text into the canvas

        inserts a textbox created by self.textengine.text into the canvas

        returns the inserted textbox"""

        return self.insert(self.textengine.text(x, y, atext, *args, **kwargs))


    def text_pt(self, x, y, atext, *args):
        """insert a text into the canvas

        inserts a textbox created by self.textengine.text_pt into the canvas

        returns the inserted textbox"""

        return self.insert(self.textengine.text_pt(x, y, atext, *args))

    writeEPSfile = _wrappedindocument(document.document.writeEPSfile)
    writePSfile = _wrappedindocument(document.document.writePSfile)
    writePDFfile = _wrappedindocument(document.document.writePDFfile)
    writeSVGfile = _wrappedindocument(document.document.writeSVGfile)
    writetofile = _wrappedindocument(document.document.writetofile)


    def _gscmd(self, device, filename, resolution=100, gs="gs", gsoptions=[],
               textalphabits=4, graphicsalphabits=4, ciecolor=False, **kwargs):

        cmd = [gs, "-dEPSCrop", "-dNOPAUSE", "-dQUIET", "-dBATCH", "-r%d" % resolution, "-sDEVICE=%s" % device, "-sOutputFile=%s" % filename]
        if textalphabits is not None:
            cmd.append("-dTextAlphaBits=%i" % textalphabits)
        if graphicsalphabits is not None:
            cmd.append("-dGraphicsAlphaBits=%i" % graphicsalphabits)
        if ciecolor:
            cmd.append("-dUseCIEColor")
        cmd.extend(gsoptions)

        return cmd, kwargs

    def writeGSfile(self, filename=None, device=None, input="eps", **kwargs):
        """
        convert EPS or PDF output to a file via Ghostscript

        If filename is None it is auto-guessed from the script name. If
        filename is "-", the output is written to stdout. In both cases, a
        device needs to be specified to define the format.

        If device is None, but a filename with suffix is given, PNG files will
        be written using the png16m device and JPG files using the jpeg device.
        """
        if filename is None:
            if not sys.argv[0].endswith(".py"):
                raise RuntimeError("could not auto-guess filename")
            if device.startswith("png"):
                filename = sys.argv[0][:-2] + "png"
            elif device.startswith("jpeg"):
                filename = sys.argv[0][:-2] + "jpg"
            else:
                filename = sys.argv[0][:-2] + device
        if device is None:
            if filename.endswith(".png"):
                device = "png16m"
            elif filename.endswith(".jpg"):
                device = "jpeg"
            else:
                raise RuntimeError("could not auto-guess device")

        cmd, kwargs = self._gscmd(device, filename, **kwargs)

        if input == "eps":
            cmd.append("-")
            p = config.Popen(cmd, stdin=config.PIPE)
            self.writeEPSfile(p.stdin, **kwargs)
            p.stdin.close()
            p.wait()
        elif input == "pdf":
            # PDF files need to be accesible by random access and thus we need to create
            # a temporary file
            with tempfile.NamedTemporaryFile("wb", delete=False) as f:
                self.writePDFfile(f, **kwargs)
                fname = f.name
            cmd.append(fname)
            config.Popen(cmd).wait()
            os.unlink(fname)
        else:
            raise RuntimeError("input 'eps' or 'pdf' expected")


    def pipeGS(self, device, input="eps", **kwargs):
        """
        returns a BytesIO instance with the Ghostscript output of the EPS or PDF
        """

        cmd, kwargs = self._gscmd(device, "-", **kwargs)

        with tempfile.NamedTemporaryFile("wb", delete=False) as f:
            if input == "eps":
                self.writeEPSfile(f, **kwargs)
            elif input == "pdf":
                self.writePDFfile(f, **kwargs)
            else:
                raise RuntimeError("input 'eps' or 'pdf' expected")
            fname = f.name

        cmd.append(fname)
        p = config.Popen(cmd, stdout=config.PIPE)
        data, error = p.communicate()
        os.unlink(fname)

        if error:
            raise ValueError("error received while waiting for ghostscript")
        return io.BytesIO(data)
