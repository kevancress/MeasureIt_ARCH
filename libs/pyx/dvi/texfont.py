# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2007-2011 Jörg Lehmann <joerg@pyx-project.org>
# Copyright (C) 2007-2011 André Wobst <wobsta@pyx-project.org>
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


from pyx import bbox, font, config
from . import tfmfile, vffile

class TeXFontError(Exception): pass

class TeXfont:

    def __init__(self, name, c, q, d, tfmconv, pyxconv, debug=0):
        self.name = name
        self.q = q                  # desired size of font (fix_word) in TeX points
        self.d = d                  # design size of font (fix_word) in TeX points
        self.tfmconv = tfmconv      # conversion factor from tfm units to dvi units
        self.pyxconv = pyxconv      # conversion factor from dvi units to PostScript points
        with config.open(self.name, [config.format.tfm]) as file:
            self.TFMfile = tfmfile.TFMfile(file, debug)

        # We only check for equality of font checksums if none of them
        # is zero. The case c == 0 happend in some VF files and
        # according to the VFtoVP documentation, paragraph 40, a check
        # is only performed if TFMfile.checksum > 0. Anyhow, being
        # more generous here seems to be reasonable
        if self.TFMfile.checksum != c and self.TFMfile.checksum > 0 and c > 0:
            raise TeXFontError("check sums do not agree: %d vs. %d" %
                               (self.TFMfile.checksum, c))

        # Check whether the given design size matches the one defined in the tfm file
        if abs(self.TFMfile.designsize - d) > 4: # XXX: why the deviation?
            raise TeXFontError("design sizes do not agree: %d vs. %d" % (self.TFMfile.designsize, d))
        #if q < 0 or q > 134217728:
        #    raise TeXFontError("font '%s' not loaded: bad scale" % self.name)
        if d < 0 or d > 134217728:
            raise TeXFontError("font '%s' not loaded: bad design size" % self.name)

    def __str__(self):
        return "font %s designed at %g TeX pts used at %g TeX pts" % (self.name, 
                                                                      16.0*self.d/16777216,
                                                                      16.0*self.q/16777216)

    def getsize_pt(self):
        """ return size of font in (PS) points """
        # The factor 16L/16777216L=2**(-20) converts a fix_word (here self.q)
        # to the corresponding float. Furthermore, we have to convert from TeX
        # points to points, hence the factor 72/72.27.
        return 72/72.27 * 16*self.q/16777216

    def _convert_tfm_to_dvi(self, length):
        # doing the integer math with long integers will lead to different roundings
        # return 16*length*int(round(self.q*self.tfmconv))/16777216

        # Knuth instead suggests the following algorithm based on 4 byte integer logic only
        # z = int(round(self.q*self.tfmconv))
        # b0, b1, b2, b3 = [ord(c) for c in struct.pack(">L", length)]
        # assert b0 == 0 or b0 == 255
        # shift = 4
        # while z >= 8388608:
        #     z >>= 1
        #     shift -= 1
        # assert shift >= 0
        # result = ( ( ( ( ( b3 * z ) >> 8 ) + ( b2 * z ) ) >> 8 ) + ( b1 * z ) ) >> shift
        # if b0 == 255:
        #     result = result - (z << (8-shift))

        # however, we can simplify this using a single long integer multiplication,
        # but take into account the transformation of z
        z = int(round(self.q*self.tfmconv))
        assert -16777216 <= length < 16777216 # -(1 << 24) <= length < (1 << 24)
        assert z < 134217728 # 1 << 27
        shift = 20 # 1 << 20
        while z >= 8388608: # 1 << 23
            z >>= 1
            shift -= 1
        # length*z is a long integer, but the result will be a regular integer
        return int(length*int(z) >> shift)

    def _convert_tfm_to_pt(self, length):
        return (16*int(round(length*float(self.q)*self.tfmconv))/16777216) * self.pyxconv

    # routines returning lengths as integers in dvi units

    def getwidth_dvi(self, charcode):
        return self._convert_tfm_to_dvi(self.TFMfile.width[self.TFMfile.char_info[charcode].width_index])

    def getheight_dvi(self, charcode):
        return self._convert_tfm_to_dvi(self.TFMfile.height[self.TFMfile.char_info[charcode].height_index])

    def getdepth_dvi(self, charcode):
        return self._convert_tfm_to_dvi(self.TFMfile.depth[self.TFMfile.char_info[charcode].depth_index])

    def getitalic_dvi(self, charcode):
        return self._convert_tfm_to_dvi(self.TFMfile.italic[self.TFMfile.char_info[charcode].italic_index])

    # routines returning lengths as floats in PostScript points

    def getwidth_pt(self, charcode):
        return self._convert_tfm_to_pt(self.TFMfile.width[self.TFMfile.char_info[charcode].width_index])

    def getheight_pt(self, charcode):
        return self._convert_tfm_to_pt(self.TFMfile.height[self.TFMfile.char_info[charcode].height_index])

    def getdepth_pt(self, charcode):
        return self._convert_tfm_to_pt(self.TFMfile.depth[self.TFMfile.char_info[charcode].depth_index])

    def getitalic_pt(self, charcode):
        return self._convert_tfm_to_pt(self.TFMfile.italic[self.TFMfile.char_info[charcode].italic_index])

    def text_pt(self, x_pt, y_pt, charcodes, fontmap=None):
        return TeXtext_pt(self, x_pt, y_pt, charcodes, self.getsize_pt(), fontmap=fontmap)

    def getMAPline(self, fontmap):
        if self.name not in fontmap:
            raise RuntimeError("missing font information for '%s'; check fontmapping file(s)" % self.name)
        return fontmap[self.name]


