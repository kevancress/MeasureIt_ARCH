# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2002-2011 Jörg Lehmann <joerg@pyx-project.org>
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

import math
from . import attr, baseclasses, unit

# some helper routines

def _rmatrix(angle):
    phi = math.pi*angle/180.0

    return  ((math.cos(phi), -math.sin(phi)), 
             (math.sin(phi),  math.cos(phi)))

def _rvector(angle, x, y):
    phi = math.pi*angle/180.0

    return  ((1-math.cos(phi))*x + math.sin(phi)    *y,
              -math.sin(phi)   *x + (1-math.cos(phi))*y)


def _mmatrix(angle):
    phi = math.pi*angle/180.0

    return ( (math.cos(phi)*math.cos(phi)-math.sin(phi)*math.sin(phi),
              -2*math.sin(phi)*math.cos(phi)                ),
             (-2*math.sin(phi)*math.cos(phi),
              math.sin(phi)*math.sin(phi)-math.cos(phi)*math.cos(phi) ) )


# trafo: affine transformations

class trafo_pt(baseclasses.deformer):

    """affine transformation (coordinates in constructor in pts)

    Note that though the coordinates in the constructor are in
    pts (which is useful for internal purposes), all other
    methods only accept units in the standard user notation.

    """

    def __init__(self, matrix=((1, 0), (0, 1)), vector=(0, 0)):
        """Return trafo with given transformation matrix and vector.
        """
        self.matrix = matrix
        self.vector = vector

    def __mul__(self, other):
        if isinstance(other, trafo_pt):
            matrix = ( ( self.matrix[0][0]*other.matrix[0][0] +
                         self.matrix[0][1]*other.matrix[1][0],
                         self.matrix[0][0]*other.matrix[0][1] +
                         self.matrix[0][1]*other.matrix[1][1] ),
                       ( self.matrix[1][0]*other.matrix[0][0] +
                         self.matrix[1][1]*other.matrix[1][0],
                         self.matrix[1][0]*other.matrix[0][1] +
                         self.matrix[1][1]*other.matrix[1][1] )
                     )

            vector = ( self.matrix[0][0]*other.vector[0] +
                       self.matrix[0][1]*other.vector[1] +
                       self.vector[0],
                       self.matrix[1][0]*other.vector[0] +
                       self.matrix[1][1]*other.vector[1] +
                       self.vector[1] )

            return trafo_pt(matrix=matrix, vector=vector)
        else:
            raise NotImplementedError("can only multiply two transformations")

    def __str__(self):
        return "[%f %f %f %f %f %f]" % \
               ( self.matrix[0][0], self.matrix[1][0],
                 self.matrix[0][1], self.matrix[1][1],
                 self.vector[0], self.vector[1] )

    def processPS(self, file, writer, context, registry):
        file.write("[%f %f %f %f %f %f] concat\n" % \
                    ( self.matrix[0][0], self.matrix[1][0],
                      self.matrix[0][1], self.matrix[1][1],
                      self.vector[0], self.vector[1] ) )

    def processPDF(self, file, writer, context, registry):
        file.write("%f %f %f %f %f %f cm\n" % \
                    ( self.matrix[0][0], self.matrix[1][0],
                      self.matrix[0][1], self.matrix[1][1],
                      self.vector[0], self.vector[1] ) )

    def processSVGattrs(self, attrs, writer, context, registry):
        assert "transform" not in attrs
        attrs["transform"] = "matrix(%f,%f,%f,%f,%f,%f)" % \
                    ( self.matrix[0][0], -self.matrix[1][0],
                      -self.matrix[0][1], self.matrix[1][1],
                      self.vector[0], -self.vector[1] )

    def apply_pt(self, x_pt, y_pt):
        """apply transformation to point (x_pt, y_pt) in pts"""
        return ( self.matrix[0][0]*x_pt + self.matrix[0][1]*y_pt + self.vector[0],
                 self.matrix[1][0]*x_pt + self.matrix[1][1]*y_pt + self.vector[1] )

    def apply(self, x, y):
        # for the transformation we have to convert to points
        tx, ty = self.apply_pt(unit.topt(x), unit.topt(y))
        return tx * unit.t_pt, ty * unit.t_pt

    def deform(self, path):
        return path.transformed(self)

    def inverse(self):
        det = 1.0*(self.matrix[0][0]*self.matrix[1][1] - self.matrix[0][1]*self.matrix[1][0])
        matrix = ( ( self.matrix[1][1]/det, -self.matrix[0][1]/det),
                   (-self.matrix[1][0]/det,  self.matrix[0][0]/det) )
        return ( trafo_pt(matrix=matrix) *
                 trafo_pt(vector=(-self.vector[0], -self.vector[1])) )

    def mirrored(self, angle):
        return mirror(angle) * self

    def rotated_pt(self, angle, x=None, y=None):
        return rotate_pt(angle, x, y) * self

    def rotated(self, angle, x=None, y=None):
        return rotate(angle, x, y) * self

    def scaled_pt(self, sx, sy=None, x=None, y=None):
        return scale_pt(sx, sy, x, y) * self

    def scaled(self, sx, sy=None, x=None, y=None):
        return scale(sx, sy, x, y) * self

    def slanted_pt(self, a, angle=0, x=None, y=None):
        return slant_pt(a, angle, x, y) * self

    def slanted(self, a, angle=0, x=None, y=None):
        return slant(a, angle, x, y) * self

    def translated_pt(self, x, y):
        return translate_pt(x, y) * self

    def translated(self, x, y):
        return translate(x, y) * self


