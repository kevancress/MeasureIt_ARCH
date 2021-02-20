# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2005-2011 André Wobst <wobsta@pyx-project.org>
# Copyright (C) 2006-2011 Jörg Lehmann <joerg@pyx-project.org>
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

import array, binascii, io, logging, math, re
try:
    import zlib
    haszlib = True
except ImportError:
    haszlib = False

logger = logging.getLogger("pyx")

from pyx import trafo, reader, writer
from pyx.path import path, moveto_pt, lineto_pt, curveto_pt, closepath

try:
    from ._t1code import *
except:
    from .t1code import *


adobestandardencoding = [None, None, None, None, None, None, None, None,
                         None, None, None, None, None, None, None, None,
                         None, None, None, None, None, None, None, None,
                         None, None, None, None, None, None, None, None,
                         "space", "exclam", "quotedbl", "numbersign", "dollar", "percent", "ampersand", "quoteright",
                         "parenleft", "parenright", "asterisk", "plus", "comma", "hyphen", "period", "slash",
                         "zero", "one", "two", "three", "four", "five", "six", "seven",
                         "eight", "nine", "colon", "semicolon", "less", "equal", "greater", "question",
                         "at", "A", "B", "C", "D", "E", "F", "G",
                         "H", "I", "J", "K", "L", "M", "N", "O",
                         "P", "Q", "R", "S", "T", "U", "V", "W",
                         "X", "Y", "Z", "bracketleft", "backslash", "bracketright", "asciicircum", "underscore",
                         "quoteleft", "a", "b", "c", "d", "e", "f", "g",
                         "h", "i", "j", "k", "l", "m", "n", "o",
                         "p", "q", "r", "s", "t", "u", "v", "w",
                         "x", "y", "z", "braceleft", "bar", "braceright", "asciitilde", None,
                         None, None, None, None, None, None, None, None,
                         None, None, None, None, None, None, None, None,
                         None, None, None, None, None, None, None, None,
                         None, None, None, None, None, None, None, None,
                         None, "exclamdown", "cent", "sterling", "fraction", "yen", "florin", "section",
                         "currency", "quotesingle", "quotedblleft", "guillemotleft", "guilsinglleft", "guilsinglright", "fi", "fl",
                         None, "endash", "dagger", "daggerdbl", "periodcentered", None, "paragraph", "bullet",
                         "quotesinglbase", "quotedblbase", "quotedblright", "guillemotright", "ellipsis", "perthousand", None, "questiondown",
                         None, "grave", "acute", "circumflex", "tilde", "macron", "breve", "dotaccent",
                         "dieresis", None, "ring", "cedilla", None, "hungarumlaut", "ogonek", "caron",
                         "emdash", None, None, None, None, None, None, None,
                         None, None, None, None, None, None, None, None,
                         None, "AE", None, "ordfeminine", None, None, None, None,
                         "Lslash", "Oslash", "OE", "ordmasculine", None, None, None, None,
                         None, "ae", None, None, None, "dotlessi", None, None,
                         "lslash", "oslash", "oe", "germandbls", None, None, None, None]

class T1context:

    def __init__(self, t1font, flex=True):
        """context for T1cmd evaluation"""
        self.t1font = t1font

        # state description
        self.x = None
        self.y = None
        self.wx = None
        self.wy = None
        self.t1stack = []
        self.psstack = []
        self.flex = flex


######################################################################
# T1 commands
# Note, that the T1 commands are variable-free except for plain number,
# which are stored as integers. All other T1 commands exist as a single
# instance only

T1cmds = {}
T1subcmds = {}

class T1cmd:

    def __init__(self, code, subcmd=0):
        self.code = code
        self.subcmd = subcmd
        if subcmd:
            T1subcmds[code] = self
        else:
            T1cmds[code] = self

    def __str__(self):
        """returns a string representation of the T1 command"""
        raise NotImplementedError

    def updatepath(self, path, trafo, context):
        """update path instance applying trafo to the points"""
        raise NotImplementedError

    def gathercalls(self, seacglyphs, subrs, context):
        """gather dependancy information

        subrs is the "called-subrs" dictionary. gathercalls will insert the
        subr number as key having the value 1, i.e. subrs will become the
        numbers of used subrs. Similar seacglyphs will contain all glyphs in
        composite characters (subrs for those glyphs will also
        already be included).

        This method might will not properly update all information in the
        context (especially consuming values from the stack) and will also skip
        various tests for performance reasons. For most T1 commands it just
        doesn't need to do anything.
        """
        pass


# commands for starting and finishing

class _T1endchar(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 14)

    def __str__(self):
        return "endchar"

    def updatepath(self, path, trafo, context):
        pass

T1endchar = _T1endchar()


class _T1hsbw(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 13)

    def __str__(self):
        return "hsbw"

    def updatepath(self, path, trafo, context):
        sbx = context.t1stack.pop(0)
        wx = context.t1stack.pop(0)
        path.append(moveto_pt(*trafo.apply_pt(sbx, 0)))
        context.x = sbx
        context.y = 0
        context.wx = wx
        context.wy = 0

T1hsbw = _T1hsbw()


