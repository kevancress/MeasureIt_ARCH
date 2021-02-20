# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2002-2011 Jörg Lehmann <joerg@pyx-project.org>
# Copyright (C) 2003-2011 Michael Schindler <m-schindler@users.sourceforge.net>
# Copyright (C) 2002-2013 André Wobst <wobsta@pyx-project.org>
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

# TODO:
# - should we improve on the arc length -> arg parametrization routine or
#   should we at least factor it out?

import sys, math
from . import attr, baseclasses, canvas, color, path, normpath, style, trafo, unit, deformer

_marker = object()

#
# Decorated path
#

class decoratedpath(baseclasses.canvasitem):
    """Decorated path

    The main purpose of this class is during the drawing
    (stroking/filling) of a path. It collects attributes for the
    stroke and/or fill operations.
    """

    def __init__(self, path, strokepath=None, fillpath=None,
                 styles=None, strokestyles=None, fillstyles=None,
                 ornaments=None):

        self.path = path

        # global style for stroking and filling and subdps
        self.styles = styles

        # styles which apply only for stroking and filling
        self.strokestyles = strokestyles
        self.fillstyles = fillstyles

        # the decoratedpath can contain additional elements of the
        # path (ornaments), e.g., arrowheads.
        if ornaments is None:
            self.ornaments = canvas.canvas()
        else:
            self.ornaments = ornaments

        self.nostrokeranges = None

    def ensurenormpath(self):
        """convert self.path into a normpath"""
        assert self.nostrokeranges is None or isinstance(self.path, path.normpath), "you don't understand what you are doing"
        self.path = self.path.normpath()

    def excluderange(self, begin, end):
        assert isinstance(self.path, path.normpath), "you don't understand what this is about"
        if self.nostrokeranges is None:
            self.nostrokeranges = [(begin, end)]
        else:
            ibegin = 0
            while ibegin < len(self.nostrokeranges) and self.nostrokeranges[ibegin][1] < begin:
                ibegin += 1

            if ibegin == len(self.nostrokeranges):
                self.nostrokeranges.append((begin, end))
                return

            iend = len(self.nostrokeranges) - 1
            while 0 <= iend and end < self.nostrokeranges[iend][0]:
                iend -= 1

            if iend == -1:
                self.nostrokeranges.insert(0, (begin, end))
                return

            if self.nostrokeranges[ibegin][0] < begin:
                begin = self.nostrokeranges[ibegin][0]
            if end < self.nostrokeranges[iend][1]:
                end = self.nostrokeranges[iend][1]

            self.nostrokeranges[ibegin:iend+1] = [(begin, end)]

    def bbox(self):
        pathbbox = self.path.bbox()
        ornamentsbbox = self.ornaments.bbox()
        if ornamentsbbox is not None:
            return ornamentsbbox + pathbbox
        else:
            return pathbbox

    def strokepath(self):
        if self.nostrokeranges:
            splitlist = []
            for begin, end in self.nostrokeranges:
                splitlist.append(begin)
                splitlist.append(end)
            split = self.path.split(splitlist)
            # XXX properly handle closed paths?
            result = split[0]
            for i in range(2, len(split), 2):
                result += split[i]
            return result
        else:
            return self.path

    def processPS(self, file, writer, context, registry, bbox):
        # draw (stroke and/or fill) the decoratedpath on the canvas
        # while trying to produce an efficient output, e.g., by
        # not writing one path two times

        # small helper
        def _writestyles(styles, context, registry):
            for style in styles:
                style.processPS(file, writer, context, registry)

        strokepath = self.strokepath()
        fillpath = self.path

        # apply global styles
        if self.styles:
            file.write("gsave\n")
            context = context()
            _writestyles(self.styles, context, registry)

        if self.fillstyles is not None:
            file.write("newpath\n")
            fillpath.outputPS(file, writer)

            if self.strokestyles is not None and strokepath is fillpath:
                # do efficient stroking + filling if respective paths are identical
                file.write("gsave\n")

                if self.fillstyles:
                    _writestyles(self.fillstyles, context(), registry)

                if context.fillrule:
                    file.write("eofill\n")
                else:
                    file.write("fill\n")
                file.write("grestore\n")

                acontext = context()
                if self.strokestyles:
                    file.write("gsave\n")
                    _writestyles(self.strokestyles, acontext, registry)

                file.write("stroke\n")
                # take linewidth into account for bbox when stroking a path
                bbox += strokepath.bbox().enlarged_pt(0.5*acontext.linewidth_pt)

                if self.strokestyles:
                    file.write("grestore\n")
            else:
                # only fill fillpath - for the moment
                if self.fillstyles:
                    file.write("gsave\n")
                    _writestyles(self.fillstyles, context(), registry)

                if context.fillrule:
                    file.write("eofill\n")
                else:
                    file.write("fill\n")
                bbox += fillpath.bbox()

                if self.fillstyles:
                    file.write("grestore\n")

        if self.strokestyles is not None and (strokepath is not fillpath or self.fillstyles is None):
            # this is the only relevant case still left
            # Note that a possible filling has already been done.
            acontext = context()
            if self.strokestyles:
                file.write("gsave\n")
                _writestyles(self.strokestyles, acontext, registry)

            file.write("newpath\n")
            strokepath.outputPS(file, writer)
            file.write("stroke\n")
            # take linewidth into account for bbox when stroking a path
            bbox += strokepath.bbox().enlarged_pt(0.5*acontext.linewidth_pt)

            if self.strokestyles:
                file.write("grestore\n")

        # now, draw additional elements of decoratedpath
        self.ornaments.processPS(file, writer, context, registry, bbox)

        # restore global styles
        if self.styles:
            file.write("grestore\n")

    def processPDF(self, file, writer, context, registry, bbox):
        # draw (stroke and/or fill) the decoratedpath on the canvas

        def _writestyles(styles, context, registry):
            for style in styles:
                style.processPDF(file, writer, context, registry)

        def _writestrokestyles(strokestyles, context, registry):
            context.fillattr = 0
            for style in strokestyles:
                style.processPDF(file, writer, context, registry)
            context.fillattr = 1

        def _writefillstyles(fillstyles, context, registry):
            context.strokeattr = 0
            for style in fillstyles:
                style.processPDF(file, writer, context, registry)
            context.strokeattr = 1

        strokepath = self.strokepath()
        fillpath = self.path

        # apply global styles
        if self.styles:
            file.write("q\n") # gsave
            context = context()
            _writestyles(self.styles, context, registry)

        if self.fillstyles is not None:
            fillpath.outputPDF(file, writer)

            if self.strokestyles is not None and strokepath is fillpath:
                # do efficient stroking + filling
                file.write("q\n") # gsave
                acontext = context()

                if self.fillstyles:
                    _writefillstyles(self.fillstyles, acontext, registry)
                if self.strokestyles:
                    _writestrokestyles(self.strokestyles, acontext, registry)

                if context.fillrule:
                    file.write("B*\n")
                else:
                    file.write("B\n") # both stroke and fill
                # take linewidth into account for bbox when stroking a path
                bbox += strokepath.bbox().enlarged_pt(0.5*acontext.linewidth_pt)

                file.write("Q\n") # grestore
            else:
                # only fill fillpath - for the moment
                if self.fillstyles:
                    file.write("q\n") # gsave
                    _writefillstyles(self.fillstyles, context(), registry)

                if context.fillrule:
                    file.write("f*\n")
                else:
                    file.write("f\n") # fill
                bbox += fillpath.bbox()

                if self.fillstyles:
                    file.write("Q\n") # grestore

        if self.strokestyles is not None and (strokepath is not fillpath or self.fillstyles is None):
            # this is the only relevant case still left
            # Note that a possible stroking has already been done.
            acontext = context()

            if self.strokestyles:
                file.write("q\n") # gsave
                _writestrokestyles(self.strokestyles, acontext, registry)

            strokepath.outputPDF(file, writer)
            file.write("S\n") # stroke
            # take linewidth into account for bbox when stroking a path
            bbox += strokepath.bbox().enlarged_pt(0.5*acontext.linewidth_pt)

            if self.strokestyles:
                file.write("Q\n") # grestore

        # now, draw additional elements of decoratedpath
        self.ornaments.processPDF(file, writer, context, registry, bbox)

        # restore global styles
        if self.styles:
            file.write("Q\n") # grestore

    def processSVG(self, xml, writer, context, registry, bbox):
        def _writestrokestyles(attrs, context):
            context.fillattr = False
            for style in self.strokestyles or []:
                style.processSVGattrs(attrs, writer, context, registry)
            context.fillattr = True

        def _writefillstyles(attrs, context):
            context.strokeattr = False
            for style in self.fillstyles or []:
                style.processSVGattrs(attrs, writer, context, registry)
            context.strokeattr = True

        strokepath = self.strokepath()
        fillpath = self.path

        acontext = context()
        gattrs = {}
        for style in self.styles or []:
            style.processSVGattrs(gattrs, writer, acontext, registry)
        if gattrs:
            xml.startSVGElement("g", gattrs)

        if strokepath is not fillpath:
            if self.strokestyles is not None:
                attrs = {"d": strokepath.returnSVGdata()}
                _writestrokestyles(attrs, acontext)
                attrs["stroke"] = acontext.strokecolor
                if acontext.strokeopacity != 1:
                    attrs["opacity"] = "%f" % acontext.strokeopacity
                xml.startSVGElement("path", attrs)
                xml.endSVGElement("path")
                bbox += strokepath.bbox().enlarged_pt(0.5*acontext.linewidth_pt)
            if self.fillstyles is not None:
                attrs = {"d": fillpath.returnSVGdata()}
                _writefillstyles(attrs, acontext)
                attrs["fill"] = acontext.fillcolor
                if acontext.fillopacity != 1:
                    attrs["opacity"] = "%f" % acontext.fillopacity
                xml.startSVGElement("path", attrs)
                xml.endSVGElement("path")
                bbox += fillpath.bbox()
        else:
            attrs = {"d": fillpath.returnSVGdata()}
            _writestrokestyles(attrs, acontext)
            _writefillstyles(attrs, acontext)
            if self.strokestyles is not None:
                attrs["stroke"] = acontext.strokecolor
            if self.fillstyles is not None:
                attrs["fill"] = acontext.fillcolor
            if acontext.strokeopacity != acontext.fillopacity and self.strokestyles is not None and self.fillstyles is not None:
                if acontext.strokeopacity != 1:
                    attrs["opacity"] = "%f" % acontext.strokeopacity
                attrs["stroke"] = acontext.strokecolor
                attrs["fill"] = "none"
                xml.startSVGElement("path", attrs)
                xml.endSVGElement("path")
                if acontext.fillopacity != 1:
                    attrs["opacity"] = "%f" % acontext.fillopacity
                attrs["stroke"] = "none"
                attrs["fill"] = acontext.fillcolor
                xml.startSVGElement("path", attrs)
                xml.endSVGElement("path")
            else:
                if acontext.strokeopacity != 1 and self.strokestyles is not None:
                    attrs["opacity"] = "%f" % acontext.strokeopacity
                if acontext.fillopacity != 1 and self.fillstyles is not None:
                    attrs["opacity"] = "%f" % acontext.fillopacity
                xml.startSVGElement("path", attrs)
                xml.endSVGElement("path")
            if self.strokestyles is not None:
                bbox += strokepath.bbox().enlarged_pt(0.5*acontext.linewidth_pt)
            else:
                bbox += strokepath.bbox()

        self.ornaments.processSVG(xml, writer, acontext, registry, bbox)

        if gattrs:
            xml.endSVGElement("g")

