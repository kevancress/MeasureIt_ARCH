# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2005-2011 Jörg Lehmann <joerg@pyx-project.org>
# Copyright (C) 2005-2011 André Wobst <wobsta@pyx-project.org>
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

import io, copy, time, math
from . import bbox, config, style, version, unit, trafo, writer


class PSregistry:

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

    def output(self, file, writer):
        """ write all PostScript code of the prolog resources """
        for resource in self.resourceslist:
            resource.output(file, writer, self)

#
# Abstract base class
#

class PSresource:

    """ a PostScript resource """

    def __init__(self, type, id):
        # Every PSresource has to have a type and a unique id.
        # Resources with the same type and id will be merged
        # when they are registered in the PSregistry
        self.type = type
        self.id = id

    def merge(self, other):
        """ merge self with other, which has to be a resource of the same type and with
        the same id"""
        pass

    def output(self, file, writer, registry):
        raise NotImplementedError("output not implemented for %s" % repr(self))

class PSdefinition(PSresource):

    """ PostScript function definition included in the prolog """

    def __init__(self, id, body):
        self.type = "definition"
        self.id = id
        self.body = body

    def output(self, file, writer, registry):
        file.write("%%%%BeginResource: %s\n" % self.id)
        file.write_bytes(self.body)
        file.write(" /%s exch def\n" % self.id)
        file.write("%%EndResource\n")

#
# Writers
#

class _PSwriter:

    def __init__(self, title=None, 
                 stripfonts=True, textaspath=False, meshasbitmap=False, meshasbitmapresolution=300,
                 strip_fonts=None, text_as_path=None, mesh_as_bitmap=None, mesh_as_bitmap_resolution=None):
        self._fontmap = None
        self.title = title
        if strip_fonts is not None:
            logger.warning("(E)PSwriter: strip_fonts deprecated, use stripfonts instead")
            stripfonts = strip_fonts
        self.stripfonts = stripfonts
        if text_as_path is not None:
            logger.warning("(E)PSwriter: text_as_path deprecated, use textaspath instead")
            textaspath = text_as_path
        self.textaspath = textaspath
        if mesh_as_bitmap is not None:
            logger.warning("(E)PSwriter: mesh_as_bitmap deprecated, use meshasbitmap instead")
            meshasbitmap = mash_as_bitmap
        self.meshasbitmap = meshasbitmap
        if mesh_as_bitmap_resolution is not None:
            logger.warning("PSwriter: mesh_as_bitmap_resolution deprecated, use meshasbitmapresolution instead")
            meshasbitmapresolution = mash_as_bitmap_resolution

        # dictionary mapping font names to dictionaries mapping encoding names to encodings
        # encodings themselves are mappings from glyphnames to codepoints
        self.encodings = {}

    def writeinfo(self, file):
        file.write("%%%%Creator: PyX %s\n" % version.version)
        if self.title is not None:
            file.write("%%%%Title: %s\n" % self.title)
        file.write("%%%%CreationDate: %s\n" %
                   time.asctime(time.localtime(time.time())))

    def getfontmap(self):
        if self._fontmap is None:
            # late import due to cyclic dependency
            from pyx.dvi import mapfile
            fontmapfiles = config.getlist("text", "psfontmaps", ["psfonts.map"])
            self._fontmap = mapfile.readfontmap(fontmapfiles)
        return self._fontmap


class EPSwriter(_PSwriter):

    def __init__(self, document, file, **kwargs):
        _PSwriter.__init__(self, **kwargs)
        file = writer.writer(file)

        if len(document.pages) != 1:
            raise ValueError("EPS file can be constructed out of a single page document only")
        page = document.pages[0]
        canvas = page.canvas

        pagefile = writer.writer(io.BytesIO())
        registry = PSregistry()
        acontext = context()
        pagebbox = bbox.empty()

        page.processPS(pagefile, self, acontext, registry, pagebbox)

        file.write("%!PS-Adobe-3.0 EPSF-3.0\n")
        if pagebbox:
            file.write("%%%%BoundingBox: %d %d %d %d\n" % pagebbox.lowrestuple_pt())
            file.write("%%%%HiResBoundingBox: %g %g %g %g\n" % pagebbox.highrestuple_pt())
        self.writeinfo(file)
        file.write("%%EndComments\n")

        file.write("%%BeginProlog\n")
        registry.output(file, self)
        file.write("%%EndProlog\n")

        file.write_bytes(pagefile.file.getvalue())

        file.write("showpage\n")
        file.write("%%Trailer\n")
        file.write("%%EOF\n")