class _T1seac(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 6, subcmd=1)

    def __str__(self):
        return "seac"

    def updatepath(self, path, atrafo, context):
        sab = context.t1stack.pop(0)
        adx = context.t1stack.pop(0)
        ady = context.t1stack.pop(0)
        bchar = context.t1stack.pop(0)
        achar = context.t1stack.pop(0)
        aglyph = adobestandardencoding[achar]
        bglyph = adobestandardencoding[bchar]
        context.t1font.updateglyphpath(bglyph, path, atrafo, context)
        atrafo = atrafo * trafo.translate_pt(adx-sab, ady)
        context.t1font.updateglyphpath(aglyph, path, atrafo, context)

    def gathercalls(self, seacglyphs, subrs, context):
        achar = context.t1stack.pop()
        bchar = context.t1stack.pop()
        aglyph = adobestandardencoding[achar]
        bglyph = adobestandardencoding[bchar]
        seacglyphs.add(aglyph)
        seacglyphs.add(bglyph)
        context.t1font.gatherglyphcalls(bglyph, seacglyphs, subrs, context)
        context.t1font.gatherglyphcalls(aglyph, seacglyphs, subrs, context)

T1seac = _T1seac()


class _T1sbw(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 7, subcmd=1)

    def __str__(self):
        return "sbw"

    def updatepath(self, path, trafo, context):
        sbx = context.t1stack.pop(0)
        sby = context.t1stack.pop(0)
        wx = context.t1stack.pop(0)
        wy = context.t1stack.pop(0)
        path.append(moveto_pt(*trafo.apply_pt(sbx, sby)))
        context.x = sbx
        context.y = sby
        context.wx = wx
        context.wy = wy

T1sbw = _T1sbw()


# path construction commands

class _T1closepath(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 9)

    def __str__(self):
        return "closepath"

    def updatepath(self, path, trafo, context):
        path.append(closepath())
        # The closepath in T1 is different from PostScripts in that it does
        # *not* modify the current position; hence we need to add an additional
        # moveto here ...
        path.append(moveto_pt(*trafo.apply_pt(context.x, context.y)))

T1closepath = _T1closepath()


class _T1hlineto(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 6)

    def __str__(self):
        return "hlineto"

    def updatepath(self, path, trafo, context):
        dx = context.t1stack.pop(0)
        path.append(lineto_pt(*trafo.apply_pt(context.x + dx, context.y)))
        context.x += dx

T1hlineto = _T1hlineto()


class _T1hmoveto(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 22)

    def __str__(self):
        return "hmoveto"

    def updatepath(self, path, trafo, context):
        dx = context.t1stack.pop(0)
        path.append(moveto_pt(*trafo.apply_pt(context.x + dx, context.y)))
        context.x += dx

T1hmoveto = _T1hmoveto()


class _T1hvcurveto(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 31)

    def __str__(self):
        return "hvcurveto"

    def updatepath(self, path, trafo, context):
        dx1 = context.t1stack.pop(0)
        dx2 = context.t1stack.pop(0)
        dy2 = context.t1stack.pop(0)
        dy3 = context.t1stack.pop(0)
        path.append(curveto_pt(*(trafo.apply_pt(context.x + dx1,       context.y) +
                                 trafo.apply_pt(context.x + dx1 + dx2, context.y + dy2) +
                                 trafo.apply_pt(context.x + dx1 + dx2, context.y + dy2 + dy3))))
        context.x += dx1+dx2
        context.y += dy2+dy3

T1hvcurveto = _T1hvcurveto()


class _T1rlineto(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 5)

    def __str__(self):
        return "rlineto"

    def updatepath(self, path, trafo, context):
        dx = context.t1stack.pop(0)
        dy = context.t1stack.pop(0)
        path.append(lineto_pt(*trafo.apply_pt(context.x + dx, context.y + dy)))
        context.x += dx
        context.y += dy

T1rlineto = _T1rlineto()


class _T1rmoveto(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 21)

    def __str__(self):
        return "rmoveto"

    def updatepath(self, path, trafo, context):
        dx = context.t1stack.pop(0)
        dy = context.t1stack.pop(0)
        path.append(moveto_pt(*trafo.apply_pt(context.x + dx, context.y + dy)))
        context.x += dx
        context.y += dy

T1rmoveto = _T1rmoveto()


class _T1rrcurveto(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 8)

    def __str__(self):
        return "rrcurveto"

    def updatepath(self, path, trafo, context):
        dx1 = context.t1stack.pop(0)
        dy1 = context.t1stack.pop(0)
        dx2 = context.t1stack.pop(0)
        dy2 = context.t1stack.pop(0)
        dx3 = context.t1stack.pop(0)
        dy3 = context.t1stack.pop(0)
        path.append(curveto_pt(*(trafo.apply_pt(context.x + dx1,             context.y + dy1) +
                                 trafo.apply_pt(context.x + dx1 + dx2,       context.y + dy1 + dy2) +
                                 trafo.apply_pt(context.x + dx1 + dx2 + dx3, context.y + dy1 + dy2 + dy3))))
        context.x += dx1+dx2+dx3
        context.y += dy1+dy2+dy3

