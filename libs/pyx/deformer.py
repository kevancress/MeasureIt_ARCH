# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2003-2013 Michael Schindler <m-schindler@users.sourceforge.net>
# Copyright (C) 2003-2005 André Wobst <wobsta@pyx-project.org>
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

import functools, logging, math
from . import attr, baseclasses, mathutils, path, normpath, unit, color

normpath.invalid = 175e175 # Just a very crude workaround to get the code running again. normpath.invalid does not exist anymore.

logger = logging.getLogger("pyx")

# specific exception for an invalid parameterization point
# used in parallel
class InvalidParamException(Exception):

    def __init__(self, param):
        self.normsubpathitemparam = param

# error raised in parallel if we are trying to get badly defined intersections
class IntersectionError(Exception): pass

# None has a meaning in linesmoothed
class _marker: pass

class inf_curvature: pass

def curvescontrols_from_endlines_pt(B, tangent1, tangent2, r1, r2, softness): # <<<
    # calculates the parameters for two bezier curves connecting two lines (curvature=0)
    # starting at B - r1*tangent1
    # ending at   B + r2*tangent2
    #
    # Takes the corner B
    # and two tangent vectors heading to and from B
    # and two radii r1 and r2:
    # All arguments must be in Points
    # Returns the seven control points of the two bezier curves:
    #  - start d1
    #  - control points g1 and f1
    #  - midpoint e
    #  - control points f2 and g2
    #  - endpoint d2

    # make direction vectors d1: from B to A
    #                        d2: from B to C
    d1 = -tangent1[0] / math.hypot(*tangent1), -tangent1[1] / math.hypot(*tangent1)
    d2 =  tangent2[0] / math.hypot(*tangent2),  tangent2[1] / math.hypot(*tangent2)

    # 0.3192 has turned out to be the maximum softness available
    # for straight lines ;-)
    f = 0.3192 * softness
    g = (15.0 * f + math.sqrt(-15.0*f*f + 24.0*f))/12.0

    # make the control points of the two bezier curves
    f1 = B[0] + f * r1 * d1[0], B[1] + f * r1 * d1[1]
    f2 = B[0] + f * r2 * d2[0], B[1] + f * r2 * d2[1]
    g1 = B[0] + g * r1 * d1[0], B[1] + g * r1 * d1[1]
    g2 = B[0] + g * r2 * d2[0], B[1] + g * r2 * d2[1]
    d1 = B[0] +     r1 * d1[0], B[1] +     r1 * d1[1]
    d2 = B[0] +     r2 * d2[0], B[1] +     r2 * d2[1]
    e  = 0.5 * (f1[0] + f2[0]), 0.5 * (f1[1] + f2[1])

    return (d1, g1, f1, e, f2, g2, d2)
# >>>

def controldists_from_endgeometry_pt(A, B, tangA, tangB, curvA, curvB, allownegative=False, curv_epsilon=1.0e-8): # <<<

    """For a curve with given tangents and curvatures at the endpoints this gives the distances between the controlpoints

    This helper routine returns a list of two distances between the endpoints and the
    corresponding control points of a (cubic) bezier curve that has
    prescribed tangents tangentA, tangentB and curvatures curvA, curvB at the
    end points.

    Note: The returned distances are not always positive.
          But only positive values are geometrically correct, so please check!
          The outcome is sorted so that the first entry is expected to be the
          most reasonable one
    """
    debug = 0

    def test_divisions(T, D, E, AB, curvA, curvB, debug):# <<<
        small = AB * 1.0e-4 # at infinite curvature, avoid setting control points exactly on the startpoint
                            # TODO: is this consistent with the avoiding of curv=inf in normpath?
        arbitrary = AB * 0.33 # at zero curvature, we know nothing about a or b

        def is_zero(x):
            return abs(x) < curv_epsilon
            # the following gave different results for forward/reverse paths
            # in test/functional/test_deformer parallel G
            #try:
            #    1.0 / x
            #except ZeroDivisionError:
            #    return True
            #return False


        if is_zero(T):

            if curvA is inf_curvature:
               a = small
               if curvB is inf_curvature:
                   b = small
               elif is_zero(curvB):
                    assert abs(E) < 1.0e-10
                    b = arbitrary
               else:
                    b = math.sqrt(abs(E / (1.5 * curvB))) * mathutils.sign(E*curvB)
            elif is_zero(curvA):
                assert abs(D) < 1.0e-10
                a = arbitrary
                if curvB is inf_curvature:
                    b = small
                elif is_zero(curvB):
                    assert abs(E) < 1.0e-10
                    b = arbitrary
                else:
                    b = math.sqrt(abs(E / (1.5 * curvB))) * mathutils.sign(E*curvB)
            else:
                a = math.sqrt(abs(D / (1.5 * curvA))) * mathutils.sign(D*curvA)
                if curvB is inf_curvature:
                    b = small
                elif is_zero(curvB):
                    assert abs(E) < 1.0e-10
                    b = arbitrary
                else:
                    b = math.sqrt(abs(E / (1.5 * curvB))) * mathutils.sign(E*curvB)

        else:
            if curvA is inf_curvature:
               a = small
               if curvB is inf_curvature:
                   b = small
               elif is_zero(curvB):
                   b = arbitrary
               else:
                   b1 = math.sqrt(abs(E / (1.5 * curvB))) * mathutils.sign(E*curvB)
                   b2 = D / T
                   if abs(b1) < abs(b2):
                       b = b1
                   else:
                       b = b2
            elif curvB is inf_curvature:
               b = small
               if is_zero(curvA):
                   a = arbitrary
               else:
                   a1 = math.sqrt(abs(D / (1.5 * curvA))) * mathutils.sign(D*curvA)
                   a2 = E / T
                   if abs(a1) < abs(a2):
                       a = a1
                   else:
                       a = a2
            elif is_zero(curvA):
                b = D / T
                a = (E - 1.5*curvB*b*abs(b)) / T
            elif is_zero(curvB):
                a = E / T
                b = (D - 1.5*curvA*a*abs(a)) / T
            else:
                return []

        if debug:
            print("fallback with exact zero value")
        return [(a, b)]
    # >>>
    def fallback_smallT(T, D, E, AB, curvA, curvB, threshold, debug):# <<<
        a = math.sqrt(abs(D / (1.5 * curvA))) * mathutils.sign(D*curvA)
        b = math.sqrt(abs(E / (1.5 * curvB))) * mathutils.sign(E*curvB)
        q1 = min(abs(1.5*a*a*curvA), abs(D))
        q2 = min(abs(1.5*b*b*curvB), abs(E))
        if (a >= 0 and b >= 0 and
            abs(b*T) < threshold * q1 and abs(1.5*a*abs(a)*curvA - D) < threshold * q1 and
            abs(a*T) < threshold * q2 and abs(1.5*b*abs(b)*curvB - E) < threshold * q2):
            if debug:
                print("fallback with T approx 0")
            return [(a, b)]
        return []
    # >>>
    def fallback_smallcurv(T, D, E, AB, curvA, curvB, threshold, debug):# <<<
        result = []

        # is curvB approx zero?
        a = E / T
        b = (D - 1.5*curvA*a*abs(a)) / T
        if (a >= 0 and b >= 0 and
            abs(1.5*b*b*curvB) < threshold * min(abs(a*T), abs(E)) and
            abs(a*T - E) < threshold * min(abs(a*T), abs(E))):
            if debug:
                print("fallback with curvB approx 0")
            result.append((a, b))

        # is curvA approx zero?
        b = D / T
        a = (E - 1.5*curvB*b*abs(b)) / T
        if (a >= 0 and b >= 0 and
            abs(1.5*a*a*curvA) < threshold * min(abs(b*T), abs(D)) and
            abs(b*T - D) < threshold * min(abs(b*T), abs(D))):
            if debug:
                print("fallback with curvA approx 0")
            result.append((a, b))

        return result
    # >>>
    def findnearest(x, ys): # <<<
        I = 0
        Y = ys[I]
        mindist = abs(x - Y)

        # find the value in ys which is nearest to x
        for i, y in enumerate(ys[1:]):
            dist = abs(x - y)
            if dist < mindist:
                I, Y, mindist = i, y, dist

        return I, Y
    # >>>

    # some shortcuts
    T = tangA[0] * tangB[1] - tangA[1] * tangB[0]
    D = tangA[0] * (B[1]-A[1]) - tangA[1] * (B[0]-A[0])
    E = tangB[0] * (A[1]-B[1]) - tangB[1] * (A[0]-B[0])
    AB = math.hypot(A[0] - B[0], A[1] - B[1])

    # try if one of the prefactors is exactly zero
    testsols = test_divisions(T, D, E, AB, curvA, curvB, debug)
    if testsols:
        return testsols

    # The general case:
    # we try to find all the zeros of the decoupled 4th order problem
    # for the combined problem:
    # The control points of a cubic Bezier curve are given by a, b:
    #     A, A + a*tangA, B - b*tangB, B
    # for the derivation see /design/beziers.tex
    #     0 = 1.5 a |a| curvA + b * T - D
    #     0 = 1.5 b |b| curvB + a * T - E
    # because of the absolute values we get several possibilities for the signs
    # in the equation. We test all signs, also the invalid ones!
    if allownegative:
        signs = [(+1, +1), (-1, +1), (+1, -1), (-1, -1)]
    else:
        signs = [(+1, +1)]

    candidates_a = []
    candidates_b = []
    for sign_a, sign_b in signs:
        coeffs_a = (sign_b*3.375*curvA*curvA*curvB, 0.0, -sign_b*sign_a*4.5*curvA*curvB*D, T**3, sign_b*1.5*curvB*D*D - T*T*E)
        coeffs_b = (sign_a*3.375*curvA*curvB*curvB, 0.0, -sign_a*sign_b*4.5*curvA*curvB*E, T**3, sign_a*1.5*curvA*E*E - T*T*D)
        candidates_a += [root for root in mathutils.realpolyroots(*coeffs_a) if sign_a*root >= 0]
        candidates_b += [root for root in mathutils.realpolyroots(*coeffs_b) if sign_b*root >= 0]
    solutions = []
    if candidates_a and candidates_b:
        for a in candidates_a:
            i, b = findnearest((D - 1.5*curvA*a*abs(a))/T, candidates_b)
            solutions.append((a, b))

    # try if there is an approximate solution
    for thr in [1.0e-2, 1.0e-1]:
        if not solutions:
            solutions = fallback_smallT(T, D, E, AB, curvA, curvB, thr, debug)
        if not solutions:
            solutions = fallback_smallcurv(T, D, E, AB, curvA, curvB, thr, debug)

    # sort the solutions: the more reasonable values at the beginning
    def mycmp(x,y): # <<<
        # first the pairs that are purely positive, then all the pairs with some negative signs
        # inside the two sets: sort by magnitude
        sx = (x[0] > 0 and x[1] > 0)
        sy = (y[0] > 0 and y[1] > 0)

        # experimental stuff:
        # what criterion should be used for sorting ?
        #
        #errx = abs(1.5*curvA*x[0]*abs(x[0]) + x[1]*T - D) + abs(1.5*curvB*x[1]*abs(x[1]) + x[0]*T - E)
        #erry = abs(1.5*curvA*y[0]*abs(y[0]) + y[1]*T - D) + abs(1.5*curvB*y[1]*abs(y[1]) + y[0]*T - E)
        # # For each equation, a value like
        # #   abs(1.5*curvA*y[0]*abs(y[0]) + y[1]*T - D) / abs(curvA*(D - y[1]*T))
        # # indicates how good the solution is. In order to avoid the division,
        # # we here multiply with all four denominators:
        # errx = max(abs( (1.5*curvA*y[0]*abs(y[0]) + y[1]*T - D) * (curvB*(E - y[0]*T))*(curvA*(D - x[1]*T))*(curvB*(E - x[0]*T)) ),
        #            abs( (1.5*curvB*y[1]*abs(y[1]) + y[0]*T - E) * (curvA*(D - y[1]*T))*(curvA*(D - x[1]*T))*(curvB*(E - x[0]*T)) ))
        # errx = max(abs( (1.5*curvA*x[0]*abs(x[0]) + x[1]*T - D) * (curvA*(D - y[1]*T))*(curvB*(E - y[0]*T))*(curvB*(E - x[0]*T)) ),
        #            abs( (1.5*curvB*x[1]*abs(x[1]) + x[0]*T - E) * (curvA*(D - y[1]*T))*(curvB*(E - y[0]*T))*(curvA*(D - x[1]*T)) ))
        #errx = (abs(curvA*x[0]) - 1.0)**2 + (abs(curvB*x[1]) - 1.0)**2
        #erry = (abs(curvA*y[0]) - 1.0)**2 + (abs(curvB*y[1]) - 1.0)**2

        errx = x[0]**2 + x[1]**2
        erry = y[0]**2 + y[1]**2

        if sx == 1 and sy == 1:
            # try to use longer solutions if there are any crossings in the control-arms
            # the following combination yielded fewest sorting errors in test_bezier.py
            t, s = intersection(A, B, tangA, tangB)
            t, s = abs(t), abs(s)
            if (t > 0 and t < x[0] and s > 0 and s < x[1]):
                if (t > 0 and t < y[0] and s > 0 and s < y[1]):
                    # use the shorter one
                    return int(errx > erry) - int(errx < erry)
                else:
                    # use the longer one
                    return -1
            else:
                if (t > 0 and t < y[0] and s > 0 and s < y[1]):
                    # use the longer one
                    return 1
                else:
                    # use the shorter one
                    return int(errx > erry) - int(errx < erry)
            #return cmp(x[0]**2 + x[1]**2, y[0]**2 + y[1]**2)
        else:
            return int(sy > sx) - int(sy < sx)
    # >>>
    solutions.sort(key=functools.cmp_to_key(mycmp))

    return solutions