class PSwriter(_PSwriter):

    def __init__(self, document, file, writebbox=False, **kwargs):
        _PSwriter.__init__(self, **kwargs)
        file = writer.writer(file)

        # We first have to process the content of the pages, writing them into the stream pagesfile
        # Doing so, we fill the registry and also calculate the page bounding boxes, which are
        # stored in page._bbox for every page
        pagesfile = writer.writer(io.BytesIO())
        registry = PSregistry()

        # calculated bounding boxes of the whole document
        documentbbox = bbox.empty()

        for nr, page in enumerate(document.pages):
            # process contents of page
            pagefile = writer.writer(io.BytesIO())
            acontext = context()
            pagebbox = bbox.empty()
            page.processPS(pagefile, self, acontext, registry, pagebbox)

            documentbbox += pagebbox

            pagesfile.write("%%%%Page: %s %d\n" % (page.pagename is None and str(nr+1) or page.pagename, nr+1))
            if page.paperformat:
                pagesfile.write("%%%%PageMedia: %s\n" % page.paperformat.name)
            pagesfile.write("%%%%PageOrientation: %s\n" % (page.rotated and "Landscape" or "Portrait"))
            if pagebbox and writebbox:
                pagesfile.write("%%%%PageBoundingBox: %d %d %d %d\n" % pagebbox.lowrestuple_pt())

            # page setup section
            pagesfile.write("%%BeginPageSetup\n")
            pagesfile.write("/pgsave save def\n")

            pagesfile.write("%%EndPageSetup\n")
            pagesfile.write_bytes(pagefile.file.getvalue())
            pagesfile.write("pgsave restore\n")
            pagesfile.write("showpage\n")
            pagesfile.write("%%PageTrailer\n")

        file.write("%!PS-Adobe-3.0\n")
        if documentbbox and writebbox:
            file.write("%%%%BoundingBox: %d %d %d %d\n" % documentbbox.lowrestuple_pt())
            file.write("%%%%HiResBoundingBox: %g %g %g %g\n" % documentbbox.highrestuple_pt())
        self.writeinfo(file)

        # required paper formats
        paperformats = {}
        for page in document.pages:
            if page.paperformat:
                paperformats[page.paperformat] = page.paperformat

        first = 1
        for paperformat in list(paperformats.values()):
            if first:
                file.write("%%DocumentMedia: ")
                first = 0
            else:
                file.write("%%+ ")
            file.write("%s %d %d 75 white ()\n" % (paperformat.name,
                                                   unit.topt(paperformat.width),
                                                   unit.topt(paperformat.height)))

        # file.write(%%DocumentNeededResources: ") # register not downloaded fonts here

        file.write("%%%%Pages: %d\n" % len(document.pages))
        file.write("%%PageOrder: Ascend\n")
        file.write("%%EndComments\n")

        # document defaults section
        #file.write("%%BeginDefaults\n")
        #file.write("%%EndDefaults\n")

        # document prolog section
        file.write("%%BeginProlog\n")
        registry.output(file, self)
        file.write("%%EndProlog\n")

        # document setup section
        #file.write("%%BeginSetup\n")
        #file.write("%%EndSetup\n")

        file.write_bytes(pagesfile.file.getvalue())

        file.write("%%Trailer\n")
        file.write("%%EOF\n")


class context:

    def __init__(self):
        self.linewidth_pt = None
        self.colorspace = None
        self.selectedfont = None
        self.fillrule = 0

    def __call__(self, **kwargs):
        newcontext = copy.copy(self)
        for key, value in list(kwargs.items()):
            setattr(newcontext, key, value)
        return newcontext