T1rrcurveto = _T1rrcurveto()


class _T1vlineto(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 7)

    def __str__(self):
        return "vlineto"

    def updatepath(self, path, trafo, context):
        dy = context.t1stack.pop(0)
        path.append(lineto_pt(*trafo.apply_pt(context.x, context.y + dy)))
        context.y += dy

T1vlineto = _T1vlineto()


class _T1vmoveto(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 4)

    def __str__(self):
        return "vmoveto"

    def updatepath(self, path, trafo, context):
        dy = context.t1stack.pop(0)
        path.append(moveto_pt(*trafo.apply_pt(context.x, context.y + dy)))
        context.y += dy

T1vmoveto = _T1vmoveto()


class _T1vhcurveto(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 30)

    def __str__(self):
        return "vhcurveto"

    def updatepath(self, path, trafo, context):
        dy1 = context.t1stack.pop(0)
        dx2 = context.t1stack.pop(0)
        dy2 = context.t1stack.pop(0)
        dx3 = context.t1stack.pop(0)
        path.append(curveto_pt(*(trafo.apply_pt(context.x,             context.y + dy1) +
                                 trafo.apply_pt(context.x + dx2,       context.y + dy1 + dy2) +
                                 trafo.apply_pt(context.x + dx2 + dx3, context.y + dy1 + dy2))))
        context.x += dx2+dx3
        context.y += dy1+dy2

T1vhcurveto = _T1vhcurveto()


# hint commands

class _T1dotsection(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 0, subcmd=1)

    def __str__(self):
        return "dotsection"

    def updatepath(self, path, trafo, context):
        pass

T1dotsection = _T1dotsection()


class _T1hstem(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 1)

    def __str__(self):
        return "hstem"

    def updatepath(self, path, trafo, context):
        y = context.t1stack.pop(0)
        dy = context.t1stack.pop(0)

T1hstem = _T1hstem()


class _T1hstem3(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 2, subcmd=1)

    def __str__(self):
        return "hstem3"

    def updatepath(self, path, trafo, context):
        y0 = context.t1stack.pop(0)
        dy0 = context.t1stack.pop(0)
        y1 = context.t1stack.pop(0)
        dy1 = context.t1stack.pop(0)
        y2 = context.t1stack.pop(0)
        dy2 = context.t1stack.pop(0)

T1hstem3 = _T1hstem3()


class _T1vstem(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 3)

    def __str__(self):
        return "vstem"

    def updatepath(self, path, trafo, context):
        x = context.t1stack.pop(0)
        dx = context.t1stack.pop(0)

T1vstem = _T1vstem()


class _T1vstem3(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 1, subcmd=1)

    def __str__(self):
        return "vstem3"

    def updatepath(self, path, trafo, context):
        self.x0 = context.t1stack.pop(0)
        self.dx0 = context.t1stack.pop(0)
        self.x1 = context.t1stack.pop(0)
        self.dx1 = context.t1stack.pop(0)
        self.x2 = context.t1stack.pop(0)
        self.dx2 = context.t1stack.pop(0)

T1vstem3 = _T1vstem3()


# arithmetic command

class _T1div(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 12, subcmd=1)

    def __str__(self):
        return "div"

    def updatepath(self, path, trafo, context):
        num2 = context.t1stack.pop()
        num1 = context.t1stack.pop()
        context.t1stack.append(divmod(num1, num2)[0])

    def gathercalls(self, seacglyphs, subrs, context):
        num2 = context.t1stack.pop()
        num1 = context.t1stack.pop()
        context.t1stack.append(divmod(num1, num2)[0])

T1div = _T1div()


# subroutine commands

class _T1callothersubr(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 16, subcmd=1)

    def __str__(self):
        return "callothersubr"

    def updatepath(self, path, trafo, context):
        othersubrnumber = context.t1stack.pop()
        n = context.t1stack.pop()
        for i in range(n):
            context.psstack.append(context.t1stack.pop(0))
        if othersubrnumber == 0:
            flex_size, x, y = context.psstack[-3:]
            if context.flex:
                x1, y1, x2, y2, x3, y3 = context.psstack[2:8]
                x1, y1 = trafo.apply_pt(x1, y1)
                x2, y2 = trafo.apply_pt(x2, y2)
                x3, y3 = trafo.apply_pt(x3, y3)
                path.append(curveto_pt(x1, y1, x2, y2, x3, y3))
                x1, y1, x2, y2, x3, y3 = context.psstack[8:14]
                x1, y1 = trafo.apply_pt(x1, y1)
                x2, y2 = trafo.apply_pt(x2, y2)
                x3, y3 = trafo.apply_pt(x3, y3)
                path.append(curveto_pt(x1, y1, x2, y2, x3, y3))
            else:
                path.append(lineto_pt(*trafo.apply_pt(x, y)))
            context.psstack = [y, x]
        elif othersubrnumber == 1:
            pass
        elif othersubrnumber == 2:
            path.pathitems.pop()
            context.psstack.append(context.x)
            context.psstack.append(context.y)

    def gathercalls(self, seacglyphs, subrs, context):
        othersubrnumber = context.t1stack.pop()
        n = context.t1stack.pop()
        context.psstack.extend([context.t1stack.pop() for i in range(n)][::-1])