# >>>

def normcurve_from_endgeometry_pt(A, B, tangA, tangB, curvA, curvB): # <<<
    a, b = controldists_from_endgeometry_pt(A, B, tangA, tangB, curvA, curvB)[0]
    return normpath.normcurve_pt(A[0], A[1],
        A[0] + a * tangA[0], A[1] + a * tangA[1],
        B[0] - b * tangB[0], B[1] - b * tangB[1], B[0], B[1])
    # >>>

def intersection(A, D, tangA, tangD): # <<<

    """returns the intersection parameters of two evens

    they are defined by:
      x(t) = A + t * tangA
      x(s) = D + s * tangD
    """
    det = -tangA[0] * tangD[1] + tangA[1] * tangD[0]
    try:
        1.0 / det
    except ArithmeticError:
        return None, None

    DA = D[0] - A[0], D[1] - A[1]

    t = (-tangD[1]*DA[0] + tangD[0]*DA[1]) / det
    s = (-tangA[1]*DA[0] + tangA[0]*DA[1]) / det

    return t, s
# >>>

class cycloid(baseclasses.deformer): # <<<
    """Wraps a cycloid around a path.

    The outcome looks like a spring with the originalpath as the axis.
    radius: radius of the cycloid
    halfloops:  number of halfloops
    skipfirst/skiplast: undeformed end lines of the original path
    curvesperhloop:
    sign: start left (1) or right (-1) with the first halfloop
    turnangle: angle of perspective on a (3D) spring
               turnangle=0 will produce a sinus-like cycloid,
               turnangle=90 will procude a row of connected circles

    """

    def __init__(self, radius=0.5*unit.t_cm, halfloops=10,
    skipfirst=1*unit.t_cm, skiplast=1*unit.t_cm, curvesperhloop=3, sign=1, turnangle=45):
        self.skipfirst = skipfirst
        self.skiplast = skiplast
        self.radius = radius
        self.halfloops = halfloops
        self.curvesperhloop = curvesperhloop
        self.sign = sign
        self.turnangle = turnangle

    def __call__(self, radius=None, halfloops=None,
    skipfirst=None, skiplast=None, curvesperhloop=None, sign=None, turnangle=None):
        if radius is None:
            radius = self.radius
        if halfloops is None:
            halfloops = self.halfloops
        if skipfirst is None:
            skipfirst = self.skipfirst
        if skiplast is None:
            skiplast = self.skiplast
        if curvesperhloop is None:
            curvesperhloop = self.curvesperhloop
        if sign is None:
            sign = self.sign
        if turnangle is None:
            turnangle = self.turnangle

        return cycloid(radius=radius, halfloops=halfloops, skipfirst=skipfirst, skiplast=skiplast,
                       curvesperhloop=curvesperhloop, sign=sign, turnangle=turnangle)

    def deform(self, basepath):
        resultnormsubpaths = [self.deformsubpath(nsp) for nsp in basepath.normpath().normsubpaths]
        return normpath.normpath(resultnormsubpaths)

    def deformsubpath(self, normsubpath):

        skipfirst = abs(unit.topt(self.skipfirst))
        skiplast = abs(unit.topt(self.skiplast))
        radius = abs(unit.topt(self.radius))
        turnangle = math.radians(self.turnangle)
        sign = mathutils.sign(self.sign)

        cosTurn = math.cos(turnangle)
        sinTurn = math.sin(turnangle)

        # make list of the lengths and parameters at points on normsubpath
        # where we will add cycloid-points
        totlength = normsubpath.arclen_pt()
        if totlength <= skipfirst + skiplast + 2*radius*sinTurn:
            logger.warning("normsubpath is too short for deformation with cycloid -- skipping...")
            return normsubpath

        # parameterization is in rotation-angle around the basepath
        # differences in length, angle ... between two basepoints
        # and between basepoints and controlpoints
        Dphi = math.pi / self.curvesperhloop
        phis = [i * Dphi for i in range(self.halfloops * self.curvesperhloop + 1)]
        DzDphi = (totlength - skipfirst - skiplast - 2*radius*sinTurn) * 1.0 / (self.halfloops * math.pi * cosTurn)
        # Dz = (totlength - skipfirst - skiplast - 2*radius*sinTurn) * 1.0 / (self.halfloops * self.curvesperhloop * cosTurn)
        # zs = [i * Dz for i in range(self.halfloops * self.curvesperhloop + 1)]
        # from path._arctobcurve:
        # optimal relative distance along tangent for second and third control point
        L = 4 * radius * (1 - math.cos(Dphi/2)) / (3 * math.sin(Dphi/2))

        # Now the transformation of z into the turned coordinate system
        Zs = [ skipfirst + radius*sinTurn # here the coordinate z starts
             - sinTurn*radius*math.cos(phi) + cosTurn*DzDphi*phi # the transformed z-coordinate
             for phi in phis]
        params = normsubpath._arclentoparam_pt(Zs)[0]

        # get the positions of the splitpoints in the cycloid
        points = []
        for phi, param in zip(phis, params):
            # the cycloid is a circle that is stretched along the normsubpath
            # here are the points of that circle
            basetrafo = normsubpath.trafo([param])[0]

            # The point on the cycloid, in the basepath's local coordinate system
            baseZ, baseY = 0, radius*math.sin(phi)

            # The tangent there, also in local coords
            tangentX = -cosTurn*radius*math.sin(phi) + sinTurn*DzDphi
            tangentY = radius*math.cos(phi)
            tangentZ = sinTurn*radius*math.sin(phi) + DzDphi*cosTurn
            norm = math.sqrt(tangentX*tangentX + tangentY*tangentY + tangentZ*tangentZ)
            tangentY, tangentZ = tangentY/norm, tangentZ/norm

            # Respect the curvature of the basepath for the cycloid's curvature
            # XXX this is only a heuristic, not a "true" expression for
            #     the curvature in curved coordinate systems
            try:
                pathradius = 1/normsubpath.curvature_pt([param])[0]
            except ArithmeticError:
                factor = 1
            else:
                factor = (pathradius - baseY) / pathradius
                factor = abs(factor)
            l = L * factor

            # The control points prior and after the point on the cycloid
            preeZ, preeY = baseZ - l * tangentZ, baseY - l * tangentY
            postZ, postY = baseZ + l * tangentZ, baseY + l * tangentY

            # Now put everything at the proper place
            points.append(basetrafo.apply_pt(preeZ, sign * preeY) +
                          basetrafo.apply_pt(baseZ, sign * baseY) +
                          basetrafo.apply_pt(postZ, sign * postY))

        if len(points) <= 1:
            logger.warning("normsubpath is too short for deformation with cycloid -- skipping...")
            return normsubpath

        # Build the path from the pointlist
        # containing (control x 2,  base x 2, control x 2)
        if skipfirst > normsubpath.epsilon:
            normsubpathitems = normsubpath.segments([0, params[0]])[0]
            normsubpathitems.append(normpath.normcurve_pt(*(points[0][2:6] + points[1][0:4])))
        else:
            normsubpathitems = [normpath.normcurve_pt(*(points[0][2:6] + points[1][0:4]))]
        for i in range(1, len(points)-1):
            normsubpathitems.append(normpath.normcurve_pt(*(points[i][2:6] + points[i+1][0:4])))
        if skiplast > normsubpath.epsilon:
            for nsp in normsubpath.segments([params[-1], len(normsubpath)]):
                normsubpathitems.extend(nsp.normsubpathitems)

        # That's it
        return normpath.normsubpath(normsubpathitems, epsilon=normsubpath.epsilon)
