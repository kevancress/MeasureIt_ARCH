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

from pyx import reader

_VF_LONG_CHAR  = 242   # character packet (long version)
_VF_FNTDEF1234 = 243   # font definition
_VF_PRE        = 247   # preamble
_VF_POST       = 248   # postamble
_VF_ID         = 202   # VF id byte

class VFError(Exception): pass

class vffile:

    def __init__(self, file, scale, tfmconv, pyxconv, debug=0):
        self.scale = scale
        self.tfmconv = tfmconv
        self.pyxconv = pyxconv
        self.debug = debug
        self.fonts = {}            # used fonts
        self.widths = {}           # widths of defined chars
        self.chardefs = {}         # dvi chunks for defined chars

        afile = reader.bytesreader(file.read())

        cmd = afile.readuchar()
        if cmd == _VF_PRE:
            if afile.readuchar() != _VF_ID: raise VFError
            comment = afile.read(afile.readuchar())
            self.cs = afile.readuint32()
            self.ds = afile.readuint32()
        else:
            raise VFError

        while True:
            cmd = afile.readuchar()
            if cmd >= _VF_FNTDEF1234 and cmd < _VF_FNTDEF1234 + 4:
                # font definition
                if cmd == _VF_FNTDEF1234:
                    num = afile.readuchar()
                elif cmd == _VF_FNTDEF1234+1:
                    num = afile.readuint16()
                elif cmd == _VF_FNTDEF1234+2:
                    num = afile.readuint24()
                elif cmd == _VF_FNTDEF1234+3:
                    num = afile.readint32()
                c = afile.readint32()
                s = afile.readint32()     # relative scaling used for font (fix_word)
                d = afile.readint32()     # design size of font
                fontname = afile.read(afile.readuchar() + afile.readuchar()).decode("ascii")

                # rescaled size of font: s is relative to the scaling
                # of the virtual font itself.  Note that realscale has
                # to be a fix_word (like s)
                # XXX: check rounding
                reals = int(round(self.scale * (16*self.ds/16777216) * s))

                # print ("defining font %s -- VF scale: %g, VF design size: %d, relative font size: %d => real size: %d" %
                #        (fontname, self.scale, self.ds, s, reals)
                #        )

                from pyx import config
                from . import texfont
                try:
                    with config.open(fontname, [config.format.vf]) as fontfile:
                        self.fonts[num] = texfont.virtualfont(fontname, fontfile, c, reals, d, self.tfmconv, self.pyxconv, self.debug>1)
                except EnvironmentError:
                    self.fonts[num] = texfont.TeXfont(fontname, c, reals, d, self.tfmconv, self.pyxconv, self.debug>1)
            elif cmd == _VF_LONG_CHAR:
                # character packet (long form)
                pl = afile.readuint32()   # packet length
                cc = afile.readuint32()   # char code (assumed unsigned, but anyhow only 0 <= cc < 255 is actually used)
                tfm = afile.readuint24()  # character width
                dvi = afile.read(pl)      # dvi code of character
                self.widths[cc] = tfm
                self.chardefs[cc] = dvi
            elif cmd < _VF_LONG_CHAR:
                # character packet (short form)
                cc = afile.readuchar()    # char code
                tfm = afile.readuint24()  # character width
                dvi = afile.read(cmd)
                self.widths[cc] = tfm
                self.chardefs[cc] = dvi
            elif cmd == _VF_POST:
                break
            else:
                raise VFError

    def getfonts(self):
        return self.fonts

    def getchar(self, cc):
        return self.chardefs[cc]

