# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2002-2004, 2006, 2013 Jörg Lehmann <joerg@pyx-project.org>
# Copyright (C) 2003-2006 Michael Schindler <m-schindler@users.sourceforge.net>
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

import binascii, colorsys, logging, math, struct
from . import attr, style, pdfwriter

logger = logging.getLogger("pyx")

# device-dependent (nonlinear) functions for color conversion
# UCRx : [0,1] -> [-1, 1] UnderColorRemoval (removes black from c, y, m)
# BG   : [0,1] -> [0, 1]  BlackGeneration (generate the black from the nominal k-value)
# as long as we have no further knowledge we define them linearly with constants 1
def _UCRc(x): return x
def _UCRm(x): return x
def _UCRy(x): return x
def _BG(x): return x

def set(UCRc=None, UCRm=None, UCRy=None, BG=None):
    global _UCRc
    global _UCRm
    global _UCRy
    global _BG

    if UCRc is not None:
        _UCRc = UCRc
    if UCRm is not None:
        _UCRm = UCRm
    if UCRy is not None:
        _UCRy = UCRy
    if BG is not None:
        _BG = BG


class color(attr.exclusiveattr, style.strokestyle, style.fillstyle):
    """base class for all colors"""
    def __init__(self):
        super().__init__(color)

    def processSVGattrs(self, attrs, writer, context, registry):
        if context.strokeattr:
            context.strokecolor = self.rgb().tohexstring()
        if context.fillattr:
            context.fillcolor = self.rgb().tohexstring()


clear = attr.clearclass(color)


class gray(color):

    """grey tones"""

    def __init__(self, g=0.0):
        super().__init__()
        if g<0 or g>1:
            raise ValueError("Value g out of range [0,1]")
        self.g = g

    def processPS(self, file, writer, context, registry):
        file.write("%f setgray\n" % self.g)

    def processPDF(self, file, writer, context, registry):
        if context.strokeattr:
            file.write("%f G\n" % self.g)
        if context.fillattr:
            file.write("%f g\n" % self.g)

    def cmyk(self):
        return cmyk(0, 0, 0, 1 - self.g)

    def gray(self):
        return gray(self.g)
    grey = gray

    def hsb(self):
        return hsb(0, 0, self.g)

    def rgb(self):
        return rgb(self.g, self.g, self.g)

    def colorspacestring(self):
        return "/DeviceGray"

    def to8bitbytes(self):
        return bytes((int(self.g*255),))

gray.black = gray(0.0)
gray.white = gray(1.0)
grey = gray


class rgb(color):

    """rgb colors"""

    def __init__(self, r=0.0, g=0.0, b=0.0):
        super().__init__()
        if r<0 or r>1:
            raise ValueError("Value r out of range [0,1]")
        if g<0 or g>1:
            raise ValueError("Value g out of range [0,1]")
        if b<0 or b>1:
            raise ValueError("Value b out of range [0,1]")
        self.r = r
        self.g = g
        self.b = b

    def processPS(self, file, writer, context, registry):
        file.write("%f %f %f setrgbcolor\n" % (self.r, self.g, self.b))

    def processPDF(self, file, writer, context, registry):
        if context.strokeattr:
            file.write("%f %f %f RG\n" % (self.r, self.g, self.b))
        if context.fillattr:
            file.write("%f %f %f rg\n" % (self.r, self.g, self.b))

    def cmyk(self):
        # conversion to cmy
        c, m, y = 1 - self.r, 1 - self.g, 1 - self.b
        # conversion from cmy to cmyk with device-dependent functions
        k = min([c, m, y])
        return cmyk(min(1, max(0, c - _UCRc(k))),
                    min(1, max(0, m - _UCRm(k))),
                    min(1, max(0, y - _UCRy(k))),
                    _BG(k))

    def gray(self):
        return gray(0.3*self.r + 0.59*self.g + 0.11*self.b)
    grey = gray

    def hsb(self):
        h, s, b = colorsys.rgb_to_hsv(self.r, self.g, self.b)
        return hsb(h, s, b)

    def rgb(self):
        return rgb(self.r, self.g, self.b)

    def colorspacestring(self):
        return "/DeviceRGB"

    def to8bitbytes(self):
        return struct.pack("BBB", int(self.r*255), int(self.g*255), int(self.b*255))

    def tohexstring(self, cssstrip=1, addhash=1):
        hexstring = binascii.b2a_hex(self.to8bitbytes()).decode('ascii')
        if cssstrip and hexstring[0] == hexstring[1] and hexstring[2] == hexstring[3] and hexstring[4] == hexstring[5]:
            hexstring = "".join([hexstring[0], hexstring[2], hexstring[4]])
        if addhash:
            hexstring = "#" + hexstring
        return hexstring


