# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2004-2006 André Wobst <wobsta@pyx-project.org>
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


import datetime
from pyx.graph import style
from pyx.graph.axis import axis, rater

"""some experimental code for creating a time axis
- it needs python 2.3 to be used (it is based on the new datetime data type)
- a timeaxis is always based on the datetime data type (there is no distinction between times and dates)
"""

class timeaxis(axis.linear):
    "time axis mapping based "

    # TODO: how to deal with reversed timeaxis?

    def __init__(self, parter=None, rater=rater.linear(), **args):
        super().__init__(self, divisor=None, **args)
        self.parter = parter
        self.rater = rater

    def convert(self, data, x):
        # XXX float division of timedelta instances
        def mstimedelta(td):
            "return the timedelta in microseconds"
            return td.microseconds + 1000000*(td.seconds + 3600*24*td.days)
        return mstimedelta(x - data.min) / float(mstimedelta(data.max - data.min))
        # we could store float(mstimedelta(self.dx)) instead of self.dx, but
        # I prefer a different solution (not based on huge integers) for the
        # future

    zero = datetime.timedelta(0)


class timetick(datetime.datetime):

    # TODO: http://stackoverflow.com/questions/399022/why-cant-i-subclass-datetime-date
    # possible fix: make the datetime an attribute of the tick

    def __new__(cls, year, month, day, ticklevel=0, labellevel=0, label=None, labelattrs=[], **kwargs):
        return datetime.datetime.__new__(cls, year, month, day, **kwargs)

    def __init__(self, year, month, day, ticklevel=0, labellevel=0, label=None, labelattrs=[], **kwargs):
        self.ticklevel = ticklevel
        self.labellevel = labellevel
        self.label = label
        self.labelattrs = labelattrs[:]

    def merge(self, other):
        if self.ticklevel is None or (other.ticklevel is not None and other.ticklevel < self.ticklevel):
            self.ticklevel = other.ticklevel
        if self.labellevel is None or (other.labellevel is not None and other.labellevel < self.labellevel):
            self.labellevel = other.labellevel


class timetexter:

    def __init__(self, format="%c"):
        self.format = format

    def labels(self, ticks):
        for tick in ticks:
            if tick.labellevel is not None and tick.label is None:
                tick.label = tick.strftime(self.format)



