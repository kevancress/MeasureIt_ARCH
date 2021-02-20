# -*- encoding: utf-8 -*-
#
#
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

import struct, re
from . import metric


ansiglyphs = {"space": 32,
              "exclam": 33,
              "quotedbl": 34,
              "numbersign": 35,
              "dollar": 36,
              "percent": 37,
              "ampersand": 38,
              "quotesingle": 39,
              "parenleft": 40,
              "parenright": 41,
              "asterisk": 42,
              "plus": 43,
              "comma": 44,
              "hyphen": 45,
              "period": 46,
              "slash": 47,
              "zero": 48,
              "one": 49,
              "two": 50,
              "three": 51,
              "four": 52,
              "five": 53,
              "six": 54,
              "seven": 55,
              "eight": 56,
              "nine": 57,
              "colon": 58,
              "semicolon": 59,
              "less": 60,
              "equal": 61,
              "greater": 62,
              "question": 63,
              "at": 64,
              "A": 65,
              "B": 66,
              "C": 67,
              "D": 68,
              "E": 69,
              "F": 70,
              "G": 71,
              "H": 72,
              "I": 73,
              "J": 74,
              "K": 75,
              "L": 76,
              "M": 77,
              "N": 78,
              "O": 79,
              "P": 80,
              "Q": 81,
              "R": 82,
              "S": 83,
              "T": 84,
              "U": 85,
              "V": 86,
              "W": 87,
              "X": 88,
              "Y": 89,
              "Z": 90,
              "bracketleft": 91,
              "backslash": 92,
              "bracketright": 93,
              "asciicircum": 94,
              "underscore": 95,
              "grave": 96,
              "a": 97,
              "b": 98,
              "c": 99,
              "d": 100,
              "e":101,
              "f":102,
              "g":103,
              "h":104,
              "i":105,
              "j":106,
              "k":107,
              "l":108,
              "m":109,
              "n":110,
              "o":111,
              "p":112,
              "q":113,
              "r":114,
              "s":115,
              "t":116,
              "u":117,
              "v":118,
              "w":119,
              "x":120,
              "y":121,
              "z":122,
              "braceleft":123,
              "bar":124,
              "braceright":125,
              "asciitilde":126,
              "bullet":127,
              "Euro":128,
              "bullet":129,
              "quotesinglbase":130,
              "florin":131,
              "quotedblbase":132,
              "ellipsis":133,
              "dagger":134,
              "daggerdbl":135,
              "circumflex":136,
              "perthousand":137,
              "Scaron":138,
              "guilsinglleft":139,
              "OE":140,
              "bullet":141,
              "Zcaron":142,
              "bullet":143,
              "bullet":144,
              "quoteleft":145,
              "quoteright":146,
              "quotedblleft":147,
              "quotedblright":148,
              "bullet":149,
              "endash":150,
              "emdash":151,
              "tilde":152,
              "trademark":153,
              "scaron":154,
              "guilsinglright":155,
              "oe":156,
              "bullet":157,
              "zcaron":158,
              "Ydieresis":159,
              "space":160,
              "exclamdown":161,
              "cent":162,
              "sterling":163,
              "currency":164,
              "yen":165,
              "brokenbar":166,
              "section":167,
              "dieresis":168,
              "copyright":169,
              "ordfeminine":170,
              "guillemotleft":171,
              "logicalnot":172,
              "hyphen":173,
              "registered":174,
              "macron":175,
              "degree":176,
              "plusminus":177,
              "twosuperior":178,
              "threesuperior":179,
              "acute":180,
              "mu":181,
              "paragraph":182,
              "periodcentered":183,
              "cedilla":184,
              "onesuperior":185,
              "ordmasculine":186,
              "guillemotright":187,
              "onequarter":188,
              "onehalf":189,
              "threequarters":190,
              "questiondown":191,
              "Agrave":192,
              "Aacute":193,
              "Acircumflex":194,
              "Atilde":195,
              "Adieresis":196,
              "Aring":197,
              "AE":198,
              "Ccedilla":199,
              "Egrave":200,
              "Eacute":201,
              "Ecircumflex":202,
              "Edieresis":203,
              "Igrave":204,
              "Iacute":205,
              "Icircumflex":206,
              "Idieresis":207,
              "Eth":208,
              "Ntilde":209,
              "Ograve":210,
              "Oacute":211,
              "Ocircumflex":212,
              "Otilde":213,
              "Odieresis":214,
              "multiply":215,
              "Oslash":216,
              "Ugrave":217,
              "Uacute":218,
              "Ucircumflex":219,
              "Udieresis":220,
              "Yacute":221,
              "Thorn":222,
              "germandbls":223,
              "agrave":224,
              "aacute":225,
              "acircumflex":226,
              "atilde":227,
              "adieresis":228,
              "aring":229,
              "ae":230,
              "ccedilla":231,
              "egrave":232,
              "eacute":233,
              "ecircumflex":234,
              "edieresis":235,
              "igrave":236,
              "iacute":237,
              "icircumflex":238,
              "idieresis":239,
              "eth":240,
              "ntilde":241,
              "ograve":242,
              "oacute":243,
              "ocircumflex":244,
              "otilde":245,
              "odieresis":246,
              "divide":247,
              "oslash":248,
              "ugrave":249,
              "uacute":250,
              "ucircumflex":251,
              "udieresis":252,
              "yacute":253,
              "thorn":254,
              "ydieresis":255}