def rgbfromhexstring(hexstring):
    hexstring = hexstring.strip().lstrip("#")
    if len(hexstring) == 3:
        hexstring = "".join([hexstring[0], hexstring[0], hexstring[1], hexstring[1], hexstring[2], hexstring[2]])
    elif len(hexstring) != 6:
        raise ValueError("3 or 6 digit hex number expected (with optional leading hash character)")
    return rgb(*[value/255.0 for value in struct.unpack("BBB", binascii.a2b_hex(hexstring))])

rgb.red   = rgb(1, 0, 0)
rgb.green = rgb(0, 1, 0)
rgb.blue  = rgb(0, 0, 1)
rgb.white = rgb(1, 1, 1)
rgb.black = rgb(0, 0, 0)


class hsb(color):

    """hsb colors"""

    def __init__(self, h=0.0, s=0.0, b=0.0):
        super().__init__()
        if h<0 or h>1:
            raise ValueError("Value h out of range [0,1]")
        if s<0 or s>1:
            raise ValueError("Value s out of range [0,1]")
        if b<0 or b>1:
            raise ValueError("Value b out of range [0,1]")
        self.h = h
        self.s = s
        self.b = b

    def processPS(self, file, writer, context, registry):
        file.write("%f %f %f sethsbcolor\n" % (self.h, self.s, self.b))

    def processPDF(self, file, writer, context, registry):
        self.rgb().processPDF(file, writer, context, registry)

    def cmyk(self):
        return self.rgb().cmyk()

    def gray(self):
        return self.rgb().gray()
    grey = gray

    def hsb(self):
        return hsb(self.h, self.s, self.b)

    def rgb(self):
        r, g, b = colorsys.hsv_to_rgb(self.h, self.s, self.b)
        return rgb(r, g, b)

    def colorspacestring(self):
        raise RuntimeError("colorspace string not available for hsb colors")


class cmyk(color):

    """cmyk colors"""

    def __init__(self, c=0.0, m=0.0, y=0.0, k=0.0):
        super().__init__()
        if c<0 or c>1:
            raise ValueError("Value c out of range [0,1]")
        if m<0 or m>1:
            raise ValueError("Value m out of range [0,1]")
        if y<0 or y>1:
            raise ValueError("Value y out of range [0,1]")
        if k<0 or k>1:
            raise ValueError("Value k out of range [0,1]")
        self.c = c
        self.m = m
        self.y = y
        self.k = k

    def processPS(self, file, writer, context, registry):
        file.write("%f %f %f %f setcmykcolor\n" % (self.c, self.m, self.y, self.k))

    def processPDF(self, file, writer, context, registry):
        if context.strokeattr:
            file.write("%f %f %f %f K\n" % (self.c, self.m, self.y, self.k))
        if context.fillattr:
            file.write("%f %f %f %f k\n" % (self.c, self.m, self.y, self.k))

    def cmyk(self):
        return cmyk(self.c, self.m, self.y, self.k)

    def gray(self):
        return gray(1 - min([1, 0.3*self.c + 0.59*self.m + 0.11*self.y + self.k]))
    grey = gray

    def hsb(self):
        return self.rgb().hsb()

    def rgb(self):
        # conversion to cmy:
        c = min(1, self.c + self.k)
        m = min(1, self.m + self.k)
        y = min(1, self.y + self.k)
        # conversion from cmy to rgb:
        return rgb(1 - c, 1 - m, 1 - y)

    def colorspacestring(self):
        return "/DeviceCMYK"

    def to8bitbytes(self):
        return struct.pack("BBBB", int(self.c*255), int(self.m*255), int(self.y*255), int(self.k*255))

