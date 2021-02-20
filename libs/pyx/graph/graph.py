# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2002-2012 Jörg Lehmann <joerg@pyx-project.org>
# Copyright (C) 2003-2004 Michael Schindler <m-schindler@users.sourceforge.net>
# Copyright (C) 2002-2012 André Wobst <wobsta@pyx-project.org>
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


import logging, math, re, string
from pyx import canvas, path, trafo, unit
from pyx.graph.axis import axis, positioner

logger = logging.getLogger("pyx")
goldenmean = 0.5 * (math.sqrt(5) + 1)


# The following two methods are used to register and get a default provider
# for keys. A key is a variable name in sharedata. A provider is a style
# which creates variables in sharedata.

_defaultprovider = {}

def registerdefaultprovider(style, keys):
    """sets a style as a default creator for sharedata variables 'keys'"""
    for key in keys:
        assert key in style.providesdata, "key not provided by style"
        # we might allow for overwriting the defaults, i.e. the following is not checked:
        # assert key in _defaultprovider.keys(), "default provider already registered for key"
        _defaultprovider[key] = style

def getdefaultprovider(key):
    """returns a style, which acts as a default creator for the
    sharedata variable 'key'"""
    return _defaultprovider[key]


class styledata:
    """style data storage class

    Instances of this class are used to store data from the styles
    and to pass point data to the styles by instances named privatedata
    and sharedata. sharedata is shared between all the style(s) in use
    by a data instance, while privatedata is private to each style and
    used as a storage place instead of self to prevent side effects when
    using a style several times."""
    pass


class plotitem:

    def __init__(self, graph, data, styles):
        self.data = data
        self.title = data.title

        addstyles = [None]
        while addstyles:
            # add styles to ensure all needs of the given styles
            provided = [] # already provided sharedata variables
            addstyles = [] # a list of style instances to be added in front
            for s in styles:
                for n in s.needsdata:
                    if n not in provided:
                        defaultprovider = getdefaultprovider(n)
                        addstyles.append(defaultprovider)
                        provided.extend(defaultprovider.providesdata)
                provided.extend(s.providesdata)
            styles = addstyles + styles

        self.styles = styles
        self.sharedata = styledata()
        self.dataaxisnames = {}
        self.privatedatalist = [styledata() for s in self.styles]

        # perform setcolumns to all styles
        self.usedcolumnnames = set()
        for privatedata, s in zip(self.privatedatalist, self.styles):
            self.usedcolumnnames.update(set(s.columnnames(privatedata, self.sharedata, graph, self.data.columnnames, self.dataaxisnames)))

    def selectstyles(self, graph, selectindex, selecttotal):
        for privatedata, style in zip(self.privatedatalist, self.styles):
            style.selectstyle(privatedata, self.sharedata, graph, selectindex, selecttotal)

    def adjustaxesstatic(self, graph):
        for columnname, data in list(self.data.columns.items()):
            for privatedata, style in zip(self.privatedatalist, self.styles):
                style.adjustaxis(privatedata, self.sharedata, graph, self, columnname, data)

    def makedynamicdata(self, graph):
        self.dynamiccolumns = self.data.dynamiccolumns(graph, self.dataaxisnames)

    def adjustaxesdynamic(self, graph):
        for columnname, data in list(self.dynamiccolumns.items()):
            for privatedata, style in zip(self.privatedatalist, self.styles):
                style.adjustaxis(privatedata, self.sharedata, graph, self, columnname, data)

    def draw(self, graph):
        for privatedata, style in zip(self.privatedatalist, self.styles):
            style.initdrawpoints(privatedata, self.sharedata, graph)

        point = dict([(columnname, None) for columnname in self.usedcolumnnames])
        # fill point with (static) column data first
        columns = list(self.data.columns.keys())
        for values in zip(*list(self.data.columns.values())):
            for column, value in zip(columns, values):
                point[column] = value
            for privatedata, style in zip(self.privatedatalist, self.styles):
                style.drawpoint(privatedata, self.sharedata, graph, point)

        point = dict([(columnname, None) for columnname in self.usedcolumnnames])
        # insert an empty point
        if self.data.columns and self.dynamiccolumns:
            for privatedata, style in zip(self.privatedatalist, self.styles):
                style.drawpoint(privatedata, self.sharedata, graph, point)
        # fill point with dynamic column data
        columns = list(self.dynamiccolumns.keys())
        for values in zip(*list(self.dynamiccolumns.values())):
            for key, value in zip(columns, values):
                point[key] = value
            for privatedata, style in zip(self.privatedatalist, self.styles):
                style.drawpoint(privatedata, self.sharedata, graph, point)
        for privatedata, style in zip(self.privatedatalist, self.styles):
            style.donedrawpoints(privatedata, self.sharedata, graph)

    def key_pt(self, graph, x_pt, y_pt, width_pt, height_pt):
        for privatedata, style in zip(self.privatedatalist, self.styles):
            style.key_pt(privatedata, self.sharedata, graph, x_pt, y_pt, width_pt, height_pt)

    def __getattr__(self, attr):
        # read only access to the styles privatedata
        # this is just a convenience method
        # use case: access the path of a the line style
        stylesdata = [getattr(styledata, attr)
                      for styledata in self.privatedatalist
                      if hasattr(styledata, attr)]
        if len(stylesdata) > 1:
            return stylesdata
        elif len(stylesdata) == 1:
            return stylesdata[0]
        raise AttributeError("access to styledata attribute '%s' failed" % attr)