T1callothersubr = _T1callothersubr()


class _T1callsubr(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 10)

    def __str__(self):
        return "callsubr"

    def updatepath(self, path, trafo, context):
        subr = context.t1stack.pop()
        context.t1font.updatesubrpath(subr, path, trafo, context)

    def gathercalls(self, seacglyphs, subrs, context):
        subr = context.t1stack.pop()
        subrs.add(subr)
        context.t1font.gathersubrcalls(subr, seacglyphs, subrs, context)

T1callsubr = _T1callsubr()


class _T1pop(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 17, subcmd=1)

    def __str__(self):
        return "pop"

    def updatepath(self, path, trafo, context):
        context.t1stack.append(context.psstack.pop())

    def gathercalls(self, seacglyphs, subrs, context):
        context.t1stack.append(context.psstack.pop())

T1pop = _T1pop()


class _T1return(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 11)

    def __str__(self):
        return "return"

    def updatepath(self, path, trafo, context):
        pass

T1return = _T1return()


class _T1setcurrentpoint(T1cmd):

    def __init__(self):
        T1cmd.__init__(self, 33, subcmd=1)

    def __str__(self):
        return "setcurrentpoint"

    def updatepath(self, path, trafo, context):
        context.x = context.t1stack.pop(0)
        context.y = context.t1stack.pop(0)

T1setcurrentpoint = _T1setcurrentpoint()


######################################################################

class FontFormatError(Exception):
    pass