# >>>

cycloid.clear = attr.clearclass(cycloid)

class cornersmoothed(baseclasses.deformer): # <<<

    """Bends corners in a normpath.

    This decorator replaces corners in a normpath with bezier curves. There are two cases:
    - If the corner lies between two lines, _two_ bezier curves will be used
      that are highly optimized to look good (their curvature is to be zero at the ends
      and has to have zero derivative in the middle).
      Additionally, it can controlled by the softness-parameter.
    - If the corner lies between curves then _one_ bezier is used that is (except in some
      special cases) uniquely determined by the tangents and curvatures at its end-points.
      In some cases it is necessary to use only the absolute value of the curvature to avoid a
      cusp-shaped connection of the new bezier to the old path. In this case the use of
      "obeycurv=0" allows the sign of the curvature to switch.
    - The radius argument gives the arclength-distance of the corner to the points where the
      old path is cut and the beziers are inserted.
    - Path elements that are too short (shorter than the radius) are skipped
    """

    def __init__(self, radius, softness=1, obeycurv=0, relskipthres=0.01):
        self.radius = radius
        self.softness = softness
        self.obeycurv = obeycurv
        self.relskipthres = relskipthres

    def __call__(self, radius=None, softness=None, obeycurv=None, relskipthres=None):
        if radius is None:
            radius = self.radius
        if softness is None:
            softness = self.softness
        if obeycurv is None:
            obeycurv = self.obeycurv
        if relskipthres is None:
            relskipthres = self.relskipthres
        return cornersmoothed(radius=radius, softness=softness, obeycurv=obeycurv, relskipthres=relskipthres)

    def deform(self, basepath):
        return normpath.normpath([self.deformsubpath(normsubpath)
                              for normsubpath in basepath.normpath().normsubpaths])

    def deformsubpath(self, normsubpath):
        radius_pt = unit.topt(self.radius)
        epsilon = normsubpath.epsilon

        # remove too short normsubpath items (shorter than self.relskipthres*radius_pt or epsilon)
        pertinentepsilon = max(epsilon, self.relskipthres*radius_pt)
        pertinentnormsubpath = normpath.normsubpath(normsubpath.normsubpathitems,
                                                epsilon=pertinentepsilon)
        pertinentnormsubpath.flushskippedline()
        pertinentnormsubpathitems = pertinentnormsubpath.normsubpathitems

        # calculate the splitting parameters for the pertinentnormsubpathitems
        arclens_pt = []
        params = []
        for pertinentnormsubpathitem in pertinentnormsubpathitems:
            arclen_pt = pertinentnormsubpathitem.arclen_pt(epsilon)
            arclens_pt.append(arclen_pt)
            l1_pt = min(radius_pt, 0.5*arclen_pt)
            l2_pt = max(0.5*arclen_pt, arclen_pt - radius_pt)
            params.append(pertinentnormsubpathitem.arclentoparam_pt([l1_pt, l2_pt], epsilon))

        # handle the first and last pertinentnormsubpathitems for a non-closed normsubpath
        if not normsubpath.closed:
            l1_pt = 0
            l2_pt = max(0, arclens_pt[0] - radius_pt)
            params[0] = pertinentnormsubpathitems[0].arclentoparam_pt([l1_pt, l2_pt], epsilon)
            l1_pt = min(radius_pt, arclens_pt[-1])
            l2_pt = arclens_pt[-1]
            params[-1] = pertinentnormsubpathitems[-1].arclentoparam_pt([l1_pt, l2_pt], epsilon)

        newnormsubpath = normpath.normsubpath(epsilon=normsubpath.epsilon)
        for i in range(len(pertinentnormsubpathitems)):
            this = i
            next = (i+1) % len(pertinentnormsubpathitems)
            thisparams = params[this]
            nextparams = params[next]
            thisnormsubpathitem = pertinentnormsubpathitems[this]
            nextnormsubpathitem = pertinentnormsubpathitems[next]
            thisarclen_pt = arclens_pt[this]
            nextarclen_pt = arclens_pt[next]

            # insert the middle segment
            newnormsubpath.append(thisnormsubpathitem.segments(thisparams)[0])

            # insert replacement curves for the corners
            if next or normsubpath.closed:

                t1 = thisnormsubpathitem.rotation([thisparams[1]])[0].apply_pt(1, 0)
                t2 = nextnormsubpathitem.rotation([nextparams[0]])[0].apply_pt(1, 0)
                # TODO: normpath.invalid

                if (isinstance(thisnormsubpathitem, normpath.normline_pt) and
                    isinstance(nextnormsubpathitem, normpath.normline_pt)):

                    # case of two lines -> replace by two curves
                    d1, g1, f1, e, f2, g2, d2 = curvescontrols_from_endlines_pt(
                        thisnormsubpathitem.atend_pt(), t1, t2,
                        thisarclen_pt*(1-thisparams[1]), nextarclen_pt*(nextparams[0]), softness=self.softness)

                    p1 = thisnormsubpathitem.at_pt([thisparams[1]])[0]
                    p2 = nextnormsubpathitem.at_pt([nextparams[0]])[0]

                    newnormsubpath.append(normpath.normcurve_pt(*(d1 + g1 + f1 + e)))
                    newnormsubpath.append(normpath.normcurve_pt(*(e + f2 + g2 + d2)))

                else:

                    # generic case -> replace by a single curve with prescribed tangents and curvatures
                    p1 = thisnormsubpathitem.at_pt([thisparams[1]])[0]
                    p2 = nextnormsubpathitem.at_pt([nextparams[0]])[0]
                    c1 = thisnormsubpathitem.curvature_pt([thisparams[1]])[0]
                    c2 = nextnormsubpathitem.curvature_pt([nextparams[0]])[0]
                    # TODO: normpath.invalid

                    # TODO: more intelligent fallbacks:
                    #   circle -> line
                    #   circle -> circle

                    if not self.obeycurv:
                        # do not obey the sign of the curvature but
                        # make the sign such that the curve smoothly passes to the next point
                        # this results in a discontinuous curvature
                        # (but the absolute value is still continuous)
                        s1 = +mathutils.sign(t1[0] * (p2[1]-p1[1]) - t1[1] * (p2[0]-p1[0]))
                        s2 = -mathutils.sign(t2[0] * (p2[1]-p1[1]) - t2[1] * (p2[0]-p1[0]))
                        c1 = s1 * abs(c1)
                        c2 = s2 * abs(c2)

                    # get the length of the control "arms"
                    controldists = controldists_from_endgeometry_pt(p1, p2, t1, t2, c1, c2)

                    if controldists and (controldists[0][0] >= 0 and controldists[0][1] >= 0):
                        # use the first entry in the controldists
                        # this should be the "smallest" pair
                        a, d = controldists[0]
                        # avoid curves with invalid parameterization
                        a = max(a, epsilon)
                        d = max(d, epsilon)

                        # avoid overshooting at the corners:
                        # this changes not only the sign of the curvature
                        # but also the magnitude
                        if not self.obeycurv:
                            t, s = intersection(p1, p2, t1, t2)
                            if (t is not None and s is not None and
                                t > 0 and s < 0):
                                a = min(a, abs(t))
                                d = min(d, abs(s))

                    else:
                        # use a fallback
                        t, s = intersection(p1, p2, t1, t2)
                        if t is not None and s is not None:
                            a = 0.65 * abs(t)
                            d = 0.65 * abs(s)
                        else:
                            # if there is no useful result:
                            # take an arbitrary smoothing curve that does not obey
                            # the curvature constraints
                            dist = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
                            a = dist / (3.0 * math.hypot(*t1))
                            d = dist / (3.0 * math.hypot(*t2))

                    # calculate the two missing control points
                    q1 = p1[0] + a * t1[0], p1[1] + a * t1[1]
                    q2 = p2[0] - d * t2[0], p2[1] - d * t2[1]

                    newnormsubpath.append(normpath.normcurve_pt(*(p1 + q1 + q2 + p2)))

        if normsubpath.closed:
            newnormsubpath.close()
        return newnormsubpath