#
# Path decorators
#

class deco:

    """decorators

    In contrast to path styles, path decorators depend on the concrete
    path to which they are applied. In particular, they don't make
    sense without any path and can thus not be used in canvas.set!

    """

    def decorate(self, dp, texrunner):
        """apply a style to a given decoratedpath object dp

        decorate accepts a decoratedpath object dp, applies PathStyle
        by modifying dp in place.
        """

        pass

#
# stroked and filled: basic decos which stroked and fill,
# respectively the path
#

class _stroked(deco, attr.exclusiveattr):

    """stroked is a decorator, which draws the outline of the path"""

    def __init__(self, styles=[]):
        attr.exclusiveattr.__init__(self, _stroked)
        self.styles = attr.mergeattrs(styles)
        attr.checkattrs(self.styles, [style.strokestyle])

    def __call__(self, styles=[]):
        # XXX or should we also merge self.styles
        return _stroked(styles)

    def decorate(self, dp, texrunner):
        if dp.strokestyles is not None:
            raise RuntimeError("Cannot stroke an already stroked path")
        dp.strokestyles = self.styles

stroked = _stroked()
stroked.clear = attr.clearclass(_stroked)


class _filled(deco, attr.exclusiveattr):

    """filled is a decorator, which fills the interior of the path"""

    def __init__(self, styles=[]):
        attr.exclusiveattr.__init__(self, _filled)
        self.styles = attr.mergeattrs(styles)
        attr.checkattrs(self.styles, [style.fillstyle])

    def __call__(self, styles=[]):
        # XXX or should we also merge self.styles
        return _filled(styles)

    def decorate(self, dp, texrunner):
        if dp.fillstyles is not None:
            raise RuntimeError("Cannot fill an already filled path")
        dp.fillstyles = self.styles

filled = _filled()
filled.clear = attr.clearclass(_filled)

#
# Arrows
#