class graph(canvas.canvas):

    def __init__(self):
        canvas.canvas.__init__(self)
        for name in ["background", "filldata", "axes.grid", "axes.baseline", "axes.ticks", "axes.labels", "axes.title", "data", "key"]:
            self.layer(name)
        self.axes = {}
        self.plotitems = []
        self.keyitems = []
        self._calls = {}
        self.didranges = 0
        self.didstyles = 0

    def did(self, method, *args, **kwargs):
        if method not in self._calls:
            self._calls[method] = []
        for callargs in self._calls[method]:
            if callargs == (args, kwargs):
                return 1
        self._calls[method].append((args, kwargs))
        return 0

    def bbox(self):
        self.finish()
        return canvas.canvas.bbox(self)


    def processPS(self, file, writer, context, registry, bbox):
        self.finish()
        canvas.canvas.processPS(self, file, writer, context, registry, bbox)

    def processPDF(self, file, writer, context, registry, bbox):
        self.finish()
        canvas.canvas.processPDF(self, file, writer, context, registry, bbox)

    def plot(self, data, styles=None, rangewarning=1):
        if self.didranges and rangewarning:
            logger.warning("axes ranges have already been analysed; no further adjustments will be performed")
        if self.didstyles:
            raise RuntimeError("can't plot further data after dostyles() has been executed")
        singledata = 0
        try:
            for d in data:
                pass
        except:
            usedata = [data]
            singledata = 1
        else:
            usedata = data
        if styles is None:
            for d in usedata:
                if styles is None:
                    styles = d.defaultstyles
                elif styles != d.defaultstyles:
                    raise RuntimeError("defaultstyles differ")
        plotitems = []
        for d in usedata:
            plotitems.append(plotitem(self, d, styles))
        self.plotitems.extend(plotitems)
        if self.didranges:
            for aplotitem in plotitems:
                aplotitem.makedynamicdata(self)
        if singledata:
            return plotitems[0]
        else:
            return plotitems

    def doranges(self):
        if self.did(self.doranges):
            return
        for plotitem in self.plotitems:
            plotitem.adjustaxesstatic(self)
        for plotitem in self.plotitems:
            plotitem.makedynamicdata(self)
        for plotitem in self.plotitems:
            plotitem.adjustaxesdynamic(self)
        self.didranges = 1

    def doaxiscreate(self, axisname):
        if self.did(self.doaxiscreate, axisname):
            return
        self.doaxispositioner(axisname)
        self.axes[axisname].create()

    def dolayout(self):
        raise NotImplementedError

    def dobackground(self):
        pass

    def doaxes(self):
        raise NotImplementedError

    def dostyles(self):
        if self.did(self.dostyles):
            return
        self.dolayout()
        self.dobackground()

        # count the usage of styles and perform selects
        styletotal = {}
        def stylesid(styles):
            return ":".join([str(id(style)) for style in styles])
        for plotitem in self.plotitems:
            try:
                styletotal[stylesid(plotitem.styles)] += 1
            except:
                styletotal[stylesid(plotitem.styles)] = 1
        styleindex = {}
        for plotitem in self.plotitems:
            try:
                styleindex[stylesid(plotitem.styles)] += 1
            except:
                styleindex[stylesid(plotitem.styles)] = 0
            plotitem.selectstyles(self, styleindex[stylesid(plotitem.styles)],
                                        styletotal[stylesid(plotitem.styles)])

        self.didstyles = 1

    def doplotitem(self, plotitem):
        if self.did(self.doplotitem, plotitem):
            return
        self.dostyles()
        plotitem.draw(self)

    def doplot(self):
        for plotitem in self.plotitems:
            self.doplotitem(plotitem)

    def dodata(self):
        logger.warning("dodata() has been deprecated. Use doplot() instead.")
        self.doplot()

    def dokeyitem(self, plotitem):
        if self.did(self.dokeyitem, plotitem):
            return
        self.dostyles()
        if plotitem.title is not None:
            self.keyitems.append(plotitem)

    def dokey(self):
        raise NotImplementedError

    def finish(self):
        self.dobackground()
        self.doaxes()
        self.doplot()
        self.dokey()


