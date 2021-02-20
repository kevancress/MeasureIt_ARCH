# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2002-2011 Jörg Lehmann <joerg@pyx-project.org>
# Copyright (C) 2003-2004,2006,2007 Michael Schindler <m-schindler@users.sourceforge.net>
# Copyright (C) 2002-2011 André Wobst <wobsta@pyx-project.org>
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

import io, logging, math, re, string, struct, sys
from pyx import  bbox, canvas, color, epsfile, config, path, reader, trafo, unit
from . import texfont, tfmfile

logger = logging.getLogger("pyx")


_DVI_CHARMIN     =   0 # typeset a character and move right (range min)
_DVI_CHARMAX     = 127 # typeset a character and move right (range max)
_DVI_SET1234     = 128 # typeset a character and move right
_DVI_SETRULE     = 132 # typeset a rule and move right
_DVI_PUT1234     = 133 # typeset a character
_DVI_PUTRULE     = 137 # typeset a rule
_DVI_NOP         = 138 # no operation
_DVI_BOP         = 139 # beginning of page
_DVI_EOP         = 140 # ending of page
_DVI_PUSH        = 141 # save the current positions (h, v, w, x, y, z)
_DVI_POP         = 142 # restore positions (h, v, w, x, y, z)
_DVI_RIGHT1234   = 143 # move right
_DVI_W0          = 147 # move right by w
_DVI_W1234       = 148 # move right and set w
_DVI_X0          = 152 # move right by x
_DVI_X1234       = 153 # move right and set x
_DVI_DOWN1234    = 157 # move down
_DVI_Y0          = 161 # move down by y
_DVI_Y1234       = 162 # move down and set y
_DVI_Z0          = 166 # move down by z
_DVI_Z1234       = 167 # move down and set z
_DVI_FNTNUMMIN   = 171 # set current font (range min)
_DVI_FNTNUMMAX   = 234 # set current font (range max)
_DVI_FNT1234     = 235 # set current font
_DVI_SPECIAL1234 = 239 # special (dvi extention)
_DVI_FNTDEF1234  = 243 # define the meaning of a font number
_DVI_PRE         = 247 # preamble
_DVI_POST        = 248 # postamble beginning
_DVI_POSTPOST    = 249 # postamble ending

_DVI_VERSION     = 2   # dvi version

# position variable indices
_POS_H           = 0
_POS_V           = 1
_POS_W           = 2
_POS_X           = 3
_POS_Y           = 4
_POS_Z           = 5

# reader states
_READ_PRE       = 1
_READ_NOPAGE    = 2
_READ_PAGE      = 3
_READ_POST      = 4 # XXX not used
_READ_POSTPOST  = 5 # XXX not used
_READ_DONE      = 6


class DVIError(Exception): pass