# helper function which constructs the arrowhead

def _arrowhead(anormpath, arclenfrombegin, direction, size, angle, constriction, constrictionlen):

    """helper routine, which returns an arrowhead from a given anormpath

    - arclenfrombegin: position of arrow in arc length from the start of the path
    - direction: +1 for an arrow pointing along the direction of anormpath or
                 -1 for an arrow pointing opposite to the direction of normpath
    - size: size of the arrow as arc length
    - angle. opening angle
    - constriction: boolean to indicate whether the constriction point is to be taken into account or not
    - constrictionlen: arc length of constriction. (not used when constriction is false)
    """

    # arc length and coordinates of tip
    tx, ty = anormpath.at(arclenfrombegin)

    # construct the template for the arrow by cutting the path at the
    # corresponding length
    arrowtemplate = anormpath.split([arclenfrombegin, arclenfrombegin - direction * size])[1]

    # from this template, we construct the two outer curves of the arrow
    arrowl = arrowtemplate.transformed(trafo.rotate(-angle/2.0, tx, ty))
    arrowr = arrowtemplate.transformed(trafo.rotate( angle/2.0, tx, ty))

    # now come the joining backward parts
    if constriction:
        # constriction point (cx, cy) lies on path
        cx, cy = anormpath.at(arclenfrombegin - direction * constrictionlen)
        arrowcr= path.line(*(arrowr.atend() + (cx,cy)))
        arrow = arrowl.reversed() << arrowr << arrowcr
    else:
        arrow = arrowl.reversed() << arrowr

    arrow[-1].close()

    return arrow


_base = 6 * unit.v_pt

class arrow(deco, attr.attr):

    """arrow is a decorator which adds an arrow to either side of the path"""

    def __init__(self, attrs=[], pos=1, reversed=0, size=_base, angle=45, constriction=0.8):
        self.attrs = attr.mergeattrs([style.linestyle.solid, filled] + attrs)
        attr.checkattrs(self.attrs, [deco, style.fillstyle, style.strokestyle])
        self.pos = pos
        self.reversed = reversed
        self.size = size
        self.angle = angle
        self.constriction = constriction

        # calculate absolute arc length of constricition
        # Note that we have to correct this length because the arrowtemplates are rotated
        # by self.angle/2 to the left and right. Hence, if we want no constriction, i.e., for
        # self.constriction = 1, we actually have a length which is approximately shorter
        # by the given geometrical factor.
        if self.constriction is not None:
            self.constrictionlen = self.size * self.constriction * math.cos(math.radians(self.angle/2.0))
        else:
            # if we do not want a constriction, i.e. constriction is None, we still
            # need constrictionlen for cutting the path
            self.constrictionlen = self.size * 1 * math.cos(math.radians(self.angle/2.0))

    def __call__(self, attrs=None, pos=None, reversed=None, size=None, angle=None, constriction=_marker):
        if attrs is None:
            attrs = self.attrs
        if pos is None:
            pos = self.pos
        if reversed is None:
            reversed = self.reversed
        if size is None:
            size = self.size
        if angle is None:
            angle = self.angle
        if constriction is _marker:
            constriction = self.constriction
        return arrow(attrs=attrs, pos=pos, reversed=reversed, size=size, angle=angle, constriction=constriction)

    def decorate(self, dp, texrunner):
        dp.ensurenormpath()
        anormpath = dp.path

        arclenfrombegin = (1-self.reversed)*self.constrictionlen + self.pos * (anormpath.arclen() - self.constrictionlen)
        direction = self.reversed and -1 or 1
        arrowhead = _arrowhead(anormpath, arclenfrombegin, direction, self.size, self.angle,
                               self.constriction is not None, self.constrictionlen)

        # add arrowhead to decoratedpath
        dp.ornaments.draw(arrowhead, self.attrs)

        # exlude part of the path from stroking when the arrow is strictly at the begin or the end
        if self.pos == 0 and self.reversed:
            dp.excluderange(0, min(self.size, self.constrictionlen))
        elif self.pos == 1 and not self.reversed:
            dp.excluderange(anormpath.end() - min(self.size, self.constrictionlen), anormpath.end())

arrow.clear = attr.clearclass(arrow)

# arrows at begin of path
barrow = arrow(pos=0, reversed=1)
barrow.SMALL = barrow(size=_base/math.sqrt(64))
barrow.SMALl = barrow(size=_base/math.sqrt(32))
barrow.SMAll = barrow(size=_base/math.sqrt(16))
barrow.SMall = barrow(size=_base/math.sqrt(8))
barrow.Small = barrow(size=_base/math.sqrt(4))
barrow.small = barrow(size=_base/math.sqrt(2))
barrow.normal = barrow(size=_base)
barrow.large = barrow(size=_base*math.sqrt(2))
barrow.Large = barrow(size=_base*math.sqrt(4))
barrow.LArge = barrow(size=_base*math.sqrt(8))
barrow.LARge = barrow(size=_base*math.sqrt(16))
barrow.LARGe = barrow(size=_base*math.sqrt(32))
barrow.LARGE = barrow(size=_base*math.sqrt(64))

# arrows at end of path
earrow = arrow()
earrow.SMALL = earrow(size=_base/math.sqrt(64))
earrow.SMALl = earrow(size=_base/math.sqrt(32))
earrow.SMAll = earrow(size=_base/math.sqrt(16))
earrow.SMall = earrow(size=_base/math.sqrt(8))
earrow.Small = earrow(size=_base/math.sqrt(4))
earrow.small = earrow(size=_base/math.sqrt(2))
earrow.normal = earrow(size=_base)
earrow.large = earrow(size=_base*math.sqrt(2))
earrow.Large = earrow(size=_base*math.sqrt(4))
earrow.LArge = earrow(size=_base*math.sqrt(8))
earrow.LARge = earrow(size=_base*math.sqrt(16))
earrow.LARGe = earrow(size=_base*math.sqrt(32))
earrow.LARGE = earrow(size=_base*math.sqrt(64))


