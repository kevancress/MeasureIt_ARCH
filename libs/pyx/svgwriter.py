# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2015 André Wobst <wobsta@pyx-project.org>
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

import io, copy, time, xml.sax.saxutils
from . import bbox, config, style, version, unit, trafo

svg_uri = "http://www.w3.org/2000/svg"
xlink_uri = "http://www.w3.org/1999/xlink"

class SVGregistry:

    def __init__(self):
        # in order to keep a consistent order of the registered resources we
        # not only store them in a hash but also keep an ordered list (up to a
        # possible merging of resources, in which case the first instance is
        # kept)
        self.resourceshash = {}
        self.resourceslist = []

    def add(self, resource):
        rkey = (resource.type, resource.id)
        if rkey in self.resourceshash:
           self.resourceshash[rkey].merge(resource)
        else:
           self.resourceshash[rkey] = resource
           self.resourceslist.append(resource)

    def mergeregistry(self, registry):
        for resource in registry.resources:
            self.add(resource)

    def output(self, xml, writer):
        if self.resourceslist:
            xml.startSVGElement("defs", {})
            for resource in self.resourceslist:
                resource.output(xml, writer, self)
            xml.endSVGElement("defs")

#
# Abstract base class
#

class SVGresource:

    def __init__(self, type, id):
        # Every SVGresource has to have a type and a unique id.
        # Resources with the same type and id will be merged
        # when they are registered in the SVGregistry
        self.type = type
        self.id = id

    def merge(self, other):
        """ merge self with other, which has to be a resource of the same type and with
        the same id"""
        pass

    def output(self, xml, writer, registry):
        raise NotImplementedError("output not implemented for %s" % repr(self))


#
# XML generator with shortcut namespace support
#

class SVGGenerator(xml.sax.saxutils.XMLGenerator):

    def __init__(self, svg, xlink=True):
        super().__init__(svg, "utf-8", short_empty_elements=True)
        self.svg = svg
        self.xlink_enabled = xlink
        self.passthrough = False

    def convertName(self, name):
        split = name.split(":")
        if len(split) == 1:
            uri = svg_uri
            name = split[0]
        else:
            short_uri, name = split
            assert short_uri == "xlink"
            if not self.xlink_enabled:
                raise ValueError("xlink namespace found but not enabled")
            self.xlink_used = True
            uri = xlink_uri
        return uri, name

    def convertAttrs(self, attrs):
        return {self.convertName(name): value for name, value in attrs.items()}

    def startDocument(self, *args, **kwargs):
        if not self.passthrough:
            raise NotImplemented("use startSVGDocument")

    def endDocument(self, *args, **kwargs):
        if not self.passthrough:
            raise NotImplemented("use endSVGDocument")

    def startElementNS(self, *args, **kwargs):
        if not self.passthrough:
            raise NotImplemented("use startSVGElement")
        super().startElementNS(*args, **kwargs)

    def endElementNS(self, *args, **kwargs):
        if not self.passthrough:
            raise NotImplemented("use endSVGElement")
        super().endElementNS(*args, **kwargs)

    def startSVGDocument(self):
        super().startDocument()
        super().startPrefixMapping(None, svg_uri)
        if self.xlink_enabled:
            super().startPrefixMapping("xlink", xlink_uri)
        self.indent = 0
        self.newline = True
        self.xlink_used = False

    def startSVGElement(self, name, attrs):
        if name != "tspan":
            if not self.newline:
                self.characters("\n")
            self.characters(" "*self.indent)
        super().startElementNS(self.convertName(name), None, self.convertAttrs(attrs))
        if name != "tspan":
            self.indent += 1
            self.last_was_end = False
            self.newline = False

    def newline_and_tell(self):
        self.characters("\n")
        self.newline = True
        return self.svg.tell()

    def endSVGElement(self, name):
        if name != "tspan":
            self.indent -= 1
            if self.last_was_end:
                if not self.newline:
                    self.characters("\n")
                self.characters(" "*self.indent)
        super().endElementNS(self.convertName(name), None)
        if name != "tspan":
            self.last_was_end = True
            self.newline = False

    def endSVGDocument(self):
        assert not self.indent
        self.characters("\n")
        super().endPrefixMapping(None)
        if self.xlink_enabled:
            super().endPrefixMapping("xlink")
        super().endDocument()