class graphxy(graph):

    def __init__(self, xpos=0, ypos=0, width=None, height=None, ratio=goldenmean,
                 key=None, backgroundattrs=None, axesdist=0.8*unit.v_cm, flipped=False,
                 xaxisat=None, yaxisat=None, **axes):
        graph.__init__(self)

        self.xpos = xpos
        self.ypos = ypos
        self.xpos_pt = unit.topt(self.xpos)
        self.ypos_pt = unit.topt(self.ypos)
        self.xaxisat = xaxisat
        self.yaxisat = yaxisat
        self.key = key
        self.backgroundattrs = backgroundattrs
        self.axesdist_pt = unit.topt(axesdist)
        self.flipped = flipped

        self.width = width
        self.height = height
        if width is None:
            if height is None:
                raise ValueError("specify width and/or height")
            else:
                self.width = ratio * self.height
        elif height is None:
            self.height = (1.0/ratio) * self.width
        self.width_pt = unit.topt(self.width)
        self.height_pt = unit.topt(self.height)

        for axisname, aaxis in list(axes.items()):
            if aaxis is not None:
                if not isinstance(aaxis, axis.linkedaxis):
                    self.axes[axisname] = axis.anchoredaxis(aaxis, self.textengine, axisname)
                else:
                    self.axes[axisname] = aaxis
        for axisname, axisat in [("x", xaxisat), ("y", yaxisat)]:
            okey = axisname + "2"
            if axisname not in axes:
                if okey not in axes or axes[okey] is None:
                    self.axes[axisname] = axis.anchoredaxis(axis.linear(), self.textengine, axisname)
                    if okey not in axes:
                        self.axes[okey] = axis.linkedaxis(self.axes[axisname], okey)
                else:
                    self.axes[axisname] = axis.linkedaxis(self.axes[okey], axisname)
            elif okey not in axes and axisat is None:
                self.axes[okey] = axis.linkedaxis(self.axes[axisname], okey)

        if "x" in self.axes:
            self.xbasepath = self.axes["x"].basepath
            self.xvbasepath = self.axes["x"].vbasepath
            self.xgridpath = self.axes["x"].gridpath
            self.xtickpoint_pt = self.axes["x"].tickpoint_pt
            self.xtickpoint = self.axes["x"].tickpoint
            self.xvtickpoint_pt = self.axes["x"].vtickpoint_pt
            self.xvtickpoint = self.axes["x"].tickpoint
            self.xtickdirection = self.axes["x"].tickdirection
            self.xvtickdirection = self.axes["x"].vtickdirection

        if "y" in self.axes:
            self.ybasepath = self.axes["y"].basepath
            self.yvbasepath = self.axes["y"].vbasepath
            self.ygridpath = self.axes["y"].gridpath
            self.ytickpoint_pt = self.axes["y"].tickpoint_pt
            self.ytickpoint = self.axes["y"].tickpoint
            self.yvtickpoint_pt = self.axes["y"].vtickpoint_pt
            self.yvtickpoint = self.axes["y"].vtickpoint
            self.ytickdirection = self.axes["y"].tickdirection
            self.yvtickdirection = self.axes["y"].vtickdirection

        self.axesnames = ([], [])
        for axisname, aaxis in list(self.axes.items()):
            if axisname[0] not in "xy" or (len(axisname) != 1 and (not axisname[1:].isdigit() or
                                                                   axisname[1:] == "1")):
                raise ValueError("invalid axis name")
            if axisname[0] == "x":
                self.axesnames[0].append(axisname)
            else:
                self.axesnames[1].append(axisname)
            aaxis.setcreatecall(self.doaxiscreate, axisname)

        self.axespositioners = dict(x=positioner.lineaxispos_pt(self.xpos_pt, self.ypos_pt,
                                                                self.xpos_pt + self.width_pt, self.ypos_pt,
                                                                (0, 1), self.xvgridpath),
                                    x2=positioner.lineaxispos_pt(self.xpos_pt, self.ypos_pt + self.height_pt,
                                                                 self.xpos_pt + self.width_pt, self.ypos_pt + self.height_pt,
                                                                 (0, -1), self.xvgridpath),
                                    y=positioner.lineaxispos_pt(self.xpos_pt, self.ypos_pt,
                                                                self.xpos_pt, self.ypos_pt + self.height_pt,
                                                                (1, 0), self.yvgridpath),
                                    y2=positioner.lineaxispos_pt(self.xpos_pt + self.width_pt, self.ypos_pt,
                                                                 self.xpos_pt + self.width_pt, self.ypos_pt + self.height_pt,
                                                                 (-1, 0), self.yvgridpath))
        if self.flipped:
            self.axespositioners = dict(x=self.axespositioners["y2"],
                                        y2=self.axespositioners["x2"],
                                        y=self.axespositioners["x"],
                                        x2=self.axespositioners["y"])

    def pos_pt(self, x, y, xaxis=None, yaxis=None):
        if xaxis is None:
            xaxis = self.axes["x"]
        if yaxis is None:
            yaxis = self.axes["y"]
        vx = xaxis.convert(x)
        vy = yaxis.convert(y)
        if self.flipped:
            vx, vy = vy, vx
        return (self.xpos_pt + vx*self.width_pt,
                self.ypos_pt + vy*self.height_pt)

    def pos(self, x, y, xaxis=None, yaxis=None):
        if xaxis is None:
            xaxis = self.axes["x"]
        if yaxis is None:
            yaxis = self.axes["y"]
        vx = xaxis.convert(x)
        vy = yaxis.convert(y)
        if self.flipped:
            vx, vy = vy, vx
        return (self.xpos + vx*self.width,
                self.ypos + vy*self.height)

    def vpos_pt(self, vx, vy):
        if self.flipped:
            vx, vy = vy, vx
        return (self.xpos_pt + vx*self.width_pt,
                self.ypos_pt + vy*self.height_pt)

    def vpos(self, vx, vy):
        if self.flipped:
            vx, vy = vy, vx
        return (self.xpos + vx*self.width,
                self.ypos + vy*self.height)

    def vzindex(self, vx, vy):
        return 0

    def vangle(self, vx1, vy1, vx2, vy2, vx3, vy3):
        return 1

    def vgeodesic(self, vx1, vy1, vx2, vy2):
        """returns a geodesic path between two points in graph coordinates"""
        if self.flipped:
            vx1, vy1 = vy1, vx1
            vx2, vy2 = vy2, vx2
        return path.line_pt(self.xpos_pt + vx1*self.width_pt,
                            self.ypos_pt + vy1*self.height_pt,
                            self.xpos_pt + vx2*self.width_pt,
                            self.ypos_pt + vy2*self.height_pt)

    def vgeodesic_el(self, vx1, vy1, vx2, vy2):
        """returns a geodesic path element between two points in graph coordinates"""
        if self.flipped:
            vx1, vy1 = vy1, vx1
            vx2, vy2 = vy2, vx2
        return path.lineto_pt(self.xpos_pt + vx2*self.width_pt,
                              self.ypos_pt + vy2*self.height_pt)

    def vcap_pt(self, coordinate, length_pt, vx, vy):
        """returns an error cap path for a given coordinate, lengths and
        point in graph coordinates"""
        if self.flipped:
            coordinate = 1-coordinate
            vx, vy = vy, vx
        if coordinate == 0:
            return path.line_pt(self.xpos_pt + vx*self.width_pt - 0.5*length_pt,
                                self.ypos_pt + vy*self.height_pt,
                                self.xpos_pt + vx*self.width_pt + 0.5*length_pt,
                                self.ypos_pt + vy*self.height_pt)
        elif coordinate == 1:
            return path.line_pt(self.xpos_pt + vx*self.width_pt,
                                self.ypos_pt + vy*self.height_pt - 0.5*length_pt,
                                self.xpos_pt + vx*self.width_pt,
                                self.ypos_pt + vy*self.height_pt + 0.5*length_pt)
        else:
            raise ValueError("direction invalid")

    def xvgridpath(self, vx):
        return path.line_pt(self.xpos_pt + vx*self.width_pt, self.ypos_pt,
                            self.xpos_pt + vx*self.width_pt, self.ypos_pt + self.height_pt)

    def yvgridpath(self, vy):
        return path.line_pt(self.xpos_pt, self.ypos_pt + vy*self.height_pt,
                            self.xpos_pt + self.width_pt, self.ypos_pt + vy*self.height_pt)

    def autokeygraphattrs(self):
        return dict(direction="vertical", length=self.height)

    def autokeygraphtrafo(self, keygraph):
        dependsonaxisnumber = None
        if self.flipped:
            dependsonaxisname = "x"
        else:
            dependsonaxisname = "y"
        for axisname in self.axes:
            if axisname[0] == dependsonaxisname:
                if len(axisname) == 1:
                    axisname += "1"
                axisnumber = int(axisname[1:])
                if not (axisnumber % 2) and not self.flipped or (axisnumber % 2) and self.flipped:
                    if dependsonaxisnumber is None or dependsonaxisnumber < axisnumber:
                        dependsonaxisnumber = axisnumber
        if dependsonaxisnumber is None:
            x_pt = self.xpos_pt + self.width_pt
        else:
            if dependsonaxisnumber > 1:
                dependsonaxisname += str(dependsonaxisnumber)
            self.doaxiscreate(dependsonaxisname)
            x_pt = self.axes[dependsonaxisname].positioner.x1_pt + self.axes[dependsonaxisname].canvas.extent_pt
        x_pt += self.axesdist_pt
        return trafo.translate_pt(x_pt, self.ypos_pt)

    def axisatv(self, axis, v):
        if axis.positioner.fixtickdirection[0]:
            # it is a y-axis
            t = trafo.translate_pt(self.xpos_pt + v*self.width_pt - axis.positioner.x1_pt, 0)
        else:
            # it is an x-axis
            t = trafo.translate_pt(0, self.ypos_pt + v*self.height_pt - axis.positioner.y1_pt)
        c = canvas.canvas()
        for layer, subcanvas in list(axis.canvas.layers.items()):
            c.layer(layer).insert(subcanvas, [t])
        assert len(axis.canvas.layers) == len(axis.canvas.items), str(axis.canvas.items)
        axis.canvas = c

    def doaxispositioner(self, axisname):
        if self.did(self.doaxispositioner, axisname):
            return
        self.doranges()
        if axisname in ["x", "x2", "y", "y2"]:
            self.axes[axisname].setpositioner(self.axespositioners[axisname])
        else:
            if axisname[1:] == "3":
                dependsonaxisname = axisname[0]
            else:
                dependsonaxisname = "%s%d" % (axisname[0], int(axisname[1:]) - 2)
            self.doaxiscreate(dependsonaxisname)
            sign = 2*(int(axisname[1:]) % 2) - 1
            if axisname[0] == "x" and self.flipped:
                sign = -sign
            if axisname[0] == "x" and not self.flipped or axisname[0] == "y" and self.flipped:
                y_pt = self.axes[dependsonaxisname].positioner.y1_pt - sign * (self.axes[dependsonaxisname].canvas.extent_pt + self.axesdist_pt)
                self.axes[axisname].setpositioner(positioner.lineaxispos_pt(self.xpos_pt, y_pt,
                                                                            self.xpos_pt + self.width_pt, y_pt,
                                                                            (0, sign), self.xvgridpath))
            else:
                x_pt = self.axes[dependsonaxisname].positioner.x1_pt - sign * (self.axes[dependsonaxisname].canvas.extent_pt + self.axesdist_pt)
                self.axes[axisname].setpositioner(positioner.lineaxispos_pt(x_pt, self.ypos_pt,
                                                                            x_pt, self.ypos_pt + self.height_pt,
                                                                            (sign, 0), self.yvgridpath))

    def dolayout(self):
        if self.did(self.dolayout):
            return
        for axisname in list(self.axes.keys()):
            self.doaxiscreate(axisname)
        if self.xaxisat is not None:
            self.axisatv(self.axes["x"], self.axes["y"].convert(self.xaxisat))
        if self.yaxisat is not None:
            self.axisatv(self.axes["y"], self.axes["x"].convert(self.yaxisat))

    def dobackground(self):
        if self.did(self.dobackground):
            return
        if self.backgroundattrs is not None:
            self.layer("background").draw(path.rect_pt(self.xpos_pt, self.ypos_pt, self.width_pt, self.height_pt),
                                          self.backgroundattrs)

    def doaxes(self):
        if self.did(self.doaxes):
            return
        self.dolayout()
        self.dobackground()
        for axis in list(self.axes.values()):
            for layer, canvas in list(axis.canvas.layers.items()):
                self.layer("axes.%s" % layer).insert(canvas)
            assert len(axis.canvas.layers) == len(axis.canvas.items), str(axis.canvas.items)

    def dokey(self):
        if self.did(self.dokey):
            return
        self.dobackground()
        for plotitem in self.plotitems:
            self.dokeyitem(plotitem)
        if self.key is not None:
            c = self.key.paint(self.keyitems)
            bbox = c.bbox()
            def parentchildalign(pmin, pmax, cmin, cmax, pos, dist, inside):
                ppos = pmin+0.5*(cmax-cmin)+dist+pos*(pmax-pmin-cmax+cmin-2*dist)
                cpos = 0.5*(cmin+cmax)+(1-inside)*(1-2*pos)*(cmax-cmin+2*dist)
                return ppos-cpos
            if bbox:
                x = parentchildalign(self.xpos_pt, self.xpos_pt+self.width_pt,
                                     bbox.llx_pt, bbox.urx_pt,
                                     self.key.hpos, unit.topt(self.key.hdist), self.key.hinside)
                y = parentchildalign(self.ypos_pt, self.ypos_pt+self.height_pt,
                                     bbox.lly_pt, bbox.ury_pt,
                                     self.key.vpos, unit.topt(self.key.vdist), self.key.vinside)
                self.layer("key").insert(c, [trafo.translate_pt(x, y)])