class text(deco, attr.attr):
    """a simple text decorator"""

    def __init__(self, text, textattrs=[], angle=0, relangle=None, textdist=0.2,
                       relarclenpos=0.5, arclenfrombegin=None, arclenfromend=None,
                       texrunner=None):
        if arclenfrombegin is not None and arclenfromend is not None:
            raise ValueError("either set arclenfrombegin or arclenfromend")
        self.text = text
        self.textattrs = textattrs
        self.angle = angle
        self.relangle = relangle
        self.textdist = textdist
        self.relarclenpos = relarclenpos
        self.arclenfrombegin = arclenfrombegin
        self.arclenfromend = arclenfromend
        self.texrunner = texrunner

    def decorate(self, dp, texrunner):
        if self.texrunner:
            texrunner = self.texrunner
        from . import text as textmodule
        textattrs = attr.mergeattrs([textmodule.halign.center, textmodule.vshift.mathaxis] + self.textattrs)

        dp.ensurenormpath()
        if self.arclenfrombegin is not None:
            param = dp.path.begin() + self.arclenfrombegin
        elif self.arclenfromend is not None:
            param = dp.path.end() - self.arclenfromend
        else:
            # relarcpos is used, when neither arcfrombegin nor arcfromend is given
            param = self.relarclenpos * dp.path.arclen()
        x, y = dp.path.at(param)

        if self.relangle is not None:
            a = dp.path.trafo(param).apply_pt(math.cos(self.relangle*math.pi/180), math.sin(self.relangle*math.pi/180))
            b = dp.path.trafo(param).apply_pt(0, 0)
            angle = math.atan2(a[1] - b[1], a[0] - b[0])
        else:
            angle = self.angle*math.pi/180
        t = texrunner.text(x, y, self.text, textattrs)
        t.linealign(self.textdist, math.cos(angle), math.sin(angle))
        dp.ornaments.insert(t)

class curvedtext(deco, attr.attr):
    """a text decorator for curved text

    - text: is typeset along the path to which this decorator is applied
    - relarclenpos: position for the base point of the text (default: 0)
    - arlenfrombegin, arclenfromend: alternative ways of specifying the position of the base point;
                                     use of relarclenpos, arclenfrombegin and arclenfromend is mutually exclusive
    - textattrs, texrunner: standard text arguments (defaults: [] resp None)

    """

    # defaulttextattrs = [textmodule.halign.center] # TODO: not possible due to cyclic import issue

    def __init__(self, text, textattrs=[],
                       relarclenpos=0.5, arclenfrombegin=None, arclenfromend=None,
                       texrunner=None, exclude=None):
        if arclenfrombegin is not None and arclenfromend is not None:
            raise ValueError("either set arclenfrombegin or arclenfromend")
        self.text = text
        self.textattrs = textattrs
        self.relarclenpos = relarclenpos
        self.arclenfrombegin = arclenfrombegin
        self.arclenfromend = arclenfromend
        self.texrunner = texrunner
        self.exclude = exclude

    def decorate(self, dp, texrunner):
        if self.texrunner:
            texrunner = self.texrunner
        from . import text as textmodule
        self.defaulttextattrs = [textmodule.halign.center]

        dp.ensurenormpath()
        if self.arclenfrombegin is not None:
            textpos = dp.path.begin() + self.arclenfrombegin
        elif self.arclenfromend is not None:
            textpos = dp.path.end() - self.arclenfromend
        else:
            # relarcpos is used if neither arcfrombegin nor arcfromend is given
            textpos = self.relarclenpos * dp.path.arclen()

        textattrs = self.defaulttextattrs + self.textattrs
        t = texrunner.text(0, 0, self.text, textattrs, singlecharmode=1)
        t.do_finish()

        # we copy the style from the original textbox and modify the position for each dvicanvas item
        c = canvas.canvas(t.dvicanvas.styles)
        for item in t.dvicanvas.items:
            bbox = item.bbox()
            bbox = bbox.transformed(t.texttrafo)
            x = bbox.center()[0]
            atrafo = dp.path.trafo(textpos+x)
            c.insert(item, [t.texttrafo] + [trafo.translate(-x, 0)] + [atrafo])
            if self.exclude is not None:
                dp.excluderange(textpos+bbox.left()-self.exclude, textpos+bbox.right()+self.exclude)

        dp.ornaments.insert(c)


class shownormpath(deco, attr.attr):

    default_normline_attrs = [color.rgb.blue]
    default_normcurve_attrs = [color.rgb.green]
    default_endpoint_attrs = []
    default_controlline_attrs = [color.rgb.red, style.linestyle.dashed]
    default_controlpoint_attrs = [color.rgb.red]

    def __init__(self, normline_attrs=[], normcurve_attrs=[],
                       endpoint_size=0.05*unit.v_cm, endpoint_attrs=[],
                       controlline_attrs=[],
                       controlpoint_size=0.05*unit.v_cm, controlpoint_attrs=[]):
        self.normline_attrs = attr.refineattrs(normline_attrs, self.default_normline_attrs, [style.strokestyle])
        self.normcurve_attrs = attr.refineattrs(normcurve_attrs, self.default_normcurve_attrs, [style.strokestyle])
        self.endpoint_size_pt = unit.topt(endpoint_size)
        self.endpoint_attrs = attr.refineattrs(endpoint_attrs, self.default_endpoint_attrs, [style.fillstyle])
        self.controlline_attrs = attr.refineattrs(controlline_attrs, self.default_controlline_attrs, [style.strokestyle])
        self.controlpoint_size_pt = unit.topt(controlpoint_size)
        self.controlpoint_attrs = attr.refineattrs(controlpoint_attrs, self.default_controlpoint_attrs, [style.fillstyle])

    def decorate(self, dp, texrunner):
        dp.ensurenormpath()
        for normsubpath in dp.path.normsubpaths:
            for i, normsubpathitem in enumerate(normsubpath.normsubpathitems):
                p = path.path(path.moveto_pt(*normsubpathitem.atbegin_pt()), normsubpathitem.pathitem())
                if isinstance(normsubpathitem, normpath.normcurve_pt):
                    if self.normcurve_attrs is not None:
                        dp.ornaments.stroke(p, self.normcurve_attrs)
                else:
                    if self.normline_attrs is not None:
                        dp.ornaments.stroke(p, self.normline_attrs)
        for normsubpath in dp.path.normsubpaths:
            for i, normsubpathitem in enumerate(normsubpath.normsubpathitems):
                if isinstance(normsubpathitem, normpath.normcurve_pt):
                    if self.controlline_attrs is not None:
                        dp.ornaments.stroke(path.line_pt(normsubpathitem.x0_pt, normsubpathitem.y0_pt,
                                                         normsubpathitem.x1_pt, normsubpathitem.y1_pt), self.controlline_attrs)
                        dp.ornaments.stroke(path.line_pt(normsubpathitem.x2_pt, normsubpathitem.y2_pt,
                                                         normsubpathitem.x3_pt, normsubpathitem.y3_pt), self.controlline_attrs)
                    if self.controlpoint_attrs is not None:
                        dp.ornaments.fill(path.circle_pt(normsubpathitem.x1_pt, normsubpathitem.y1_pt, self.controlpoint_size_pt), self.controlpoint_attrs)
                        dp.ornaments.fill(path.circle_pt(normsubpathitem.x2_pt, normsubpathitem.y2_pt, self.controlpoint_size_pt), self.controlpoint_attrs)
        if self.endpoint_attrs is not None:
            for normsubpath in dp.path.normsubpaths:
                for i, normsubpathitem in enumerate(normsubpath.normsubpathitems):
                    if not i:
                        x_pt, y_pt = normsubpathitem.atbegin_pt()
                        dp.ornaments.fill(path.circle_pt(x_pt, y_pt, self.endpoint_size_pt), self.endpoint_attrs)
                    x_pt, y_pt = normsubpathitem.atend_pt()
                    dp.ornaments.fill(path.circle_pt(x_pt, y_pt, self.endpoint_size_pt), self.endpoint_attrs)


