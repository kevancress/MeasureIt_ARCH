# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2002-2007 Jörg Lehmann <joerg@pyx-project.org>
# Copyright (C) 2002-2007 André Wobst <wobsta@pyx-project.org>
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

from . import attr

class canvasitem:

    """Base class for everything which can be inserted into a canvas"""

    def bbox(self):
        """return bounding box of canvasitem"""
        raise NotImplementedError()

    def requiretextregion(self):
        """indicates whether a canvasitem needs to be part of a PDF text
        region"""
        return False

    def processPS(self, file, writer, context, registry, bbox):
        """process canvasitem by writing the corresponding PS code to file and
        by updating context, registry as well as bbox

        - the PS code corresponding to the canvasitem has to be written in the
          stream file, which provides a write(string) method
        - writer is the PSwriter used for the output
        - context is an instance of pswriter.context which is used for keeping
          track of the graphics state (current linewidth, colorspace and font,
          etc.)
        - registry is used for tracking resources needed by the canvasitem
        - bbox has to be updated to include the bounding box of the canvasitem
        """
        raise NotImplementedError()

    def processPDF(self, file, writer, context, registry, bbox):
        """process canvasitem by writing the corresponding PDF code to file and
        by updating context, registry as well as bbox

        - the PDF code corresponding to the canvasitem has to be written in the
          stream file, which provides a write(string) method
        - writer is the PDFwriter used for the output, which contains properties
          like whether streamcompression is used
        - context is an instance of pdfwriter.context which is used for keeping
          track of the graphics state, in particular for the emulation of PS
          behaviour regarding fill and stroke styles, for keeping track of the
          currently selected font as well as of text regions.
        - registry is used for tracking resources needed by the canvasitem
        - bbox has to be updated to include the bounding box of the canvasitem
        """
        raise NotImplementedError()


class deformer(attr.attr):

    def deform(self, basepath):
        raise NotImplementedError()

