# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2015 André Wobst <wobsta@pyx-project.org>
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


import xml.sax, re, math, logging
from . import baseclasses, bbox, canvas, path, trafo, deco, style, color, unit

logger = logging.getLogger("pyx")


def endpointarc(x1, y1, x2, y2, fA, fS, rx, ry, phi):
    # Note: all lengths are _pt, but has been skipped to prevent clumsy notation
    # See http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes

    # F.6.6 step 1
    if rx == 0 or ry == 0:
        return path.line_pt(x1, y1, x2, y2)

    # F.6.6 step 2
    if rx < 0: rx = -rx
    if ry < 0: ry = -ry

    # F.6.5 step 1
    cos_phi = math.cos(math.radians(phi))
    sin_phi = math.sin(math.radians(phi))
    dx = (x1 - x2) / 2
    dy = (y1 - y2) / 2
    x1prim = cos_phi * dx + sin_phi * dy
    y1prim = -sin_phi * dx + cos_phi * dy

    # F.6.6 step 3
    Lambda = (x1prim/rx)**2 + (y1prim/ry)**2
    if Lambda > 1:
        Lambda_sqrt = math.sqrt(Lambda)
        rx *= Lambda_sqrt
        ry *= Lambda_sqrt

    # F.6.5 step 2
    c_sq = ((rx*ry)**2 - (rx*y1prim)**2 - (ry*x1prim)**2) / ((rx*y1prim)**2 + (ry*x1prim)**2)
    c = math.sqrt(c_sq) if c_sq > 0 else 0
    if fA == fS:
        c = -c
    cxprim = c * rx * y1prim / ry
    cyprim = -c * ry * x1prim / rx

    # F.6.5 step 3
    cx = cos_phi * cxprim - sin_phi * cyprim + dx
    cy = sin_phi * cxprim + cos_phi * cyprim + dy

    # F.6.5 step 4
    theta1 = math.atan2((y1prim - cyprim)/ry, (x1prim - cxprim)/rx)
    theta2 = math.atan2((-y1prim - cyprim)/ry, (-x1prim - cxprim)/rx)

    if fS:
        # clockwise and counterclockwise are exchanged due to negative y axis direction
        arc = path.path(path.arc_pt(0, 0, 1, theta1*180/math.pi, theta2*180/math.pi))
    else:
        arc = path.path(path.arcn_pt(0, 0, 1, theta1*180/math.pi, theta2*180/math.pi))
    arc = arc.transformed(trafo.scale(rx, ry).rotated(phi))
    x1p, y1p = arc.atbegin_pt()
    return arc.transformed(trafo.translate_pt(x1-x1p, y1-y1p))


class svgValueError(ValueError): pass

class _marker: pass

_svgFloatPattern = re.compile("(?P<value>[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)(?P<unit>(px|pt|pc|mm|cm|in|%)?)\s*,?\s*")
_svgBoolPattern = re.compile("(?P<bool>[01])\s*,?\s*")
_svgPathPattern = re.compile("(?P<cmd>[mlhvcsqtaz])\s*(?P<args>(([^mlhvcsqtaz]|pt|pc|mm|cm)*))", re.IGNORECASE)
_svgColorAbsPattern = re.compile("rgb\(\s*(?P<red>[0-9]+)\s*,\s*(?P<green>[0-9]+)\s*,\s*(?P<blue>[0-9]+)\s*\)$", re.IGNORECASE)
_svgColorRelPattern = re.compile("rgb\(\s*(?P<red>[0-9]+)%\s*,\s*(?P<green>[0-9]+)%\s*,\s*(?P<blue>[0-9]+)%\s*\)$", re.IGNORECASE)