class linehatched(deco, attr.exclusiveattr, attr.clearclass):
    """draws a pattern with explicit lines

    This class acts as a drop-in replacement for postscript patterns
    from the pattern module which are not understood by some printers"""

    def __init__(self, dist, angle, strokestyles=[], cross=0):
        attr.clearclass.__init__(self, _filled)
        attr.exclusiveattr.__init__(self, linehatched)
        self.dist = dist
        self.angle = angle
        self.strokestyles = attr.mergeattrs([style.linewidth.THIN] + strokestyles)
        attr.checkattrs(self.strokestyles, [style.strokestyle])
        self.cross = cross

    def __call__(self, dist=None, angle=None, strokestyles=None, cross=None):
        if dist is None:
            dist = self.dist
        if angle is None:
            angle = self.angle
        if strokestyles is None:
            strokestyles = self.strokestyles
        if cross is None:
            cross = self.cross
        return linehatched(dist, angle, strokestyles, cross)

    def _decocanvas(self, angle, dp, texrunner):
        dp.ensurenormpath()
        dist_pt = unit.topt(self.dist)

        c = canvas.canvas([canvas.clip(dp.path)])
        llx_pt, lly_pt, urx_pt, ury_pt = dp.path.bbox().highrestuple_pt()
        center_pt = 0.5*(llx_pt+urx_pt), 0.5*(lly_pt+ury_pt)
        radius_pt = 0.5*math.hypot(urx_pt-llx_pt, ury_pt-lly_pt) + dist_pt
        n = int(2*radius_pt / dist_pt) + 1
        for i in range(n):
            x_pt = center_pt[0] - radius_pt + i*dist_pt
            c.stroke(path.line_pt(x_pt, center_pt[1]-radius_pt, x_pt, center_pt[1]+radius_pt),
                     [trafo.rotate_pt(angle, center_pt[0], center_pt[1])] + self.strokestyles)
        return c

    def decorate(self, dp, texrunner):
        dp.ornaments.insert(self._decocanvas(self.angle, dp, texrunner))
        if self.cross:
            dp.ornaments.insert(self._decocanvas(self.angle+90, dp, texrunner))

    def merge(self, attrs):
        # act as attr.clearclass and as attr.exclusiveattr at the same time
        newattrs = attr.exclusiveattr.merge(self, attrs)
        return attr.clearclass.merge(self, newattrs)

linehatched.clear = attr.clearclass(linehatched)

_hatch_base = 0.1 * unit.v_cm

linehatched0 = linehatched(_hatch_base, 0)
linehatched0.SMALL = linehatched0(_hatch_base/math.sqrt(64))
linehatched0.SMALL = linehatched0(_hatch_base/math.sqrt(64))
linehatched0.SMALl = linehatched0(_hatch_base/math.sqrt(32))
linehatched0.SMAll = linehatched0(_hatch_base/math.sqrt(16))
linehatched0.SMall = linehatched0(_hatch_base/math.sqrt(8))
linehatched0.Small = linehatched0(_hatch_base/math.sqrt(4))
linehatched0.small = linehatched0(_hatch_base/math.sqrt(2))
linehatched0.normal = linehatched0(_hatch_base)
linehatched0.large = linehatched0(_hatch_base*math.sqrt(2))
linehatched0.Large = linehatched0(_hatch_base*math.sqrt(4))
linehatched0.LArge = linehatched0(_hatch_base*math.sqrt(8))
linehatched0.LARge = linehatched0(_hatch_base*math.sqrt(16))
linehatched0.LARGe = linehatched0(_hatch_base*math.sqrt(32))
linehatched0.LARGE = linehatched0(_hatch_base*math.sqrt(64))

linehatched45 = linehatched(_hatch_base, 45)
linehatched45.SMALL = linehatched45(_hatch_base/math.sqrt(64))
linehatched45.SMALl = linehatched45(_hatch_base/math.sqrt(32))
linehatched45.SMAll = linehatched45(_hatch_base/math.sqrt(16))
linehatched45.SMall = linehatched45(_hatch_base/math.sqrt(8))
linehatched45.Small = linehatched45(_hatch_base/math.sqrt(4))
linehatched45.small = linehatched45(_hatch_base/math.sqrt(2))
linehatched45.normal = linehatched45(_hatch_base)
linehatched45.large = linehatched45(_hatch_base*math.sqrt(2))
linehatched45.Large = linehatched45(_hatch_base*math.sqrt(4))
linehatched45.LArge = linehatched45(_hatch_base*math.sqrt(8))
linehatched45.LARge = linehatched45(_hatch_base*math.sqrt(16))
linehatched45.LARGe = linehatched45(_hatch_base*math.sqrt(32))
linehatched45.LARGE = linehatched45(_hatch_base*math.sqrt(64))

linehatched90 = linehatched(_hatch_base, 90)
linehatched90.SMALL = linehatched90(_hatch_base/math.sqrt(64))
linehatched90.SMALl = linehatched90(_hatch_base/math.sqrt(32))
linehatched90.SMAll = linehatched90(_hatch_base/math.sqrt(16))
linehatched90.SMall = linehatched90(_hatch_base/math.sqrt(8))
linehatched90.Small = linehatched90(_hatch_base/math.sqrt(4))
linehatched90.small = linehatched90(_hatch_base/math.sqrt(2))
linehatched90.normal = linehatched90(_hatch_base)
linehatched90.large = linehatched90(_hatch_base*math.sqrt(2))
linehatched90.Large = linehatched90(_hatch_base*math.sqrt(4))
linehatched90.LArge = linehatched90(_hatch_base*math.sqrt(8))
linehatched90.LARge = linehatched90(_hatch_base*math.sqrt(16))
linehatched90.LARGe = linehatched90(_hatch_base*math.sqrt(32))
linehatched90.LARGE = linehatched90(_hatch_base*math.sqrt(64))