class DVIfile:

    def __init__(self, filename, debug=0, debugfile=sys.stdout):
        """ opens the dvi file and reads the preamble """
        self.filename = filename
        self.debug = debug
        self.debugfile = debugfile
        self.debugstack = []

        self.fonts = {}
        self.activefont = None

        # stack of fonts and fontscale currently used (used for VFs)
        self.fontstack = []
        self.stack = []

        # pointer to currently active page
        self.actpage = None

        # stack for self.file, self.fonts and self.stack, needed for VF inclusion
        self.statestack = []

        self.file = reader.reader(self.filename)

        # currently read byte in file (for debugging output)
        self.filepos = None

        self._read_pre()

    # helper routines

    def beginsubpage(self, attrs):
        c = canvas.canvas(attrs)
        c.parent = self.actpage
        c.markers = {}
        self.actpage.insert(c)
        self.actpage = c

    def endsubpage(self):
        for key, value in list(self.actpage.markers.items()):
            self.actpage.parent.markers[key] = self.actpage.trafo.apply(*value)
        self.actpage = self.actpage.parent

    def flushtext(self, fontmap):
        """ finish currently active text object """
        if self.activetext:
            x, y, charcodes = self.activetext
            x_pt, y_pt = x * self.pyxconv, -y*self.pyxconv
            self.actpage.insert(self.activefont.text_pt(x_pt, y_pt, charcodes, fontmap=fontmap))
            if self.debug:
                self.debugfile.write("[%s]\n" % "".join([chr(char) for char in self.activetext[2]]))
            self.activetext = None

    def putrule(self, height, width, advancepos, fontmap):
        self.flushtext(fontmap)
        x1 =  self.pos[_POS_H] * self.pyxconv
        y1 = -self.pos[_POS_V] * self.pyxconv
        w = width * self.pyxconv
        h = height * self.pyxconv

        if height > 0 and width > 0:
            if self.debug:
                self.debugfile.write("%d: %srule height %d, width %d (???x??? pixels)\n" %
                                     (self.filepos, advancepos and "set" or "put", height, width))
            self.actpage.fill(path.rect_pt(x1, y1, w, h))
        else:
            if self.debug:
                self.debugfile.write("%d: %srule height %d, width %d (invisible)\n" %
                                     (self.filepos, advancepos and "set" or "put", height, width))

        if advancepos:
            if self.debug:
                self.debugfile.write(" h:=%d+%d=%d, hh:=???\n" %
                                     (self.pos[_POS_H], width, self.pos[_POS_H]+width))
            self.pos[_POS_H] += width * self.scale

    def putchar(self, char, advancepos, id1234, fontmap):
        dx = advancepos and self.activefont.getwidth_dvi(char) or 0

        if self.debug:
            self.debugfile.write("%d: %s%s%d h:=%d+%d=%d, hh:=???\n" %
                                 (self.filepos,
                                  advancepos and "set" or "put",
                                  id1234 and "%i " % id1234 or "char",
                                  char,
                                  self.pos[_POS_H], dx, self.pos[_POS_H]+dx))

        if isinstance(self.activefont, texfont.virtualfont):
            # virtual font handling
            afterpos = list(self.pos)
            afterpos[_POS_H] += dx
            self._push_dvistring(self.activefont.getchar(char), self.activefont.getfonts(), afterpos,
                                 self.activefont.getsize_pt(), fontmap)
        else:
            if self.activetext is None:
                self.activetext = (self.pos[_POS_H], self.pos[_POS_V], [])
            self.activetext[2].append(char)
            self.pos[_POS_H] += dx

        if (not advancepos) or self.singlecharmode:
            self.flushtext(fontmap)

    def usefont(self, fontnum, id1234, fontmap):
        self.flushtext(fontmap)
        self.activefont = self.fonts[fontnum]
        if self.debug:
            self.debugfile.write("%d: fnt%s%i current font is %s\n" %
                                 (self.filepos,
                                  id1234 and "%i " % id1234 or "num",
                                  fontnum,
                                  self.fonts[fontnum].name))


    def definefont(self, cmdnr, num, c, q, d, fontname):
        # cmdnr: type of fontdef command (only used for debugging output)
        # c:     checksum
        # q:     scaling factor (fix_word)
        #        Note that q is actually s in large parts of the documentation.
        # d:     design size (fix_word)

        # check whether it's a virtual font by trying to open it. if this fails, it is an ordinary TeX font
        try:
            with config.open(fontname, [config.format.vf]) as fontfile:
                afont = texfont.virtualfont(fontname, fontfile, c, q/self.tfmconv, d/self.tfmconv, self.tfmconv, self.pyxconv, self.debug>1)
        except EnvironmentError:
            afont = texfont.TeXfont(fontname, c, q/self.tfmconv, d/self.tfmconv, self.tfmconv, self.pyxconv, self.debug>1)

        self.fonts[num] = afont

        if self.debug:
            self.debugfile.write("%d: fntdef%d %i: %s\n" % (self.filepos, cmdnr, num, fontname))