class svgBaseHandler(xml.sax.ContentHandler):

    def __init__(self, resolution):
        self.resolution = resolution
        self.units = {"": 72/self.resolution,
                      "px": 72/self.resolution,
                      "pt": 1,
                      "pc": 12,
                      "mm": 72/25.4,
                      "cm": 72/2.54,
                      "in": 72}

    def toFloat(self, arg, relative=None, single=False, units=True):
        match = _svgFloatPattern.match(arg)
        if not match:
            raise svgValueError("could not match float for '%s'" % arg)
        if match.group("unit") and not units:
            raise svgValueError("no units allowed for '%s'" % arg)
        value = float(match.group("value"))
        if match.group("unit") == "%":
            if relative is not None:
                value *= 0.01 * relative
            else:
                raise svgValueError("missing support for relative coordinates")
        elif units:
            value *= self.units[match.group("unit")]
        if single:
            if match.end() < len(arg):
                raise svgValueError("could not match single float for '%s'" % arg)
            return value
        return value, arg[match.end():]

    def toFloats(self, args, units=True):
        while args:
            float, args = self.toFloat(args, units=units)
            yield float


class svgHandler(svgBaseHandler):

    def __init__(self, resolution):
        super().__init__(resolution)
        self.stack = []
        self.stroke = None
        self.fill = color.grey.black

    def toBool(self, arg):
        match = _svgBoolPattern.match(arg)
        if not match:
            raise svgValueError("could not match boolean for '%s'" % arg)
        return match.group("bool") == "1", arg[match.end():]

    def toPath(self, svgPath):
        # Note: all lengths are _pt, but _pt has been skipped to prevent clumsy notation
        p = path.path()
        for match in _svgPathPattern.finditer(svgPath):
            cmd = match.group("cmd")
            args = match.group("args")
            try:
                if cmd not in "aA":
                    args = self.toFloats(args)
                if cmd in "MmLl":
                    first = True
                    while args:
                        x, y, *args = args
                        if cmd in "Ll" or not first:
                            p.append(path.lineto_pt(x, y) if cmd.isupper() else
                                     path.rlineto_pt(x, y))
                        else:
                            p.append(path.moveto_pt(x, y) if cmd.isupper() or not p else
                                     path.rmoveto_pt(x, y))
                        first = False
                elif cmd in "HhVv":
                    x, y = p.atend_pt() if cmd.isupper() else (0, 0)
                    for arg in args:
                        if cmd in "Hh":
                            x = arg
                        else:
                            y = arg
                        p.append(path.lineto_pt(x, y) if cmd.isupper() else
                                 path.rlineto_pt(x, y))
                elif cmd in "CcSs":
                    while args:
                        if cmd in "Cc":
                            x1, y1, x2, y2, x3, y3, *args = args
                        else:
                            x2, y2, x3, y3, *args = args
                            if isinstance(p[-1], path.curveto_pt):
                                x1 = p[-1].x3_pt - p[-1].x2_pt
                                y1 = p[-1].y3_pt - p[-1].y2_pt
                            elif isinstance(p[-1], path.rcurveto_pt):
                                x1 = p[-1].dx3_pt - p[-1].dx2_pt
                                y1 = p[-1].dy3_pt - p[-1].dy2_pt
                            else:
                                x1, y1 = 0, 0
                            if cmd == "S":
                                x0, y0 = p.atend_pt()
                                x1 += x0
                                y1 += y0
                        p.append(path.curveto_pt(x1, y1, x2, y2, x3, y3) if cmd.isupper() else
                                 path.rcurveto_pt(x1, y1, x2, y2, x3, y3))
                elif cmd in "QqTt":
                    while args:
                        x0, y0 = p.atend_pt()
                        if cmd in "Qq":
                            xq, yq, x3, y3, *args = args
                            if cmd == "q":
                                xq += x0
                                yq += y0
                                x3 += x0
                                y3 += y0
                        else:
                            x3, y3, *args = args
                            if cmd == "t":
                                x3 += x0
                                y3 += y0
                            if isinstance(p[-1], path.curveto_pt):
                                xq = x0 + 3/2 * (p[-1].x3_pt - p[-1].x2_pt)
                                yq = y0 + 3/2 * (p[-1].y3_pt - p[-1].y2_pt)
                            elif isinstance(p[-1], path.rcurveto_pt):
                                xq = x0 + 3/2 * (p[-1].dx3_pt - p[-1].dx2_pt)
                                yq = y0 + 3/2 * (p[-1].dy3_pt - p[-1].dy2_pt)
                            else:
                                xq, yq = p.atend_pt()
                        x1 = x0 + 2/3 * (xq - x0)
                        y1 = y0 + 2/3 * (yq - y0)
                        x2 = x3 + 2/3 * (xq - x3)
                        y2 = y3 + 2/3 * (yq - y3)
                        p.append(path.curveto_pt(x1, y1, x2, y2, x3, y3))
                elif cmd in "aA":
                        while args:
                            rx, args = self.toFloat(args)
                            ry, args = self.toFloat(args)
                            phi, args = self.toFloat(args)
                            fA, args = self.toBool(args)
                            fS, args = self.toBool(args)
                            x2, args = self.toFloat(args)
                            y2, args = self.toFloat(args)
                            x1, y1 = p.atend_pt()
                            if cmd == "a":
                                x2 += x1
                                y2 += y1
                            p.join(endpointarc(x1, y1, x2, y2, fA, fS, rx, ry, phi))
                else:
                    assert cmd in "zZ"
                    p.append(path.closepath())
            except svgValueError:
                pass
        return p

    def toTrafo(self, svgTrafo):
        t = trafo.identity
        for match in reversed(list(re.finditer("(?P<cmd>matrix|translate|scale|rotate|skewX|skewY)\((?P<args>[^)]*)\)", svgTrafo))):
            cmd = match.group("cmd")
            args = match.group("args")
            if cmd == "matrix":
                a, args = self.toFloat(args, units=False)
                b, args = self.toFloat(args, units=False)
                c, args = self.toFloat(args, units=False)
                d, args = self.toFloat(args, units=False)
                e, args = self.toFloat(args)
                f = self.toFloat(args, single=True)
                t = t * trafo.trafo_pt(((a, b), (c, d)), (e, f))
            elif cmd == "translate":
                args = list(self.toFloats(args))
                if len(args) == 1:
                    args.append(0)
                assert len(args) == 2
                t = t.translated_pt(args[0], args[1])
            elif cmd == "scale":
                args = list(self.toFloats(args, units=False))
                if len(args) == 1:
                    args.append(args[0])
                assert len(args) == 2
                t = t.scaled(args[0], args[1])
            elif cmd == "rotate":
                a, args = self.toFloat(args, units=False)
                if args:
                    b, args = self.toFloat(args)
                    c = self.toFloat(args, single=True)
                else:
                    b, c = 0, 0
                t = t.rotated_pt(a, b, c)
            elif cmd == "skewX":
                t = t * trafo.trafo_pt(((1, math.tan(self.toFloat(args, units=False, single=True)*math.pi/180)), (0, 1)))
            else:
                assert cmd == "skewY"
                t = t * trafo.trafo_pt(((1, 0), (math.tan(self.toFloat(args, units=False, single=True)*math.pi/180), 1)))
        return t

    def toColor(self, name, inherit):
        if name == "currentColor":
            return None # TODO
        if name == "inherit":
            return inherit
        if name == "none":
            return None
        names = {"aliceblue": "rgb(240, 248, 255)", "antiquewhite": "rgb(250, 235, 215)", "aqua": "rgb( 0, 255, 255)",
                 "aquamarine": "rgb(127, 255, 212)", "azure": "rgb(240, 255, 255)", "beige": "rgb(245, 245, 220)",
                 "bisque": "rgb(255, 228, 196)", "black": "rgb( 0, 0, 0)", "blanchedalmond": "rgb(255, 235, 205)",
                 "blue": "rgb( 0, 0, 255)", "blueviolet": "rgb(138, 43, 226)", "brown": "rgb(165, 42, 42)",
                 "burlywood": "rgb(222, 184, 135)", "cadetblue": "rgb( 95, 158, 160)", "chartreuse": "rgb(127, 255, 0)",
                 "chocolate": "rgb(210, 105, 30)", "coral": "rgb(255, 127, 80)", "cornflowerblue": "rgb(100, 149, 237)",
                 "cornsilk": "rgb(255, 248, 220)", "crimson": "rgb(220, 20, 60)", "cyan": "rgb( 0, 255, 255)",
                 "darkblue": "rgb( 0, 0, 139)", "darkcyan": "rgb( 0, 139, 139)", "darkgoldenrod": "rgb(184, 134, 11)",
                 "darkgray": "rgb(169, 169, 169)", "darkgreen": "rgb( 0, 100, 0)", "darkgrey": "rgb(169, 169, 169)",
                 "darkkhaki": "rgb(189, 183, 107)", "darkmagenta": "rgb(139, 0, 139)", "darkolivegreen": "rgb( 85, 107, 47)",
                 "darkorange": "rgb(255, 140, 0)", "darkorchid": "rgb(153, 50, 204)", "darkred": "rgb(139, 0, 0)",
                 "darksalmon": "rgb(233, 150, 122)", "darkseagreen": "rgb(143, 188, 143)", "darkslateblue": "rgb( 72, 61, 139)",
                 "darkslategray": "rgb( 47, 79, 79)", "darkslategrey": "rgb( 47, 79, 79)", "darkturquoise": "rgb( 0, 206, 209)",
                 "darkviolet": "rgb(148, 0, 211)", "deeppink": "rgb(255, 20, 147)", "deepskyblue": "rgb( 0, 191, 255)",
                 "dimgray": "rgb(105, 105, 105)", "dimgrey": "rgb(105, 105, 105)", "dodgerblue": "rgb( 30, 144, 255)",
                 "firebrick": "rgb(178, 34, 34)", "floralwhite": "rgb(255, 250, 240)", "forestgreen": "rgb( 34, 139, 34)",
                 "fuchsia": "rgb(255, 0, 255)", "gainsboro": "rgb(220, 220, 220)", "ghostwhite": "rgb(248, 248, 255)",
                 "gold": "rgb(255, 215, 0)", "goldenrod": "rgb(218, 165, 32)", "gray": "rgb(128, 128, 128)",
                 "grey": "rgb(128, 128, 128)", "green": "rgb( 0, 128, 0)", "greenyellow": "rgb(173, 255, 47)",
                 "honeydew": "rgb(240, 255, 240)", "hotpink": "rgb(255, 105, 180)", "indianred": "rgb(205, 92, 92)",
                 "indigo": "rgb( 75, 0, 130)", "ivory": "rgb(255, 255, 240)", "khaki": "rgb(240, 230, 140)",
                 "lavender": "rgb(230, 230, 250)", "lavenderblush": "rgb(255, 240, 245)", "lawngreen": "rgb(124, 252, 0)",
                 "lemonchiffon": "rgb(255, 250, 205)", "lightblue": "rgb(173, 216, 230)", "lightcoral": "rgb(240, 128, 128)",
                 "lightcyan": "rgb(224, 255, 255)", "lightgoldenrodyellow": "rgb(250, 250, 210)", "lightgray": "rgb(211, 211, 211)",
                 "lightgreen": "rgb(144, 238, 144)", "lightgrey": "rgb(211, 211, 211)", "lightpink": "rgb(255, 182, 193)",
                 "lightsalmon": "rgb(255, 160, 122)", "lightseagreen": "rgb( 32, 178, 170)", "lightskyblue": "rgb(135, 206, 250)",
                 "lightslategray": "rgb(119, 136, 153)", "lightslategrey": "rgb(119, 136, 153)", "lightsteelblue": "rgb(176, 196, 222)",
                 "lightyellow": "rgb(255, 255, 224)", "lime": "rgb( 0, 255, 0)", "limegreen": "rgb( 50, 205, 50)",
                 "linen": "rgb(250, 240, 230)", "magenta": "rgb(255, 0, 255)", "maroon": "rgb(128, 0, 0)",
                 "mediumaquamarine": "rgb(102, 205, 170)", "mediumblue": "rgb( 0, 0, 205)", "mediumorchid": "rgb(186, 85, 211)",
                 "mediumpurple": "rgb(147, 112, 219)", "mediumseagreen": "rgb( 60, 179, 113)", "mediumslateblue": "rgb(123, 104, 238)",
                 "mediumspringgreen": "rgb( 0, 250, 154)", "mediumturquoise": "rgb( 72, 209, 204)", "mediumvioletred": "rgb(199, 21, 133)",
                 "midnightblue": "rgb( 25, 25, 112)", "mintcream": "rgb(245, 255, 250)", "mistyrose": "rgb(255, 228, 225)",
                 "moccasin": "rgb(255, 228, 181)", "navajowhite": "rgb(255, 222, 173)", "navy": "rgb( 0, 0, 128)",
                 "oldlace": "rgb(253, 245, 230)", "olive": "rgb(128, 128, 0)", "olivedrab": "rgb(107, 142, 35)",
                 "orange": "rgb(255, 165, 0)", "orangered": "rgb(255, 69, 0)", "orchid": "rgb(218, 112, 214)",
                 "palegoldenrod": "rgb(238, 232, 170)", "palegreen": "rgb(152, 251, 152)", "paleturquoise": "rgb(175, 238, 238)",
                 "palevioletred": "rgb(219, 112, 147)", "papayawhip": "rgb(255, 239, 213)", "peachpuff": "rgb(255, 218, 185)",
                 "peru": "rgb(205, 133, 63)", "pink": "rgb(255, 192, 203)", "plum": "rgb(221, 160, 221)",
                 "powderblue": "rgb(176, 224, 230)", "purple": "rgb(128, 0, 128)", "red": "rgb(255, 0, 0)",
                 "rosybrown": "rgb(188, 143, 143)", "royalblue": "rgb( 65, 105, 225)", "saddlebrown": "rgb(139, 69, 19)",
                 "salmon": "rgb(250, 128, 114)", "sandybrown": "rgb(244, 164, 96)", "seagreen": "rgb( 46, 139, 87)",
                 "seashell": "rgb(255, 245, 238)", "sienna": "rgb(160, 82, 45)", "silver": "rgb(192, 192, 192)",
                 "skyblue": "rgb(135, 206, 235)", "slateblue": "rgb(106, 90, 205)", "slategray": "rgb(112, 128, 144)",
                 "slategrey": "rgb(112, 128, 144)", "snow": "rgb(255, 250, 250)", "springgreen": "rgb( 0, 255, 127)",
                 "steelblue": "rgb( 70, 130, 180)", "tan": "rgb(210, 180, 140)", "teal": "rgb( 0, 128, 128)",
                 "thistle": "rgb(216, 191, 216)", "tomato": "rgb(255, 99, 71)", "turquoise": "rgb( 64, 224, 208)",
                 "violet": "rgb(238, 130, 238)", "wheat": "rgb(245, 222, 179)", "white": "rgb(255, 255, 255)",
                 "whitesmoke": "rgb(245, 245, 245)", "yellow": "rgb(255, 255, 0)", "yellowgreen": "rgb(154, 205, 50)"}
        name = names.get(name, name)
        match = _svgColorAbsPattern.match(name.strip())
        if match:
            return color.rgb(int(match.group("red"))/255, int(match.group("green"))/255, int(match.group("blue"))/255)
        match = _svgColorRelPattern.match(name.strip())
        if match:
            return color.rgb(int(match.group("red"))/100, int(match.group("green"))/100, int(match.group("blue"))/100)
        return color.rgbfromhexstring(name)

    def startElementNS(self, name, qname, attributes):

        def floatAttr(localname, default=_marker):
            if default is _marker:
                return self.toFloat(attributes[None, localname])[0]
            else:
                try:
                    return self.toFloat(attributes[None, localname])[0]
                except KeyError:
                    return default

        def pathAttrs(default=_marker):
            if default is not _marker:
                attrs = default
            else:
                attrs = []
            if (None, "transform") in attributes:
                attrs.append(self.toTrafo(attributes[None, "transform"]))
            if (None, "stroke-dasharray") in attributes:
                attrs.append(style.dash(self.toFloats(attributes[None, "stroke-dasharray"]),
                                        offset=floatAttr("stroke-dashoffset", 0),
                                        rellengths=False))
            if (None, "stroke-linecap") in attributes:
                attrs.append({"butt": style.linecap.butt,
                              "round": style.linecap.round,
                              "square": style.linecap.square}[attributes[None, "stroke-linecap"]])
            if (None, "stroke-linejoin") in attributes:
                attrs.append({"miter": style.linejoin.miter,
                              "round": style.linejoin.round,
                              "bevel": style.linejoin.bevel}[attributes[None, "stroke-linejoin"]])
            if (None, "stroke-miterlimit") in attributes:
                attrs.append(style.miterlimit(floatAttr("stroke-miterlimit")))
            if (None, "stroke-width") in attributes:
                attrs.append(style.linewidth(floatAttr("stroke-width")*unit.t_pt))
            if (None, "fill-rule") in attributes:
                attrs.append({"nonzero": style.fillrule.nonzero_winding,
                              "evenodd": style.fillrule.even_odd}[attributes[None, "fill-rule"]])
            return attrs

        namespace, localname = name
        if namespace == "http://www.w3.org/2000/svg":
            if localname == "svg":
                attrs = pathAttrs([style.linewidth(1*unit.t_pt), style.miterlimit(4)])
                outer_x = self.toFloat(attributes.get((None, "x"), "0"), single=True)
                outer_y = self.toFloat(attributes.get((None, "y"), "0"), single=True)
                if (None, "viewBox") in attributes:
                    inner_x, inner_y, inner_width, inner_height = self.toFloats(attributes[None, "viewBox"])
                    if attributes.get((None, "clip"), "auto") == "auto":
                        attrs.append(canvas.clip(path.rect(inner_x, inner_y, inner_width, inner_height)))
                    outer_width = self.toFloat(attributes.get((None, "width"), "100%"), single=True, relative=inner_width)
                    outer_height = self.toFloat(attributes.get((None, "height"), "100%"), single=True, relative=inner_height)
                    self.bbox = bbox.bbox_pt(outer_x, -outer_y, outer_x+outer_width, -outer_y+outer_height)
                    attrs.append(trafo.translate_pt(-inner_x, -inner_y))
                    attrs.append(trafo.scale(outer_width/inner_width, outer_height/inner_height))
                    attrs.append(trafo.translate_pt(outer_x, outer_y))
                    attrs.append(trafo.translate_pt(0, -outer_height))
                elif (None, "width") in attributes and (None, "height") in attributes:
                    outer_width = self.toFloat(attributes.get((None, "width"), "100%"), single=True)
                    outer_height = self.toFloat(attributes.get((None, "height"), "100%"), single=True)
                    self.bbox = bbox.bbox_pt(outer_x, -outer_y, outer_x+outer_width, -outer_y+outer_height)
                    attrs.append(trafo.translate_pt(outer_x, outer_y))
                    attrs.append(trafo.translate_pt(0, -outer_height))
                else:
                    self.bbox = None
                    raise ValueError("SVG viewbox or width and height missing, we continue by aligning by SVG coordinates (top-left) instead of PyX-like (bottom-left) and calculate the bbox from the SVG content")
                attrs.append(trafo.mirror(0))
                self.canvas = canvas.canvas(attrs)
            elif localname == "g":
                self.stack.append((self.canvas, self.stroke, self.fill))
                self.canvas = self.canvas.insert(canvas.canvas(pathAttrs()))
                self.fill = self.toColor(attributes.get((None, "fill"), "inherit"), self.fill)
                self.stroke = self.toColor(attributes.get((None, "stroke"), "inherit"), self.stroke)
            elif localname in ["rect", "circle", "ellipse", "line", "polyline", "polygon", "path"]:
                if localname == "line":
                    p = path.line_pt(floatAttr("x1"), floatAttr("y1"), floatAttr("x2"), floatAttr("y2"))
                elif localname == "rect":
                    x, y = floatAttr("x", 0), floatAttr("y", 0)
                    width, height = floatAttr("width"), floatAttr("height")
                    if width == 0 or height == 0:
                        p = None
                    else:
                        rx, ry = floatAttr("rx", None), floatAttr("ry", None)
                        if ((rx is None or rx < 1e-10) and (ry is None or ry < 1e-10)):
                            p = path.rect_pt(x, y, width, height)
                        else:
                            if rx is None: rx = ry
                            elif ry is None: ry = rx
                            if 2*rx > width: rx = 0.5*width
                            if 2*ry > height: ry = 0.5*height
                            c = path.circle_pt(0, 0, 1).transformed(trafo.scale(rx, ry))
                            c1, c2, c3, c4 = c.split_pt([i*c.arclen_pt()/4 for i in range(4)])
                            p = c1.transformed(trafo.translate_pt(x+width-rx, y+ry))
                            p.join(c2.transformed(trafo.translate_pt(x+width-rx, y+height-ry)))
                            p.join(c3.transformed(trafo.translate_pt(x+rx, y+height-ry)))
                            p.join(c4.transformed(trafo.translate_pt(x+rx, y+ry)))
                            p.append(path.closepath())
                elif localname == "circle":
                    if floatAttr("r") != 0:
                        p = path.circle_pt(floatAttr("cx", 0), floatAttr("cy", 0), floatAttr("r"))
                    else:
                        p = None
                elif localname == "ellipse":
                    if floatAttr("rx") != 0 and floatAttr("ry") != 0:
                        p = path.ellipse_pt(floatAttr("cx", 0), floatAttr("cy", 0), floatAttr("rx"), floatAttr("ry"), angle=0)
                    else:
                        p = None
                elif localname == "polyline" or localname == "polygon":
                    x, y, *args = self.toFloats(attributes[None, "points"])
                    p = path.path(path.moveto_pt(x, y))
                    while len(args) >= 2:
                        x, y, *args = args
                        p.append(path.lineto_pt(x, y))
                    if localname == "polygon":
                        p.append(path.closepath())
                else:
                    assert localname == "path"
                    p = self.toPath(attributes[None, "d"])
                if p is not None:
                    attrs = pathAttrs()
                    fill = self.toColor(attributes.get((None, "fill"), "inherit"), self.fill)
                    if fill:
                        attrs.append(deco.filled([fill]))
                    stroke = self.toColor(attributes.get((None, "stroke"), "inherit"), self.stroke)
                    if stroke:
                        attrs.append(deco.stroked([stroke]))
                    if stroke or fill:
                        self.canvas.draw(p, attrs)

    def endElementNS(self, name, qname):
        namespace, localname = name
        if namespace == "http://www.w3.org/2000/svg":
            if localname == "g":
                self.canvas, self.stroke, self.fill = self.stack.pop()

