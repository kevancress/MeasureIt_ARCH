# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2002-2004 Jörg Lehmann <joerg@pyx-project.org>
# Copyright (C) 2003-2004 Michael Schindler <m-schindler@users.sourceforge.net>
# Copyright (C) 2002-2004 André Wobst <wobsta@pyx-project.org>
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

from fractions import Fraction

from pyx import text, utils
from pyx.graph.axis.tick import tick as Tick


class _texter:
    def labels(self, ticks):
        """fill the label attribute of ticks
        - ticks is a list of instances of tick
        - for each element of ticks the value of the attribute label is set to
          a string or MultiEngineText instance appropriate to the attributes
          num and denom of that tick instance
        - label attributes of the tick instances are just kept, whenever they
          are not equal to None
        - the method might modify the labelattrs attribute of the ticks; be sure
          to not modify it in-place!"""
        raise NotImplementedError


class decimal(_texter):
    "a texter creating decimal labels (e.g. '1.234' or even '0.\overline{3}')"

    def __init__(self, prefix="", infix="", suffix="", equalprecision=False,
                       decimalsep=".", thousandsep="", thousandthpartsep="",
                       plus="", minus="-", period=r"\overline{%s}",
                       labelattrs=[text.mathmode]):
        r"""initializes the instance
        - prefix, infix, and suffix (strings) are added at the begin,
          immediately after the minus, and at the end of the label,
          respectively
        - equalprecision forces the same number of digits after decimalsep,
          even when the tailing digits are zero
        - decimalsep, thousandsep, and thousandthpartsep (strings)
          are used as separators
        - plus or minus (string) is inserted for non-negative or negative numbers
        - period (string) is taken as a format string generating a period;
          it has to contain exactly one string insert operators "%s" for the
          period; usually it should be r"\overline{%s}"
        - labelattrs is a list of attributes to be added to the label attributes
          given in the painter"""
        self.prefix = prefix
        self.infix = infix
        self.suffix = suffix
        self.equalprecision = equalprecision
        self.decimalsep = decimalsep
        self.thousandsep = thousandsep
        self.thousandthpartsep = thousandthpartsep
        self.plus = plus
        self.minus = minus
        self.period = period
        self.labelattrs = labelattrs

    def labels(self, ticks):
        labeledticks = []
        maxdecprecision = 0
        for tick in ticks:
            if tick.label is None and tick.labellevel is not None:
                labeledticks.append(tick)
                m, n = tick.num, tick.denom
                if m < 0: m = -m
                if n < 0: n = -n
                quotient, remainder = divmod(m, n)
                quotient = str(quotient)
                if len(self.thousandsep):
                    l = len(quotient)
                    tick.label = ""
                    for i in range(l):
                        tick.label += quotient[i]
                        if not ((l-i-1) % 3) and l > i+1:
                            tick.label += self.thousandsep
                else:
                    tick.label = quotient
                if remainder:
                    tick.label += self.decimalsep
                oldremainders = []
                tick.temp_decprecision = 0
                while (remainder):
                    tick.temp_decprecision += 1
                    if remainder in oldremainders:
                        tick.temp_decprecision = None
                        periodstart = len(tick.label) - (len(oldremainders) - oldremainders.index(remainder))
                        tick.label = tick.label[:periodstart] + self.period % tick.label[periodstart:]
                        break
                    oldremainders += [remainder]
                    remainder *= 10
                    quotient, remainder = divmod(remainder, n)
                    if not ((tick.temp_decprecision - 1) % 3) and tick.temp_decprecision > 1:
                        tick.label += self.thousandthpartsep
                    tick.label += str(quotient)
                else:
                    if maxdecprecision < tick.temp_decprecision:
                        maxdecprecision = tick.temp_decprecision
        if self.equalprecision:
            for tick in labeledticks:
                if tick.temp_decprecision is not None:
                    if tick.temp_decprecision == 0 and maxdecprecision > 0:
                        tick.label += self.decimalsep
                    for i in range(tick.temp_decprecision, maxdecprecision):
                        if not ((i - 1) % 3) and i > 1:
                            tick.label += self.thousandthpartsep
                        tick.label += "0"
        for tick in labeledticks:
            if tick.num * tick.denom < 0:
                plusminus = self.minus
            else:
                plusminus = self.plus
            tick.label = "%s%s%s%s%s" % (self.prefix, plusminus, self.infix, tick.label, self.suffix)
            tick.labelattrs = tick.labelattrs + self.labelattrs

            # del tick.temp_decprecision  # we've inserted this temporary variable ... and do not care any longer about it



class skipmantissaunity:
    pass

skipmantissaunity.never = 0
skipmantissaunity.each = 1
skipmantissaunity.all = 2