class graphx(graphxy):

    def __init__(self, xpos=0, ypos=0, length=None, size=0.5*unit.v_cm, direction="vertical",
                 key=None, backgroundattrs=None, axesdist=0.8*unit.v_cm, **axes):
        for name in axes:
            if not name.startswith("x"):
                raise ValueError("Only x axes are allowed")
        self.direction = direction
        if self.direction == "vertical":
            kwargsxy = dict(width=size, height=length, flipped=True)
        elif self.direction == "horizontal":
            kwargsxy = dict(width=length, height=size)
        else:
            raise ValueError("vertical or horizontal direction required")
        kwargsxy.update(**axes)

        graphxy.__init__(self, xpos=xpos, ypos=ypos, ratio=None, key=key, y=axis.lin(min=0, max=1, parter=None),
                         backgroundattrs=backgroundattrs, axesdist=axesdist, **kwargsxy)

    def pos_pt(self, x, xaxis=None):
        return graphxy.pos_pt(self, x, 0.5, xaxis)

    def pos(self, x, xaxis=None):
        return graphxy.pos(self, x, 0.5, xaxis)

    def vpos_pt(self, vx):
        return graphxy.vpos_pt(self, vx, 0.5)

    def vpos(self, vx):
        return graphxy.vpos(self, vx, 0.5)

    def vgeodesic(self, vx1, vx2):
        return graphxy.vgeodesic(self, vx1, 0.5, vx2, 0.5)

    def vgeodesic_el(self, vx1, vy1, vx2, vy2):
        return graphxy.vgeodesic_el(self, vx1, 0.5, vx2, 0.5)

    def vcap_pt(self, coordinate, length_pt, vx):
        if coordinate == 0:
            return graphxy.vcap_pt(self, coordinate, length_pt, vx, 0.5)
        else:
            raise ValueError("direction invalid")

    def xvgridpath(self, vx):
        return graphxy.xvgridpath(self, vx)

    def yvgridpath(self, vy):
        raise Exception("This method does not exist on a one dimensional graph.")

    def axisatv(self, axis, v):
        raise Exception("This method does not exist on a one dimensional graph.")



