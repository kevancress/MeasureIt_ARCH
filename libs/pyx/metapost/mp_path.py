# -*- coding: ISO-8859-1 -*-
#
# Copyright (C) 2011 Michael Schindler <m-schindler@users.sourceforge.net>
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

from math import atan2, sin, cos, sqrt, pi

################################################################################
# Internal functions of MetaPost
#
# This file re-implements some of the functionality of MetaPost
# (http://tug.org/metapost). MetaPost was developed by John D. Hobby and
# others. The code of Metapost is in the public domain, which we understand as
# an implicit permission to reuse the code here (see the comment at
# http://www.gnu.org/licenses/license-list.html)
#
# This file is based on the MetaPost version distributed by TeXLive:
# svn://tug.org/texlive/trunk/Build/source/texk/web2c/mplibdir revision 22737 #
# (2011-05-31)
################################################################################

# from mplib.h:
mp_endpoint = 0
mp_explicit = 1
mp_given = 2
mp_curl = 3
mp_open = 4
mp_end_cycle = 5

# from mpmath.c:
unity = 1.0
two = 2.0
fraction_half = 0.5
fraction_one = 1.0
fraction_three = 3.0
one_eighty_deg = pi
three_sixty_deg = 2*pi

def mp_make_choices(knots, epsilon): # <<<
    """Implements mp_make_choices from metapost (mp.c)"""
    # 334: If consecutive knots are equal, join them explicitly
    p = knots
    while True:
        q = p.next
        if p.rtype > mp_explicit and (p.x_pt-q.x_pt)**2 + (p.y_pt-q.y_pt)**2 < epsilon**2:
            p.rtype = mp_explicit
            if p.ltype == mp_open:
                p.ltype = mp_curl
                p.set_left_curl(unity)
            q.ltype = mp_explicit
            if q.rtype == mp_open:
                q.rtype = mp_curl
                q.set_right_curl(unity)
            p.rx_pt = p.x_pt
            q.lx_pt = p.x_pt
            p.ry_pt = p.y_pt
            q.ly_pt = p.y_pt
        p = q
        if p is knots:
            break

    # 335:
    # If there are no breakpoints, it is necessary to compute the direction angles around an entire cycle.
    # In this case the mp left type of the first node is temporarily changed to end cycle.
    # Find the first breakpoint, h, on the path
    # insert an artificial breakpoint if the path is an unbroken cycle
    h = knots
    while True:
        if h.ltype != mp_open or h.rtype != mp_open:
            break
        h = h.next
        if h is knots:
            h.ltype = mp_end_cycle
            break

    p = h
    while True:
        # 336:
        # Fill in the control points between p and the next breakpoint, then advance p to that breakpoint
        q = p.next
        if p.rtype >= mp_given:
            while q.ltype == mp_open and q.rtype == mp_open:
                q = q.next
            # the breakpoints are now p and q

            # 346:
            # Calculate the turning angles psi_k and the distances d(k, k+1)
            # set n to the length of the path
            k = 0
            s = p
            n = knots.linked_len()
            delta_x, delta_y, delta, psi = [], [], [], [None]
            while True:
                t = s.next
                assert len(delta_x) == k
                delta_x.append(t.x_pt - s.x_pt)
                delta_y.append(t.y_pt - s.y_pt)
                delta.append(mp_pyth_add(delta_x[k], delta_y[k]))
                if k > 0:
                    sine = mp_make_fraction(delta_y[k-1], delta[k-1])
                    cosine = mp_make_fraction(delta_x[k-1], delta[k-1])
                    psi.append(mp_n_arg(
                      mp_take_fraction(delta_x[k], cosine) + mp_take_fraction(delta_y[k], sine),
                      mp_take_fraction(delta_y[k], cosine) - mp_take_fraction(delta_x[k], sine)))
                k += 1
                s = t
                if s == q:
                    n = k
                if k >= n and s.ltype != mp_end_cycle:
                    break
            if k == n:
                psi.append(0)
            else:
                # for closed paths:
                psi.append(psi[1])

            # 347: Remove open types at the breakpoints
            if q.ltype == mp_open:
                delx_pt = q.rx_pt - q.x_pt
                dely_pt = q.ry_pt - q.y_pt
                if delx_pt**2 + dely_pt**2 < epsilon**2:
                    # use curl if the controls are not usable for giving an angle
                    q.ltype = mp_curl
                    q.set_left_curl(unity)
                else:
                    q.ltype = mp_given
                    q.set_left_given(mp_n_arg(delx_pt, dely_pt))

            if p.rtype == mp_open and p.ltype == mp_explicit:
                delx_pt = p.x_pt - p.lx_pt
                dely_pt = p.y_pt - p.ly_pt
                if delx_pt**2 + dely_pt**2 < epsilon**2:
                    p.rtype = mp_curl
                    p.set_right_curl(unity)
                else:
                    p.rtype = mp_given
                    p.set_right_given(mp_n_arg(delx_pt, dely_pt))

            # call the internal solving routine
            mp_solve_choices(p, q, n, delta_x, delta_y, delta, psi)

        elif p.rtype == mp_endpoint:
            # 337: Give reasonable values for the unused control points between p and q
            p.rx_pt = p.x_pt
            p.ry_pt = p.y_pt
            q.lx_pt = q.x_pt
            q.ly_pt = q.y_pt

        p = q
        if p is h:
            break