class T1File:

    eexecr = 55665
    charstringr = 4330

    fontnamepattern = re.compile("/FontName\s+/(.*?)\s+def\s+")
    fontmatrixpattern = re.compile("/FontMatrix\s*\[\s*(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s*\]\s*(readonly\s+)?def")

    def __init__(self, data1, data2eexec, data3):
        """initializes a t1font instance

        data1 and data3 are the two clear text data parts and data2 is
        the binary data part"""
        self.data1 = data1
        self._data2eexec = data2eexec
        self.data3 = data3

        # marker and value for decoded data
        self._data2 = None
        # note that data2eexec is set to none by setsubrcmds and setglyphcmds
        # this *also* denotes, that data2 is out-of-date; hence they are both
        # marked by an _ and getdata2 and getdata2eexec will properly resolve
        # the current state of decoding ...

        # marker and value for standard encoding check
        self.encoding = None

        self.name, = self.fontnamepattern.search(self.data1).groups()
        m11, m12, m21, m22, v1, v2 = list(map(float, self.fontmatrixpattern.search(self.data1).groups()[:6]))
        self.fontmatrix = trafo.trafo_pt(matrix=((m11, m12), (m21, m22)), vector=(v1, v2))

    def _eexecdecode(self, code):
        """eexec decoding of code"""
        return decoder(code, self.eexecr, 4)

    def _charstringdecode(self, code):
        """charstring decoding of code"""
        return decoder(code, self.charstringr, self.lenIV)

    def _eexecencode(self, data):
        """eexec encoding of data"""
        return encoder(data, self.eexecr, b"PyX!")

    def _charstringencode(self, data):
        """eexec encoding of data"""
        return encoder(data, self.charstringr, b"PyX!"[:self.lenIV])

    def _encoding(self):
        """helper method to lookup the encoding in the font"""
        c = reader.PStokenizer(self.data1, "/Encoding")
        token1 = c.gettoken()
        token2 = c.gettoken()
        if token1 == "StandardEncoding" and token2 == "def":
            self.encoding = adobestandardencoding
        else:
            self.encoding = [None]*256
            while True:
                self.encodingstart = c.pos
                if c.gettoken() == "dup":
                    break
            while True:
                i = c.getint()
                glyph = c.gettoken()
                if 0 <= i < 256:
                    self.encoding[i] = glyph[1:]
                token = c.gettoken(); assert token == "put"
                self.encodingend = c.pos
                token = c.gettoken()
                if token == "readonly" or token == "def":
                    break
                assert token == "dup"

    lenIVpattern = re.compile(b"/lenIV\s+(\d+)\s+def\s+")
    flexhintsubrs = [[3, 0, T1callothersubr, T1pop, T1pop, T1setcurrentpoint, T1return],
                     [0, 1, T1callothersubr, T1return],
                     [0, 2, T1callothersubr, T1return],
                     [T1return]]

    def _data2decode(self):
        """decodes data2eexec to the data2 string and the subr and glyphs dictionary

        It doesn't make sense to call this method twice -- check the content of
        data2 before calling. The method also keeps the subrs and charstrings
        start and end positions for later use."""
        self._data2 = self._eexecdecode(self._data2eexec)

        m = self.lenIVpattern.search(self._data2)
        if m:
            self.lenIV = int(m.group(1))
        else:
            self.lenIV = 4

        self.emptysubr = self._charstringencode(b"\x0b") # 11, i.e. return

        # extract Subrs
        c = reader.PSbytes_tokenizer(self._data2, b"/Subrs")
        self.subrsstart = c.pos
        arraycount = c.getint()
        token = c.gettoken(); assert token == b"array"
        self.subrs = []
        for i in range(arraycount):
            token = c.gettoken(); assert token == b"dup"
            token = c.getint(); assert token == i
            size = c.getint()
            if not i:
                self.subrrdtoken = c.gettoken()
            else:
                token = c.gettoken(); assert token == self.subrrdtoken
            self.subrs.append(c.getbytes(size))
            token = c.gettoken()
            if token == b"noaccess":
                token = token + b" " + c.gettoken()
            if not i:
                self.subrnptoken = token
            else:
                assert token == self.subrnptoken
        self.subrsend = c.pos

        # hasflexhintsubrs is a boolean indicating that the font uses flex or
        # hint replacement subrs as specified by Adobe (tm). When it does, the
        # first 4 subrs should all be copied except when none of them are used
        # in the stripped version of the font since we then get a font not
        # using flex or hint replacement subrs at all.
        self.hasflexhintsubrs = (arraycount >= len(self.flexhintsubrs) and
                                 [self.getsubrcmds(i)
                                  for i in range(len(self.flexhintsubrs))] == self.flexhintsubrs)

        # extract glyphs
        self.glyphs = {}
        self.glyphlist = [] # we want to keep the order of the glyph names
        c = reader.PSbytes_tokenizer(self._data2, b"/CharStrings")
        self.charstringsstart = c.pos
        c.getint()
        token = c.gettoken(); assert token == b"dict"
        token = c.gettoken(); assert token == b"dup"
        token = c.gettoken(); assert token == b"begin"
        first = True
        while True:
            chartoken = c.gettoken().decode("ascii")
            if chartoken == "end":
                break
            assert chartoken[0] == "/"
            size = c.getint()
            if first:
                self.glyphrdtoken = c.gettoken()
            else:
                token = c.gettoken(); assert token == self.glyphrdtoken
            self.glyphlist.append(chartoken[1:])
            self.glyphs[chartoken[1:]] = c.getbytes(size)
            if first:
                self.glyphndtoken = c.gettoken()
            else:
                token = c.gettoken(); assert token == self.glyphndtoken
            first = False
        self.charstringsend = c.pos
        assert not self.subrs or self.subrrdtoken == self.glyphrdtoken

    def _cmds(self, code):
        """return a list of T1cmd's for encoded charstring data in code"""
        code = array.array("B", self._charstringdecode(code))
        cmds = []
        while code:
            x = code.pop(0)
            if x == 12: # this starts an escaped cmd
                cmds.append(T1subcmds[code.pop(0)])
            elif 0 <= x < 32: # those are cmd's
                cmds.append(T1cmds[x])
            elif 32 <= x <= 246: # short ints
                cmds.append(x-139)
            elif 247 <= x <= 250: # mid size ints
                cmds.append(((x - 247)*256) + code.pop(0) + 108)
            elif 251 <= x <= 254: # mid size ints
                cmds.append(-((x - 251)*256) - code.pop(0) - 108)
            else: # x = 255, i.e. full size ints
                y = ((code.pop(0)*256+code.pop(0))*256+code.pop(0))*256+code.pop(0)
                if y > (1 << 31):
                    cmds.append(y - (1 << 32))
                else:
                    cmds.append(y)
        return cmds

    def _code(self, cmds):
        """return an encoded charstring data for list of T1cmd's in cmds"""
        code = array.array("B")
        for cmd in cmds:
            try:
                if cmd.subcmd:
                    code.append(12)
                code.append(cmd.code)
            except AttributeError:
                if -107 <= cmd <= 107:
                    code.append(cmd+139)
                elif 108 <= cmd <= 1131:
                    a, b = divmod(cmd-108, 256)
                    code.append(a+247)
                    code.append(b)
                elif -1131 <= cmd <= -108:
                    a, b = divmod(-cmd-108, 256)
                    code.append(a+251)
                    code.append(b)
                else:
                    if cmd < 0:
                        cmd += 1 << 32
                    cmd, x4 = divmod(cmd, 256)
                    cmd, x3 = divmod(cmd, 256)
                    x1, x2 = divmod(cmd, 256)
                    code.append(255)
                    code.append(x1)
                    code.append(x2)
                    code.append(x3)
                    code.append(x4)
        return self._charstringencode(code.tobytes())

    def getsubrcmds(self, subr):
        """return a list of T1cmd's for subr subr"""
        if not self._data2:
            self._data2decode()
        return self._cmds(self.subrs[subr])

    def getglyphcmds(self, glyph):
        """return a list of T1cmd's for glyph glyph"""
        if not self._data2:
            self._data2decode()
        return self._cmds(self.glyphs[glyph])

    def setsubrcmds(self, subr, cmds):
        """replaces the T1cmd's by the list cmds for subr subr"""
        if not self._data2:
            self._data2decode()
        self._data2eexec = None
        self.subrs[subr] = self._code(cmds)

    def setglyphcmds(self, glyph, cmds):
        """replaces the T1cmd's by the list cmds for glyph glyph"""
        if not self._data2:
            self._data2decode()
        self._data2eexec = None
        self.glyphs[glyph] = self._code(cmds)

    def updatepath(self, cmds, path, trafo, context):
        for cmd in cmds:
            if isinstance(cmd, T1cmd):
                cmd.updatepath(path, trafo, context)
            else:
                context.t1stack.append(cmd)

    def updatesubrpath(self, subr, path, trafo, context):
        self.updatepath(self.getsubrcmds(subr), path, trafo, context)

    def updateglyphpath(self, glyph, path, trafo, context):
        self.updatepath(self.getglyphcmds(glyph), path, trafo, context)

    def gathercalls(self, cmds, seacglyphs, subrs, context):
        for cmd in cmds:
            if isinstance(cmd, T1cmd):
                cmd.gathercalls(seacglyphs, subrs, context)
            else:
                context.t1stack.append(cmd)

    def gathersubrcalls(self, subr, seacglyphs, subrs, context):
        self.gathercalls(self.getsubrcmds(subr), seacglyphs, subrs, context)

    def gatherglyphcalls(self, glyph, seacglyphs, subrs, context):
        self.gathercalls(self.getglyphcmds(glyph), seacglyphs, subrs, context)

    def getglyphpath_pt(self, x_pt, y_pt, glyph, size_pt, convertcharcode=False, flex=True):
        """return an object containing the PyX path, wx_pt and wy_pt for glyph named glyph"""
        if convertcharcode:
            if not self.encoding:
                self._encoding()
            glyph = self.encoding[glyph]
        t = self.fontmatrix.scaled(size_pt)
        tpath = t.translated_pt(x_pt, y_pt)
        context = T1context(self, flex=flex)
        p = path()
        self.updateglyphpath(glyph, p, tpath, context)
        class glyphpath:
            def __init__(self, p, wx_pt, wy_pt):
                self.path = p
                self.wx_pt = wx_pt
                self.wy_pt = wy_pt
        return glyphpath(p, *t.apply_pt(context.wx, context.wy))

    def getdata2(self, subrs=None, glyphs=None):
        """makes a data2 string

        subrs is a dict containing those subrs numbers as keys,
        which are to be contained in the subrsstring to be created.
        If subrs is None, all subrs in self.subrs will be used.
        The subrs dict might be modified *in place*.

        glyphs is a dict containing those glyph names as keys,
        which are to be contained in the charstringsstring to be created.
        If glyphs is None, all glyphs in self.glyphs will be used."""
        w = writer.writer(io.BytesIO())

        def addsubrs(subrs):
            if subrs is not None:
                # some adjustments to the subrs dict
                if subrs:
                    subrsmin = min(subrs)
                    subrsmax = max(subrs)
                    if self.hasflexhintsubrs and subrsmin < len(self.flexhintsubrs):
                        # According to the spec we need to keep all the flex and hint subrs
                        # as long as any of it is used.
                        for subr in range(len(self.flexhintsubrs)):
                            subrs.add(subr)
                        subrsmax = max(subrs)
                else:
                    subrsmax = -1
            else:
                # build a new subrs dict containing all subrs
                subrs = dict([(subr, 1) for subr in range(len(self.subrs))])
                subrsmax = len(self.subrs) - 1

            # build the string from all selected subrs
            w.write("%d array\n" % (subrsmax + 1))
            for subr in range(subrsmax+1):
                if subr in subrs:
                    code = self.subrs[subr]
                else:
                    code = self.emptysubr
                w.write("dup %d %d " % (subr, len(code)))
                w.write_bytes(self.subrrdtoken)
                w.write_bytes(b" ")
                w.write_bytes(code)
                w.write_bytes(b" ")
                w.write_bytes(self.subrnptoken)
                w.write_bytes(b"\n")

        def addcharstrings(glyphs):
            w.write("%d dict dup begin\n" % (glyphs is None and len(self.glyphlist) or len(glyphs)))
            for glyph in self.glyphlist:
                if glyphs is None or glyph in glyphs:
                    w.write("/%s %d " % (glyph, len(self.glyphs[glyph])))
                    w.write_bytes(self.glyphrdtoken)
                    w.write_bytes(b" ")
                    w.write_bytes(self.glyphs[glyph])
                    w.write_bytes(b" ")
                    w.write_bytes(self.glyphndtoken)
                    w.write_bytes(b"\n")
            w.write("end\n")

        if self.subrsstart < self.charstringsstart:
            w.write_bytes(self._data2[:self.subrsstart])
            addsubrs(subrs)
            w.write_bytes(self._data2[self.subrsend:self.charstringsstart])
            addcharstrings(glyphs)
            w.write_bytes(self._data2[self.charstringsend:])
        else:
            w.write_bytes(self._data2[:self.charstringsstart])
            addcharstrings(glyphs)
            w.write_bytes(self._data2[self.charstringsend:self.subrsstart])
            addsubrs(subrs)
            w.write_bytes(self._data2[self.subrsend:])
        return w.file.getvalue()

    def getdata2eexec(self):
        if self._data2eexec:
            return self._data2eexec
        # note that self._data2 is out-of-date here too, hence we need to call getdata2
        return self._eexecencode(self.getdata2())

    newlinepattern = re.compile("\s*[\r\n]\s*")
    uniqueidstrpattern = re.compile("%?/UniqueID\s+\d+\s+def\s+")
    uniqueidbytespattern = re.compile(b"%?/UniqueID\s+\d+\s+def\s+")
        # when UniqueID is commented out (as in modern latin), prepare to remove the comment character as well

    def getstrippedfont(self, glyphs, charcodes):
        """create a T1File instance containing only certain glyphs

        glyphs is a set of the glyph names. It might be modified *in place*!
        """
        if not self.encoding:
            self._encoding()
        for charcode in charcodes:
            glyphs.add(self.encoding[charcode])

        # collect information about used glyphs and subrs
        seacglyphs = set()
        subrs = set()
        for glyph in glyphs:
            self.gatherglyphcalls(glyph, seacglyphs, subrs, T1context(self))
        # while we have gathered all subrs for the seacglyphs alreadys, we
        # might have missed the glyphs themself (when they are not used stand-alone)
        glyphs.update(seacglyphs)
        glyphs.add(".notdef")

        # strip data1
        if self.encoding is adobestandardencoding:
            data1 = self.data1
        else:
            encodingstrings = []
            for char, glyph in enumerate(self.encoding):
                if glyph in glyphs:
                    encodingstrings.append("dup %i /%s put\n" % (char, glyph))
            data1 = self.data1[:self.encodingstart] + "\n" + "".join(encodingstrings) + self.data1[self.encodingend:]
        data1 = self.newlinepattern.subn("\n", data1)[0]
        data1 = self.uniqueidstrpattern.subn("", data1)[0]

        # strip data2
        data2 = self.uniqueidbytespattern.subn(b"", self.getdata2(subrs, glyphs))[0]

        # strip data3
        data3 = self.newlinepattern.subn("\n", self.data3)[0]

        # create and return the new font instance
        return T1File(data1.rstrip() + "\n", self._eexecencode(data2), data3.rstrip() + "\n")

    # The following two methods, writePDFfontinfo and getglyphinfo,
    # extract informtion which should better be taken from the afm file.
    def writePDFfontinfo(self, file):
        try:
            glyphinfo_y = self.getglyphinfo("y")
            glyphinfo_W = self.getglyphinfo("W")
            glyphinfo_H = self.getglyphinfo("H")
            glyphinfo_h = self.getglyphinfo("h")
            glyphinfo_period = self.getglyphinfo("period")
            glyphinfo_colon = self.getglyphinfo("colon")
        except:
            logger.warning("Auto-guessing of font information for font '%s' failed. We're writing stub data instead." % self.name)
            file.write("/Flags 4\n")
            file.write("/FontBBox [0 -100 1000 1000]\n")
            file.write("/ItalicAngle 0\n")
            file.write("/Ascent 1000\n")
            file.write("/Descent -100\n")
            file.write("/CapHeight 700\n")
            file.write("/StemV 100\n")
        else:
            if not self.encoding:
                self._encoding()
            # As a simple heuristics we assume non-symbolic fonts if and only
            # if the Adobe standard encoding is used. All other font flags are
            # not specified here.
            if self.encoding is adobestandardencoding:
                file.write("/Flags 32\n")
            else:
                file.write("/Flags 4\n")
            file.write("/FontBBox [0 %d %d %d]\n" % (glyphinfo_y[3], glyphinfo_W[0], glyphinfo_H[5]))
            file.write("/ItalicAngle %d\n" % math.degrees(math.atan2(glyphinfo_period[4]-glyphinfo_colon[4], glyphinfo_colon[5]-glyphinfo_period[5])))
            file.write("/Ascent %d\n" % glyphinfo_H[5])
            file.write("/Descent %d\n" % glyphinfo_y[3])
            file.write("/CapHeight %d\n" % glyphinfo_h[5])
            file.write("/StemV %d\n" % (glyphinfo_period[4]-glyphinfo_period[2]))

    def getglyphinfo(self, glyph, flex=True):
        logger.warning("We are about to extract font information for the Type 1 font '%s' from its pfb file. This is bad practice (and it's slow). You should use an afm file instead." % self.name)
        context = T1context(self, flex=flex)
        p = path()
        self.updateglyphpath(glyph, p, trafo.trafo(), context)
        bbox = p.bbox()
        return context.wx, context.wy, bbox.llx_pt, bbox.lly_pt, bbox.urx_pt, bbox.ury_pt

    def outputPFA(self, file, remove_UniqueID_lookup=False):
        """output the T1File in PFA format"""
        data1 = self.data1
        data3 = self.data3
        if remove_UniqueID_lookup:
            m1 = re.search("""FontDirectory\s*/%(name)s\s+known{/%(name)s\s+findfont\s+dup\s*/UniqueID\s+known\s*{\s*dup\s*
                              /UniqueID\s+get\s+\d+\s+eq\s+exch\s*/FontType\s+get\s+1\s+eq\s+and\s*}\s*{\s*pop\s+false\s*}\s*ifelse\s*
                              {save\s+true\s*}\s*{\s*false\s*}\s*ifelse\s*}\s*{\s*false\s*}\s*ifelse""" % {"name": self.name},
                           data1, re.VERBOSE)
            m3 = re.search("\s*{restore}\s*if", data3)
            if m1 and m3:
                data1 = data1[:m1.start()] + data1[m1.end():]
                data3 = data3[:m3.start()] + data3[m3.end():]
        file.write(data1)
        data2eexechex = binascii.b2a_hex(self.getdata2eexec())
        linelength = 64
        for i in range((len(data2eexechex)-1)//linelength + 1):
            file.write_bytes(data2eexechex[i*linelength: i*linelength+linelength])
            file.write("\n")
        file.write(data3)

    def outputPFB(self, file):
        """output the T1File in PFB format"""
        data2eexec = self.getdata2eexec()
        def pfblength(data):
            l = len(data)
            l, x1 = divmod(l, 256)
            l, x2 = divmod(l, 256)
            x4, x3 = divmod(l, 256)
            return chr(x1) + chr(x2) + chr(x3) + chr(x4)
        file.write("\200\1")
        file.write(pfblength(self.data1))
        file.write(self.data1)
        file.write("\200\2")
        file.write(pfblength(data2eexec))
        file.write(data2eexec)
        file.write("\200\1")
        file.write(pfblength(self.data3))
        file.write(self.data3)
        file.write("\200\3")

    def outputPS(self, file, writer):
        """output the PostScript code for the T1File to the file file"""
        self.outputPFA(file, remove_UniqueID_lookup=True)

    def outputPDF(self, file, writer):
        data2eexec = self.getdata2eexec()
        data3 = self.data3
        # we might be allowed to skip the third part ...
        if (data3.replace("\n", "")
                 .replace("\r", "")
                 .replace("\t", "")
                 .replace(" ", "")) == "0"*512 + "cleartomark":
            data3 = ""

        data = self.data1.encode("ascii", errors="surrogateescape") + data2eexec + data3.encode("ascii", errors="surrogateescape")
        if writer.compress and haszlib:
            data = zlib.compress(data)

        file.write("<<\n"
                   "/Length %d\n"
                   "/Length1 %d\n"
                   "/Length2 %d\n"
                   "/Length3 %d\n" % (len(data), len(self.data1), len(data2eexec), len(data3)))
        if writer.compress and haszlib:
            file.write("/Filter /FlateDecode\n")
        file.write(">>\n"
                   "stream\n")
        file.write_bytes(data)
        file.write("\n"
                   "endstream\n")

    @classmethod
    def from_PFA_bytes(cls, bytes):
        """create a T1File instance from a string of bytes corresponding to a PFA file"""
        try:
            m1 = bytes.index("eexec") + 6
            m2 = bytes.index("0"*40)
        except ValueError:
           raise FontFormatError

        data1 = bytes[:m1].decode("ascii", errors="surrogateescape")
        data2eexec = binascii.a2b_hex(bytes[m1: m2].replace(" ", "").replace("\r", "").replace("\n", ""))
        data3 = bytes[m2:].decode("ascii", errors="surrogateescape")
        return cls(data1, data2eexec, data3)

    @classmethod
    def from_PFA_filename(cls, filename):
        """create a T1File instance from PFA font file of given name"""
        with open(filename, "rb") as file:
            t1file = cls.from_PFA_bytes(file.read())
        return t1file

    @classmethod
    def from_PFB_bytes(cls, bytes):
        """create a T1File instance from a string of bytes corresponding to a PFB file"""

        def pfblength(s):
            if len(s) != 4:
                raise ValueError("invalid string length")
            return (s[0] +
                    s[1]*256 +
                    s[2]*256*256 +
                    s[3]*256*256*256)
        class consumer:
            def __init__(self, bytes):
                self.bytes = bytes
                self.pos = 0
            def __call__(self, n):
                result = self.bytes[self.pos:self.pos+n]
                self.pos += n
                return result

        consume = consumer(bytes)
        mark = consume(2)
        if mark != b"\200\1":
            raise FontFormatError
        data1 = consume(pfblength(consume(4))).decode("ascii", errors="surrogateescape")
        mark = consume(2)
        if mark != b"\200\2":
            raise FontFormatError
        data2eexec = b""
        while mark == b"\200\2":
            data2eexec = data2eexec + consume(pfblength(consume(4)))
            mark = consume(2)
        if mark != b"\200\1":
            raise FontFormatError
        data3 = consume(pfblength(consume(4))).decode("ascii", errors="surrogateescape")
        mark = consume(2)
        if mark != b"\200\3":
            raise FontFormatError
        if consume(1):
            raise FontFormatError

        return cls(data1, data2eexec, data3)

    @classmethod
    def from_PFB_filename(cls, filename):
        """create a T1File instance from PFB font file of given name"""
        with open(filename, "rb") as file:
            t1file = cls.from_PFB_bytes(file.read())
        return t1file

    @classmethod
    def from_PF_bytes(cls, bytes):
        try:
            return cls.from_PFB_bytes(bytes)
        except FontFormatError:
            return cls.from_PFA_bytes(bytes)

    @classmethod
    def from_PF_filename(cls, filename):
        """create a T1File instance from PFA or PFB font file of given name"""
        with open(filename, "rb") as file:
            t1file = cls.from_PF_bytes(file.read())
        return t1file