class graphxyz(graph):

    class central:

        def __init__(self, distance, phi, theta, anglefactor=math.pi/180):
            phi *= anglefactor
            theta *= anglefactor
            self.distance = distance

            self.a = (-math.sin(phi), math.cos(phi), 0)
            self.b = (-math.cos(phi)*math.sin(theta),
                      -math.sin(phi)*math.sin(theta),
                      math.cos(theta))
            self.eye = (distance*math.cos(phi)*math.cos(theta),
                        distance*math.sin(phi)*math.cos(theta),
                        distance*math.sin(theta))

        def point(self, x, y, z):
            d0 = (self.a[0]*self.b[1]*(z-self.eye[2])
                + self.a[2]*self.b[0]*(y-self.eye[1])
                + self.a[1]*self.b[2]*(x-self.eye[0])
                - self.a[2]*self.b[1]*(x-self.eye[0])
                - self.a[0]*self.b[2]*(y-self.eye[1])
                - self.a[1]*self.b[0]*(z-self.eye[2]))
            da = (self.eye[0]*self.b[1]*(z-self.eye[2])
                + self.eye[2]*self.b[0]*(y-self.eye[1])
                + self.eye[1]*self.b[2]*(x-self.eye[0])
                - self.eye[2]*self.b[1]*(x-self.eye[0])
                - self.eye[0]*self.b[2]*(y-self.eye[1])
                - self.eye[1]*self.b[0]*(z-self.eye[2]))
            db = (self.a[0]*self.eye[1]*(z-self.eye[2])
                + self.a[2]*self.eye[0]*(y-self.eye[1])
                + self.a[1]*self.eye[2]*(x-self.eye[0])
                - self.a[2]*self.eye[1]*(x-self.eye[0])
                - self.a[0]*self.eye[2]*(y-self.eye[1])
                - self.a[1]*self.eye[0]*(z-self.eye[2]))
            return da/d0, db/d0

        def zindex(self, x, y, z):
            return math.sqrt((x-self.eye[0])*(x-self.eye[0])+(y-self.eye[1])*(y-self.eye[1])+(z-self.eye[2])*(z-self.eye[2]))-self.distance

        def angle(self, x1, y1, z1, x2, y2, z2, x3, y3, z3):
            sx = (x1-self.eye[0])
            sy = (y1-self.eye[1])
            sz = (z1-self.eye[2])
            nx = (y2-y1)*(z3-z1)-(z2-z1)*(y3-y1)
            ny = (z2-z1)*(x3-x1)-(x2-x1)*(z3-z1)
            nz = (x2-x1)*(y3-y1)-(y2-y1)*(x3-x1)
            return (sx*nx+sy*ny+sz*nz)/math.sqrt(nx*nx+ny*ny+nz*nz)/math.sqrt(sx*sx+sy*sy+sz*sz)


    class parallel:

        def __init__(self, phi, theta, anglefactor=math.pi/180):
            phi *= anglefactor
            theta *= anglefactor

            self.a = (-math.sin(phi), math.cos(phi), 0)
            self.b = (-math.cos(phi)*math.sin(theta),
                      -math.sin(phi)*math.sin(theta),
                      math.cos(theta))
            self.c = (-math.cos(phi)*math.cos(theta),
                      -math.sin(phi)*math.cos(theta),
                      -math.sin(theta))

        def point(self, x, y, z):
            return self.a[0]*x+self.a[1]*y+self.a[2]*z, self.b[0]*x+self.b[1]*y+self.b[2]*z

        def zindex(self, x, y, z):
            return self.c[0]*x+self.c[1]*y+self.c[2]*z

        def angle(self, x1, y1, z1, x2, y2, z2, x3, y3, z3):
            nx = (y2-y1)*(z3-z1)-(z2-z1)*(y3-y1)
            ny = (z2-z1)*(x3-x1)-(x2-x1)*(z3-z1)
            nz = (x2-x1)*(y3-y1)-(y2-y1)*(x3-x1)
            return (self.c[0]*nx+self.c[1]*ny+self.c[2]*nz)/math.sqrt(nx*nx+ny*ny+nz*nz)


    def __init__(self, xpos=0, ypos=0, size=None,
                 xscale=1, yscale=1, zscale=1/goldenmean, xy12axesat=None, xy12axesatname="z",
                 projector=central(10, -30, 30), axesdist=0.8*unit.v_cm, key=None,
                 **axes):
        graph.__init__(self)
        for name in ["hiddenaxes.grid", "hiddenaxes.baseline", "hiddenaxes.ticks", "hiddenaxes.labels", "hiddenaxes.title"]:
            self.layer(name)
        self.layer("hiddenaxes", below="filldata")

        self.xpos = xpos
        self.ypos = ypos
        self.size = size
        self.xpos_pt = unit.topt(xpos)
        self.ypos_pt = unit.topt(ypos)
        self.size_pt = unit.topt(size)
        self.xscale = xscale
        self.yscale = yscale
        self.zscale = zscale
        self.xy12axesat = xy12axesat
        self.xy12axesatname = xy12axesatname
        self.projector = projector
        self.axesdist_pt = unit.topt(axesdist)
        self.key = key

        self.xorder = projector.zindex(0, -1, 0) > projector.zindex(0, 1, 0) and 1 or 0
        self.yorder = projector.zindex(-1, 0, 0) > projector.zindex(1, 0, 0) and 1 or 0
        self.zindexscale = math.sqrt(xscale*xscale+yscale*yscale+zscale*zscale)

        # the pXYshow attributes are booleans stating whether plane perpendicular to axis X
        # at the virtual graph coordinate Y will be hidden by data or not. An axis is considered
        # to be visible if one of the two planes it is part of is visible. Other axes are drawn
        # in the hiddenaxes layer (i.e. layer group).
        # TODO: Tick and grid visibility is treated like the axis visibility at the moment.
        self.pz0show = self.vangle(0, 0, 0, 1, 0, 0, 1, 1, 0) > 0
        self.pz1show = self.vangle(0, 0, 1, 0, 1, 1, 1, 1, 1) > 0
        self.py0show = self.vangle(0, 0, 0, 0, 0, 1, 1, 0, 1) > 0
        self.py1show = self.vangle(0, 1, 0, 1, 1, 0, 1, 1, 1) > 0
        self.px0show = self.vangle(0, 0, 0, 0, 1, 0, 0, 1, 1) > 0
        self.px1show = self.vangle(1, 0, 0, 1, 0, 1, 1, 1, 1) > 0

        for axisname, aaxis in list(axes.items()):
            if aaxis is not None:
                if not isinstance(aaxis, axis.linkedaxis):
                    self.axes[axisname] = axis.anchoredaxis(aaxis, self.textengine, axisname)
                else:
                    self.axes[axisname] = aaxis
        for axisname in ["x", "y"]:
            okey = axisname + "2"
            if axisname not in axes:
                if okey not in axes or axes[okey] is None:
                    self.axes[axisname] = axis.anchoredaxis(axis.linear(), self.textengine, axisname)
                    if okey not in axes:
                        self.axes[okey] = axis.linkedaxis(self.axes[axisname], okey)
                else:
                    self.axes[axisname] = axis.linkedaxis(self.axes[okey], axisname)
            elif okey not in axes:
                self.axes[okey] = axis.linkedaxis(self.axes[axisname], okey)
        if "z" not in axes:
            self.axes["z"] = axis.anchoredaxis(axis.linear(), self.textengine, "z")

        if "x" in self.axes:
            self.xbasepath = self.axes["x"].basepath
            self.xvbasepath = self.axes["x"].vbasepath
            self.xgridpath = self.axes["x"].gridpath
            self.xtickpoint_pt = self.axes["x"].tickpoint_pt
            self.xtickpoint = self.axes["x"].tickpoint
            self.xvtickpoint_pt = self.axes["x"].vtickpoint_pt
            self.xvtickpoint = self.axes["x"].tickpoint
            self.xtickdirection = self.axes["x"].tickdirection
            self.xvtickdirection = self.axes["x"].vtickdirection

        if "y" in self.axes:
            self.ybasepath = self.axes["y"].basepath
            self.yvbasepath = self.axes["y"].vbasepath
            self.ygridpath = self.axes["y"].gridpath
            self.ytickpoint_pt = self.axes["y"].tickpoint_pt
            self.ytickpoint = self.axes["y"].tickpoint
            self.yvtickpoint_pt = self.axes["y"].vtickpoint_pt
            self.yvtickpoint = self.axes["y"].vtickpoint
            self.ytickdirection = self.axes["y"].tickdirection
            self.yvtickdirection = self.axes["y"].vtickdirection

        if "z" in self.axes:
            self.zbasepath = self.axes["z"].basepath
            self.zvbasepath = self.axes["z"].vbasepath
            self.zgridpath = self.axes["z"].gridpath
            self.ztickpoint_pt = self.axes["z"].tickpoint_pt
            self.ztickpoint = self.axes["z"].tickpoint
            self.zvtickpoint_pt = self.axes["z"].vtickpoint
            self.zvtickpoint = self.axes["z"].vtickpoint
            self.ztickdirection = self.axes["z"].tickdirection
            self.zvtickdirection = self.axes["z"].vtickdirection

        self.axesnames = ([], [], [])
        for axisname, aaxis in list(self.axes.items()):
            if axisname[0] not in "xyz" or (len(axisname) != 1 and (not axisname[1:].isdigit() or
                                                                    axisname[1:] == "1")):
                raise ValueError("invalid axis name")
            if axisname[0] == "x":
                self.axesnames[0].append(axisname)
            elif axisname[0] == "y":
                self.axesnames[1].append(axisname)
            else:
                self.axesnames[2].append(axisname)
            aaxis.setcreatecall(self.doaxiscreate, axisname)

    def pos_pt(self, x, y, z, xaxis=None, yaxis=None, zaxis=None):
        if xaxis is None:
            xaxis = self.axes["x"]
        if yaxis is None:
            yaxis = self.axes["y"]
        if zaxis is None:
            zaxis = self.axes["z"]
        return self.vpos_pt(xaxis.convert(x), yaxis.convert(y), zaxis.convert(z))

    def pos(self, x, y, z, xaxis=None, yaxis=None, zaxis=None):
        if xaxis is None:
            xaxis = self.axes["x"]
        if yaxis is None:
            yaxis = self.axes["y"]
        if zaxis is None:
            zaxis = self.axes["z"]
        return self.vpos(xaxis.convert(x), yaxis.convert(y), zaxis.convert(z))

    def vpos_pt(self, vx, vy, vz):
        x, y = self.projector.point(2*self.xscale*(vx - 0.5),
                                    2*self.yscale*(vy - 0.5),
                                    2*self.zscale*(vz - 0.5))
        return self.xpos_pt+x*self.size_pt, self.ypos_pt+y*self.size_pt

    def vpos(self, vx, vy, vz):
        x, y = self.projector.point(2*self.xscale*(vx - 0.5),
                                    2*self.yscale*(vy - 0.5),
                                    2*self.zscale*(vz - 0.5))
        return self.xpos+x*self.size, self.ypos+y*self.size

    def vzindex(self, vx, vy, vz):
        return self.projector.zindex(2*self.xscale*(vx - 0.5),
                                     2*self.yscale*(vy - 0.5),
                                     2*self.zscale*(vz - 0.5))/self.zindexscale

    def vangle(self, vx1, vy1, vz1, vx2, vy2, vz2, vx3, vy3, vz3):
        return self.projector.angle(2*self.xscale*(vx1 - 0.5),
                                    2*self.yscale*(vy1 - 0.5),
                                    2*self.zscale*(vz1 - 0.5),
                                    2*self.xscale*(vx2 - 0.5),
                                    2*self.yscale*(vy2 - 0.5),
                                    2*self.zscale*(vz2 - 0.5),
                                    2*self.xscale*(vx3 - 0.5),
                                    2*self.yscale*(vy3 - 0.5),
                                    2*self.zscale*(vz3 - 0.5))

    def vgeodesic(self, vx1, vy1, vz1, vx2, vy2, vz2):
        """returns a geodesic path between two points in graph coordinates"""
        return path.line_pt(*(self.vpos_pt(vx1, vy1, vz1) + self.vpos_pt(vx2, vy2, vz2)))

    def vgeodesic_el(self, vx1, vy1, vz1, vx2, vy2, vz2):
        """returns a geodesic path element between two points in graph coordinates"""
        return path.lineto_pt(*self.vpos_pt(vx2, vy2, vz2))

    def vcap_pt(self, coordinate, length_pt, vx, vy, vz):
        """returns an error cap path for a given coordinate, lengths and
        point in graph coordinates"""
        if coordinate == 0:
            return self.vgeodesic(vx-0.5*length_pt/self.size_pt, vy, vz, vx+0.5*length_pt/self.size_pt, vy, vz)
        elif coordinate == 1:
            return self.vgeodesic(vx, vy-0.5*length_pt/self.size_pt, vz, vx, vy+0.5*length_pt/self.size_pt, vz)
        elif coordinate == 2:
            return self.vgeodesic(vx, vy, vz-0.5*length_pt/self.size_pt, vx, vy, vz+0.5*length_pt/self.size_pt)
        else:
            raise ValueError("direction invalid")

    def xvtickdirection(self, vx):
        if self.xorder:
            x1_pt, y1_pt = self.vpos_pt(vx, 1, 0)
            x2_pt, y2_pt = self.vpos_pt(vx, 0, 0)
        else:
            x1_pt, y1_pt = self.vpos_pt(vx, 0, 0)
            x2_pt, y2_pt = self.vpos_pt(vx, 1, 0)
        dx_pt = x2_pt - x1_pt
        dy_pt = y2_pt - y1_pt
        norm = math.hypot(dx_pt, dy_pt)
        return dx_pt/norm, dy_pt/norm

    def yvtickdirection(self, vy):
        if self.yorder:
            x1_pt, y1_pt = self.vpos_pt(1, vy, 0)
            x2_pt, y2_pt = self.vpos_pt(0, vy, 0)
        else:
            x1_pt, y1_pt = self.vpos_pt(0, vy, 0)
            x2_pt, y2_pt = self.vpos_pt(1, vy, 0)
        dx_pt = x2_pt - x1_pt
        dy_pt = y2_pt - y1_pt
        norm = math.hypot(dx_pt, dy_pt)
        return dx_pt/norm, dy_pt/norm

    def vtickdirection(self, vx1, vy1, vz1, vx2, vy2, vz2):
        x1_pt, y1_pt = self.vpos_pt(vx1, vy1, vz1)
        x2_pt, y2_pt = self.vpos_pt(vx2, vy2, vz2)
        dx_pt = x2_pt - x1_pt
        dy_pt = y2_pt - y1_pt
        norm = math.hypot(dx_pt, dy_pt)
        return dx_pt/norm, dy_pt/norm

    def xvgridpath(self, vx):
        return path.path(path.moveto_pt(*self.vpos_pt(vx, 0, 0)),
                         path.lineto_pt(*self.vpos_pt(vx, 1, 0)),
                         path.lineto_pt(*self.vpos_pt(vx, 1, 1)),
                         path.lineto_pt(*self.vpos_pt(vx, 0, 1)),
                         path.closepath())

    def yvgridpath(self, vy):
        return path.path(path.moveto_pt(*self.vpos_pt(0, vy, 0)),
                         path.lineto_pt(*self.vpos_pt(1, vy, 0)),
                         path.lineto_pt(*self.vpos_pt(1, vy, 1)),
                         path.lineto_pt(*self.vpos_pt(0, vy, 1)),
                         path.closepath())

    def zvgridpath(self, vz):
        return path.path(path.moveto_pt(*self.vpos_pt(0, 0, vz)),
                         path.lineto_pt(*self.vpos_pt(1, 0, vz)),
                         path.lineto_pt(*self.vpos_pt(1, 1, vz)),
                         path.lineto_pt(*self.vpos_pt(0, 1, vz)),
                         path.closepath())

    def autokeygraphattrs(self):
        return dict(direction="vertical", length=self.size)

    def autokeygraphtrafo(self, keygraph):
        self.doaxes()
        x_pt = self.layer("axes").bbox().right_pt() + self.axesdist_pt
        y_pt = 0.5*(self.layer("axes").bbox().top_pt() + self.layer("axes").bbox().bottom_pt() - self.size_pt)
        return trafo.translate_pt(x_pt, y_pt)

    def doaxispositioner(self, axisname):
        if self.did(self.doaxispositioner, axisname):
            return
        self.doranges()
        if self.xy12axesat is not None:
            self.doaxiscreate(self.xy12axesatname)
            self.doaxispositioner(self.xy12axesatname)
            xy12axesatv = self.axes[self.xy12axesatname].convert(self.xy12axesat)
        else:
            xy12axesatv = 0
        if axisname == "x":
            self.axes[axisname].setpositioner(positioner.flexlineaxispos_pt(lambda vx: self.vpos_pt(vx, self.xorder, xy12axesatv),
                                                                            lambda vx: self.vtickdirection(vx, self.xorder, 0, vx, 1-self.xorder, xy12axesatv),
                                                                            self.xvgridpath))
            if self.xorder:
                self.axes[axisname].hidden = not self.py1show and not self.pz0show
            else:
                self.axes[axisname].hidden = not self.py0show and not self.pz0show
        elif axisname == "x2":
            self.axes[axisname].setpositioner(positioner.flexlineaxispos_pt(lambda vx: self.vpos_pt(vx, 1-self.xorder, xy12axesatv),
                                                                            lambda vx: self.vtickdirection(vx, 1-self.xorder, 0, vx, self.xorder, xy12axesatv),
                                                                            self.xvgridpath))
            if self.xorder:
                self.axes[axisname].hidden = not self.py0show and not self.pz0show
            else:
                self.axes[axisname].hidden = not self.py1show and not self.pz0show
        elif axisname == "x3":
            self.axes[axisname].setpositioner(positioner.flexlineaxispos_pt(lambda vx: self.vpos_pt(vx, self.xorder, 1),
                                                                            lambda vx: self.vtickdirection(vx, self.xorder, 1, vx, 1-self.xorder, 1),
                                                                            self.xvgridpath))
            if self.xorder:
                self.axes[axisname].hidden = not self.py1show and not self.pz1show
            else:
                self.axes[axisname].hidden = not self.py0show and not self.pz1show
        elif axisname == "x4":
            self.axes[axisname].setpositioner(positioner.flexlineaxispos_pt(lambda vx: self.vpos_pt(vx, 1-self.xorder, 1),
                                                                            lambda vx: self.vtickdirection(vx, 1-self.xorder, 1, vx, self.xorder, 1),
                                                                            self.xvgridpath))
            if self.xorder:
                self.axes[axisname].hidden = not self.py0show and not self.pz1show
            else:
                self.axes[axisname].hidden = not self.py1show and not self.pz1show
        elif axisname == "y":
            self.axes[axisname].setpositioner(positioner.flexlineaxispos_pt(lambda vy: self.vpos_pt(self.yorder, vy, xy12axesatv),
                                                                            lambda vy: self.vtickdirection(self.yorder, vy, 0, 1-self.yorder, vy, xy12axesatv),
                                                                            self.yvgridpath))
            if self.yorder:
                self.axes[axisname].hidden = not self.px1show and not self.pz0show
            else:
                self.axes[axisname].hidden = not self.px0show and not self.pz0show
        elif axisname == "y2":
            self.axes[axisname].setpositioner(positioner.flexlineaxispos_pt(lambda vy: self.vpos_pt(1-self.yorder, vy, xy12axesatv),
                                                                            lambda vy: self.vtickdirection(1-self.yorder, vy, 0, self.yorder, vy, xy12axesatv),
                                                                            self.yvgridpath))
            if self.yorder:
                self.axes[axisname].hidden = not self.px0show and not self.pz0show
            else:
                self.axes[axisname].hidden = not self.px1show and not self.pz0show
        elif axisname == "y3":
            self.axes[axisname].setpositioner(positioner.flexlineaxispos_pt(lambda vy: self.vpos_pt(self.yorder, vy, 1),
                                                                            lambda vy: self.vtickdirection(self.yorder, vy, 1, 1-self.yorder, vy, 1),
                                                                            self.yvgridpath))
            if self.yorder:
                self.axes[axisname].hidden = not self.px1show and not self.pz1show
            else:
                self.axes[axisname].hidden = not self.px0show and not self.pz1show
        elif axisname == "y4":
            self.axes[axisname].setpositioner(positioner.flexlineaxispos_pt(lambda vy: self.vpos_pt(1-self.yorder, vy, 1),
                                                                            lambda vy: self.vtickdirection(1-self.yorder, vy, 1, self.yorder, vy, 1),
                                                                            self.yvgridpath))
            if self.yorder:
                self.axes[axisname].hidden = not self.px0show and not self.pz1show
            else:
                self.axes[axisname].hidden = not self.px1show and not self.pz1show
        elif axisname == "z":
            self.axes[axisname].setpositioner(positioner.flexlineaxispos_pt(lambda vz: self.vpos_pt(0, 0, vz),
                                                                            lambda vz: self.vtickdirection(0, 0, vz, 1, 1, vz),
                                                                            self.zvgridpath))
            self.axes[axisname].hidden = not self.px0show and not self.py0show
        elif axisname == "z2":
            self.axes[axisname].setpositioner(positioner.flexlineaxispos_pt(lambda vz: self.vpos_pt(1, 0, vz),
                                                                            lambda vz: self.vtickdirection(1, 0, vz, 0, 1, vz),
                                                                            self.zvgridpath))
            self.axes[axisname].hidden = not self.px1show and not self.py0show
        elif axisname == "z3":
            self.axes[axisname].setpositioner(positioner.flexlineaxispos_pt(lambda vz: self.vpos_pt(0, 1, vz),
                                                                            lambda vz: self.vtickdirection(0, 1, vz, 1, 0, vz),
                                                                            self.zvgridpath))
            self.axes[axisname].hidden = not self.px0show and not self.py1show
        elif axisname == "z4":
            self.axes[axisname].setpositioner(positioner.flexlineaxispos_pt(lambda vz: self.vpos_pt(1, 1, vz),
                                                                            lambda vz: self.vtickdirection(1, 1, vz, 0, 0, vz),
                                                                            self.zvgridpath))
            self.axes[axisname].hidden = not self.px1show and not self.py1show
        else:
            raise NotImplementedError("4 axis per dimension supported only")

    def dolayout(self):
        if self.did(self.dolayout):
            return
        for axisname in list(self.axes.keys()):
            self.doaxiscreate(axisname)

    def dobackground(self):
        if self.did(self.dobackground):
            return

    def doaxes(self):
        if self.did(self.doaxes):
            return
        self.dolayout()
        self.dobackground()
        for axis in list(self.axes.values()):
            if axis.hidden:
                self.layer("hiddenaxes").insert(axis.canvas)
            else:
                self.layer("axes").insert(axis.canvas)

    def dokey(self):
        if self.did(self.dokey):
            return
        self.dobackground()
        for plotitem in self.plotitems:
            self.dokeyitem(plotitem)
        if self.key is not None:
            c = self.key.paint(self.keyitems)
            bbox = c.bbox()
            def parentchildalign(pmin, pmax, cmin, cmax, pos, dist, inside):
                ppos = pmin+0.5*(cmax-cmin)+dist+pos*(pmax-pmin-cmax+cmin-2*dist)
                cpos = 0.5*(cmin+cmax)+(1-inside)*(1-2*pos)*(cmax-cmin+2*dist)
                return ppos-cpos
            if bbox:
                x = parentchildalign(self.xpos_pt, self.xpos_pt+self.size_pt,
                                     bbox.llx_pt, bbox.urx_pt,
                                     self.key.hpos, unit.topt(self.key.hdist), self.key.hinside)
                y = parentchildalign(self.ypos_pt, self.ypos_pt+self.size_pt,
                                     bbox.lly_pt, bbox.ury_pt,
                                     self.key.vpos, unit.topt(self.key.vdist), self.key.vinside)
                self.insert(c, [trafo.translate_pt(x, y)])