# >>>
def mp_solve_choices(p, q, n, delta_x, delta_y, delta, psi): # <<<
    """Implements mp_solve_choices form metapost (mp.c)"""
    uu = [None]*(len(delta)+1) # relations between adjacent angles ("matrix" entries)
    ww = [None]*len(uu) # additional matrix entries for the cyclic case
    vv = [None]*len(uu) # angles ("rhs" entries)
    theta = [None]*len(uu) # solution of the linear system of equations
    # 348:
    # the "matrix" is in tridiagonal form, the solution is obtained by Gaussian elimination.
    # uu and ww are of type "fraction", vv and theta are of type "angle"
    # k is the current knot number
    # r, s, t registers for list traversal
    k = 0
    s = p
    r = 0
    while True:
        t = s.next
        if k == 0: # <<<
            # 354:
            # Get the linear equations started
            # or return with the control points in place, if linear equations needn't be solved

            if s.rtype == mp_given: # <<<
                if t.ltype == mp_given:
                    # 372: Reduce to simple case of two givens and return
                    aa = mp_n_arg(delta_x[0], delta_y[0])
                    ct, st = mp_n_sin_cos(p.right_given() - aa)
                    cf, sf = mp_n_sin_cos(q.left_given() - aa)
                    mp_set_controls(p, q, delta_x[0], delta_y[0], st, ct, -sf, cf)
                    return
                else:
                    # 362:
                    vv[0] = s.right_given() - mp_n_arg(delta_x[0], delta_y[0])
                    vv[0] = reduce_angle(vv[0])
                    uu[0] = 0
                    ww[0] = 0
            # >>>
            elif s.rtype == mp_curl: # <<<
                if t.ltype == mp_curl:
                    # 373: (mp.pdf) Reduce to simple case of straight line and return
                    p.rtype = mp_explicit
                    q.ltype = mp_explicit
                    lt = abs(q.left_tension())
                    rt = abs(p.right_tension())

                    ff = mp_make_fraction(unity, 3.0*rt)
                    p.rx_pt = p.x_pt + mp_take_fraction(delta_x[0], ff)
                    p.ry_pt = p.y_pt + mp_take_fraction(delta_y[0], ff)

                    ff = mp_make_fraction(unity, 3.0*lt)
                    q.lx_pt = q.x_pt - mp_take_fraction(delta_x[0], ff)
                    q.ly_pt = q.y_pt - mp_take_fraction(delta_y[0], ff)
                    return

                else: # t.ltype != mp_curl
                    # 363:
                    cc = s.right_curl()
                    lt = abs(t.left_tension())
                    rt = abs(s.right_tension())
                    uu[0] = mp_curl_ratio(cc, rt, lt)
                    vv[0] = -mp_take_fraction(psi[1], uu[0])
                    ww[0] = 0
            # >>>
            elif s.rtype == mp_open: # <<<
                uu[0] = 0
                vv[0] = 0
                ww[0] = fraction_one
            # >>>
        # end of 354 >>>
        else: # k > 0 <<<

            if s.ltype == mp_end_cycle or s.ltype == mp_open: # <<<
                # 356: Set up equation to match mock curvatures at z_k;
                #      then finish loop with theta_n adjusted to equal theta_0, if a
                #      cycle has ended

                # 357: Calculate the values
                #      aa = Ak/Bk, bb = Dk/Ck, dd = (3-alpha_{k-1})d(k,k+1),
                #      ee = (3-beta_{k+1})d(k-1,k), cc=(Bk-uk-Ak)/Bk
                aa = mp_make_fraction(unity, 3.0*abs(r.right_tension()) - unity)
                dd = mp_take_fraction(delta[k],
                                      fraction_three - mp_make_fraction(unity, abs(r.right_tension())))
                bb = mp_make_fraction(unity, 3*abs(t.left_tension()) - unity)
                ee = mp_take_fraction(delta[k-1],
                                      fraction_three - mp_make_fraction(unity, abs(t.left_tension())))
                cc = fraction_one - mp_take_fraction(uu[k-1], aa)

                # 358: Calculate the ratio ff = Ck/(Ck + Bk - uk-1Ak)
                dd = mp_take_fraction(dd, cc)
                lt = abs(s.left_tension())
                rt = abs(s.right_tension())
                if lt < rt:
                    dd *= (lt/rt)**2
                elif lt > rt:
                    ee *= (rt/lt)**2
                ff = mp_make_fraction(ee, ee + dd)

                uu[k] = mp_take_fraction(ff, bb)

                # 359: Calculate the values of vk and wk
                acc = -mp_take_fraction(psi[k+1], uu[k])
                if r.rtype == mp_curl:
                    ww[k] = 0
                    vv[k] = acc - mp_take_fraction(psi[1], fraction_one - ff)
                else:
                    ff = mp_make_fraction(fraction_one - ff, cc)
                    acc = acc - mp_take_fraction(psi[k], ff)
                    ff = mp_take_fraction(ff, aa)
                    vv[k] = acc - mp_take_fraction(vv[k-1], ff)
                    ww[k] = -mp_take_fraction(ww[k-1], ff)

                if s.ltype == mp_end_cycle:
                    # 360: Adjust theta_n to equal theta_0 and finish loop

                    aa = 0
                    bb = fraction_one
                    while True:
                        k -= 1
                        if k == 0:
                            k = n
                        aa = vv[k] - mp_take_fraction(aa, uu[k])
                        bb = ww[k] - mp_take_fraction(bb, uu[k])
                        if k == n:
                            break
                    aa = mp_make_fraction(aa, fraction_one - bb)
                    theta[n] = aa
                    vv[0] = aa
                    for k in range(1, n):
                        vv[k] = vv[k] + mp_take_fraction(aa, ww[k])
                    break
            # >>>
            elif s.ltype == mp_curl: # <<<
                # 364:
                cc = s.left_curl()
                lt = abs(s.left_tension())
                rt = abs(r.right_tension())
                ff = mp_curl_ratio(cc, lt, rt)
                theta[n] = -mp_make_fraction(mp_take_fraction(vv[n-1], ff),
                                             fraction_one - mp_take_fraction(ff, uu[n-1]))
                break
            # >>>
            elif s.ltype == mp_given: # <<<
                # 361:
                theta[n] = s.left_given() - mp_n_arg(delta_x[n-1], delta_y[n-1])
                theta[n] = reduce_angle(theta[n])
                break
            # >>>

        # end of k == 0, k != 0 >>>

        r = s
        s = t
        k += 1

    # 367:
    # Finish choosing angles and assigning control points
    for k in range(n-1, -1, -1):
        theta[k] = vv[k] - mp_take_fraction(theta[k+1], uu[k])
    s = p
    k = 0
    while True:
        t = s.next
        ct, st = mp_n_sin_cos(theta[k])
        cf, sf = mp_n_sin_cos(-psi[k+1]-theta[k+1])
        mp_set_controls(s, t, delta_x[k], delta_y[k], st, ct, sf, cf)
        k += 1
        s = t
        if k == n:
            break