cmyk.GreenYellow    = cmyk(0.15, 0, 0.69, 0)
cmyk.Yellow         = cmyk(0, 0, 1, 0)
cmyk.Goldenrod      = cmyk(0, 0.10, 0.84, 0)
cmyk.Dandelion      = cmyk(0, 0.29, 0.84, 0)
cmyk.Apricot        = cmyk(0, 0.32, 0.52, 0)
cmyk.Peach          = cmyk(0, 0.50, 0.70, 0)
cmyk.Melon          = cmyk(0, 0.46, 0.50, 0)
cmyk.YellowOrange   = cmyk(0, 0.42, 1, 0)
cmyk.Orange         = cmyk(0, 0.61, 0.87, 0)
cmyk.BurntOrange    = cmyk(0, 0.51, 1, 0)
cmyk.Bittersweet    = cmyk(0, 0.75, 1, 0.24)
cmyk.RedOrange      = cmyk(0, 0.77, 0.87, 0)
cmyk.Mahogany       = cmyk(0, 0.85, 0.87, 0.35)
cmyk.Maroon         = cmyk(0, 0.87, 0.68, 0.32)
cmyk.BrickRed       = cmyk(0, 0.89, 0.94, 0.28)
cmyk.Red            = cmyk(0, 1, 1, 0)
cmyk.OrangeRed      = cmyk(0, 1, 0.50, 0)
cmyk.RubineRed      = cmyk(0, 1, 0.13, 0)
cmyk.WildStrawberry = cmyk(0, 0.96, 0.39, 0)
cmyk.Salmon         = cmyk(0, 0.53, 0.38, 0)
cmyk.CarnationPink  = cmyk(0, 0.63, 0, 0)
cmyk.Magenta        = cmyk(0, 1, 0, 0)
cmyk.VioletRed      = cmyk(0, 0.81, 0, 0)
cmyk.Rhodamine      = cmyk(0, 0.82, 0, 0)
cmyk.Mulberry       = cmyk(0.34, 0.90, 0, 0.02)
cmyk.RedViolet      = cmyk(0.07, 0.90, 0, 0.34)
cmyk.Fuchsia        = cmyk(0.47, 0.91, 0, 0.08)
cmyk.Lavender       = cmyk(0, 0.48, 0, 0)
cmyk.Thistle        = cmyk(0.12, 0.59, 0, 0)
cmyk.Orchid         = cmyk(0.32, 0.64, 0, 0)
cmyk.DarkOrchid     = cmyk(0.40, 0.80, 0.20, 0)
cmyk.Purple         = cmyk(0.45, 0.86, 0, 0)
cmyk.Plum           = cmyk(0.50, 1, 0, 0)
cmyk.Violet         = cmyk(0.79, 0.88, 0, 0)
cmyk.RoyalPurple    = cmyk(0.75, 0.90, 0, 0)
cmyk.BlueViolet     = cmyk(0.86, 0.91, 0, 0.04)
cmyk.Periwinkle     = cmyk(0.57, 0.55, 0, 0)
cmyk.CadetBlue      = cmyk(0.62, 0.57, 0.23, 0)
cmyk.CornflowerBlue = cmyk(0.65, 0.13, 0, 0)
cmyk.MidnightBlue   = cmyk(0.98, 0.13, 0, 0.43)
cmyk.NavyBlue       = cmyk(0.94, 0.54, 0, 0)
cmyk.RoyalBlue      = cmyk(1, 0.50, 0, 0)
cmyk.Blue           = cmyk(1, 1, 0, 0)
cmyk.Cerulean       = cmyk(0.94, 0.11, 0, 0)
cmyk.Cyan           = cmyk(1, 0, 0, 0)
cmyk.ProcessBlue    = cmyk(0.96, 0, 0, 0)
cmyk.SkyBlue        = cmyk(0.62, 0, 0.12, 0)
cmyk.Turquoise      = cmyk(0.85, 0, 0.20, 0)
cmyk.TealBlue       = cmyk(0.86, 0, 0.34, 0.02)
cmyk.Aquamarine     = cmyk(0.82, 0, 0.30, 0)
cmyk.BlueGreen      = cmyk(0.85, 0, 0.33, 0)
cmyk.Emerald        = cmyk(1, 0, 0.50, 0)
cmyk.JungleGreen    = cmyk(0.99, 0, 0.52, 0)
cmyk.SeaGreen       = cmyk(0.69, 0, 0.50, 0)
cmyk.Green          = cmyk(1, 0, 1, 0)
cmyk.ForestGreen    = cmyk(0.91, 0, 0.88, 0.12)
cmyk.PineGreen      = cmyk(0.92, 0, 0.59, 0.25)
cmyk.LimeGreen      = cmyk(0.50, 0, 1, 0)
cmyk.YellowGreen    = cmyk(0.44, 0, 0.74, 0)
cmyk.SpringGreen    = cmyk(0.26, 0, 0.76, 0)
cmyk.OliveGreen     = cmyk(0.64, 0, 0.95, 0.40)
cmyk.RawSienna      = cmyk(0, 0.72, 1, 0.45)
cmyk.Sepia          = cmyk(0, 0.83, 1, 0.70)
cmyk.Brown          = cmyk(0, 0.81, 1, 0.60)
cmyk.Tan            = cmyk(0.14, 0.42, 0.56, 0)
cmyk.Gray           = cmyk(0, 0, 0, 0.50)
cmyk.Grey           = cmyk.Gray
cmyk.Black          = cmyk(0, 0, 0, 1)
cmyk.White          = cmyk(0, 0, 0, 0)
cmyk.white          = cmyk.White
cmyk.black          = cmyk.Black


