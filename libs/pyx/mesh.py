# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2006-2011 André Wobst <wobsta@pyx-project.org>
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


# Just a quick'n'dirty ascii art (I'll do a nice PyX plot later on):
#
#
#      node1 *
#            | \
#            |   \  neighbor2
#            |     \
#            |       \
#  neighbor3 |element * node3
#            |       /
#            |     /
#            |   /  neighbor1
#            | /
#      node2 *


import struct, binascii, zlib, os, tempfile
from . import bbox, baseclasses, color, pdfwriter, unit


class node_pt:

    def __init__(self, coords_pt, value):
        self.coords_pt = coords_pt
        self.value = value


class node(node_pt):

    def __init__(self, coords, value):
        node_pt.__init__(self, [unit.topt(coord) for coord in coords], value)


class element:

    def __init__(self, nodes, neighbors=None):
        self.nodes = nodes
        self.neighbors = neighbors


def coords24bit_pt(coords_pt, min_pt, max_pt):
    return struct.pack(">I", int((coords_pt-min_pt)*16777215.0/(max_pt-min_pt)))[1:]


class PDFGenericResource(pdfwriter.PDFobject):

    def __init__(self, type, name, content):
        pdfwriter.PDFobject.__init__(self, type, name)
        self.content = content

    def write(self, file, writer, registry):
        file.write_bytes(self.content)


class mesh(baseclasses.canvasitem):

    def __init__(self, elements, check=1):
        self.elements = elements
        if check:
            colorspacestring = ""
            for element in elements:
                if len(element.nodes) != 3:
                    raise ValueError("triangular mesh expected")
                try:
                    for node in element.nodes:
                        if not colorspacestring:
                            colorspacestring = node.value.colorspacestring()
                        elif node.value.colorspacestring() != colorspacestring:
                            raise ValueError("color space mismatch")
                except AttributeError:
                    raise ValueError("gray, rgb or cmyk color values expected")
                for node in element.nodes:
                    if len(node.coords_pt) != 2:
                        raise ValueError("two dimensional coordinates expected")

    def bbox(self):
        return bbox.bbox_pt(min([node.coords_pt[0] for element in self.elements for node in element.nodes]),
                            min([node.coords_pt[1] for element in self.elements for node in element.nodes]),
                            max([node.coords_pt[0] for element in self.elements for node in element.nodes]),
                            max([node.coords_pt[1] for element in self.elements for node in element.nodes]))

    def data(self, bbox):
        return b"".join([b"\000" + coords24bit_pt(node.coords_pt[0], bbox.llx_pt, bbox.urx_pt) +
                                   coords24bit_pt(node.coords_pt[1], bbox.lly_pt, bbox.ury_pt) +
                                   node.value.to8bitbytes()
                         for element in self.elements for node in element.nodes])

    def processPS(self, file, writer, context, registry, bbox):
        if writer.meshasbitmap:
            from pyx import bitmap, canvas
            from PIL import Image
            c = canvas.canvas()
            c.insert(self)
            i = Image.open(c.pipeGS("pngalpha", resolution=writer.meshasbitmapresolution))
            i.load()
            b = bitmap.bitmap_pt(self.bbox().llx_pt, self.bbox().lly_pt, i)
            # we slightly shift the bitmap to re-center it, as the bitmap might contain some additional border
            # unfortunately we need to construct another bitmap instance for that ...
            b = bitmap.bitmap_pt(self.bbox().llx_pt + 0.5*(self.bbox().width_pt()-b.bbox().width_pt()),
                                 self.bbox().lly_pt + 0.5*(self.bbox().height_pt()-b.bbox().height_pt()), i)
            b.processPS(file, writer, context, registry, bbox)
        else:
            thisbbox = self.bbox()
            bbox += thisbbox
            file.write("""<< /ShadingType 4
/ColorSpace %s
/BitsPerCoordinate 24
/BitsPerComponent 8
/BitsPerFlag 8
/Decode [%f %f %f %f %s]
/DataSource currentfile /ASCIIHexDecode filter /FlateDecode filter
>> shfill\n""" % (self.elements[0].nodes[0].value.colorspacestring(),
                  thisbbox.llx_pt, thisbbox.urx_pt, thisbbox.lly_pt, thisbbox.ury_pt,
                  " ".join(["0 1" for value in self.elements[0].nodes[0].value.to8bitbytes()])))
            file.write_bytes(binascii.b2a_hex(zlib.compress(self.data(thisbbox))))
            file.write(">\n")

    def processPDF(self, file, writer, context, registry, bbox):
        if writer.meshasbitmap:
            from pyx import bitmap, canvas
            from PIL import Image
            c = canvas.canvas()
            c.insert(self)
            i = Image.open(c.pipeGS("pngalpha", resolution=writer.meshasbitmapresolution))
            i.load()
            b = bitmap.bitmap_pt(self.bbox().llx_pt, self.bbox().lly_pt, i)
            # we slightly shift the bitmap to re-center it, as the bitmap might contain some additional border
            # unfortunately we need to construct another bitmap instance for that ...
            b = bitmap.bitmap_pt(self.bbox().llx_pt + 0.5*(self.bbox().width_pt()-b.bbox().width_pt()),
                                 self.bbox().lly_pt + 0.5*(self.bbox().height_pt()-b.bbox().height_pt()), i)
            b.processPDF(file, writer, context, registry, bbox)
        else:
            thisbbox = self.bbox()
            bbox += thisbbox
            d = self.data(thisbbox)
            if writer.compress:
                filter = "/Filter /FlateDecode\n"
                d = zlib.compress(d)
            else:
                filter = ""
            name = "shading-%s" % id(self)
            shading = PDFGenericResource("shading", name, ("""<<
/ShadingType 4
/ColorSpace %s
/BitsPerCoordinate 24
/BitsPerComponent 8
/BitsPerFlag 8
/Decode [%f %f %f %f %s]
/Length %i
%s>>
stream
""" %            (self.elements[0].nodes[0].value.colorspacestring(),
                  thisbbox.llx_pt, thisbbox.urx_pt, thisbbox.lly_pt, thisbbox.ury_pt,
                  " ".join(["0 1" for value in self.elements[0].nodes[0].value.to8bitbytes()]),
                  len(d), filter)).encode('ascii') + d + b"\nendstream\n")
            registry.add(shading)
            registry.addresource("Shading", name, shading)
            file.write("/%s sh\n" % name)

    def processSVG(self, xml, writer, context, registry, bbox):
        from pyx import bitmap, canvas
        from PIL import Image
        c = canvas.canvas()
        c.insert(self)
        i = Image.open(c.pipeGS("pngalpha", resolution=writer.meshasbitmapresolution))
        i.load()
        b = bitmap.bitmap_pt(self.bbox().llx_pt, self.bbox().lly_pt, i)
        # we slightly shift the bitmap to re-center it, as the bitmap might contain some additional border
        # unfortunately we need to construct another bitmap instance for that ...
        b = bitmap.bitmap_pt(self.bbox().llx_pt + 0.5*(self.bbox().width_pt()-b.bbox().width_pt()),
                             self.bbox().lly_pt + 0.5*(self.bbox().height_pt()-b.bbox().height_pt()), i)
        b.processSVG(xml, writer, context, registry, bbox)