class svgBboxDoneException(Exception): pass

class svgBboxHandler(svgBaseHandler):

    def startElementNS(self, name, qname, attributes):
        if name != ("http://www.w3.org/2000/svg", "svg"):
            raise ValueError("not an SVG file")
        if (None, "width") not in attributes or (None, "height") not in attributes:
            raise ValueError("SVG width and height missing, which is required for unparsed SVG inclusion")
        outer_x = self.toFloat(attributes.get((None, "x"), "0"), single=True)
        outer_y = self.toFloat(attributes.get((None, "y"), "0"), single=True)
        try:
            outer_width = self.toFloat(attributes.get((None, "width")), single=True)
            outer_height = self.toFloat(attributes.get((None, "height")), single=True)
            self.trafo = trafo.translate_pt(0, outer_height) * trafo.scale(72/self.resolution)
        except svgValueError:
            inner_x, inner_y, inner_width, inner_height = self.toFloats(attributes[None, "viewBox"])
            outer_width = self.toFloat(attributes.get((None, "width")), relative=inner_width, single=True)
            outer_height = self.toFloat(attributes.get((None, "height")), relative=inner_height, single=True)
            self.trafo = trafo.translate_pt(-0.5*outer_width, outer_height)
        self.bbox = bbox.bbox_pt(outer_x, -outer_y, outer_x+outer_width, -outer_y+outer_height)
        raise svgBboxDoneException()