class palette(attr.changelist):
    """color palettes

    A color palette is a discrete, ordered list of colors"""

palette.clear = attr.clearclass(palette)

#
# gradients
#

class gradient(attr.changeattr):

    """base class for color gradients

    A gradient is a continuous collection of colors with a single parameter ranging from 0 to 1
    to address them"""

    def getcolor(self, param):
        """return color corresponding to param"""
        pass

    def select(self, index, n_indices):
        """return a color corresponding to an index out of n_indices"""
        if n_indices == 1:
            param = 0
        else:
            param = index / (n_indices - 1.0)
        return self.getcolor(param)

gradient.clear = attr.clearclass(gradient)

#
# gradient with arbitrary non-linear dependency
#

class functiongradient_gray(gradient):

    """arbitrary non-linear gradients of gray colors

    f_gray: a function mapping [0,1] to the gray value
    """

    def __init__(self, f_gray):
        super().__init__()
        self.f_gray = f_gray

    def getcolor(self, param):
        return gray(self.f_gray(param))


class functiongradient_cmyk(gradient):

    """arbitrary non-linear gradients of cmyk colors

    f_c: a function mapping [0,1] to the c component
    f_m: a function mapping [0,1] to the m component
    f_y: a function mapping [0,1] to the y component
    f_k: a function mapping [0,1] to the k component
    """

    def __init__(self, f_c, f_m, f_y, f_k):
        super().__init__()
        self.f_c = f_c
        self.f_m = f_m
        self.f_y = f_y
        self.f_k = f_k

    def getcolor(self, param):
        return cmyk(self.f_c(param), self.f_m(param), self.f_y(param), self.f_k(param))


class functiongradient_hsb(gradient):

    """arbitrary non-linear gradients of hsb colors

    f_h: a function mapping [0,1] to the h component
    f_s: a function mapping [0,1] to the s component
    f_b: a function mapping [0,1] to the b component
    """

    def __init__(self, f_h, f_s, f_b):
        super().__init__()
        self.f_h = f_h
        self.f_s = f_s
        self.f_b = f_b

    def getcolor(self, param):
        return hsb(self.f_h(param), self.f_s(param), self.f_b(param))


class functiongradient_rgb(gradient):

    """arbitrary non-linear gradients of rgb colors

    f_r: a function mapping [0,1] to the r component
    f_g: a function mapping [0,1] to the b component
    f_b: a function mapping [0,1] to the b component
    """

    def __init__(self, f_r, f_g, f_b):
        super().__init__()
        self.f_r = f_r
        self.f_g = f_g
        self.f_b = f_b

    def getcolor(self, param):
        return rgb(self.f_r(param), self.f_g(param), self.f_b(param))

#
# factory functions for gradients interpolating linearly between two colors
#

def lineargradient_cmyk(mincolor, maxcolor):
     return functiongradient_cmyk(lambda x:maxcolor.c * x + mincolor.c * (1-x),
                                  lambda x:maxcolor.m * x + mincolor.m * (1-x),
                                  lambda x:maxcolor.y * x + mincolor.y * (1-x),
                                  lambda x:maxcolor.k * x + mincolor.k * (1-x))

def lineargradient_gray(mincolor, maxcolor):
     return functiongradient_gray(lambda x:maxcolor.g * x + mincolor.g * (1-x))