class default(_texter):

    "a texter creating regular (e.g. '2') and exponential (e.g. '2\cdot10^5') labels"

    def __init__(self, multiplication_tex=r"\cdot{}", multiplication_unicode="·", base=Fraction(10),
                       skipmantissaunity=skipmantissaunity.all, minusunity="-",
                       minexponent=4, minnegexponent=None, uniformexponent=True,
                       mantissatexter=decimal(), basetexter=decimal(), exponenttexter=decimal(),
                       labelattrs=[text.mathmode]):
                       # , **kwargs): # future
        r"""initializes the instance
        - multiplication_tex and multiplication_unicode are the strings to
          indicate the multiplication between the mantissa and the base
          number for the TexEngine and the UnicodeEngine, respecitvely
        - base is the number of the base of the exponent
        - skipmantissaunity is either skipmantissaunity.never (never skip the
          unity mantissa), skipmantissaunity.each (skip the unity mantissa
          whenever it occurs for each label separately), or skipmantissaunity.all
          (skip the unity mantissa whenever if all labels happen to be
          mantissafixed with unity)
        - minusunity is used as the output of -unity for the mantissa
        - minexponent is the minimal positive exponent value to be printed by
          exponential notation
        - minnegexponent is the minimal negative exponent value to be printed by
          exponential notation, for None it is considered to be equal to minexponent
        - uniformexponent forces all numbers to be written in exponential notation
          when at least one label excets the limits for non-exponential
          notiation
        - mantissatexter, basetexter, and exponenttexter generate the texts
          for the mantissa, basetexter, and exponenttexter
        - labelattrs is a list of attributes to be added to the label attributes
          given in the painter"""
        self.multiplication_tex = multiplication_tex
        self.multiplication_unicode = multiplication_unicode
        self.base = base
        self.skipmantissaunity = skipmantissaunity
        self.minusunity = minusunity
        self.minexponent = minexponent
        self.minnegexponent = minnegexponent if minnegexponent is not None else minexponent
        self.uniformexponent = uniformexponent
        self.mantissatexter = mantissatexter
        self.basetexter = basetexter
        self.exponenttexter = exponenttexter
        self.labelattrs = labelattrs

        # future:
        # kwargs = utils.kwsplit(kwargs, ['mantissatexter', 'basetexter', 'exponenttexter'])
        # self.mantissatexter = mantissatexter(a=1, **kwargs['mantissatexter'])
        # self.basetexter = basetexter(**kwargs['basetexter'])
        # self.exponenttexter = exponenttexter(**kwargs['exponenttexter'])

    def labels(self, ticks):
        labeledticks = []
        for tick in ticks:
            if tick.label is None and tick.labellevel is not None:
                labeledticks.append(tick)

                tick.labelattrs = tick.labelattrs + self.labelattrs

                if tick.num:
                    # express tick = tick.temp_sign * tick.temp_mantissa * self.base ** tick.temp_exponent with 1 <= temp_mantissa < self.base 
                    # and decide whether a tick is to be written in exponential notation
                    tick.temp_sign = 1 if tick >= 0 else -1
                    tick.temp_mantissa = abs(Fraction(tick.num, tick.denom))
                    tick.temp_exponent = 0
                    while tick.temp_mantissa >= self.base:
                        tick.temp_exponent += 1
                        tick.temp_mantissa /= self.base
                    while tick.temp_mantissa < 1:
                        tick.temp_exponent -= 1
                        tick.temp_mantissa *= self.base
                    tick.temp_wantexponent = not (-self.minnegexponent < tick.temp_exponent < self.minexponent)
                else:
                    tick.temp_mantissa = tick.temp_exponent = 0
                    tick.temp_sign = 1
                    tick.temp_wantexponent = not (-self.minnegexponent < 0 < self.minexponent)

        # make decision on exponential notation uniform if requested
        if self.uniformexponent and any(tick.temp_wantexponent for tick in labeledticks):
            for tick in labeledticks:
                if tick.num:
                    tick.temp_wantexponent = True

        # mark mantissa == 1 to be not labeled
        if self.skipmantissaunity == skipmantissaunity.each:
            for tick in labeledticks:
                if tick.temp_wantexponent and tick.temp_mantissa == 1:
                    tick.temp_mantissa = None
        elif self.skipmantissaunity == skipmantissaunity.all and all(tick.temp_mantissa == 1 for tick in labeledticks if tick.temp_wantexponent):
            for tick in labeledticks:
                if tick.temp_wantexponent:
                    tick.temp_mantissa = None

        # construct labels
        basetick = Tick(self.base, labellevel=0)
        self.basetexter.labels([basetick])
        for tick in labeledticks:
            if tick.temp_wantexponent:
                if tick.temp_mantissa is not None:
                    tick.temp_mantissatick = Tick(tick.temp_sign * tick.temp_mantissa, labellevel=0)
                tick.temp_exponenttick = Tick(tick.temp_exponent, labellevel=0)
            else:
                tick.temp_mantissatick = tick

        self.mantissatexter.labels([tick.temp_mantissatick for tick in labeledticks if tick.temp_mantissa is not None])
        self.exponenttexter.labels([tick.temp_exponenttick for tick in labeledticks if tick.temp_wantexponent])
        for tick in labeledticks:
            if tick.temp_wantexponent:
                if tick.temp_mantissa is not None:
                    mantissalabel_tex = tick.temp_mantissatick.label + self.multiplication_tex
                    mantissalabel_unicode = tick.temp_mantissatick.label + self.multiplication_unicode
                else:
                    mantissalabel_tex = self.minusunity if tick.temp_sign == -1 else ""
                    mantissalabel_unicode = self.minusunity if tick.temp_sign == -1 else ""
                tick.label = text.MultiEngineText("%s%s^{%s}" % (mantissalabel_tex, basetick.label, tick.temp_exponenttick.label), [mantissalabel_unicode + basetick.label, text.Text(tick.temp_exponenttick.label, scale=0.8, shift=0.5)])