# >>>

cornersmoothed.clear = attr.clearclass(cornersmoothed)
smoothed = cornersmoothed
smoothed.clear = attr.clearclass(smoothed)

class mynormpathparam(normpath.normpathparam): # <<<
    """In the parallel deformer we use properties such as the curvature, which
    are not continuous on a path (at points between normsubpathitems). We
    therefore require a better parameter class which really resolves the
    nsp-item """

    # TODO: find reasonable values for these eps:
    rounding_eps = 1.0e-8

    def __init__(self, np, normsubpathindex, normsubpathitemindex, normsubpathitemparam):
        normpath.normpathparam.__init__(self, np, normsubpathindex, normsubpathitemindex + normsubpathitemparam)
        self.normsubpathitemindex = normsubpathitemindex
        self.normsubpathitemparam = normsubpathitemparam
        self.beg_nspitem_known = False
        self.end_nspitem_known = False

        # guarantee that normpath.normpathparam always gets the correct item:
        if int(self.normsubpathparam) != self.normsubpathitemindex:
            if int(self.normsubpathparam) == self.normsubpathitemindex - 1:
                self.normsubpathparam = self.normsubpathitemindex + self.rounding_eps
                self.beg_nspitem_known = True
            elif int(self.normsubpathparam) == self.normsubpathitemindex + 1:
                self.normsubpathparam = (self.normsubpathitemindex + 1) - self.rounding_eps
                self.end_nspitem_known = True
            else:
                assert False
        assert int(self.normsubpathparam) == self.normsubpathitemindex
        #assert 0 <= self.normsubpathparam - self.normsubpathitemindex
        #assert 1 >= self.normsubpathparam - self.normsubpathitemindex

    def __str__(self):
        return "npp(%d, %d, %.3f)" % (self.normsubpathindex, self.normsubpathitemindex, self.normsubpathitemparam)

    def __eq__(self, other):
        if isinstance(other, mynormpathparam):
            assert self.normpath is other.normpath, "normpathparams have to belong to the same normpath"
            return (self.normsubpathindex, self.normsubpathitemindex, self.normsubpathitemparam) == (other.normsubpathindex, other.normsubpathitemindex, other.normsubpathitemparam)
        else:
            normpath.normpathparam.__eq__(self, other)

    def __lt__(self, other):
        if isinstance(other, mynormpathparam):
            assert self.normpath is other.normpath, "normpathparams have to belong to the same normpath"
            return (self.normsubpathindex, self.normsubpathitemindex, self.normsubpathitemparam) < (other.normsubpathindex, other.normsubpathitemindex, other.normsubpathitemparam)
        else:
            normpath.normpathparam.__eq__(self, other)

    def __hash__(self):
        return id(self)

    def smaller_equiv(self, epsilon=None):
        """Returns smaller equivalent parameter, if self is between two nsp-items"""
        if not self.is_beg_of_nspitem(epsilon):
            return self
        nsp = self.normpath[self.normsubpathindex]
        nspi_index = self.normsubpathitemindex - 1
        nspi_param = 1
        if nsp.closed:
            nspi_index = nspi_index % len(nsp)
        elif nspi_index < 0:
            nspi_index = 0
            nspi_param = 0
        other = mynormpathparam(self.normpath, self.normsubpathindex, nspi_index, nspi_param)
        if self.is_equiv(other, epsilon):
            return other
        return self

    def larger_equiv(self, epsilon=None):
        """Returns smaller equivalent parameter, if self is between two nsp-items"""
        if not self.is_end_of_nspitem(epsilon):
            return self
        nsp = self.normpath[self.normsubpathindex]
        nspi_index = self.normsubpathitemindex + 1
        nspi_param = 0
        if nsp.closed:
            nspi_index = nspi_index % len(nsp)
        elif nspi_index >= len(nsp):
            nspi_index = len(nsp) - 1
            nspi_param = 1
        other = mynormpathparam(self.normpath, self.normsubpathindex, nspi_index, nspi_param)
        if self.is_equiv(other, epsilon):
            return other
        return self

    def is_equiv(self, other, epsilon=None):
        """Test whether the two params yield essentially the same point"""
        assert self.normpath is other.normpath, "normpathparams have to belong to the same normpath"
        if self.normsubpathindex != other.normsubpathindex:
            return False
        nsp = self.normpath[self.normsubpathindex]
        if epsilon is None:
            epsilon = nsp.epsilon
        A, B = self.normpath.at_pt([self, other])
        return math.hypot(A[0]-B[0], A[1]-B[1]) < epsilon

    def is_beg_of_nspitem(self, epsilon=None):
        if self.beg_nspitem_known:
            return True
        return self.is_equiv(mynormpathparam(self.normpath, self.normsubpathindex, self.normsubpathitemindex, 0), epsilon)

    def is_end_of_nspitem(self, epsilon=None):
        if self.end_nspitem_known:
            return True
        return self.is_equiv(mynormpathparam(self.normpath, self.normsubpathindex, self.normsubpathitemindex, 1), epsilon)

    def is_beg_of_nsp(self, epsilon=None):
        if self.normsubpathitemindex > 0:
            return False
        return self.is_equiv(mynormpathparam(self.normpath, self.normsubpathindex, 0, 0), epsilon)

    def is_end_of_nsp(self, epsilon=None):
        n = len(self.normpath[self.normsubpathindex]) - 1
        if self.normsubpathitemindex < n:
            return False
        return self.is_equiv(mynormpathparam(self.normpath, self.normsubpathindex, n, 1), epsilon)

# >>>
def _length_pt(path, param1, param2): # <<<
    point1, point2 = path.at_pt([param1, param2])
    return math.hypot(point1[0] - point2[0], point1[1] - point2[1])