def lineargradient_hsb(mincolor, maxcolor):
     return functiongradient_hsb(lambda x:maxcolor.h * x + mincolor.h * (1-x),
                                 lambda x:maxcolor.s * x + mincolor.s * (1-x),
                                 lambda x:maxcolor.b * x + mincolor.b * (1-x))

def lineargradient_rgb(mincolor, maxcolor):
     return functiongradient_rgb(lambda x:maxcolor.r * x + mincolor.r * (1-x),
                                 lambda x:maxcolor.g * x + mincolor.g * (1-x),
                                 lambda x:maxcolor.b * x + mincolor.b * (1-x))


#
# gradients converted into other color spaces
#

class rgbgradient(gradient):

    "a gradient, which takes another gradient and returns rgb colors"

    def __init__(self, gradient):
        super().__init__()
        self.gradient = gradient

    def getcolor(self, param):
        return self.gradient.getcolor(param).rgb()


class cmykgradient(gradient):

    "a gradient, which takes another gradient and returns cmyk colors"

    def __init__(self, gradient):
        super().__init__()
        self.gradient = gradient

    def getcolor(self, param):
        return self.gradient.getcolor(param).cmyk()


gradient.Gray           = lineargradient_gray(gray.white, gray.black)
gradient.Grey           = gradient.Gray
gradient.ReverseGray    = lineargradient_gray(gray.black, gray.white)
gradient.ReverseGrey    = gradient.ReverseGray
gradient.BlackYellow    = functiongradient_rgb( # compare this with reversegray above
    f_r=lambda x: 2*x*(1-x)**5 + 3.5*x**2*(1-x)**3 + 2.1*x*x*(1-x)**2 + 3.0*x**3*(1-x)**2 + x**0.5*(1-(1-x)**2),
    f_g=lambda x: 1.5*x**2*(1-x)**3 - 0.8*x**3*(1-x)**2 + 2.0*x**4*(1-x) + x**4,
    f_b=lambda x: 5*x*(1-x)**5 - 0.5*x**2*(1-x)**3 + 0.3*x*x*(1-x)**2 + 5*x**3*(1-x)**2 + 0.5*x**6)
gradient.YellowBlack    = functiongradient_rgb(
    f_r=lambda x: 2*(1-x)*x**5 + 3.5*(1-x)**2*x**3 + 2.1*(1-x)*(1-x)*x**2 + 3.0*(1-x)**3*x**2 + (1-x)**0.5*(1-x**2),
    f_g=lambda x: 1.5*(1-x)**2*x**3 - 0.8*(1-x)**3*x**2 + 2.0*(1-x)**4*x + (1-x)**4,
    f_b=lambda x: 5*(1-x)*x**5 - 0.5*(1-x)**2*x**3 + 0.3*(1-x)*(1-x)*x**2 + 5*(1-x)**3*x**2 + 0.5*(1-x)**6)