linehatched135 = linehatched(_hatch_base, 135)
linehatched135.SMALL = linehatched135(_hatch_base/math.sqrt(64))
linehatched135.SMALl = linehatched135(_hatch_base/math.sqrt(32))
linehatched135.SMAll = linehatched135(_hatch_base/math.sqrt(16))
linehatched135.SMall = linehatched135(_hatch_base/math.sqrt(8))
linehatched135.Small = linehatched135(_hatch_base/math.sqrt(4))
linehatched135.small = linehatched135(_hatch_base/math.sqrt(2))
linehatched135.normal = linehatched135(_hatch_base)
linehatched135.large = linehatched135(_hatch_base*math.sqrt(2))
linehatched135.Large = linehatched135(_hatch_base*math.sqrt(4))
linehatched135.LArge = linehatched135(_hatch_base*math.sqrt(8))
linehatched135.LARge = linehatched135(_hatch_base*math.sqrt(16))
linehatched135.LARGe = linehatched135(_hatch_base*math.sqrt(32))
linehatched135.LARGE = linehatched135(_hatch_base*math.sqrt(64))

crosslinehatched0 = linehatched(_hatch_base, 0, cross=1)
crosslinehatched0.SMALL = crosslinehatched0(_hatch_base/math.sqrt(64))
crosslinehatched0.SMALl = crosslinehatched0(_hatch_base/math.sqrt(32))
crosslinehatched0.SMAll = crosslinehatched0(_hatch_base/math.sqrt(16))
crosslinehatched0.SMall = crosslinehatched0(_hatch_base/math.sqrt(8))
crosslinehatched0.Small = crosslinehatched0(_hatch_base/math.sqrt(4))
crosslinehatched0.small = crosslinehatched0(_hatch_base/math.sqrt(2))
crosslinehatched0.normal = crosslinehatched0
crosslinehatched0.large = crosslinehatched0(_hatch_base*math.sqrt(2))
crosslinehatched0.Large = crosslinehatched0(_hatch_base*math.sqrt(4))
crosslinehatched0.LArge = crosslinehatched0(_hatch_base*math.sqrt(8))
crosslinehatched0.LARge = crosslinehatched0(_hatch_base*math.sqrt(16))
crosslinehatched0.LARGe = crosslinehatched0(_hatch_base*math.sqrt(32))
crosslinehatched0.LARGE = crosslinehatched0(_hatch_base*math.sqrt(64))

crosslinehatched45 = linehatched(_hatch_base, 45, cross=1)
crosslinehatched45.SMALL = crosslinehatched45(_hatch_base/math.sqrt(64))
crosslinehatched45.SMALl = crosslinehatched45(_hatch_base/math.sqrt(32))
crosslinehatched45.SMAll = crosslinehatched45(_hatch_base/math.sqrt(16))
crosslinehatched45.SMall = crosslinehatched45(_hatch_base/math.sqrt(8))
crosslinehatched45.Small = crosslinehatched45(_hatch_base/math.sqrt(4))
crosslinehatched45.small = crosslinehatched45(_hatch_base/math.sqrt(2))
crosslinehatched45.normal = crosslinehatched45
crosslinehatched45.large = crosslinehatched45(_hatch_base*math.sqrt(2))
crosslinehatched45.Large = crosslinehatched45(_hatch_base*math.sqrt(4))
crosslinehatched45.LArge = crosslinehatched45(_hatch_base*math.sqrt(8))
crosslinehatched45.LARge = crosslinehatched45(_hatch_base*math.sqrt(16))
crosslinehatched45.LARGe = crosslinehatched45(_hatch_base*math.sqrt(32))
crosslinehatched45.LARGE = crosslinehatched45(_hatch_base*math.sqrt(64))


class colorgradient(deco, attr.attr):
    """inserts pieces of the path in different colors"""

    def __init__(self, grad, attrs=[], steps=20):
        self.attrs = attrs
        self.grad = grad
        self.steps = steps

    def decorate(self, dp, texrunner):
        dp.ensurenormpath()
        l = dp.path.arclen()

        colors = [self.grad.select(n, self.steps) for n in range(self.steps)]
        colors.reverse()
        params = dp.path.arclentoparam([l*i/float(self.steps) for i in range(self.steps)])
        params.reverse()

        c = canvas.canvas()
        # treat the end pieces separately
        c.stroke(dp.path.split(params[1])[1], attr.mergeattrs([colors[0]] + self.attrs))
        for n in range(1,self.steps-1):
            c.stroke(dp.path.split([params[n-1],params[n+1]])[1], attr.mergeattrs([colors[n]] + self.attrs))
        c.stroke(dp.path.split(params[-2])[0], attr.mergeattrs([colors[-1]] + self.attrs))
        dp.ornaments.insert(c)