class svgfile_pt(baseclasses.canvasitem):

    def __init__(self, x_pt, y_pt, filename, width_pt=None, height_pt=None, ratio=None, parsed=False, resolution=96):
        self.filename = filename
        self.parsed = parsed
        self.resolution = resolution

        if parsed:
            self.svg = svgHandler(resolution)
        else:
            self.svg = svgBboxHandler(resolution)
        parser = xml.sax.make_parser()
        parser.setContentHandler(self.svg)
        parser.setFeature(xml.sax.handler.feature_namespaces, True)
        parser.setFeature(xml.sax.handler.feature_external_ges, False)
        parser.setFeature(xml.sax.handler.feature_external_pes, False)
        if parsed:
            with open(filename, "rb") as f:
                parser.parse(f)
        else:
            try:
                with open(filename, "rb") as f:
                    parser.parse(f)
            except svgBboxDoneException:
                pass
            else:
                raise ValueError("no XML found")

        if not self.svg.bbox:
            # fallback for parsed svg without viewbox
            self.svg.bbox = self.svg.canvas.bbox()

        self.trafo = trafo.translate_pt(x_pt, y_pt)

        if width_pt is not None or height_pt is not None:
            svgwidth_pt = self.svg.bbox.width_pt()
            svgheight_pt = self.svg.bbox.height_pt()
            if width_pt is None:
                if ratio is None:
                    width_pt = height_pt * svgwidth_pt / svgheight_pt
                else:
                    width_pt = ratio * height_pt
            elif height_pt is None:
                if ratio is None:
                    height_pt = width_pt * svgheight_pt / svgwidth_pt
                else:
                    height_pt = (1.0/ratio) * width_pt
            elif ratio is not None:
                raise ValueError("can't specify a ratio when setting width_pt and height_pt")
            self.trafo *= trafo.scale_pt(width_pt/svgwidth_pt, height_pt/svgheight_pt)
        else:
            if ratio is not None:
                raise ValueError("must specify width_pt or height_pt to set a ratio")

        self.trafo *= trafo.translate_pt(-self.svg.bbox.llx_pt, -self.svg.bbox.lly_pt)

        self._bbox = self.svg.bbox.transformed(self.trafo)
        if self.parsed:
            self.canvas = canvas.canvas([self.trafo])
            self.canvas.insert(self.svg.canvas)

    def bbox(self):
        return self._bbox

    def processPS(self, file, writer, context, registry, bbox):
        if not self.parsed:
            raise ValueError("cannot output unparsed SVG to PostScript")
        self.canvas.processPS(file, writer, context, registry, bbox)

    def processPDF(self, file, writer, context, registry, bbox):
        if not self.parsed:
            raise ValueError("cannot output unparsed SVG to PDF")
        self.canvas.processPDF(file, writer, context, registry, bbox)

    def processSVG(self, svg, writer, context, registry, bbox):
        if self.parsed:
            self.canvas.processSVG(svg, writer, context, registry, bbox)
        else:
            t = self.trafo * self.svg.trafo
            attrs = {"fill": "black"}
            t.processSVGattrs(attrs, writer, context, registry)
            svg.startSVGElement("g", attrs)
            parser = xml.sax.make_parser()
            parser.setContentHandler(svg)
            parser.setFeature(xml.sax.handler.feature_namespaces, True)
            parser.setFeature(xml.sax.handler.feature_external_ges, False)
            parser.setFeature(xml.sax.handler.feature_external_pes, False)
            svg.passthrough = True
            with open(self.filename, "rb") as f:
                parser.parse(f)
            svg.passthrough = False
            svg.endSVGElement("g")


class svgfile(svgfile_pt):

    def __init__(self, x, y, filename, width=None, height=None, *args, **kwargs):
        x_pt = unit.topt(x)
        y_pt = unit.topt(y)
        if width is not None:
            width_pt = unit.topt(width)
        else:
            width_pt = None
        if height is not None:
            height_pt = unit.topt(height)
        else:
            height_pt = None
        super().__init__(x_pt, y_pt, filename, width_pt, height_pt, *args, **kwargs)