# >>>
class parallel(baseclasses.deformer): # <<<

    """creates a parallel normpath with constant distance to the original normpath

    A positive 'distance' results in a curve left of the original one -- and a
    negative 'distance' in a curve at the right. Left/right are understood in
    terms of the parameterization of the original curve. The construction of
    the paralel path is done in two steps: First, an "extended" parallel path
    is built. For each path element a parallel curve/line is constructed, which
    can be too long or too short, depending on the presence of corners. At
    corners, either a circular arc is drawn around the corner, or, if possible,
    the parallel curve is cut in order to also exhibit a corner. In a second
    step all self-intersection points are determined and unnecessary parts of
    the path are cut away.

    distance:            the distance of the parallel normpath
    relerr:              distance*relerr is the maximal allowed error in the parallel distance
    sharpoutercorners:   make the outer corners not round but sharp.
                         The inner corners (corners after inflection points) will stay round
    dointersection:      boolean for doing the intersection step (default: 1).
                         Set this value to 0 if you want the whole parallel path
    checkdistanceparams: a list of parameter values in the interval (0,1) where the
                         parallel distance is checked on each normpathitem
    lookforcurvatures:   number of points per normpathitem where is looked for
                         a critical value of the curvature
    """

    # TODO:
    # * DECIDE MEANING of arcs around corners (see case L in test/functional/test_deformer.py)
    # * eliminate double, triple, ... pairs
    # * implement self-intersection of normcurve_pt
    # * implement _between_paths also for normcurve_pt


    def __init__(self, distance, relerr=0.05, sharpoutercorners=False, dointersection=True,
                       checkdistanceparams=[0.5], lookforcurvatures=11, searchstep=0.01, debug=None):
        self.distance = distance
        self.relerr = relerr
        self.sharpoutercorners = sharpoutercorners
        self.checkdistanceparams = checkdistanceparams
        self.lookforcurvatures = lookforcurvatures
        self.dointersection = dointersection
        self.searchstep = searchstep
        self.debug = debug

    def __call__(self, distance=None, relerr=None, sharpoutercorners=None, dointersection=None,
                       checkdistanceparams=None, lookforcurvatures=None, searchstep=None, debug=None):
        # returns a copy of the deformer with different parameters
        if distance is None:
            distance = self.distance
        if relerr is None:
            relerr = self.relerr
        if sharpoutercorners is None:
            sharpoutercorners = self.sharpoutercorners
        if dointersection is None:
            dointersection = self.dointersection
        if checkdistanceparams is None:
            checkdistanceparams = self.checkdistanceparams
        if lookforcurvatures is None:
            lookforcurvatures = self.lookforcurvatures
        if searchstep is None:
            searchstep = self.searchstep
        if debug is None:
            debug = self.debug

        return parallel(distance=distance, relerr=relerr,
                        sharpoutercorners=sharpoutercorners,
                        dointersection=dointersection,
                        checkdistanceparams=checkdistanceparams,
                        lookforcurvatures=lookforcurvatures,
                        searchstep=searchstep,
                        debug=debug)

    def deform(self, basepath):
        basepath = basepath.normpath()
        self.dist_pt = unit.topt(self.distance)
        resultnormsubpaths = []
        par_to_orig = {}
        for nsp in basepath.normsubpaths:
            parallel_normpath, tmp1, tmp2, par2orig = self.deformsubpath(nsp)
            resultnormsubpaths += parallel_normpath.normsubpaths
            for key in par2orig:
                par_to_orig[key] = par2orig[key]
        result = normpath.normpath(resultnormsubpaths)

        if self.dointersection:
            result = self.rebuild_intersected_normpath(result, basepath, par_to_orig)

        return result

    def deformsubpath(self, orig_nsp): # <<<

        """Performs the first step of the deformation: Returns a list of
        normsubpaths building the parallel to the given normsubpath.
        Then calls the intersection routine to do the second step."""
        # the default case is not to join the result.

        dist = self.dist_pt
        epsilon = orig_nsp.epsilon

        if len(orig_nsp.normsubpathitems) == 0:
            return normpath.normpath([]), None, None, {}

        # avoid too small dists: we would run into instabilities
        if abs(dist) < abs(epsilon):
            par_to_orig = {}
            for nspitem in orig_nsp:
                par_to_orig[nspitem] = nspitem
            return normpath.normpath([orig_nsp]), None, None, par_to_orig

        result = None
        par_to_orig = None
        join_begin = None
        prev_joinend = None

        # iterate over the normsubpath in the following way:
        # * for each item first append the additional arc
        #   and then add the next parallel piece
        # * for the first item only add the parallel piece
        #   (because this is done for curr_orig_nspitem, we need to start with i=0)
        for i in range(len(orig_nsp.normsubpathitems)):
            prev_orig_nspitem = orig_nsp.normsubpathitems[i-1]
            curr_orig_nspitem = orig_nsp.normsubpathitems[i]

            # get the next parallel piece for the normpath
            next_parallel_normpath, joinbeg, joinend, par2orig = self.deformsubpathitem(curr_orig_nspitem, epsilon)
            if result is None:
                if join_begin is None:
                    join_begin = joinbeg
                else:
                    join_begin = (join_begin and joinbeg)

            if not (next_parallel_normpath.normsubpaths and next_parallel_normpath[0].normsubpathitems):
                if prev_joinend is None:
                    prev_joinend = joinend
                else:
                    prev_joinend = (prev_joinend and joinend)
                continue

            # this starts the whole normpath
            if result is None:
                result = next_parallel_normpath
                par_to_orig = {}
                for key in par2orig:
                    par_to_orig[key] = par2orig[key]
                prev_joinend = joinend
                continue # there is nothing to join

            prev_tangent, next_tangent, is_straight, is_concave = self._get_angles(prev_orig_nspitem, curr_orig_nspitem, epsilon)
            if not (joinbeg and prev_joinend): # split due to loo large curvature
                result += next_parallel_normpath
            elif is_straight:
                # The path is quite straight between prev and next item:
                # normpath.normpath.join adds a straight line if necessary
                result.join(next_parallel_normpath)
            else:
                # The parallel path can be extended continuously.
                # We must add a corner or an arc around the corner:
                cornerpath = self._path_around_corner(curr_orig_nspitem.atbegin_pt(), result.atend_pt(), next_parallel_normpath.atbegin_pt(),
                                                      prev_tangent, next_tangent, is_concave, epsilon)
                result.join(cornerpath)
                assert len(cornerpath) == 1
                corner = curr_orig_nspitem.atbegin_pt()
                for cp_nspitem in cornerpath[0]:
                    par_to_orig[cp_nspitem] = corner
                # append the next parallel piece to the path
                result.join(next_parallel_normpath)
            for key in par2orig:
                par_to_orig[key] = par2orig[key]
            prev_joinend = joinend

        # end here if nothing has been found so far
        if result is None:
            return normpath.normpath(), False, False, {}

        # the curve around the closing corner may still be missing
        if orig_nsp.closed:
            prev_tangent, next_tangent, is_straight, is_concave = self._get_angles(orig_nsp.normsubpathitems[-1], orig_nsp.normsubpathitems[0], epsilon)
            if not (joinend and join_begin): # do not close because of infinite curvature
                do_close = False
            elif is_straight:
                # The path is quite straight at end and beginning
                do_close = True
            else:
                # The parallel path can be extended continuously.
                do_close = True
                # We must add a corner or an arc around the corner:
                cornerpath = self._path_around_corner(orig_nsp.atend_pt(), result.atend_pt(), result.atbegin_pt(),
                                                      prev_tangent, next_tangent, is_concave, epsilon)
                result.join(cornerpath)
                corner = orig_nsp.atend_pt()
                assert len(cornerpath) == 1
                for cp_nspitem in cornerpath[0]:
                    par_to_orig[cp_nspitem] = corner

            if do_close:
                if len(result) == 1:
                    result[0].close()
                else:
                    # if the parallel normpath is split into several subpaths anyway,
                    # then use the natural beginning and ending
                    # closing is not possible anymore
                    for nspitem in result[0]:
                        result[-1].append(nspitem)
                    result.normsubpaths = result.normsubpaths[1:]
                join_begin, joinend = False, False

        return result, join_begin, joinend, par_to_orig
        # >>>
    def deformsubpathitem(self, nspitem, epsilon): # <<<

        """Returns a parallel normpath for a single normsubpathitem

        Analyzes the curvature of a normsubpathitem and returns a normpath with
        the appropriate number of normsubpaths. This must be a normpath because
        a normcurve can be strongly curved, such that the parallel path must
        contain a hole"""
        # the default case is to join the result. Only if there was an infinite
        # curvature at beginning/end, we return info not to join it.

        dist = self.dist_pt

        # for a simple line we return immediately
        if isinstance(nspitem, normpath.normline_pt):
            normal = nspitem.rotation([0])[0].apply_pt(0, 1)
            start = nspitem.atbegin_pt()
            end = nspitem.atend_pt()
            result = path.line_pt(start[0] + dist * normal[0], start[1] + dist * normal[1],
                                  end[0] + dist * normal[0], end[1] + dist * normal[1]).normpath(epsilon=epsilon)
            assert len(result) == 1 and len(result[0]) == 1
            return result, True, True, {result[0][0]:nspitem}

        # for a curve we have to check if the curvatures
        # cross the singular value 1/dist
        crossings = list(self._distcrossingparameters(nspitem, epsilon))
        crossings.sort()

        # depending on the number of crossings we must consider
        # three different cases:
        if crossings:
            # The curvature crosses the borderline 1/dist
            # the parallel curve contains points with infinite curvature!
            parallcurvs = [inf_curvature]*len(crossings)

            result = normpath.normpath()
            join_begin, join_end = False, False
            par_to_orig = {}

            # we need the endpoints of the nspitem
            if _length_pt(nspitem, crossings[0], 0) > epsilon:
                crossings.insert(0, 0)
                parallcurvs.insert(0, None)
            if _length_pt(nspitem, crossings[-1], 1) > epsilon:
                crossings.append(1)
                parallcurvs.append(None)

            for i in range(len(crossings) - 1):
                middleparam = 0.5*(crossings[i] + crossings[i+1])
                middlecurv = nspitem.curvature_pt([middleparam])[0]
                # the radius is good if
                #  - middlecurv and dist have opposite signs : distance vector points "out" of the original curve
                #  - middlecurv is "smaller" than 1/dist : original curve is less curved than +-1/dist
                if dist*middlecurv < 0 or abs(dist*middlecurv) < 1:
                    if i == 0:
                        join_begin = True
                    elif i == len(crossings) - 2:
                        join_end = True
                    parallel_nsp, par2orig = self.deformnicecurve(nspitem.segments(crossings[i:i+2])[0], epsilon, curvA=parallcurvs[i], curvD=parallcurvs[i+1])
                    # never append empty normsubpaths
                    if parallel_nsp.normsubpathitems:
                        # infinite curvatures interrupt the path and start a new nsp
                        result.append(parallel_nsp)
                        for key in par2orig:
                            par_to_orig[key] = par2orig[key]
            if not (result.normsubpaths and result[0].normsubpathitems):
                return normpath.normpath(), True, True, {}
            return result, join_begin, join_end, par_to_orig

        # the curvature is either bigger or smaller than 1/dist
        middlecurv = nspitem.curvature_pt([0.5])[0]
        if dist*middlecurv < 0 or abs(dist*middlecurv) < 1:
            # The curve is everywhere less curved than 1/dist
            # We can proceed finding the parallel curve for the whole piece
            parallel_nsp, par2orig = self.deformnicecurve(nspitem, epsilon)
            # never append empty normsubpaths
            if parallel_nsp.normsubpathitems:
                par_to_orig = {}
                for key in par2orig:
                    par_to_orig[key] = par2orig[key]
                return normpath.normpath([parallel_nsp]), True, True, par_to_orig

        # the curve is everywhere stronger curved than 1/dist
        # There is nothing to be returned.
        return normpath.normpath(), False, False, {}
        # >>>
    def deformnicecurve(self, normcurve, epsilon, startparam=0.0, endparam=1.0, curvA=None, curvD=None): # <<<
        """Returns a parallel normsubpath for the normcurve.

        This routine assumes that the normcurve is everywhere
        'less' curved than 1/dist. Only at the ends, the curvature
        can be exactly +-1/dist, which is marked by curvA and/or curvD.
        """
        dist = self.dist_pt

        # normalized tangent directions
        tangA, tangD = normcurve.rotation([startparam, endparam])
        tangA = tangA.apply_pt(1, 0)
        tangD = tangD.apply_pt(1, 0)

        # the new starting points
        orig_A, orig_D = normcurve.at_pt([startparam, endparam])
        A = orig_A[0] - dist * tangA[1], orig_A[1] + dist * tangA[0]
        D = orig_D[0] - dist * tangD[1], orig_D[1] + dist * tangD[0]

        # we need to end this _before_ we will run into epsilon-problems
        # when creating curves we do not want to calculate the length of
        # or even split it for recursive calls
        if (math.hypot(A[0] - D[0], A[1] - D[1]) < epsilon and
            abs(dist)*(tangA[0]*tangD[1] - tangA[1]*tangD[0]) < epsilon):
            nl = normpath.normline_pt(A[0], A[1], D[0], D[1])
            return normpath.normsubpath([nl]), {nl:normcurve}

        result = normpath.normsubpath(epsilon=epsilon)
        # is there enough space on the normals before they intersect?
        a, d = intersection(orig_A, orig_D, (-tangA[1], tangA[0]), (-tangD[1], tangD[0]))
        # a,d are the lengths to the intersection points:
        # for a (and equally for b) we can proceed in one of the following cases:
        #   a is None (means parallel normals)
        #   a and dist have opposite signs (and the same for b)
        #   a has the same sign but is bigger
        if ( (a is None or a*dist < 0 or abs(a) > abs(dist) + epsilon) or
             (d is None or d*dist < 0 or abs(d) > abs(dist) + epsilon) ):
            # the original path is long enough to draw a parallel piece
            # this is the generic case. Get the parallel curves
            orig_curvA, orig_curvD = normcurve.curvature_pt([startparam, endparam])
            if curvA is None:
                curvA = orig_curvA / (1.0 - dist*orig_curvA)
            if curvD is None:
                curvD = orig_curvD / (1.0 - dist*orig_curvD)

            # first try to approximate the normcurve with a single item
            controldistpairs = controldists_from_endgeometry_pt(A, D, tangA, tangD, curvA, curvD)

            if controldistpairs:
                # TODO: is it good enough to get the first entry here?
                #       from testing: this fails if there are loops in the original curve
                a, d = controldistpairs[0]
                if a >= 0 and d >= 0:
                    # we avoid to create curves with invalid parameterization
                    if a < epsilon and d < epsilon:
                        result = normpath.normsubpath([normpath.normline_pt(A[0], A[1], D[0], D[1])], epsilon=epsilon)
                    else:
                        a = max(a, epsilon)
                        d = max(d, epsilon)
                        result = normpath.normsubpath([normpath.normcurve_pt(
                            A[0], A[1],
                            A[0] + a * tangA[0], A[1] + a * tangA[1],
                            D[0] - d * tangD[0], D[1] - d * tangD[1],
                            D[0], D[1])], epsilon=epsilon)

            # then try with two items, recursive call
            if ((not result.normsubpathitems) or
                (self.checkdistanceparams and result.normsubpathitems
                 and not self._distchecked(normcurve, result, epsilon, startparam, endparam))):
                # TODO: does this ever converge?
                # TODO: what if this hits epsilon?
                middleparam = 0.5*(startparam + endparam)
                firstnsp, first_par2orig = self.deformnicecurve(normcurve, epsilon, startparam, middleparam, curvA, None)
                secondnsp, second_par2orig = self.deformnicecurve(normcurve, epsilon, middleparam, endparam, None, curvD)
                if not (firstnsp.normsubpathitems and secondnsp.normsubpathitems):
                    result = normpath.normsubpath(
                        [normpath.normline_pt(A[0], A[1], D[0], D[1])], epsilon=epsilon)
                else:
                    result = firstnsp.joined(secondnsp)

        par_to_orig = {}
        for key in result:
            par_to_orig[key] = normcurve
        return result, par_to_orig
        # >>>

    def _path_around_corner(self, corner_pt, beg_pt, end_pt, beg_tangent, end_tangent, is_concave, epsilon): # <<<
        """Helper routine for parallel.deformsubpath: Draws an arc around a convex corner"""
        if self.sharpoutercorners and not is_concave:
            # straight lines:
            t1, t2 = intersection(beg_pt, end_pt, beg_tangent, end_tangent)
            B = beg_pt[0] + t1 * beg_tangent[0], beg_pt[1] + t1 * beg_tangent[1]
            return normpath.normpath([normpath.normsubpath([
                normpath.normline_pt(beg_pt[0], beg_pt[1], B[0], B[1]),
                normpath.normline_pt(B[0], B[1], end_pt[0], end_pt[1])
                ])])

        # We append an arc around the corner
        # these asserts fail in test case "E"
        #assert abs(math.hypot(beg_pt[1] - corner_pt[1], beg_pt[0] - corner_pt[0]) - abs(self.dist_pt)) < epsilon
        #assert abs(math.hypot(end_pt[1] - corner_pt[1], end_pt[0] - corner_pt[0]) - abs(self.dist_pt)) < epsilon
        angle1 = math.atan2(beg_pt[1] - corner_pt[1], beg_pt[0] - corner_pt[0])
        angle2 = math.atan2(end_pt[1] - corner_pt[1], end_pt[0] - corner_pt[0])

        # depending on the direction we have to use arc or arcn
        sinangle = beg_tangent[0]*end_tangent[1] - beg_tangent[1]*end_tangent[0] # >0 for left-turning, <0 for right-turning
        if self.dist_pt > 0:
            arcclass = path.arcn_pt
        else:
            arcclass = path.arc_pt
        return path.path(arcclass(
          corner_pt[0], corner_pt[1], abs(self.dist_pt),
          math.degrees(angle1), math.degrees(angle2))).normpath(epsilon=epsilon)
    # >>>
    def _distchecked(self, orig_normcurve, parallel_normsubpath, epsilon, tstart, tend): # <<<
        """Helper routine for parallel.deformnicecurve: Checks the distances between orig_normcurve and parallel_normsubpath.

        The checking is done at parameters self.checkdistanceparams of orig_normcurve."""

        dist = self.dist_pt
        # do not look closer than epsilon:
        dist_err = mathutils.sign(dist) * max(abs(self.relerr*dist), epsilon)

        checkdistanceparams = [tstart + (tend-tstart)*t for t in self.checkdistanceparams]

        for param, P, rotation in zip(checkdistanceparams,
                                      orig_normcurve.at_pt(checkdistanceparams),
                                      orig_normcurve.rotation(checkdistanceparams)):
            normal = rotation.apply_pt(0, 1)

            # create a short cutline for intersection only:
            cutline = normpath.normsubpath([normpath.normline_pt(
              P[0] + (dist - 2*dist_err) * normal[0], P[1] + (dist - 2*dist_err) * normal[1],
              P[0] + (dist + 2*dist_err) * normal[0], P[1] + (dist + 2*dist_err) * normal[1])], epsilon=epsilon)

            cutparams = parallel_normsubpath.intersect(cutline)
            distances = [math.hypot(P[0] - cutpoint[0], P[1] - cutpoint[1])
                         for cutpoint in cutline.at_pt(cutparams[1])]

            if (not distances) or (abs(min(distances) - abs(dist)) > abs(dist_err)):
                return False

        return True
    # >>>
    def _distcrossingparameters(self, normcurve, epsilon, tstart=0, tend=1): # <<<
        """Helper routine for parallel.deformsubpathitem: Returns a list of parameters where the curvature of normcurve is 1/distance"""

        assert tstart < tend
        dist = self.dist_pt

        # we _need_ to do this with the curvature, not with the radius
        # because the curvature is continuous at the straight line and the radius is not:
        # when passing from one slightly curved curve to the other with opposite curvature sign,
        # via the straight line, then the curvature changes its sign at curv=0, while the
        # radius changes its sign at +/-infinity
        # this causes instabilities for nearly straight curves

        # include tstart and tend
        params = [tstart + i * (tend - tstart) / (self.lookforcurvatures - 1.0)
                  for i in range(self.lookforcurvatures)]
        curvs = normcurve.curvature_pt(params)

        parampairs = list(zip(params[:-1], params[1:]))
        curvpairs = list(zip(curvs[:-1], curvs[1:]))

        crossingparams = set()
        for parampair, curvpair in zip(parampairs, curvpairs):
            begparam, endparam = parampair
            begcurv, endcurv = curvpair
            begchange = begcurv*dist - 1
            endchange = endcurv*dist - 1
            if begchange*endchange < 0:
                # the curvature crosses the value 1/dist
                # get the parmeter value by linear interpolation:
                middleparam = (
                  (begparam * abs(begchange) + endparam * abs(endchange)) /
                  (abs(begchange) + abs(endchange)))
                try:
                    middleradius = 1/normcurve.curvature_pt([middleparam])[0]
                except ArithmeticError:
                    raise InvalidParamException(middleparam)

                if abs(middleradius - dist) < epsilon or endparam-begparam < 1.0e-14:
                    # get the parmeter value by linear interpolation:
                    crossingparams.add(middleparam)
                else:
                    # call recursively:
                    for x in self._distcrossingparameters(normcurve, epsilon, tstart=begparam, tend=endparam):
                        crossingparams.add(x)
            else:
                if begchange == 0:
                    crossingparams.add(begparam)
                if endchange == 0:
                    crossingparams.add(endparam)

        return crossingparams
        # >>>
    def _get_angles(self, prev_nspitem, next_nspitem, epsilon): # <<<
        prev_rotation = prev_nspitem.rotation([1])[0]
        next_rotation = next_nspitem.rotation([0])[0]
        prev_tangent = prev_rotation.apply_pt(1, 0)
        prev_orthogo = prev_rotation.apply_pt(0, self.dist_pt) # points towards parallel path (prev_nspitem is on original path)
        next_tangent = next_rotation.apply_pt(1, 0)
        #sinangle = prev_tangent[0]*next_tangent[1] - prev_tangent[1]*next_tangent[0] # >0 for left-turning, <0 for right-turning
        cosangle = prev_tangent[0]*next_tangent[0] + prev_tangent[1]*next_tangent[1]
        proj = prev_orthogo[0]*next_tangent[0] + prev_orthogo[1]*next_tangent[1]
        is_straight = (cosangle > 0 and abs(proj) < epsilon)
        is_concave = (proj > 0)
        return prev_tangent, next_tangent, is_straight, is_concave
    # >>>

    def rebuild_intersected_normpath(self, par_np, orig_np, par2orig, epsilon=None): # <<<

        dist = self.dist_pt
        if epsilon is None:
            epsilon = orig_np.normsubpaths[0].epsilon
        eps_comparepairs = 10*epsilon

        # calculate the self-intersections of the par_np
        forwardpairs, backwardpairs = self.normpath_selfintersections(par_np, epsilon, eps_comparepairs)
        # calculate the intersections of the par_np with the original path
        origintparams, orig_origintparams = self.normpath_origintersections(orig_np, par_np, epsilon)
        if not forwardpairs:
            if origintparams:
                return normpath.normpath()
            else:
                return par_np

        # parameters at begin and end of subnormpaths:
        # omit those which start/end on the original path
        beginparams = []
        endparams = []
        testparams = origintparams + list(forwardpairs.keys()) + list(forwardpairs.values())
        for i, nsp in enumerate(par_np):
            beginparam = mynormpathparam(par_np, i, 0, 0)
            is_new = True
            for param in testparams:
                if beginparam.is_equiv(param):
                    is_new = False
                    break
            if is_new:
                beginparams.append(beginparam)

            endparam = mynormpathparam(par_np, i, len(nsp)-1, 1)
            is_new = True
            for param in testparams:
                if endparam.is_equiv(param):
                    is_new = False
                    break
            if is_new:
                endparams.append(endparam)
        beginparams.sort()
        endparams.sort()

        # we need a way to get the "next" param on the normpath
        # XXX why + beginparams + endparams ?
        allparams = list(forwardpairs.keys()) + list(backwardpairs.keys()) + origintparams + beginparams + endparams
        allparams.sort()
        done = {}
        for param in allparams:
            done[param] = False
        nextp = {}
        for i, param in enumerate(allparams[:-1]):
            nextp[param] = allparams[i+1]
        for endparam in endparams:
            if par_np[endparam.normsubpathindex].closed:
                begparam = [p for p in allparams if p.normsubpathindex == endparam.normsubpathindex][0]
                assert begparam.normsubpathitemindex == 0
                assert begparam.normsubpathitemparam == 0
                nextp[endparam] = begparam
            else:
                nextp[endparam] = None

        # exclude all intersections that are between the original and the parallel path:
        # See for example test/functional/test_deformer (parallel Z): There can
        # remain a little piece of the path (triangle) that lies between a lot
        # of intersection points. Simple intersection rules such as thoe in
        # trial_parampairs cannot exclude this piece.
        for param in forwardpairs:
            if done[param] or done[forwardpairs[param]]:
                done[param] = done[forwardpairs[param]] = True
            elif self._between_paths(par_np.at_pt(param), par2orig, 4*epsilon):
                done[param] = done[forwardpairs[param]] = True
        for param in beginparams + endparams:
            if self._between_paths(par_np.at_pt(param), par2orig, 4*epsilon):
                done[param] = True

        # visualize the intersection points: # <<<
        if self.debug is not None:
            for param1, param2 in forwardpairs.items():
                point1, point2 = par_np.at([param1, param2])
                if not done[param1]:
                    self.debug.fill(path.circle(point1[0], point1[1], 0.05), [color.rgb.red])
                if not done[param2]:
                    self.debug.fill(path.circle(point2[0], point2[1], 0.03), [color.rgb.black])
            for param in origintparams:
                #assert done[param]
                point = par_np.at([param])[0]
                self.debug.fill(path.circle(point[0], point[1], 0.05), [color.rgb.green])
            for i, nsp in enumerate(par_np):
              for j, nspi in enumerate(nsp):
                x, y = nspi.at_pt([0.5])[0]
                self.debug.text_pt(x, y, "{}/{}".format(i,j))#, [text.halign.center, text.vshift.mathaxis])
            print("aborted path intersection due to debug")
            return par_np
        # >>>

        def ptype(param): # <<<
            if param in forwardpairs : return "fw with partner %s" % (forwardpairs[param])
            if param in backwardpairs : return "bw with partner %s" % (backwardpairs[param])
            if param in origintparams: return "orig"
            if param in beginparams: return "begin"
            if param in endparams: return "end"
        # >>>
        def trial_parampairs(startp): # <<<
            """Starting at startp, try to find a valid series of intersection parameters"""
            tried = {} # a local copy of done
            for param in allparams:
                tried[param] = done[param]

            previousp = startp
            currentp = nextp[previousp]
            result = []

            while True:
                # successful and unsuccessful termination conditions:
                if tried[currentp]:
                    # we reached a branch that has already been treated
                    # ==> this is not a valid parallel path
                    return []
                if currentp in origintparams:
                    # we cross the original path
                    # ==> this is not a valid parallel path
                    return []
                if currentp in backwardpairs:
                    # we reached a branch that should be followed from another part
                    # ==> this is not a valid parallel path
                    return []
                if currentp is startp:
                    # we have reached again the starting point on a closed subpath.
                    assert startp in beginparams
                    assert previousp in endparams
                    return result
                if currentp in forwardpairs:
                    result.append((previousp, currentp))
                    if forwardpairs[currentp] is startp:
                        # we have found the same point as the startp (its pair partner)
                        return result
                    previousp = forwardpairs[currentp]
                if currentp in endparams:
                    result.append((previousp, currentp))
                    if nextp[currentp] is None: # open subpath
                        # we have found the end of a non-closed subpath
                        return result
                    previousp = currentp # closed subpath
                # follow the crossings on valid startpairs
                tried[currentp] = True
                tried[previousp] = True
                currentp = nextp[previousp]
            assert False # never reach this point
        # >>>

        # first the paths that start at the beginning of a subnormpath:
        result = normpath.normpath()
        # paths can start on subnormpaths or crossings where we can "get away":
        bwkeys = list(backwardpairs.keys())
        bwkeys.sort()
        for startp in beginparams + bwkeys:
            if done[startp]:
                continue

            # try to find a valid series of intersection points:
            parampairs = trial_parampairs(startp)
            if not parampairs:
                continue

            # collect all the pieces between parampairs:
            add_nsp = normpath.normsubpath(epsilon=epsilon)
            for begin, end in parampairs:
                # check that trial_parampairs works correctly
                assert begin is not end
                for item in par_np[begin.normsubpathindex].segments(
                    [begin.normsubpathparam, end.normsubpathparam])[0].normsubpathitems:
                    # TODO: this should be obsolete with an improved intersection algorithm
                    #       guaranteeing epsilon
                    if add_nsp.normsubpathitems:
                        item = item.modifiedbegin_pt(*(add_nsp.atend_pt()))
                    add_nsp.append(item)

                done[begin] = True
                done[end] = True

            # close the path if necessary
            if add_nsp:
                if ((parampairs[-1][-1] in forwardpairs and forwardpairs[parampairs[-1][-1]] is parampairs[0][0]) or
                    (parampairs[-1][-1] in endparams and parampairs[0][0] in beginparams and parampairs[0][0] is nextp[parampairs[-1][-1]])):
                    add_nsp.normsubpathitems[-1] = add_nsp.normsubpathitems[-1].modifiedend_pt(*add_nsp.atbegin_pt())
                    add_nsp.close()

            result.extend([add_nsp])

        return result
    # >>>
    def normpath_selfintersections(self, np, epsilon, eps_comparepairs): # <<<

        """Returns all self-intersection points of normpath np.

        This does not include the intersections of a single normcurve with itself,
        but all intersections of one normpathitem with a different one in the path.
        The intersection pairs are such that the parallel path can be continued
        from the first to the second parameter, but not vice-versa."""

        dist = self.dist_pt

        n = len(np)
        forwardpairs = {}
        for nsp_i in range(n):
            for nsp_j in range(nsp_i, n):
                for nspitem_i in range(len(np[nsp_i])):
                    if nsp_j == nsp_i:
                        nspitem_j_range = list(range(nspitem_i+1, len(np[nsp_j])))
                    else:
                        nspitem_j_range = list(range(len(np[nsp_j])))
                    for nspitem_j in nspitem_j_range:
                        intsparams = np[nsp_i][nspitem_i].intersect(np[nsp_j][nspitem_j], epsilon)
                        if intsparams:
                            for intsparam_i, intsparam_j in intsparams:
                                npp_i = mynormpathparam(np, nsp_i, nspitem_i, intsparam_i)
                                npp_j = mynormpathparam(np, nsp_j, nspitem_j, intsparam_j)

                                # skip successive nsp-items
                                if nsp_i == nsp_j:
                                    if nspitem_j == nspitem_i+1 and (npp_i.is_end_of_nspitem(epsilon) or npp_j.is_beg_of_nspitem(epsilon)):
                                        continue
                                    if np[nsp_i].closed and ((npp_i.is_beg_of_nsp(epsilon) and npp_j.is_end_of_nsp(epsilon)) or
                                                             (npp_j.is_beg_of_nsp(epsilon) and npp_i.is_end_of_nsp(epsilon))):
                                        continue

                                # correct the order of the pair, such that we can use it to continue on the path
                                if not self._can_continue(npp_i, npp_j, epsilon):
                                    assert self._can_continue(npp_j, npp_i, epsilon)
                                    npp_i, npp_j = npp_j, npp_i

                                # if the intersection is between two nsp-items, take the smallest -> largest
                                npp_i = npp_i.smaller_equiv(5*epsilon)
                                npp_j = npp_j.larger_equiv(5*epsilon)

                                # because of the above change of npp_ij, and because there may be intersections between nsp-items,
                                # it may happen that we try to insert two times the same pair
                                if self._skip_intersection_doublet(npp_i, npp_j, forwardpairs, eps_comparepairs):
                                    continue
                                forwardpairs[npp_i] = npp_j

        # this is partially done in _skip_intersection_doublet
        #forwardpairs = self._elim_intersection_doublets(forwardpairs, eps_comparepairs)
        # create the reverse mapping
        backwardpairs = {}
        for p, q in forwardpairs.items():
            backwardpairs[q] = p
        return forwardpairs, backwardpairs

    # >>>
    def normpath_origintersections(self, orig_np, par_np, epsilon): # <<<
        """return all intersection points of the original path and the parallel path"""

        # this code became necessary with introduction of mynormpathparam
        params = []
        oparams = []
        for nsp_i in range(len(orig_np)):
            for nsp_j in range(len(par_np)):
                for nspitem_i in range(len(orig_np[nsp_i])):
                    for nspitem_j in range(len(par_np[nsp_j])):
                        intsparams = orig_np[nsp_i][nspitem_i].intersect(par_np[nsp_j][nspitem_j], epsilon)
                        if intsparams:
                            for intsparam_i, intsparam_j in intsparams:
                                npp_i = mynormpathparam(orig_np, nsp_i, nspitem_i, intsparam_i)
                                npp_j = mynormpathparam(par_np, nsp_j, nspitem_j, intsparam_j)

                                oparams.append(npp_i)
                                params.append(npp_j)
        return params, oparams
    # >>>
    def _can_continue(self, param1, param2, epsilon=None): # <<<
        """Test whether the parallel path can be continued at the param-pair (param1, param2)"""
        par_np = param1.normpath
        if epsilon is None:
            epsilon = par_np[0].epsilon

        rot1, rot2 = par_np.rotation([param1, param2])
        orth1 = rot1.apply_pt(0, self.dist_pt) # directs away from original path (as seen from parallel path)
        tang2 = rot2.apply_pt(1, 0)

        # the self-intersection is valid if the tangents
        # point into the correct direction or, for parallel tangents,
        # if the curvature is such that the on-going path does not
        # enter the region defined by dist
        proj = orth1[0]*tang2[0] + orth1[1]*tang2[1]
        if abs(proj) > epsilon: # the curves are not parallel
            # tang2 must go away from the original path
            return (proj > 0)

        # tang1 and tang2 are parallel.
        curv1, curv2 = par_np.curvature_pt([param1, param2])

        # We need to treat also cases where the params are nspitem-endpoints.
        # There, we know that the tangents are continuous, but the curvature is
        # not necessarily continuous. We have to test whether the curve *after*
        # param2 has curvature such that it enters the forbidden side of the
        # curve after param1
        if param1.is_end_of_nspitem(epsilon):
            curv1 = par_np.curvature_pt([param1.larger_equiv(epsilon)])[0]
        if param2.is_end_of_nspitem(epsilon):
            curv2 = par_np.curvature_pt([param2.larger_equiv(epsilon)])[0]

        tang1 = rot1.apply_pt(1, 0)
        running_back = (tang1[0]*tang2[0] + tang1[1]*tang2[1] < 0)
        if running_back:
            # the second curve is running "back" -- the curvature sign appears to be switched
            curv2 = -curv2
            # endpoints of normsubpaths must be treated differently:

        if (not running_back) and param1.is_end_of_nsp(epsilon):
            return True

        if curv1 == curv2:
            raise IntersectionError("Cannot determine whether curves intersect (parallel and equally curved)")

        if self.dist_pt > 0:
            return (curv2 > curv1)
        else:
            return (curv2 < curv1)
    # >>>
    def _skip_intersection_doublet(self, npp_i, npp_j, parampairs, epsilon): # <<<
        # An intersection point that lies exactly between two nsp-items can occur twice or more
        # times if we calculate all mutual intersections. We should take only
        # one such parameter pair, namely the one with smallest first and
        # largest last param.
        result = False
        delete_keys = []
        delete_values = []
        # TODO: improve complexity?
        for pi, pj in parampairs.items():
            if npp_i.is_equiv(pi, epsilon) and npp_j.is_equiv(pj, epsilon):
                #print("double pair: ", npp_i, npp_j, pi, pj)
                #print("... replacing ", pi, parampairs[pi], "by", min(npp_i, pi), max(npp_j, pj))
                delete_keys.append(pi)
                delete_values.append(pj)
                result = True # we have already added this one
        newkey = min([npp_i] + delete_keys)
        newval = max([npp_j] + delete_values)
        for pi in delete_keys:
            del parampairs[pi]
        parampairs[newkey] = newval
        return result
    # >>>
    def _elim_intersection_doublets(self, parampairs, epsilon): # <<<
        # It may always happen that three intersections coincide. (It will
        # occur often with degenerate distances for technical designs such as
        # those used in microfluidics). We then have two equivalent pairs in our
        # forward list, and we must throw away one of them.
        # One of them is indeed forbidden by the _can_continue of the other.

        # TODO implement this

        keys = list(parampairs.keys())
        n = len(keys)
        for i in range(n):
            start = "equivalent pairs\n"
            for j in range(i+1, n):
                key1, key2 = keys[i], keys[j]
                npp1 = parampairs[key1]
                npp2 = parampairs[key2]
                #assert key1.is_equiv(npp1, epsilon)
                #if not key2.is_equiv(npp2, epsilon):
                #    np = key2.normpath
                #    print(np.at_pt(key2), np.at_pt(npp2), _length_pt(np, key2, npp2)/epsilon)
                #assert key2.is_equiv(npp2, epsilon)
                if ((key1.is_equiv(key2, epsilon) and npp1.is_equiv(npp2, epsilon)) or
                    (key1.is_equiv(npp2, epsilon) and npp1.is_equiv(key2, epsilon))):
                    print(start,"pair: ", key1, npp1, " and ", key2, npp2)
                    start = ""
            if not start:
                print()
        return parampairs
    # >>>
    def _between_paths(self, pos, par2orig, epsilon): # <<<
        """Tests whether the given point (pos) is found in the forbidden zone between an original and a parallel nsp-item (these are in par2orig)

        The test uses epsilon close to the original/parallel path, and sharp comparison at their ends."""
        dist = self.dist_pt
        for par_nspitem in par2orig:
            origobj = par2orig[par_nspitem]
            if isinstance(origobj, normpath.normline_pt):
                rot = origobj.rotation([0])[0]
                t, s = intersection(pos, origobj.atbegin_pt(), rot.apply_pt(0, mathutils.sign(dist)), rot.apply_pt(origobj.arclen_pt(epsilon), 0))
                if 0 <= s <= 1 and -abs(dist)+epsilon < t < -epsilon:
                    return True
            elif isinstance(origobj, normpath.normcurve_pt):
                # TODO: implement this
                # TODO: pre-sort par2orig as a list to fasten up this code
                pass
            else:
                cx, cy = origobj
                if math.hypot(pos[0]-cx, pos[1]-cy) < abs(dist) - epsilon:
                    if self.dist_pt > 0: # running around (cx,cy) in the negative sense (see _path_around_corner)
                        x0, y0 = par_nspitem.atend_pt()
                        x1, y1 = par_nspitem.atbegin_pt()
                    else: # running around (cx,cy) in the positive sense
                        x0, y0 = par_nspitem.atbegin_pt()
                        x1, y1 = par_nspitem.atend_pt()
                    t0, s0 = intersection(pos, (cx, cy), (-y0+cy, x0-cx), (x0-cx, y0-cy))
                    t1, s1 = intersection(pos, (cx, cy), ( y1-cy,-x1+cx), (x1-cx, y1-cy))
                    if t0 <= 0 and s0 >= 0 and t1 <= 0 and s1 >= 0:
                        return True
        return False
    # >>>