class virtualfont(TeXfont):

    def __init__(self, name, file, c, q, d, tfmconv, pyxconv, debug=0):
        TeXfont.__init__(self, name, c, q, d, tfmconv, pyxconv, debug)
        self.vffile = vffile.vffile(file, 1.0*q/d, tfmconv, pyxconv, debug > 1)

    def getfonts(self):
        """ return fonts used in virtual font itself """
        return self.vffile.getfonts()

    def getchar(self, cc):
        """ return dvi chunk corresponding to char code cc """
        return self.vffile.getchar(cc)

    def text_pt(self, *args, **kwargs):
        raise RuntimeError("you don't know what you're doing")


class TeXtext_pt(font.text_pt):

    def __init__(self, font, x_pt, y_pt, charcodes, size_pt, fontmap=None):
        self.font = font
        self.x_pt = x_pt
        self.y_pt = y_pt
        self.charcodes = charcodes
        self.size_pt = size_pt
        self.fontmap = fontmap

        self.width_pt = sum([self.font.getwidth_pt(charcode) for charcode in charcodes])
        self.height_pt = max([self.font.getheight_pt(charcode) for charcode in charcodes])
        self.depth_pt = max([self.font.getdepth_pt(charcode) for charcode in charcodes])

        self._bbox = bbox.bbox_pt(self.x_pt, self.y_pt-self.depth_pt, self.x_pt+self.width_pt, self.y_pt+self.height_pt)

    def bbox(self):
        return self._bbox

    def _text(self, writer):
        if self.fontmap is not None:
            mapline = self.font.getMAPline(self.fontmap)
        else:
            mapline = self.font.getMAPline(writer.getfontmap())
        font = mapline.getfont()
        return font.text_pt(self.x_pt, self.y_pt, self.charcodes, self.size_pt, decoding=mapline.getencoding(), slant=mapline.slant, ignorebbox=True)

    def textpath(self):
        from pyx import pswriter
        return self._text(pswriter._PSwriter()).textpath()

    def processPS(self, file, writer, context, registry, bbox):
        bbox += self.bbox()
        self._text(writer).processPS(file, writer, context, registry, bbox)

    def processPDF(self, file, writer, context, registry, bbox):
        bbox += self.bbox()
        self._text(writer).processPDF(file, writer, context, registry, bbox)

    def processSVG(self, xml, writer, context, registry, bbox):
        bbox += self.bbox()
        self._text(writer).processSVG(xml, writer, context, registry, bbox)