# >>>
def mp_n_arg(x, y): # <<<
    return atan2(y, x)
# >>>
def mp_n_sin_cos(z): # <<<
    """Given an integer z that is 2**20 times an angle theta in degrees, the
    purpose of n sin cos(z) is to set x = r cos theta and y = r sin theta
    (approximately), for some rather large number r. The maximum of x and y
    will be between 2**28 and 2**30, so that there will be hardly any loss of
    accuracy. Then x and y are divided by r."""
    # 67: mpmath.pdf
    return cos(z), sin(z)
# >>>
def mp_set_controls(p, q, delta_x, delta_y, st, ct, sf, cf): # <<<
    """The set controls routine actually puts the control points into a pair of
    consecutive nodes p and q. Global variables are used to record the values
    of sin(theta), cos(theta), sin(phi), and cos(phi) needed in this
    calculation.

    See mp.pdf, item 370"""
    lt = abs(q.left_tension())
    rt = abs(p.right_tension())
    rr = mp_velocity(st, ct, sf, cf, rt)
    ss = mp_velocity(sf, cf, st, ct, lt)
    if p.right_tension() < 0 or q.left_tension() < 0:
        # 371: Decrease the velocities, if necessary, to stay inside the bounding triangle
        # this is the only place where the sign of the tension counts
        if (st >= 0 and sf >= 0) or (st <= 0 and sf <= 0):
            sine = mp_take_fraction(abs(st), cf) + mp_take_fraction(abs(sf), ct) # sin(theta+phi)
            if sine > 0:
                #sine = mp_take_fraction(sine, fraction_one + unity) # safety factor
                sine *= 1.00024414062 # safety factor
                if p.right_tension() < 0:
                    if mp_ab_vs_cd(abs(sf), fraction_one, rr, sine) < 0:
                        rr = mp_make_fraction(abs(sf), sine)
                if q.left_tension() < 0:
                    if mp_ab_vs_cd(abs(st), fraction_one, ss, sine) < 0:
                        ss = mp_make_fraction(abs(st), sine)

    p.rx_pt = p.x_pt + mp_take_fraction(mp_take_fraction(delta_x, ct) - mp_take_fraction(delta_y, st), rr)
    p.ry_pt = p.y_pt + mp_take_fraction(mp_take_fraction(delta_y, ct) + mp_take_fraction(delta_x, st), rr)
    q.lx_pt = q.x_pt - mp_take_fraction(mp_take_fraction(delta_x, cf) + mp_take_fraction(delta_y, sf), ss)
    q.ly_pt = q.y_pt - mp_take_fraction(mp_take_fraction(delta_y, cf) - mp_take_fraction(delta_x, sf), ss)
    p.rtype = mp_explicit
    q.ltype = mp_explicit