gradient.RedGreen       = lineargradient_rgb(rgb.red, rgb.green)
gradient.RedBlue        = lineargradient_rgb(rgb.red, rgb.blue)
gradient.GreenRed       = lineargradient_rgb(rgb.green, rgb.red)
gradient.GreenBlue      = lineargradient_rgb(rgb.green, rgb.blue)
gradient.BlueRed        = lineargradient_rgb(rgb.blue, rgb.red)
gradient.BlueGreen      = lineargradient_rgb(rgb.blue, rgb.green)
gradient.RedBlack       = lineargradient_rgb(rgb.red, rgb.black)
gradient.BlackRed       = lineargradient_rgb(rgb.black, rgb.red)
gradient.RedWhite       = lineargradient_rgb(rgb.red, rgb.white)
gradient.WhiteRed       = lineargradient_rgb(rgb.white, rgb.red)
gradient.GreenBlack     = lineargradient_rgb(rgb.green, rgb.black)
gradient.BlackGreen     = lineargradient_rgb(rgb.black, rgb.green)
gradient.GreenWhite     = lineargradient_rgb(rgb.green, rgb.white)
gradient.WhiteGreen     = lineargradient_rgb(rgb.white, rgb.green)
gradient.BlueBlack      = lineargradient_rgb(rgb.blue, rgb.black)
gradient.BlackBlue      = lineargradient_rgb(rgb.black, rgb.blue)
gradient.BlueWhite      = lineargradient_rgb(rgb.blue, rgb.white)
gradient.WhiteBlue      = lineargradient_rgb(rgb.white, rgb.blue)
gradient.Rainbow        = lineargradient_hsb(hsb(0, 1, 1), hsb(2.0/3.0, 1, 1))
gradient.ReverseRainbow = lineargradient_hsb(hsb(2.0/3.0, 1, 1), hsb(0, 1, 1))
gradient.Hue            = lineargradient_hsb(hsb(0, 1, 1), hsb(1, 1, 1))
gradient.ReverseHue     = lineargradient_hsb(hsb(1, 1, 1), hsb(0, 1, 1))
rgbgradient.Rainbow        = rgbgradient(gradient.Rainbow)
rgbgradient.ReverseRainbow = rgbgradient(gradient.ReverseRainbow)
rgbgradient.Hue            = rgbgradient(gradient.Hue)
rgbgradient.ReverseHue     = rgbgradient(gradient.ReverseHue)
cmykgradient.Rainbow        = cmykgradient(gradient.Rainbow)
cmykgradient.ReverseRainbow = cmykgradient(gradient.ReverseRainbow)
cmykgradient.Hue            = cmykgradient(gradient.Hue)
cmykgradient.ReverseHue     = cmykgradient(gradient.ReverseHue)
def jet_r(x):
    if x < 0.38: return 0
    elif x < 0.62: return (x-0.38)/(0.62-0.38)
    elif x < 0.87: return 1
    else: return 0.5 + 0.5*(1-x)/(1-0.87)
def jet_g(x):
    if x < 0.13: return 0
    elif x < 0.38: return (x-0.13)/(0.38-0.13)
    elif x < 0.62: return 1
    elif x < 0.87: return (0.87-x)/(0.87-0.62)
    else: return 0
def jet_b(x):
    if x < 0.13: return 0.5 + 0.5*x/0.13
    elif x < 0.38: return 1
    elif x < 0.62: return 1-(x-0.38)/(0.62-0.38)
    else: return 0
gradient.Jet = functiongradient_rgb(f_r=jet_r, f_g=jet_g, f_b=jet_b)
gradient.ReverseJet = functiongradient_rgb(f_r=lambda x: jet_r(1-x), f_g=lambda x: jet_g(1-x), f_b=lambda x: jet_b(1-x))
cmykgradient.Jet = cmykgradient(gradient.Jet)
cmykgradient.ReverseJet = cmykgradient(gradient.ReverseJet)



class PDFextgstate(pdfwriter.PDFobject):

    def __init__(self, name, extgstate, registry):
        pdfwriter.PDFobject.__init__(self, "extgstate", name)
        registry.addresource("ExtGState", name, self)
        self.name = name
        self.extgstate = extgstate

    def write(self, file, writer, registry):
        file.write("%s\n" % self.extgstate)


class transparency(attr.exclusiveattr, style.strokestyle, style.fillstyle):

    def __init__(self, value):
        self.value = 1-value
        attr.exclusiveattr.__init__(self, transparency)

    def processPS(self, file, writer, context, registry):
        logger.warning("Transparency not available in PostScript, proprietary ghostscript extension code inserted.")
        file.write("%f .setshapealpha\n" % self.value)

    def processPDF(self, file, writer, context, registry):
        if context.strokeattr and context.fillattr:
            registry.add(PDFextgstate("Transparency-%f" % self.value,
                                      "<< /Type /ExtGState /CA %f /ca %f >>" % (self.value, self.value), registry))
            file.write("/Transparency-%f gs\n" % self.value)
        elif context.strokeattr:
            registry.add(PDFextgstate("Transparency-Stroke-%f" % self.value,
                                      "<< /Type /ExtGState /CA %f >>" % self.value, registry))
            file.write("/Transparency-Stroke-%f gs\n" % self.value)
        elif context.fillattr:
            registry.add(PDFextgstate("Transparency-Fill-%f" % self.value,
                                      "<< /Type /ExtGState /ca %f >>" % self.value, registry))
            file.write("/Transparency-Fill-%f gs\n" % self.value)

    def processSVGattrs(self, attrs, writer, context, registry):
        if context.strokeattr:
            context.strokeopacity = self.value
        if context.fillattr:
            context.fillopacity = self.value