#            scale = round((1000.0*self.conv*q)/(self.trueconv*d))
#            m = 1.0*q/d
#            scalestring = scale!=1000 and " scaled %d" % scale or ""
#            print ("Font %i: %s%s---loaded at size %d DVI units" %
#                   (num, fontname, scalestring, q))
#            if scale!=1000:
#                print " (this font is magnified %d%%)" % round(scale/10)

    def special(self, s, fontmap):
        x =  self.pos[_POS_H] * self.pyxconv
        y = -self.pos[_POS_V] * self.pyxconv
        if self.debug:
            self.debugfile.write("%d: xxx '%s'\n" % (self.filepos, s))
        if not s.startswith("PyX:"):
            logger.warning("ignoring special '%s'" % s)
            return

        # it is in general not safe to continue using the currently active font because
        # the specials may involve some gsave/grestore operations
        self.flushtext(fontmap)

        command, args = s[4:].split()[0], s[4:].split()[1:]
        if command == "color_begin":
            if args[0] == "cmyk":
                c = color.cmyk(float(args[1]), float(args[2]), float(args[3]), float(args[4]))
            elif args[0] == "gray":
                c = color.gray(float(args[1]))
            elif args[0] == "hsb":
                c = color.hsb(float(args[1]), float(args[2]), float(args[3]))
            elif args[0] == "rgb":
                c = color.rgb(float(args[1]), float(args[2]), float(args[3]))
            elif args[0] == "RGB":
                c = color.rgb(int(args[1])/255.0, int(args[2])/255.0, int(args[3])/255.0)
            elif args[0] == "texnamed":
                try:
                    c = getattr(color.cmyk, args[1])
                except AttributeError:
                    raise RuntimeError("unknown TeX color '%s', aborting" % args[1])
            elif args[0] == "pyxcolor":
                # pyx.color.cmyk.PineGreen or
                # pyx.color.cmyk(0,0,0,0.0)
                pat = re.compile(r"(pyx\.)?(color\.)?(?P<model>(cmyk)|(rgb)|(grey)|(gray)|(hsb))[\.]?(?P<arg>.*)")
                sd = pat.match(" ".join(args[1:]))
                if sd:
                    sd = sd.groupdict()
                    if sd["arg"][0] == "(":
                        numpat = re.compile(r"[+-]?((\d+\.\d*)|(\d*\.\d+)|(\d+))([eE][+-]\d+)?")
                        arg = tuple([float(x[0]) for x in numpat.findall(sd["arg"])])
                        try:
                            c = getattr(color, sd["model"])(*arg)
                        except TypeError or AttributeError:
                            raise RuntimeError("cannot access PyX color '%s' in TeX, aborting" % " ".join(args[1:]))
                    else:
                        try:
                            c = getattr(getattr(color, sd["model"]), sd["arg"])
                        except AttributeError:
                            raise RuntimeError("cannot access PyX color '%s' in TeX, aborting" % " ".join(args[1:]))
                else:
                    raise RuntimeError("cannot access PyX color '%s' in TeX, aborting" % " ".join(args[1:]))
            else:
                raise RuntimeError("color model '%s' cannot be handled by PyX, aborting" % args[0])

            self.beginsubpage([c])
        elif command == "color_end":
            self.endsubpage()
        elif command == "rotate_begin":
            self.beginsubpage([trafo.rotate_pt(float(args[0]), x, y)])
        elif command == "rotate_end":
            self.endsubpage()
        elif command == "scale_begin":
            self.beginsubpage([trafo.scale_pt(float(args[0]), float(args[1]), x, y)])
        elif command == "scale_end":
            self.endsubpage()
        elif command == "epsinclude":
            # parse arguments
            argdict = {}
            for arg in args:
                name, value = arg.split("=")
                argdict[name] = value

            # construct kwargs for epsfile constructor
            epskwargs = {}
            epskwargs["filename"] = argdict["file"]
            epskwargs["bbox"] = bbox.bbox_pt(float(argdict["llx"]), float(argdict["lly"]),
                                           float(argdict["urx"]), float(argdict["ury"]))
            if "width" in argdict:
                epskwargs["width"] = float(argdict["width"]) * unit.t_pt
            if "height" in argdict:
                epskwargs["height"] = float(argdict["height"]) * unit.t_pt
            if "clip" in argdict:
               epskwargs["clip"] = int(argdict["clip"])
            self.actpage.insert(epsfile.epsfile(x * unit.t_pt, y * unit.t_pt, **epskwargs))
        elif command == "marker":
            if len(args) != 1:
                raise RuntimeError("marker contains spaces")
            for c in args[0]:
                if c not in string.ascii_letters + string.digits + "@":
                    raise RuntimeError("marker contains invalid characters")
            if args[0] in self.actpage.markers:
                raise RuntimeError("marker name occurred several times")
            self.actpage.markers[args[0]] = x * unit.t_pt, y * unit.t_pt
        else:
            raise RuntimeError("unknown PyX special '%s', aborting" % command)

    # routines for pushing and popping different dvi chunks on the reader

    def _push_dvistring(self, dvi, fonts, afterpos, fontsize, fontmap):
        """ push dvi string with defined fonts on top of reader
        stack. Every positions gets scaled relatively by the factor
        scale. After interpretating the dvi chunk, continue with self.pos=afterpos.
        The designsize of the virtual font is passed as a fix_word

        """

        #if self.debug:
        #    self.debugfile.write("executing new dvi chunk\n")
        self.debugstack.append(self.debug)
        self.debug = 0

        self.statestack.append((self.file, self.fonts, self.activefont, afterpos, self.stack, self.scale))

        # units in vf files are relative to the size of the font and given as fix_words
        # which can be converted to floats by diving by 2**20.
        # This yields the following scale factor for the height and width of rects:
        self.scale = fontsize/2**20/self.pyxconv

        self.file = reader.bytesreader(dvi)
        self.fonts = fonts
        self.stack = []
        self.filepos = 0

        self.usefont(0, 0, fontmap)

    def _pop_dvistring(self, fontmap):
        self.flushtext(fontmap)
        #if self.debug:
        #    self.debugfile.write("finished executing dvi chunk\n")
        self.debug = self.debugstack.pop()

        self.file.close()
        self.file, self.fonts, self.activefont, self.pos, self.stack, self.scale = self.statestack.pop()

    # routines corresponding to the different reader states of the dvi maschine

    def _read_pre(self):
        afile = self.file
        while True:
            self.filepos = afile.tell()
            cmd = afile.readuchar()
            if cmd == _DVI_NOP:
                pass
            elif cmd == _DVI_PRE:
                if afile.readuchar() != _DVI_VERSION: raise DVIError
                num = afile.readuint32()
                den = afile.readuint32()
                self.mag = afile.readuint32()

                # For the interpretation of the lengths in dvi and tfm files, 
                # three conversion factors are relevant:
                # - self.tfmconv: tfm units -> dvi units
                # - self.pyxconv: dvi units -> (PostScript) points
                # - self.conv:    dvi units -> pixels
                self.tfmconv = (25400000.0/num)*(den/473628672.0)/16.0

                # calculate conv as described in the DVIType docu using 
                # a given resolution in dpi
                self.resolution = 300.0
                self.conv = (num/254000.0)*(self.resolution/den)

                # self.pyxconv is the conversion factor from the dvi units
                # to (PostScript) points. It consists of
                # - self.mag/1000.0:   magstep scaling
                # - self.conv:         conversion from dvi units to pixels
                # - 1/self.resolution: conversion from pixels to inch
                # - 72               : conversion from inch to points
                self.pyxconv = self.mag/1000.0*self.conv/self.resolution*72

                # scaling used for rules when VF chunks are interpreted
                self.scale = 1

                comment = afile.read(afile.readuchar())
                return
            else:
                raise DVIError

    def readpage(self, pageid=None, fontmap=None, singlecharmode=False, attrs=[]):
        """ reads a page from the dvi file

        This routine reads a page from the dvi file which is
        returned as a canvas. When there is no page left in the
        dvifile, None is returned and the file is closed properly."""

        self.singlecharmode = singlecharmode

        while True:
            self.filepos = self.file.tell()
            cmd = self.file.readuchar()
            if cmd == _DVI_NOP:
                pass
            elif cmd == _DVI_BOP:
                ispageid = [self.file.readuint32() for i in range(10)]
                if pageid is not None and ispageid != pageid:
                    raise DVIError("invalid pageid")
                if self.debug:
                    self.debugfile.write("%d: beginning of page %i\n" % (self.filepos, ispageid[0]))
                self.file.readuint32()
                break
            elif cmd == _DVI_POST:
                self.file.close()
                return None # nothing left
            else:
                raise DVIError

        self.actpage = canvas.canvas(attrs)
        self.actpage.markers = {}
        self.pos = [0, 0, 0, 0, 0, 0]

        # tuple (hpos, vpos, codepoints) to be output, or None if no output is pending
        self.activetext = None

        while True:
            afile = self.file
            self.filepos = afile.tell()
            try:
                cmd = afile.readuchar()
            except struct.error:
                # we most probably (if the dvi file is not corrupt) hit the end of a dvi chunk,
                # so we have to continue with the rest of the dvi file
                self._pop_dvistring(fontmap)
                continue
            if cmd == _DVI_NOP:
                pass
            if cmd >= _DVI_CHARMIN and cmd <= _DVI_CHARMAX:
                self.putchar(cmd, True, 0, fontmap)
            elif cmd >= _DVI_SET1234 and cmd < _DVI_SET1234 + 4:
                self.putchar(afile.readint(cmd - _DVI_SET1234 + 1), True, cmd-_DVI_SET1234+1, fontmap)
            elif cmd == _DVI_SETRULE:
                self.putrule(afile.readint32()*self.scale, afile.readint32()*self.scale, True, fontmap)
            elif cmd >= _DVI_PUT1234 and cmd < _DVI_PUT1234 + 4:
                self.putchar(afile.readint(cmd - _DVI_PUT1234 + 1), False, cmd-_DVI_SET1234+1, fontmap)
            elif cmd == _DVI_PUTRULE:
                self.putrule(afile.readint32()*self.scale, afile.readint32()*self.scale, False, fontmap)
            elif cmd == _DVI_EOP:
                self.flushtext(fontmap)
                if self.debug:
                    self.debugfile.write("%d: eop\n \n" % self.filepos)
                return self.actpage
            elif cmd == _DVI_PUSH:
                self.stack.append(list(self.pos))
                if self.debug:
                    self.debugfile.write("%s: push\n"
                                         "level %d:(h=%d,v=%d,w=%d,x=%d,y=%d,z=%d,hh=???,vv=???)\n" %
                                         ((self.filepos, len(self.stack)-1) + tuple(self.pos)))
            elif cmd == _DVI_POP:
                self.flushtext(fontmap)
                self.pos = self.stack.pop()
                if self.debug:
                    self.debugfile.write("%s: pop\n"
                                         "level %d:(h=%d,v=%d,w=%d,x=%d,y=%d,z=%d,hh=???,vv=???)\n" %
                                         ((self.filepos, len(self.stack)) + tuple(self.pos)))
            elif cmd >= _DVI_RIGHT1234 and cmd < _DVI_RIGHT1234 + 4:
                self.flushtext(fontmap)
                dh = afile.readint(cmd - _DVI_RIGHT1234 + 1, 1) * self.scale
                if self.debug:
                    self.debugfile.write("%d: right%d %d h:=%d%+d=%d, hh:=???\n" %
                                         (self.filepos,
                                          cmd - _DVI_RIGHT1234 + 1,
                                          dh,
                                          self.pos[_POS_H],
                                          dh,
                                          self.pos[_POS_H]+dh))
                self.pos[_POS_H] += dh
            elif cmd == _DVI_W0:
                self.flushtext(fontmap)
                if self.debug:
                    self.debugfile.write("%d: w0 %d h:=%d%+d=%d, hh:=???\n" %
                                         (self.filepos,
                                          self.pos[_POS_W],
                                          self.pos[_POS_H],
                                          self.pos[_POS_W],
                                          self.pos[_POS_H]+self.pos[_POS_W]))
                self.pos[_POS_H] += self.pos[_POS_W]
            elif cmd >= _DVI_W1234 and cmd < _DVI_W1234 + 4:
                self.flushtext(fontmap)
                self.pos[_POS_W] = afile.readint(cmd - _DVI_W1234 + 1, 1) * self.scale
                if self.debug:
                    self.debugfile.write("%d: w%d %d h:=%d%+d=%d, hh:=???\n" %
                                         (self.filepos,
                                          cmd - _DVI_W1234 + 1,
                                          self.pos[_POS_W],
                                          self.pos[_POS_H],
                                          self.pos[_POS_W],
                                          self.pos[_POS_H]+self.pos[_POS_W]))
                self.pos[_POS_H] += self.pos[_POS_W]
            elif cmd == _DVI_X0:
                self.flushtext(fontmap)
                if self.debug:
                    self.debugfile.write("%d: x0 %d h:=%d%+d=%d, hh:=???\n" %
                                         (self.filepos,
                                          self.pos[_POS_X],
                                          self.pos[_POS_H],
                                          self.pos[_POS_X],
                                          self.pos[_POS_H]+self.pos[_POS_X]))
                self.pos[_POS_H] += self.pos[_POS_X]
            elif cmd >= _DVI_X1234 and cmd < _DVI_X1234 + 4:
                self.flushtext(fontmap)
                self.pos[_POS_X] = afile.readint(cmd - _DVI_X1234 + 1, 1) * self.scale
                if self.debug:
                    self.debugfile.write("%d: x%d %d h:=%d%+d=%d, hh:=???\n" %
                                         (self.filepos,
                                          cmd - _DVI_X1234 + 1,
                                          self.pos[_POS_X],
                                          self.pos[_POS_H],
                                          self.pos[_POS_X],
                                          self.pos[_POS_H]+self.pos[_POS_X]))
                self.pos[_POS_H] += self.pos[_POS_X]
            elif cmd >= _DVI_DOWN1234 and cmd < _DVI_DOWN1234 + 4:
                self.flushtext(fontmap)
                dv = afile.readint(cmd - _DVI_DOWN1234 + 1, 1) * self.scale
                if self.debug:
                    self.debugfile.write("%d: down%d %d v:=%d%+d=%d, vv:=???\n" %
                                         (self.filepos,
                                          cmd - _DVI_DOWN1234 + 1,
                                          dv,
                                          self.pos[_POS_V],
                                          dv,
                                          self.pos[_POS_V]+dv))
                self.pos[_POS_V] += dv
            elif cmd == _DVI_Y0:
                self.flushtext(fontmap)
                if self.debug:
                    self.debugfile.write("%d: y0 %d v:=%d%+d=%d, vv:=???\n" %
                                         (self.filepos,
                                          self.pos[_POS_Y],
                                          self.pos[_POS_V],
                                          self.pos[_POS_Y],
                                          self.pos[_POS_V]+self.pos[_POS_Y]))
                self.pos[_POS_V] += self.pos[_POS_Y]
            elif cmd >= _DVI_Y1234 and cmd < _DVI_Y1234 + 4:
                self.flushtext(fontmap)
                self.pos[_POS_Y] = afile.readint(cmd - _DVI_Y1234 + 1, 1) * self.scale
                if self.debug:
                    self.debugfile.write("%d: y%d %d v:=%d%+d=%d, vv:=???\n" %
                                         (self.filepos,
                                          cmd - _DVI_Y1234 + 1,
                                          self.pos[_POS_Y],
                                          self.pos[_POS_V],
                                          self.pos[_POS_Y],
                                          self.pos[_POS_V]+self.pos[_POS_Y]))
                self.pos[_POS_V] += self.pos[_POS_Y]
            elif cmd == _DVI_Z0:
                self.flushtext(fontmap)
                if self.debug:
                    self.debugfile.write("%d: z0 %d v:=%d%+d=%d, vv:=???\n" %
                                         (self.filepos,
                                          self.pos[_POS_Z],
                                          self.pos[_POS_V],
                                          self.pos[_POS_Z],
                                          self.pos[_POS_V]+self.pos[_POS_Z]))
                self.pos[_POS_V] += self.pos[_POS_Z]
            elif cmd >= _DVI_Z1234 and cmd < _DVI_Z1234 + 4:
                self.flushtext(fontmap)
                self.pos[_POS_Z] = afile.readint(cmd - _DVI_Z1234 + 1, 1) * self.scale
                if self.debug:
                    self.debugfile.write("%d: z%d %d v:=%d%+d=%d, vv:=???\n" %
                                         (self.filepos,
                                          cmd - _DVI_Z1234 + 1,
                                          self.pos[_POS_Z],
                                          self.pos[_POS_V],
                                          self.pos[_POS_Z],
                                          self.pos[_POS_V]+self.pos[_POS_Z]))
                self.pos[_POS_V] += self.pos[_POS_Z]
            elif cmd >= _DVI_FNTNUMMIN and cmd <= _DVI_FNTNUMMAX:
                self.usefont(cmd - _DVI_FNTNUMMIN, 0, fontmap)
            elif cmd >= _DVI_FNT1234 and cmd < _DVI_FNT1234 + 4:
                # note that according to the DVI docs, for four byte font numbers,
                # the font number is signed. Don't ask why!
                fntnum = afile.readint(cmd - _DVI_FNT1234 + 1, cmd == _DVI_FNT1234 + 3)
                self.usefont(fntnum, cmd-_DVI_FNT1234+1, fontmap)
            elif cmd >= _DVI_SPECIAL1234 and cmd < _DVI_SPECIAL1234 + 4:
                self.special(afile.read(afile.readint(cmd - _DVI_SPECIAL1234 + 1)).decode("ascii"), fontmap)
            elif cmd >= _DVI_FNTDEF1234 and cmd < _DVI_FNTDEF1234 + 4:
                if cmd == _DVI_FNTDEF1234:
                    num = afile.readuchar()
                elif cmd == _DVI_FNTDEF1234+1:
                    num = afile.readuint16()
                elif cmd == _DVI_FNTDEF1234+2:
                    num = afile.readuint24()
                elif cmd == _DVI_FNTDEF1234+3:
                    # Cool, here we have according to docu a signed int. Why?
                    num = afile.readint32()
                self.definefont(cmd-_DVI_FNTDEF1234+1,
                                num,
                                afile.readint32(),
                                afile.readint32(),
                                afile.readint32(),
                                afile.read(afile.readuchar()+afile.readuchar()).decode("ascii"))
            else:
                raise DVIError