# >>>

parallel.clear = attr.clearclass(parallel)

class linesmoothed(baseclasses.deformer): # <<<

    def __init__(self, tension=1, atleast=False, lcurl=1, rcurl=1):
        """Tension and atleast control the tension of the replacement curves.
        l/rcurl control the curlynesses at (possible) endpoints. If a curl is
        set to None, the angle is taken from the original path."""
        if atleast:
            self.tension = -abs(tension)
        else:
            self.tension = abs(tension)
        self.lcurl = lcurl
        self.rcurl = rcurl

    def __call__(self, tension=_marker, atleast=_marker, lcurl=_marker, rcurl=_marker):
        if tension is _marker:
            tension = self.tension
        if atleast is _marker:
            atleast = (self.tension < 0)
        if lcurl is _marker:
            lcurl = self.lcurl
        if rcurl is _marker:
            rcurl = self.rcurl
        return linesmoothed(tension, atleast, lcurl, rcurl)

    def deform(self, basepath):
        newnp = normpath.normpath()
        for nsp in basepath.normpath().normsubpaths:
            newnp += self.deformsubpath(nsp)
        return newnp

    def deformsubpath(self, nsp):
        from .metapost import path as mppath
        """Returns a path/normpath from the points in the given normsubpath"""
        # TODO: epsilon ?
        knots = []

        # first point
        x_pt, y_pt = nsp.atbegin_pt()
        if nsp.closed:
            knots.append(mppath.smoothknot_pt(x_pt, y_pt))
        elif self.lcurl is None:
            rot = nsp.rotation([0])[0]
            dx, dy = rot.apply_pt(1, 0)
            angle = math.atan2(dy, dx)
            knots.append(mppath.beginknot_pt(x_pt, y_pt, angle=angle))
        else:
            knots.append(mppath.beginknot_pt(x_pt, y_pt, curl=self.lcurl))

        # intermediate points:
        for npelem in nsp[:-1]:
            knots.append(mppath.tensioncurve(self.tension))
            knots.append(mppath.smoothknot_pt(*npelem.atend_pt()))

        # last point
        knots.append(mppath.tensioncurve(self.tension))
        x_pt, y_pt = nsp.atend_pt()
        if nsp.closed:
            pass
        elif self.rcurl is None:
            rot = nsp.rotation([len(nsp)])[0]
            dx, dy = rot.apply_pt(1, 0)
            angle = math.atan2(dy, dx)
            knots.append(mppath.endknot_pt(x_pt, y_pt, angle=angle))
        else:
            knots.append(mppath.endknot_pt(x_pt, y_pt, curl=self.rcurl))

        return mppath.path(knots)
# >>>

linesmoothed.clear = attr.clearclass(linesmoothed)


# vim:foldmethod=marker:foldmarker=<<<,>>>