class trafo(trafo_pt):

    """affine transformation"""

    def __init__(self, matrix=((1,0), (0,1)), vector=(0, 0)):
        trafo_pt.__init__(self,
                          matrix, (unit.topt(vector[0]), unit.topt(vector[1])))

#
# some standard transformations 
#

identity = trafo()

class mirror(trafo):
    def __init__(self, angle=0):
        trafo.__init__(self, matrix=_mmatrix(angle))


class rotate_pt(trafo_pt):
    def __init__(self, angle, x=None, y=None):
        vector = 0, 0
        if x is not None or y is not None:
            if x is None or y is None:
                raise TrafoException("either specify both x and y or none of them")
            vector=_rvector(angle, x, y)

        trafo_pt.__init__(self, matrix=_rmatrix(angle), vector=vector)


class rotate(trafo_pt):
    def __init__(self, angle, x=None, y=None):
        vector = 0, 0 
        if x is not None or y is not None:
            if x is None or y is None:
                raise TrafoException("either specify both x and y or none of them")
            vector=_rvector(angle, unit.topt(x), unit.topt(y))

        trafo_pt.__init__(self, matrix=_rmatrix(angle), vector=vector)


class scale_pt(trafo_pt):
    def __init__(self, sx, sy=None, x=None, y=None):
        if sy is None:
            sy = sx
        vector = 0, 0
        if x is not None or y is not None:
            if x is None or y is None:
                raise TrafoException("either specify both x and y or none of them")
            vector = (1-sx)*x, (1-sy)*y
        trafo_pt.__init__(self, matrix=((sx, 0), (0, sy)), vector=vector)


class scale(trafo):
    def __init__(self, sx, sy=None, x=None, y=None):
        if sy is None:
            sy = sx
        vector = 0, 0
        if x is not None or y is not None:
            if x is None or y is None:
                raise TrafoException("either specify both x and y or none of them")
            vector = (1-sx)*x, (1-sy)*y
        trafo.__init__(self, matrix=((sx, 0), (0, sy)), vector=vector)


class slant_pt(trafo_pt):
    def __init__(self, a, angle=0, x=None, y=None):
        t = ( rotate_pt(-angle, x, y) *
              trafo(matrix=((1, a), (0, 1))) *
              rotate_pt(angle, x, y) )
        trafo_pt.__init__(self, t.matrix, t.vector)


class slant(trafo):
    def __init__(self, a, angle=0, x=None, y=None):
        t = ( rotate(-angle, x, y) *
              trafo(matrix=((1, a), (0, 1))) *
              rotate(angle, x, y) )
        trafo.__init__(self, t.matrix, t.vector)


class translate_pt(trafo_pt):
    def __init__(self, x, y):
        trafo_pt.__init__(self, vector=(x, y))


class translate(trafo):
    def __init__(self, x, y):
        trafo.__init__(self, vector=(x, y))