fontbboxpattern = re.compile(r"/FontBBox\s*\{\s*(?P<fontbbox>(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+))\s*\}\s*(readonly\s+)?def")


def _readNullString(file):
    s = []
    c = file.read(1)
    while c and c != "\0":
        s.append(c)
        c = file.read(1)
    return "".join(s)


class PFMfile(metric.metric):

    def __init__(self, file, t1file):
        # pfm is rather incomplete, the t1file instance can be used to fill the gap
        (self.dfVersion, self.dfSize, self.dfCopyright, self.dfType,
         self.dfPoint, self.dfVertRes, self.dfHorizRes, self.dfAscent,
         self.dfInternalLeading, self.dfExternalLeading, self.dfItalic,
         self.dfUnderline, self.dfStrikeOut, self.dfWeight,
         self.dfCharSet, self.dfPixWidth, self.dfPixHeight,
         self.dfPitchAndFamily, self.dfAvgWidth, self.dfMaxWidth,
         self.dfFirstChar, self.dfLastChar, self.dfDefaultChar,
         self.dfBreakChar, self.dfWidthBytes, self.dfDevice, self.dfFace,
         self.dfBitsPointer, self.dfBitsOffset) = struct.unpack("<HL60s7H3BHB2HB2H4BH4L", file.read(117))
        self.dfCopyright = self.dfCopyright.split("\000", 1)[0]
        (self.dfSizeFields, self.dfExtMetricsOffset, self.dfExtentTable,
         self.dfOriginTable, self.dfPairKernTable, self.dfTrackKernTable,
         self.dfDriverInfo, self.dfReserved) = struct.unpack("<H7L", file.read(30))
        if self.dfDevice == 0:
            raise ValueError("DeviceName is required for Type1 pfm files.")
        file.seek(self.dfDevice)
        self.deviceName = _readNullString(file)
        if self.deviceName.lower() != "postscript":
            raise ValueError("Can process pfm files for PostScript fonts only.")
        if self.dfVersion != 0x100:
            raise ValueError("Invalid pfm file version.")
        if self.dfType != 0x81:
            raise ValueError("Not a Type1 pfm file.")
        if self.dfFace == 0:
            raise ValueError("FaceName is required for Type1 pfm files.")
        if self.dfExtMetricsOffset == 0:
            raise ValueError("ExtTextMetrics is required for Type1 pfm files.")
        if self.dfExtentTable == 0:
            raise ValueError("ExtentTable is required for Type1 pfm files.")
        if self.dfOriginTable != 0:
            raise ValueError("OriginTable is forbidden for Type1 pfm files.")
        if self.dfDriverInfo == 0:
            raise ValueError("DriverInfo is required for Type1 pfm files.")
        # assert self.dfReserved == 0 (must be zero according to the spec, but we don't care)
        file.seek(self.dfExtMetricsOffset)
        (etmSize, self.etmPointSize, self.etmOrientation,
         self.etmMasterHeight, self.etmMinScale, self.etmMaxScale,
         self.etmMasterUnits, self.etmCapHeight, self.etmXHeight,
         self.etmLowerCaseAscent, self.etmLowerCaseDescent, self.etmSlant,
         self.etmSuperScript, self.etmSubScript, self.etmSuperScriptSize,
         self.etmSubScriptSize, self.etmUnderlineOffset,
         self.etmUnderlineWidth, self.etmDoubleUpperUnderlineOffset,
         self.etmDoubleLowerUnderlineOffset, self.etmDoubleUpperUnderlineWidth,
         self.etmDoubleLowerUnderlineWidth, self.etmStrikeOutOffset,
         self.etmStrikeOutWidth, self.etmKernPairs, self.etmKernTracks) = struct.unpack("<24h2H", file.read(52))
        file.seek(self.dfFace)
        self.faceName = _readNullString(file)
        file.seek(self.dfDriverInfo)
        self.driverInfo = _readNullString(file)
        file.seek(self.dfExtentTable)
        count = self.dfLastChar - self.dfFirstChar + 1
        self.widths = struct.unpack("<%dH" % count, file.read(2*count))
        self.kernpairs = []
        self.kernpairsdict = {}
        if self.dfPairKernTable:
            file.seek(self.dfPairKernTable)
            pairs, = struct.unpack("<H", file.read(2))
            if pairs != self.etmKernPairs:
                raise ValueError("number of kerning pairs mismatch in pfm file.")
            for i in range(self.etmKernPairs):
                kpFirst, kpSecond, kpKernAmount = struct.unpack("<BBh", file.read(4))
                self.kernpairs.append((kpFirst, kpSecond, kpKernAmount))
                self.kernpairsdict[(kpFirst, kpSecond)] = kpKernAmount
        self.trackkerns = []
        if self.dfTrackKernTable:
            file.seek(self.dfTrackKernTable)
            items, = struct.unpack("<H", file.read(2))
            if items != self.etmKernTracks:
                raise ValueError("number of kerning tracks mismatch in pfm file.")
            for i in range(self.etmKernTracks):
                # each item consists of the tuple ktDegree, ktMinSize, ktMinAmount, ktMaxSize, ktMaxAmount
                self.trackkerns.append(struct.unpack("<hhhhh", file.read(10)))
        if self.dfCharSet:
            if not t1file.encoding:
                t1file._encoding()
            self.glyphs = dict([(glyph, i) for i, glyph in enumerate(t1file.encoding) if glyph != None])
        else:
            self.glyphs = ansiglyphs
        self.t1file = t1file

    def width_ds(self, glyphname):
        return self.widths[self.glyphs[glyphname]-self.dfFirstChar]

    def width_pt(self, glyphnames, size_pt):
        return sum([self.widths[self.glyphs[glyphname]-self.dfFirstChar] for glyphname in glyphnames])*size_pt/1000.0

    def height_pt(self, glyphnames, size_pt):
        return self.dfAscent*size_pt/1000.0

    def depth_pt(self, glyphnames, size_pt):
        return -self.etmLowerCaseDescent*size_pt/1000.0

    def resolvekernings(self, glyphnames, size_pt=None):
        result = [None]*(2*len(glyphnames)-1)
        for i, glyphname in enumerate(glyphnames):
            result[2*i] = glyphname
        return result

    def resolvekernings(self, glyphnames, size_pt=None):
        result = [None]*(2*len(glyphnames)-1)
        for i, glyphname in enumerate(glyphnames):
            result[2*i] = glyphname
            if i:
                amount = self.kernpairsdict.get((self.glyphs[glyphnames[i-1]], self.glyphs[glyphname]))
                if amount:
                    if size_pt is not None:
                        result[2*i-1] = amount*size_pt/1000.0
                    else:
                        result[2*i-1] = amount
        return result

    def writePDFfontinfo(self, file, seriffont=False, symbolfont=True):
        flags = 0
        if self.dfMaxWidth == self.dfAvgWidth:
            flags += 1<<0
        if seriffont:
            flags += 1<<1
        if symbolfont:
            flags += 1<<2
        else:
            flags += 1<<5
        if self.dfItalic:
            flags += 1<<6
        file.write("/Flags %d\n" % flags)
        file.write("/ItalicAngle %d\n" % (self.etmSlant/10))
        file.write("/Ascent %d\n" % self.dfAscent)
        file.write("/Descent %d\n" % -self.etmLowerCaseDescent)
        file.write("/FontBBox [%s]\n" % fontbboxpattern.search(self.t1file.data1).groups('fontbbox')[0])
        file.write("/CapHeight %d\n" % self.etmCapHeight)
        if self.dfWeight >= 600:
            stemv = 120
        else:
            stemv = 70
        file.write("/StemV %d\n" % stemv)

