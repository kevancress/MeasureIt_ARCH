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

import io, logging, os.path, re
from pyx import font, config
from pyx.font import t1file, afmfile, pfmfile
from pyx.dvi import encfile

logger = logging.getLogger("pyx")

class UnsupportedFontFormat(Exception):
    pass

class UnsupportedPSFragment(Exception):
    pass

class ParseError(Exception):
    pass

_marker = object()

class MAPline:

    tokenpattern = re.compile(r'"(.*?)("\s+|"$|$)|(.*?)(\s+|$)')

    def __init__(self, s):
        """ construct font mapping from line s of font mapping file """
        self.texname = self.basepsname = self.fontfilename = None

        # standard encoding
        self.encodingfilename = None

        # supported postscript fragments occuring in psfonts.map
        # XXX extendfont not yet implemented
        self.reencodefont = self.extendfont = self.slant = None

        # cache for openend font and encoding
        self._font = None
        self._encoding = _marker

        tokens = []
        while len(s):
            match = self.tokenpattern.match(s)
            if match:
                if match.groups()[0] is not None:
                    tokens.append('"%s"' % match.groups()[0])
                else:
                    tokens.append(match.groups()[2])
                s = s[match.end():]
            else:
                raise ParseError("Cannot tokenize string '%s'" % s)

        next_token_is_encfile = False
        for token in tokens:
            if next_token_is_encfile:
                self.encodingfilename = token
                next_token_is_encfile = False
            elif token.startswith("<"):
                if token == "<":
                    next_token_is_encfile = True
                elif token.startswith("<<"):
                    # XXX: support non-partial download here
                    self.fontfilename = token[2:]
                elif token.startswith("<["):
                    self.encodingfilename = token[2:]
                elif token.endswith(".pfa") or token.endswith(".pfb"):
                    self.fontfilename = token[1:]
                elif token.endswith(".enc"):
                    self.encodingfilename = token[1:]
                elif token.endswith(".ttf"):
                    raise UnsupportedFontFormat("TrueType font")
                elif token.endswith(".t42"):
                    raise UnsupportedFontFormat("Type 42 font")
                else:
                    # Assume (as in pdftex's mapfile.c) that we are dealing with a Type 1 font.
                    # Note that this case has in particular appeared with the MinLibertine fonts,
                    # for which this heuristics seems to work well.
                    self.fontfilename = token[1:]
            elif token.startswith('"'):
                pscode = token[1:-1].split()
                # parse standard postscript code fragments
                while pscode:
                    try:
                        arg, cmd = pscode[:2]
                    except:
                        raise UnsupportedPSFragment("Unsupported Postscript fragment '%s'" % pscode)
                    pscode = pscode[2:]
                    if cmd == "ReEncodeFont":
                        self.reencodefont = arg
                    elif cmd == "ExtendFont":
                        self.extendfont = arg
                    elif cmd == "SlantFont":
                        self.slant = float(arg)
                    else:
                        raise UnsupportedPSFragment("Unsupported Postscript fragment '%s %s'" % (arg, cmd))
            else:
                if self.texname is None:
                    self.texname = token
                else:
                    self.basepsname = token
        if self.basepsname is None:
            self.basepsname = self.texname

    def getfontname(self):
        return self.basepsname

    def getfont(self):
        if self._font is None:
            if self.fontfilename is not None:
                with config.open(self.fontfilename, [config.format.type1]) as fontfile:
                    t1font = t1file.T1File.from_PF_bytes(fontfile.read())
                assert self.basepsname == t1font.name, "corrupt MAP file"
                try:
                    with config.open(os.path.splitext(self.fontfilename)[0], [config.format.afm], ascii=True) as metricfile:
                        self._font = font.T1font(t1font, afmfile.AFMfile(metricfile))
                except EnvironmentError:
                    try:
                        # fallback by using the pfm instead of the afm font metric
                        # (in all major TeX distributions there is no pfm file format defined by kpsewhich, but
                        # we can use the type1 format and search for the file including the expected suffix)
                        with config.open("%s.pfm" % os.path.splitext(self.fontfilename)[0], [config.format.type1]) as metricfile:
                            self._font = font.T1font(t1font, pfmfile.PFMfile(metricfile, t1font))
                    except EnvironmentError:
                        # we need to continue without any metric file
                        self._font = font.T1font(t1font)
            else:
                # builtin font
                with config.open(self.basepsname, [config.format.afm], ascii=True) as metricfile:
                    self._font = font.T1builtinfont(self.basepsname, afmfile.AFMfile(metricfile))
        return self._font

    def getencoding(self):
        if self._encoding is _marker:
            if self.encodingfilename is not None:
                with config.open(self.encodingfilename, [config.format.tex_ps_header]) as encodingfile:
                    ef = encfile.ENCfile(encodingfile.read().decode("ascii", errors="surrogateescape"))
                assert ef.name == "/%s" % self.reencodefont
                self._encoding = ef.vector

            else:
                self._encoding = None
        return self._encoding

    def __str__(self):
        return ("'%s' is '%s' read from '%s' encoded as '%s'" %
                (self.texname, self.basepsname, self.fontfile, repr(self.encodingfile)))

# generate fontmap

def readfontmap(filenames):
    """ read font map from filename (without path) """
    fontmap = {}
    for filename in filenames:
        with config.open(filename, [config.format.fontmap, config.format.dvips_config], ascii=True) as mapfile:
            lineno = 0
            for line in mapfile.readlines():
                lineno += 1
                line = line.rstrip()
                if not (line=="" or line[0] in (" ", "%", "*", ";" , "#")):
                    try:
                        fm = MAPline(line)
                    except (ParseError, UnsupportedPSFragment) as e:
                        logger.warning("Ignoring line %i in mapping file '%s': %s" % (lineno, filename, e))
                    except UnsupportedFontFormat as e:
                        pass
                    else:
                        fontmap[fm.texname] = fm
    return fontmap