class brace(deco, attr.attr):
    r"""draws a nicely curled brace

    In most cases, the original line is not wanted use canvas.canvas.draw(..) for it

    Geometrical parameters:

                 inner /\ strokes
          ____________/  \__________
         /   bar            bar     \ outer
        /                            \ strokes

    totalheight  distance from the jaws to the middle cap
    barthickness  thickness of the main bars
    innerstrokesthickness  thickness of the two ending strokes
    outerstrokesthickness  thickness of the inner strokes at the middle cap
    innerstrokesrelheight  height of the inner/outer strokes, relative to the total height
    outerstrokesrelheight  this determines the angle of the main bars!
                           should be around 0.5
    Note: if innerstrokesrelheight + outerstrokesrelheight == 1 then the main bars
          will be aligned parallel to the connecting line between the endpoints
    outerstrokesangle  angle of the two ending strokes
    innerstrokesangle  angle between the inner strokes at the middle cap
    slantstrokesangle  extra slanting of the inner/outer strokes
    innerstrokessmoothness  smoothing parameter for the inner + outer strokes
    outerstrokessmoothness  should be around 1 (allowed: [0,infty))
    middlerelpos  position of the middle cap (0 == left, 1 == right)
    """
    # This code is experimental because it is unclear
    # how the brace fits into the concepts of PyX
    #
    # Some thoughts:
    # - a brace needs to be decoratable with text
    #   it needs stroking and filling attributes
    # - the brace is not really a box:
    #   it has two "anchor" points that are important for aligning it to other things
    #   and one "anchor" point (plus direction) for aligning other things
    # - a brace is not a deformer:
    #   it does not look at anything else than begin/endpoint of a path
    # - a brace might be a connector (which is to be dissolved into the box concept later?)

    def __init__(self, reverse=1, stretch=None, dist=None, fillattrs=[],
        totalheight=12*unit.x_pt,
        barthickness=0.5*unit.x_pt, innerstrokesthickness=0.25*unit.x_pt, outerstrokesthickness=0.25*unit.x_pt,
        innerstrokesrelheight=0.6, outerstrokesrelheight=0.7,
        innerstrokesangle=30, outerstrokesangle=25, slantstrokesangle=5,
        innerstrokessmoothness=2.0, outerstrokessmoothness=2.5,
        middlerelpos=0.5):
        self.fillattrs = fillattrs
        self.reverse = reverse
        self.stretch = stretch
        self.dist = dist
        self.totalheight            = totalheight
        self.barthickness           = barthickness
        self.innerstrokesthickness  = innerstrokesthickness
        self.outerstrokesthickness  = outerstrokesthickness
        self.innerstrokesrelheight  = innerstrokesrelheight
        self.outerstrokesrelheight  = outerstrokesrelheight
        self.innerstrokesangle      = innerstrokesangle
        self.outerstrokesangle      = outerstrokesangle
        self.slantstrokesangle      = slantstrokesangle
        self.innerstrokessmoothness = innerstrokessmoothness
        self.outerstrokessmoothness = outerstrokessmoothness
        self.middlerelpos           = middlerelpos

    def __call__(self, **kwargs):
        for name in ["reverse", "stretch", "dist", "fillattrs",
            "totalheight", "barthickness", "innerstrokesthickness", "outerstrokesthickness",
            "innerstrokesrelheight", "outerstrokesrelheight", "innerstrokesangle", "outerstrokesangle", "slantstrokesangle",
            "innerstrokessmoothness", "outerstrokessmoothness", "middlerelpos"]:
            if name not in kwargs:
                kwargs[name] = self.__dict__[name]
        return brace(**kwargs)

    def _halfbracepath_pt(self, length_pt, height_pt, ilength_pt, olength_pt, # <<<
    ithick_pt, othick_pt, bthick_pt, cos_iangle, sin_iangle, cos_oangle,
    sin_oangle, cos_slangle, sin_slangle):

        ismooth = self.innerstrokessmoothness
        osmooth = self.outerstrokessmoothness

        # these two parameters are not important enough to be seen outside
        inner_cap_param = 1.5
        outer_cap_param = 2.5
        outerextracurved = 0.6 # in (0, 1]
        # 1.0 will lead to F=G, the outer strokes will not be curved at their ends.
        # The smaller, the more curvature

        # build an orientation path (three straight lines)
        #
        #      \q1
        #    /  \
        #   /    \
        # _/      \______________________________________q5
        #         q2         q3              q4           \
        #                                                  \
        #                                                   \
        #                                                    \q6
        #
        # get the points for that:
        q1 = (0, height_pt - inner_cap_param * ithick_pt + 0.5*ithick_pt/sin_iangle)
        q2 = (q1[0] + ilength_pt * sin_iangle,
              q1[1] - ilength_pt * cos_iangle)
        q6 = (length_pt, 0)
        q5 = (q6[0] - olength_pt * sin_oangle,
              q6[1] + olength_pt * cos_oangle)
        bardir = (q5[0] - q2[0], q5[1] - q2[1])
        bardirnorm = math.hypot(*bardir)
        bardir = (bardir[0]/bardirnorm, bardir[1]/bardirnorm)
        ismoothlength_pt = ilength_pt * ismooth
        osmoothlength_pt = olength_pt * osmooth
        if bardirnorm < ismoothlength_pt + osmoothlength_pt:
            ismoothlength_pt = bardirnorm * ismoothlength_pt / (ismoothlength_pt + osmoothlength_pt)
            osmoothlength_pt = bardirnorm * osmoothlength_pt / (ismoothlength_pt + osmoothlength_pt)
        q3 = (q2[0] + ismoothlength_pt * bardir[0],
              q2[1] + ismoothlength_pt * bardir[1])
        q4 = (q5[0] - osmoothlength_pt * bardir[0],
              q5[1] - osmoothlength_pt * bardir[1])

        #
        #    P _O
        #   / | \A2
        #  / A1\ \
        #   /   \ B2C2________D2___________E2_______F2___G2
        #        \______________________________________  \
        #       B1,C1         D1           E1      F1  G1  \
        #                                                \  \
        #                                                 \  \H2
        #                                                H1\_/I2
        #                                                  I1
        #
        # the halfbraces meet in P and A1:
        P = (0, height_pt)
        A1 = (0, height_pt - inner_cap_param * ithick_pt)
        # A2 is A1, shifted by the inner thickness
        A2 = (A1[0] + ithick_pt * cos_iangle,
              A1[1] + ithick_pt * sin_iangle)
        s, t = deformer.intersection(P, A2, (cos_slangle, sin_slangle), (sin_iangle, -cos_iangle))
        O = (P[0] + s * cos_slangle,
             P[1] + s * sin_slangle)

        # from D1 to E1 is the straight part of the brace
        # also back from E2 to D1
        D1 = (q3[0] + bthick_pt * bardir[1],
              q3[1] - bthick_pt * bardir[0])
        D2 = (q3[0] - bthick_pt * bardir[1],
              q3[1] + bthick_pt * bardir[0])
        E1 = (q4[0] + bthick_pt * bardir[1],
              q4[1] - bthick_pt * bardir[0])
        E2 = (q4[0] - bthick_pt * bardir[1],
              q4[1] + bthick_pt * bardir[0])
        # I1, I2 are the control points at the outer stroke
        I1 = (q6[0] - 0.5 * othick_pt * cos_oangle,
              q6[1] - 0.5 * othick_pt * sin_oangle)
        I2 = (q6[0] + 0.5 * othick_pt * cos_oangle,
              q6[1] + 0.5 * othick_pt * sin_oangle)
        # get the control points for the curved parts of the brace
        s, t = deformer.intersection(A1, D1, (sin_iangle, -cos_iangle), bardir)
        B1 = (D1[0] + t * bardir[0],
              D1[1] + t * bardir[1])
        s, t = deformer.intersection(A2, D2, (sin_iangle, -cos_iangle), bardir)
        B2 = (D2[0] + t * bardir[0],
              D2[1] + t * bardir[1])
        s, t = deformer.intersection(E1, I1, bardir, (-sin_oangle, cos_oangle))
        G1 = (E1[0] + s * bardir[0],
              E1[1] + s * bardir[1])
        s, t = deformer.intersection(E2, I2, bardir, (-sin_oangle, cos_oangle))
        G2 = (E2[0] + s * bardir[0],
              E2[1] + s * bardir[1])
        # at the inner strokes: use curvature zero at both ends
        C1 = B1
        C2 = B2
        # at the outer strokes: use curvature zero only at the connection to
        # the straight part
        F1 = (outerextracurved * G1[0] + (1 - outerextracurved) * E1[0],
              outerextracurved * G1[1] + (1 - outerextracurved) * E1[1])
        F2 = (outerextracurved * G2[0] + (1 - outerextracurved) * E2[0],
              outerextracurved * G2[1] + (1 - outerextracurved) * E2[1])
        # the tip of the outer stroke, endpoints of the bezier curve
        H1 = (I1[0] - outer_cap_param * othick_pt * sin_oangle,
              I1[1] + outer_cap_param * othick_pt * cos_oangle)
        H2 = (I2[0] - outer_cap_param * othick_pt * sin_oangle,
              I2[1] + outer_cap_param * othick_pt * cos_oangle)

        #for qq in [A1,B1,C1,D1,E1,F1,G1,H1,I1,
        #           A2,B2,C2,D2,E2,F2,G2,H2,I2,
        #           O,P
        #           ]:
        #    cc.fill(path.circle(qq[0], qq[1], 0.5), [color.rgb.green])

        # now build the right halfbrace
        bracepath = path.path(path.moveto_pt(*A1))
        bracepath.append(path.curveto_pt(B1[0], B1[1], C1[0], C1[1], D1[0], D1[1]))
        bracepath.append(path.lineto_pt(E1[0], E1[1]))
        bracepath.append(path.curveto_pt(F1[0], F1[1], G1[0], G1[1], H1[0], H1[1]))
        # the tip of the right halfbrace
        bracepath.append(path.curveto_pt(I1[0], I1[1], I2[0], I2[1], H2[0], H2[1]))
        # the rest of the right halfbrace
        bracepath.append(path.curveto_pt(G2[0], G2[1], F2[0], F2[1], E2[0], E2[1]))
        bracepath.append(path.lineto_pt(D2[0], D2[1]))
        bracepath.append(path.curveto_pt(C2[0], C2[1], B2[0], B2[1], A2[0], A2[1]))
        # the tip in the middle of the brace
        bracepath.append(path.curveto_pt(O[0], O[1], O[0], O[1], P[0], P[1]))

        return bracepath
    # >>>

    def _bracepath(self, x0_pt, y0_pt, x1_pt, y1_pt): # <<<
        height_pt = unit.topt(self.totalheight)
        totallength_pt = math.hypot(x1_pt - x0_pt, y1_pt - y0_pt)
        leftlength_pt = self.middlerelpos * totallength_pt
        rightlength_pt = totallength_pt - leftlength_pt
        ithick_pt = unit.topt(self.innerstrokesthickness)
        othick_pt = unit.topt(self.outerstrokesthickness)
        bthick_pt = unit.topt(self.barthickness)

        # create the left halfbrace with positive slanting
        # because we will mirror this part
        cos_iangle = math.cos(math.radians(0.5*self.innerstrokesangle - self.slantstrokesangle))
        sin_iangle = math.sin(math.radians(0.5*self.innerstrokesangle - self.slantstrokesangle))
        cos_oangle = math.cos(math.radians(self.outerstrokesangle - self.slantstrokesangle))
        sin_oangle = math.sin(math.radians(self.outerstrokesangle - self.slantstrokesangle))
        cos_slangle = math.cos(math.radians(-self.slantstrokesangle))
        sin_slangle = math.sin(math.radians(-self.slantstrokesangle))
        ilength_pt = self.innerstrokesrelheight * height_pt / cos_iangle
        olength_pt = self.outerstrokesrelheight * height_pt / cos_oangle

        bracepath = self._halfbracepath_pt(leftlength_pt, height_pt,
          ilength_pt, olength_pt, ithick_pt, othick_pt, bthick_pt, cos_iangle,
          sin_iangle, cos_oangle, sin_oangle, cos_slangle,
          sin_slangle).reversed().transformed(trafo.mirror(90))

        # create the right halfbrace with negative slanting
        cos_iangle = math.cos(math.radians(0.5*self.innerstrokesangle + self.slantstrokesangle))
        sin_iangle = math.sin(math.radians(0.5*self.innerstrokesangle + self.slantstrokesangle))
        cos_oangle = math.cos(math.radians(self.outerstrokesangle + self.slantstrokesangle))
        sin_oangle = math.sin(math.radians(self.outerstrokesangle + self.slantstrokesangle))
        cos_slangle = math.cos(math.radians(-self.slantstrokesangle))
        sin_slangle = math.sin(math.radians(-self.slantstrokesangle))
        ilength_pt = self.innerstrokesrelheight * height_pt / cos_iangle
        olength_pt = self.outerstrokesrelheight * height_pt / cos_oangle

        bracepath = bracepath << self._halfbracepath_pt(rightlength_pt, height_pt,
        ilength_pt, olength_pt, ithick_pt, othick_pt, bthick_pt, cos_iangle,
        sin_iangle, cos_oangle, sin_oangle, cos_slangle,
        sin_slangle)

        return bracepath.transformed(
          # two trafos for matching the given endpoints
          trafo.translate_pt(x0_pt, y0_pt) *
          trafo.rotate_pt(math.degrees(math.atan2(y1_pt-y0_pt, x1_pt-x0_pt))) *
          # one trafo to move the brace's left outer stroke to zero
          trafo.translate_pt(leftlength_pt, 0))
    # >>>

    def decorate(self, dp, texrunner):
        dp.ensurenormpath()
        x0_pt, y0_pt = dp.path.atbegin_pt()
        x1_pt, y1_pt = dp.path.atend_pt()
        if self.reverse:
            x0_pt, y0_pt, x1_pt, y1_pt = x1_pt, y1_pt, x0_pt, y0_pt
        if self.stretch is not None:
            xm, ym = 0.5*(x0_pt+x1_pt), 0.5*(y0_pt+y1_pt)
            x0_pt, y0_pt = xm + self.stretch*(x0_pt-xm), ym + self.stretch*(y0_pt-ym)
            x1_pt, y1_pt = xm + self.stretch*(x1_pt-xm), ym + self.stretch*(y1_pt-ym)
        if self.dist is not None:
            d = unit.topt(self.dist)
            dx, dy = dp.path.rotation_pt(dp.path.begin()).apply_pt(0, 1)
            x0_pt += d*dx; y0_pt += d*dy
            dx, dy = dp.path.rotation_pt(dp.path.end()).apply_pt(0, 1)
            x1_pt += d*dx; y1_pt += d*dy
        dp.ornaments.fill(self._bracepath(x0_pt, y0_pt, x1_pt, y1_pt), self.fillattrs)

brace.clear = attr.clearclass(brace)

leftbrace  = brace(reverse=0, middlerelpos=0.55, innerstrokesrelheight=0.6, outerstrokesrelheight=0.7, slantstrokesangle=-10)
rightbrace = brace(reverse=1, middlerelpos=0.45, innerstrokesrelheight=0.6, outerstrokesrelheight=0.7, slantstrokesangle=10)
belowbrace = brace(reverse=1, middlerelpos=0.55, innerstrokesrelheight=0.7, outerstrokesrelheight=0.9, slantstrokesangle=-10)
abovebrace = brace(reverse=0, middlerelpos=0.45, innerstrokesrelheight=0.7, outerstrokesrelheight=0.9, slantstrokesangle=-10)
straightbrace = brace(innerstrokesrelheight=0.5, outerstrokesrelheight=0.5,
        innerstrokesangle=30, outerstrokesangle=30, slantstrokesangle=0,
        innerstrokessmoothness=1.0, outerstrokessmoothness=1.0)