# >>>
def mp_make_fraction(p, q): # <<<
    # 17: mpmath.pdf
    """The make fraction routine produces the fraction equivalent of p/q, given
    integers p and q; it computes the integer f = floor(2**28 p/q + 1/2), when
    p and q are positive.

    In machine language this would simply be (2**28*p)div q"""
    return p/q
# >>>
def mp_take_fraction(q, f): # <<<
    # 20: mpmath.pdf
    """The dual of make fraction is take fraction, which multiplies a given
    integer q by a fraction f. When the operands are positive, it computes
    p = floor(q*f/2**28 + 1/2), a symmetric function of q and f."""
    return q*f
# >>>
def mp_pyth_add(a, b): # <<<
    # 44: mpmath.pdf
    """Pythagorean addition sqrt(a**2 + b**2) is implemented by an elegant
    iterative scheme due to Cleve Moler and Donald Morrison [IBM Journal of
    Research and Development 27 (1983), 577-581]. It modifies a and b in such a
    way that their Pythagorean sum remains invariant, while the smaller
    argument decreases."""
    return sqrt(a*a + b*b)
# >>>
def mp_curl_ratio(gamma, a_tension, b_tension): # <<<
    """The curl ratio subroutine has three arguments, which our previous
    notation encourages us to call gamma, 1/alpha, and 1/beta. It is a somewhat
    tedious program to calculate
      [(3-alpha)alpha^2 gamma + beta^3] / [alpha^3 gamma + (3-beta)beta^2],
    with the result reduced to 4 if it exceeds 4. (This reduction of curl is
    necessary only if the curl and tension are both large.) The values of alpha
    and beta will be at most 4/3.

    See mp.pdf (items 365, 366)."""
    alpha = 1.0/a_tension
    beta = 1.0/b_tension
    return min(4.0, ((3.0-alpha)*alpha**2*gamma + beta**3) /
                    (alpha**3*gamma + (3.0-beta)*beta**2))
# >>>
def mp_ab_vs_cd(a, b, c, d): # <<<
    """Tests rigorously if ab is greater than, equal to, or less than cd, given
    integers (a, b, c, d). In most cases a quick decision is reached. The
    result is +1, 0, or -1 in the three respective cases.
    See mpmath.pdf (item 33)."""
    if a*b == c*d:
        return 0
    if a*b > c*d:
        return 1
    return -1
# >>>
def mp_velocity(st, ct, sf, cf, t): # <<<
    """Metapost's standard velocity subroutine for cubic Bezier curves.
    See mpmath.pdf (item 30) and mp.pdf (item 339)."""
    return min(4.0, (2.0 + sqrt(2)*(st-sf/16.0)*(sf-st/16.0)*(ct-cf)) /
                    (1.5*t*(2+(sqrt(5)-1)*ct + (3-sqrt(5))*cf)))
# >>>
def reduce_angle(A): # <<<
    """A macro in mp.c"""
    if abs(A) > one_eighty_deg:
        if A > 0:
            A -= three_sixty_deg
        else:
            A += three_sixty_deg
    return A
# >>>

# vim:foldmethod=marker:foldmarker=<<<,>>>