#
# Writer
#

class SVGwriter:

    def __init__(self, document, file, textaspath=True, meshasbitmapresolution=300, text_as_path=None, mesh_as_bitmap_resolution=None):
        self._fontmap = None
        if text_as_path is not None:
            logger.warning("SVGwriter: text_as_path deprecated, use textaspath instead")
            textaspath = text_as_path
        self.textaspath = textaspath
        if mesh_as_bitmap_resolution is not None:
            logger.warning("SVGwriter: mesh_as_bitmap_resolution deprecated, use meshasbitmapresolution instead")
            meshasbitmapresolution = mash_as_bitmap_resolution
        self.meshasbitmapresolution = meshasbitmapresolution

        # dictionary mapping font names to dictionaries mapping encoding names to encodings
        # encodings themselves are mappings from glyphnames to codepoints
        self.encodings = {}

        if len(document.pages) != 1:
            raise ValueError("SVG file can be constructed out of a single page document only")
        page = document.pages[0]

        pagefile = io.BytesIO()
        pagesvg = SVGGenerator(pagefile)
        registry = SVGregistry()
        acontext = context()
        pagebbox = bbox.empty()

        pagesvg.startSVGDocument()
        pagesvg.startSVGElement("svg", {})
        pagexml_start = pagesvg.newline_and_tell()
        page.processSVG(pagesvg, self, acontext, registry, pagebbox)
        pagexml_end = pagesvg.newline_and_tell()
        pagesvg.endSVGElement("svg")
        pagesvg.endSVGDocument()

        x = SVGGenerator(file, xlink=pagesvg.xlink_used)
        x.startSVGDocument()
        attrs = {"fill": "none", "version": "1.1"}
        if pagebbox:
            # note that svg uses an inverse y coordinate; to compansate this
            # PyX writes negative y coordinates and the viewbox needs to be
            # adjusted accordingly (by that instead of a transforamtion
            # a text remains upright).
            llx, lly, urx, ury = pagebbox.highrestuple_pt()
            attrs["viewBox"] = "%g %g %g %g" % (llx, -ury, urx-llx, ury-lly)
            attrs["x"] = "%gpt" % llx
            attrs["y"] = "%gpt" % -ury
            attrs["width"] = "%gpt" % (urx-llx)
            attrs["height"] = "%gpt" % (ury-lly)
        style.linewidth.normal.processSVGattrs(attrs, self, acontext, registry)
        style.miterlimit.lessthan11deg.processSVGattrs(attrs, self, acontext, registry)
        x.startSVGElement("svg", attrs)
        registry.output(x, self)
        pagedata = pagefile.getvalue()
        x.newline_and_tell()
        file.write(pagedata[pagexml_start:pagexml_end])
        x.endSVGElement("svg")
        x.endSVGDocument()

    def getfontmap(self):
        if self._fontmap is None:
            # late import due to cyclic dependency
            from pyx.dvi import mapfile
            fontmapfiles = config.getlist("text", "psfontmaps", ["psfonts.map"])
            self._fontmap = mapfile.readfontmap(fontmapfiles)
        return self._fontmap



class context:

    def __init__(self):
        self.linewidth_pt = unit.topt(style.linewidth.normal.width)
        self.strokeattr = True
        self.fillattr = True
        self.fillcolor = "black"
        self.strokecolor = "black"
        self.fillopacity = 1
        self.strokeopacity = 1
        self.indent = 1

    def __call__(self, **kwargs):
        newcontext = copy.copy(self)
        newcontext.indent += 1
        for key, value in list(kwargs.items()):
            setattr(newcontext, key, value)
        return newcontext