class rational(_texter):
    "a texter creating rational labels (e.g. 'a/b' or even 'a \over b')"
    # we use divmod here to be more explicit

    def __init__(self, prefix="", infix="", suffix="",
                       numprefix="", numinfix="", numsuffix="",
                       denomprefix="", denominfix="", denomsuffix="",
                       plus="", minus="-", minuspos=0, over=r"{{%s}\over{%s}}",
                       equaldenom=False, skip1=True, skipnum0=True, skipnum1=True, skipdenom1=True,
                       labelattrs=[text.mathmode]):
        r"""initializes the instance
        - prefix, infix, and suffix (strings) are added at the begin,
          immediately after the minus, and at the end of the label,
          respectively
        - prefixnum, infixnum, and suffixnum (strings) are added
          to the labels numerator correspondingly
        - prefixdenom, infixdenom, and suffixdenom (strings) are added
          to the labels denominator correspondingly
        - plus or minus (string) is inserted for non-negative or negative numbers
        - minuspos is an integer, which determines the position, where the
          plus or minus sign has to be placed; the following values are allowed:
            1 - writes the plus or minus in front of the numerator
            0 - writes the plus or minus in front of the hole fraction
           -1 - writes the plus or minus in front of the denominator
        - over (string) is taken as a format string generating the
          fraction bar; it has to contain exactly two string insert
          operators "%s" -- the first for the numerator and the second
          for the denominator; by far the most common examples are
          r"{{%s}\over{%s}}" and "{{%s}/{%s}}"
        - usually the numerator and denominator are canceled; however,
          when equaldenom is set, the least common multiple of all
          denominators is used
        - skip1 (boolean) just prints the prefix, the plus or minus,
          the infix and the suffix, when the value is plus or minus one
          and at least one of prefix, infix and the suffix is present
        - skipnum0 (boolean) just prints a zero instead of
          the hole fraction, when the numerator is zero;
          no prefixes, infixes, and suffixes are taken into account
        - skipnum1 (boolean) just prints the numprefix, the plus or minus,
          the numinfix and the numsuffix, when the num value is plus or minus one
          and at least one of numprefix, numinfix and the numsuffix is present
        - skipdenom1 (boolean) just prints the numerator instead of
          the hole fraction, when the denominator is one and none of the parameters
          denomprefix, denominfix and denomsuffix are set and minuspos is not -1 or the
          fraction is positive
        - labelattrs is a list of attributes for a textengines text method;
          None is considered as an empty list; labelattrs might be changed
          in the painter as well"""
        self.prefix = prefix
        self.infix = infix
        self.suffix = suffix
        self.numprefix = numprefix
        self.numinfix = numinfix
        self.numsuffix = numsuffix
        self.denomprefix = denomprefix
        self.denominfix = denominfix
        self.denomsuffix = denomsuffix
        self.plus = plus
        self.minus = minus
        self.minuspos = minuspos
        self.over = over
        self.equaldenom = equaldenom
        self.skip1 = skip1
        self.skipnum0 = skipnum0
        self.skipnum1 = skipnum1
        self.skipdenom1 = skipdenom1
        self.labelattrs = labelattrs

    def gcd(self, *n):
        """returns the greates common divisor of all elements in n
        - the elements of n must be non-negative integers
        - return None if the number of elements is zero
        - the greates common divisor is not affected when some
          of the elements are zero, but it becomes zero when
          all elements are zero"""
        if len(n) == 2:
            i, j = n
            if i < j:
                i, j = j, i
            while j > 0:
                i, (dummy, j) = j, divmod(i, j)
            return i
        if len(n):
            res = n[0]
            for i in n[1:]:
                res = self.gcd(res, i)
            return res

    def lcm(self, *n):
        """returns the least common multiple of all elements in n
        - the elements of n must be non-negative integers
        - return None if the number of elements is zero
        - the least common multiple is zero when some of the
          elements are zero"""
        if len(n):
            res = n[0]
            for i in n[1:]:
                res = divmod(res * i, self.gcd(res, i))[0]
            return res

    def labels(self, ticks):
        labeledticks = []
        for tick in ticks:
            if tick.label is None and tick.labellevel is not None:
                labeledticks.append(tick)
                tick.temp_rationalnum = tick.num
                tick.temp_rationaldenom = tick.denom
                tick.temp_rationalminus = 1
                if tick.temp_rationalnum < 0:
                    tick.temp_rationalminus = -tick.temp_rationalminus
                    tick.temp_rationalnum = -tick.temp_rationalnum
                if tick.temp_rationaldenom < 0:
                    tick.temp_rationalminus = -tick.temp_rationalminus
                    tick.temp_rationaldenom = -tick.temp_rationaldenom
                gcd = self.gcd(tick.temp_rationalnum, tick.temp_rationaldenom)
                (tick.temp_rationalnum, dummy1), (tick.temp_rationaldenom, dummy2) = divmod(tick.temp_rationalnum, gcd), divmod(tick.temp_rationaldenom, gcd)
        if self.equaldenom:
            equaldenom = self.lcm(*[tick.temp_rationaldenom for tick in ticks if tick.label is None])
            if equaldenom is not None:
                for tick in labeledticks:
                    factor, dummy = divmod(equaldenom, tick.temp_rationaldenom)
                    tick.temp_rationalnum, tick.temp_rationaldenom = factor * tick.temp_rationalnum, factor * tick.temp_rationaldenom
        for tick in labeledticks:
            rationalminus = rationalnumminus = rationaldenomminus = ""
            if tick.temp_rationalminus == -1:
                plusminus = self.minus
            else:
                plusminus = self.plus
            if self.minuspos == 0:
                rationalminus = plusminus
            elif self.minuspos == 1:
                rationalnumminus = plusminus
            elif self.minuspos == -1:
                rationaldenomminus = plusminus
            else:
                raise RuntimeError("invalid minuspos")
            if self.skipnum0 and tick.temp_rationalnum == 0:
                tick.label = "0"
            elif (self.skip1 and self.skipdenom1 and tick.temp_rationalnum == 1 and tick.temp_rationaldenom == 1 and
                  (len(self.prefix) or len(self.infix) or len(self.suffix)) and
                  not len(rationalnumminus) and not len(self.numprefix) and not len(self.numinfix) and not len(self.numsuffix) and
                  not len(rationaldenomminus) and not len(self.denomprefix) and not len(self.denominfix) and not len(self.denomsuffix)):
                tick.label = "%s%s%s%s" % (self.prefix, rationalminus, self.infix, self.suffix)
            else:
                if self.skipnum1 and tick.temp_rationalnum == 1 and (len(self.numprefix) or len(self.numinfix) or len(self.numsuffix)):
                    tick.temp_rationalnum = "%s%s%s%s" % (self.numprefix, rationalnumminus, self.numinfix, self.numsuffix)
                else:
                    tick.temp_rationalnum = "%s%s%s%i%s" % (self.numprefix, rationalnumminus, self.numinfix, tick.temp_rationalnum, self.numsuffix)
                if self.skipdenom1 and tick.temp_rationaldenom == 1 and not len(rationaldenomminus) and not len(self.denomprefix) and not len(self.denominfix) and not len(self.denomsuffix):
                    tick.label = "%s%s%s%s%s" % (self.prefix, rationalminus, self.infix, tick.temp_rationalnum, self.suffix)
                else:
                    tick.temp_rationaldenom = "%s%s%s%i%s" % (self.denomprefix, rationaldenomminus, self.denominfix, tick.temp_rationaldenom, self.denomsuffix)
                    tick.label = text.MultiEngineText("%s%s%s%s%s" % (self.prefix, rationalminus, self.infix, self.over % (tick.temp_rationalnum, tick.temp_rationaldenom), self.suffix),
                                                      ["%s%s%s" % (self.prefix, rationalminus, self.infix)] + [text.StackedText([text.Text(tick.temp_rationalnum, shift=0.3), text.Text(tick.temp_rationaldenom, shift=-0.9)], frac=True, align=0.5)] + [self.suffix])
            tick.labelattrs = tick.labelattrs + self.labelattrs

            # del tick.temp_rationalnum    # we've inserted those temporary variables ... and do not care any longer about them
            # del tick.temp_rationaldenom
            # del tick.temp_rationalminus

