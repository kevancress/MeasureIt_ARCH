# Copyright (C) 2002-2013 Jörg Lehmann <joerg@pyx-project.org>
# Copyright (C) 2003-2011 Michael Schindler <m-schindler@users.sourceforge.net>
# Copyright (C) 2002-2013 André Wobst <wobsta@pyx-project.org>
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


import atexit, errno, functools, glob, inspect, io, itertools, logging, os
import queue, re, shutil, sys, tempfile, textwrap, threading

from pyx import config, unit, box, baseclasses, trafo, version, attr, style, path, canvas
from pyx import bbox as bboxmodule
from pyx.dvi import dvifile

logger = logging.getLogger("pyx")


def indent_text(text):
    "Prepends two spaces to each line in text."
    return "".join("  " + line for line in text.splitlines(True))


def remove_string(p, s):
    """Removes a string from a string.

    The function removes the first occurrence of a string in another string.

    :param str p: string to be removed
    :param str s: string to be searched
    :returns: tuple of the result string and a success boolean (``True`` when
        the string was removed)
    :rtype: tuple of str and bool

    .. testsetup::

        import re
        from pyx.text import *

    Example:
        >>> remove_string("XXX", "abcXXXdefXXXghi")
        ('abcdefXXXghi', True)

    """
    r = s.replace(p, '', 1)
    return r, r != s


def remove_pattern(p, s, ignore_nl=True):
    r"""Removes a pattern from a string.

    The function removes the first occurence of the pattern from a string. It
    returns a tuple of the resulting string and the matching object (or
    ``None``, if the pattern did not match).

    :param re.regex p: pattern to be removed
    :param str s: string to be searched
    :param bool ignore_nl: When ``True``, newlines in the string are ignored
        during the pattern search. The returned string will still contain all
        newline characters outside of the matching part of the string, whereas
        the returned matching object will not contain the newline characters
        inside of the matching part of the string.
    :returns: the result string and the match object or ``None`` if
        search failed
    :rtype: tuple of str and (re.match or None)

    Example:
        >>> r, m = remove_pattern(re.compile("XXX"), 'ab\ncXX\nXdefXX\nX')
        >>> r
        'ab\ncdefXX\nX'
        >>> m.string[m.start():m.end()]
        'XXX'

    """
    if ignore_nl:
        r = s.replace('\n', '')
        has_nl = r != s
    else:
        r = s
        has_nl = False
    m = p.search(r)
    if m:
        s_start = r_start = m.start()
        s_end = r_end = m.end()
        if has_nl:
            j = 0
            for c in s:
                if c == '\n':
                    if j < r_end:
                        s_end += 1
                        if j <= r_start:
                            s_start += 1
                else:
                    j += 1
        return s[:s_start] + s[s_end:], m
    return s, None


def index_all(c, s):
    """Return list of positions of a character in a string.

    Example:
        >>> index_all("X", "abXcdXef")
        [2, 5]

    """
    assert len(c) == 1
    return [i for i, x in enumerate(s) if x == c]


def pairwise(i):
    a, b = itertools.tee(i)
    next(b, None)
    return zip(a, b)


def remove_nested_brackets(s, openbracket="(", closebracket=")", quote='"'):
    """Remove nested brackets

    Return a modified string with all nested brackets 1 removed, i.e. only
    keep the first bracket nesting level. In case an opening bracket is
    immediately followed by a quote, the quoted string is left untouched,
    even if it contains brackets. The use-case for that are files in the
    folder "Program Files (x86)".

    If the bracket nesting level is broken (unbalanced), the unmodified
    string is returned.

    Example:
        >>> remove_nested_brackets('aaa("bb()bb" cc(dd(ee))ff)ggg'*2)
        'aaa("bb()bb" ccff)gggaaa("bb()bb" ccff)ggg'

    """
    openpos = index_all(openbracket, s)
    closepos = index_all(closebracket, s)
    if quote is not None:
        quotepos = index_all(quote, s)
        for openquote, closequote in pairwise(quotepos):
             if openquote-1 in openpos:
                 # ignore brackets in quoted string
                 openpos = [pos for pos in openpos
                            if not (openquote < pos < closequote)]
                 closepos = [pos for pos in closepos
                             if not (openquote < pos < closequote)]
    if len(openpos) != len(closepos):
        # unbalanced brackets
        return s

    # keep the original string in case we need to return due to broken nesting levels
    r = s

    level = 0
    # Iterate over the bracket positions from the end.
    # We go reversely to be able to immediately remove nested bracket levels
    # without influencing bracket positions yet to come in the loop.
    for pos, leveldelta in sorted(itertools.chain(zip(openpos, itertools.repeat(-1)),
                                                  zip(closepos, itertools.repeat(1))),
                                  reverse=True):
        # the current bracket nesting level
        level += leveldelta
        if level < 0:
            # unbalanced brackets
            return s
        if leveldelta == 1 and level == 2:
            # a closing bracket to cut after
            endpos = pos+1
        if leveldelta == -1 and level == 1:
            # an opening bracket to cut at -> remove
            r = r[:pos] + r[endpos:]
    return r


class TexResultError(ValueError):
    "Error raised by :class:`texmessage` parsers."
    pass


class texmessage:
    """Collection of TeX output parsers.

    This class is not meant to be instanciated. Instead, it serves as a
    namespace for TeX output parsers, which are functions receiving a TeX
    output and returning parsed output.

    In addition, this class also contains some generator functions (namely
    :attr:`texmessage.no_file` and :attr:`texmessage.pattern`), which return a
    function according to the given parameters. They are used to generate some
    of the parsers in this class and can be used to create others as well.
    """

    start_pattern = re.compile(r"This is [-0-9a-zA-Z\s_]*TeX")

    @staticmethod
    def start(msg):
        r"""Validate TeX/LaTeX startup message including scrollmode test.

        Example:
            >>> texmessage.start(r'''
            ... This is e-TeX (version)
            ... *! Undefined control sequence.
            ... <*> \raiseerror
            ...                %
            ... ''')
            ''

        """
        # check for "This is e-TeX" etc.
        if not texmessage.start_pattern.search(msg):
            raise TexResultError("TeX startup failed")

        # check for \raiseerror -- just to be sure that communication works
        new = msg.split("*! Undefined control sequence.\n<*> \\raiseerror\n               %\n", 1)[-1]
        if msg == new:
            raise TexResultError("TeX scrollmode check failed")
        return new

    @staticmethod
    def no_file(fileending, qualname=None):
        "Generator function to ignore the missing file message for fileending."
        def check(msg):
            "Ignore the missing {} file message."
            return msg.replace("No file texput.%s." % fileending, "").replace("No file %s%stexput.%s." % (os.curdir, os.sep, fileending), "")
        check.__doc__ = check.__doc__.format(fileending)
        if qualname is not None:
            check.__qualname__ = qualname
        return check

    no_aux = staticmethod(no_file.__func__("aux", "texmessage.no_aux"))
    no_nav = staticmethod(no_file.__func__("nav", "texmessage.no_nav"))

    aux_pattern = re.compile(r'\(([^()]+\.aux|"[^"]+\.aux")\)')
    log_pattern = re.compile(r"Transcript written on .*texput\.log\.", re.DOTALL)

    @staticmethod
    def end(msg):
        "Validate TeX shutdown message."
        msg = re.sub(texmessage.aux_pattern, "", msg).replace("(see the transcript file for additional information)", "")

        # check for "Transcript written on ...log."
        msg, m = remove_pattern(texmessage.log_pattern, msg)
        if not m:
            raise TexResultError("TeX logfile message expected")
        return msg

    quoted_file_pattern = re.compile(r'\("(?P<filename>[^"]+)".*?\)')
    file_pattern = re.compile(r'\((?P<filename>[^"][^ )]*).*?\)', re.DOTALL)

    @staticmethod
    def load(msg):
        """Ignore file loading messages.

        Removes text starting with a round bracket followed by a filename
        ignoring all further text until the corresponding closing bracket.
        Quotes and/or line breaks in the filename are handled as needed for TeX
        output.

        Without quoting the filename, the necessary removal of line breaks is
        not well defined and the different possibilities are tested to check
        whether one solution is ok. The last of the examples below checks this
        behavior.

        Examples:
            >>> texmessage.load(r'''other (text.py) things''')
            'other  things'
            >>> texmessage.load(r'''other ("text.py") things''')
            'other  things'
            >>> texmessage.load(r'''other ("tex
            ... t.py" further (ignored)
            ... text) things''')
            'other  things'
            >>> texmessage.load(r'''other (t
            ... ext
            ... .py
            ... fur
            ... ther (ignored) text) things''')
            'other  things'

        """
        r = remove_nested_brackets(msg)
        r, m = remove_pattern(texmessage.quoted_file_pattern, r)
        while m:
            if not os.path.isfile(config.get("text", "chroot", "") + m.group("filename")):
                return msg
            r, m = remove_pattern(texmessage.quoted_file_pattern, r)
        r, m = remove_pattern(texmessage.file_pattern, r, ignore_nl=False)
        while m:
            for filename in itertools.accumulate(m.group("filename").split("\n")):
                if os.path.isfile(config.get("text", "chroot", "") + filename):
                    break
            else:
                return msg
            r, m = remove_pattern(texmessage.file_pattern, r, ignore_nl=False)
        return r

    quoted_def_pattern = re.compile(r'\("(?P<filename>[^"]+\.(fd|def))"\)')
    def_pattern = re.compile(r'\((?P<filename>[^"][^ )]*\.(fd|def))\)')

    @staticmethod
    def load_def(msg):
        "Ignore font definition (``*.fd`` and ``*.def``) loading messages."
        r = msg
        for p in [texmessage.quoted_def_pattern, texmessage.def_pattern]:
            r, m = remove_pattern(p, r)
            while m:
                if not os.path.isfile(config.get("text", "chroot", "") + m.group("filename")):
                    return msg
                r, m = remove_pattern(p, r)
        return r

    quoted_graphics_pattern = re.compile(r'<"(?P<filename>[^"]+\.eps)">')
    graphics_pattern = re.compile(r'<(?P<filename>[^"][^>]*\.eps)>')

    @staticmethod
    def load_graphics(msg):
        "Ignore graphics file (``*.eps``) loading messages."
        r = msg
        for p in [texmessage.quoted_graphics_pattern, texmessage.graphics_pattern]:
            r, m = remove_pattern(p, r)
            while m:
                if not os.path.isfile(config.get("text", "chroot", "") + m.group("filename")):
                    return msg
                r, m = remove_pattern(texmessage.quoted_file_pattern, r)
        return r

    @staticmethod
    def ignore(msg):
        """Ignore all messages.

        Should be used as a last resort only. You should write a proper TeX
        output parser function for the output you observe.

        """
        return ""

    @staticmethod
    def warn(msg):
        """Warn about all messages.

        Similar to :attr:`ignore`, but writing a warning to the logger about
        the TeX output. This is considered to be better when you need to get it
        working quickly as you will still be prompted about the unresolved
        output, while the processing continues.

        """
        if msg:
             logger.warning("ignoring TeX warnings:\n%s" % indent_text(msg.rstrip()))
        return ""

    @staticmethod
    def pattern(p, warning, qualname=None):
        "Warn by regular expression pattern matching."
        def check(msg):
            "Warn about {}."
            msg, m = remove_pattern(p, msg, ignore_nl=False)
            while m:
                logger.warning("ignoring %s:\n%s" % (warning, m.string[m.start(): m.end()].rstrip()))
                msg, m = remove_pattern(p, msg, ignore_nl=False)
            return msg
        check.__doc__ = check.__doc__.format(warning)
        if qualname is not None:
            check.__qualname__ = qualname
        return check

    box_warning = staticmethod(pattern.__func__(re.compile(r"^(Overfull|Underfull) \\[hv]box.*$(\n^..*$)*\n^$\n", re.MULTILINE),
                               "overfull/underfull box", qualname="texmessage.box_warning"))
    font_warning = staticmethod(pattern.__func__(re.compile(r"^LaTeX Font Warning: .*$(\n^\(Font\).*$)*", re.MULTILINE),
                                "font substitutions of NFSS", qualname="texmessage.font_warning"))
    package_warning = staticmethod(pattern.__func__(re.compile(r"^package\s+(?P<packagename>\S+)\s+warning\s*:[^\n]+(?:\n\(?(?P=packagename)\)?[^\n]*)*", re.MULTILINE | re.IGNORECASE),
                                   "generic package messages", qualname="texmessage.package_warning"))
    rerun_warning = staticmethod(pattern.__func__(re.compile(r"^(LaTeX Warning: Label\(s\) may have changed\. Rerun to get cross-references right\s*\.)$", re.MULTILINE),
                                 "rerun required message", qualname="texmessage.rerun_warning"))
    nobbl_warning = staticmethod(pattern.__func__(re.compile(r"^[\s\*]*(No file .*\.bbl.)\s*", re.MULTILINE),
                                 "no-bbl message", qualname="texmessage.nobbl_warning"))


###############################################################################
# textattrs
###############################################################################

_textattrspreamble = ""

class textattr:
    "a textattr defines a apply method, which modifies a (La)TeX expression"

class _localattr: pass

_textattrspreamble += r"""\gdef\PyXFlushHAlign{0}%
\def\PyXragged{%
\leftskip=0pt plus \PyXFlushHAlign fil%
\rightskip=0pt plus 1fil%
\advance\rightskip0pt plus -\PyXFlushHAlign fil%
\parfillskip=0pt%
\pretolerance=9999%
\tolerance=9999%
\parindent=0pt%
\hyphenpenalty=9999%
\exhyphenpenalty=9999}%
"""

class boxhalign(attr.exclusiveattr, textattr, _localattr):

    def __init__(self, aboxhalign):
        self.boxhalign = aboxhalign
        attr.exclusiveattr.__init__(self, boxhalign)

    def apply(self, expr):
        return r"\gdef\PyXBoxHAlign{%.5f}%s" % (self.boxhalign, expr)

boxhalign.left = boxhalign(0)
boxhalign.center = boxhalign(0.5)
boxhalign.right = boxhalign(1)
# boxhalign.clear = attr.clearclass(boxhalign) # we can't defined a clearclass for boxhalign since it can't clear a halign's boxhalign


class flushhalign(attr.exclusiveattr, textattr, _localattr):

    def __init__(self, aflushhalign):
        self.flushhalign = aflushhalign
        attr.exclusiveattr.__init__(self, flushhalign)

    def apply(self, expr):
        return r"\gdef\PyXFlushHAlign{%.5f}\PyXragged{}%s" % (self.flushhalign, expr)

flushhalign.left = flushhalign(0)
flushhalign.center = flushhalign(0.5)
flushhalign.right = flushhalign(1)
# flushhalign.clear = attr.clearclass(flushhalign) # we can't defined a clearclass for flushhalign since it couldn't clear a halign's flushhalign


class halign(boxhalign, flushhalign, _localattr):

    def __init__(self, aboxhalign, aflushhalign):
        self.boxhalign = aboxhalign
        self.flushhalign = aflushhalign
        attr.exclusiveattr.__init__(self, halign)

    def apply(self, expr):
        return r"\gdef\PyXBoxHAlign{%.5f}\gdef\PyXFlushHAlign{%.5f}\PyXragged{}%s" % (self.boxhalign, self.flushhalign, expr)

    def apply_trafo(self, textbox):
        return textbox.transform(trafo.translate_pt(-self.boxhalign*textbox.bbox().width_pt(), 0), keep_anchor=True)

halign.left = halign(0, 0)
halign.center = halign(0.5, 0.5)
halign.right = halign(1, 1)
halign.clear = attr.clearclass(halign)
halign.boxleft = boxhalign.left
halign.boxcenter = boxhalign.center
halign.boxright = boxhalign.right
halign.flushleft = halign.raggedright = flushhalign.left
halign.flushcenter = halign.raggedcenter = flushhalign.center
halign.flushright = halign.raggedleft = flushhalign.right


class _mathmode(attr.exclusiveattr, textattr, _localattr):
    "math mode"

    def __init__(self):
        attr.exclusiveattr.__init__(self, _mathmode)

    def apply(self, expr):
        return r"$\displaystyle{%s}$" % expr

    def apply_trafo(self, textbox):
        pass

mathmode = _mathmode()
clearmathmode = attr.clearclass(_mathmode)


class _phantom(attr.attr, textattr, _localattr):
    "phantom text"

    def apply(self, expr):
        return r"\phantom{%s}" % expr

phantom = _phantom()
clearphantom = attr.clearclass(_phantom)


_textattrspreamble += "\\newbox\\PyXBoxVBox%\n\\newdimen\\PyXDimenVBox%\n"

class parbox_pt(attr.sortbeforeexclusiveattr, textattr):

    top = 1
    middle = 2
    bottom = 3

    def __init__(self, width, baseline=top):
        self.width = width * 72.27 / (unit.scale["x"] * 72)
        self.baseline = baseline
        attr.sortbeforeexclusiveattr.__init__(self, parbox_pt, [_localattr])

    def apply(self, expr):
        if self.baseline == self.top:
            return r"\linewidth=%.5ftruept\vtop{\hsize=\linewidth\textwidth=\linewidth{}%s}" % (self.width, expr)
        elif self.baseline == self.middle:
            return r"\linewidth=%.5ftruept\setbox\PyXBoxVBox=\hbox{{\vtop{\hsize=\linewidth\textwidth=\linewidth{}%s}}}\PyXDimenVBox=0.5\dp\PyXBoxVBox\setbox\PyXBoxVBox=\hbox{{\vbox{\hsize=\linewidth\textwidth=\linewidth{}%s}}}\advance\PyXDimenVBox by -0.5\dp\PyXBoxVBox\lower\PyXDimenVBox\box\PyXBoxVBox" % (self.width, expr, expr)
        elif self.baseline == self.bottom:
            return r"\linewidth=%.5ftruept\vbox{\hsize=\linewidth\textwidth=\linewidth{}%s}" % (self.width, expr)
        else:
            ValueError("invalid baseline argument")

parbox_pt.clear = attr.clearclass(parbox_pt)

class parbox(parbox_pt):

    def __init__(self, width, **kwargs):
        parbox_pt.__init__(self, unit.topt(width), **kwargs)

parbox.clear = parbox_pt.clear


_textattrspreamble += "\\newbox\\PyXBoxVAlign%\n\\newdimen\\PyXDimenVAlign%\n"

class valign(attr.sortbeforeexclusiveattr, textattr):

    def __init__(self, avalign):
        self.valign = avalign
        attr.sortbeforeexclusiveattr.__init__(self, valign, [parbox_pt, _localattr])

    def apply(self, expr):
        return r"\setbox\PyXBoxVAlign=\hbox{{%s}}\PyXDimenVAlign=%.5f\ht\PyXBoxVAlign\advance\PyXDimenVAlign by -%.5f\dp\PyXBoxVAlign\lower\PyXDimenVAlign\box\PyXBoxVAlign" % (expr, 1-self.valign, self.valign)

valign.top = valign(0)
valign.middle = valign(0.5)
valign.bottom = valign(1)
valign.clear = valign.baseline = attr.clearclass(valign)


_textattrspreamble += "\\newdimen\\PyXDimenVShift%\n"

class _vshift(attr.sortbeforeattr, textattr):

    def __init__(self):
        attr.sortbeforeattr.__init__(self, [valign, parbox_pt, _localattr])

    def apply(self, expr):
        return r"%s\setbox0\hbox{{%s}}\lower\PyXDimenVShift\box0" % (self.setheightexpr(), expr)

class vshift(_vshift):
    "vertical down shift by a fraction of a character height"

    def __init__(self, lowerratio, heightstr="0"):
        _vshift.__init__(self)
        self.lowerratio = lowerratio
        self.heightstr = heightstr

    def setheightexpr(self):
        return r"\setbox0\hbox{{%s}}\PyXDimenVShift=%.5f\ht0" % (self.heightstr, self.lowerratio)

class _vshiftmathaxis(_vshift):
    "vertical down shift by the height of the math axis"

    def setheightexpr(self):
        return r"\setbox0\hbox{$\vcenter{\vrule width0pt}$}\PyXDimenVShift=\ht0"

    def apply_trafo(self, textbox):
        return textbox.transform(trafo.translate_pt(0, -textbox.mathaxis_pt*unit.scale["x"]), keep_anchor=True)


vshift.bottomzero = vshift(0)
vshift.middlezero = vshift(0.5)
vshift.topzero = vshift(1)
vshift.mathaxis = _vshiftmathaxis()
vshift.clear = attr.clearclass(_vshift)


defaultsizelist = ["normalsize", "large", "Large", "LARGE", "huge", "Huge",
None, "tiny", "scriptsize", "footnotesize", "small"]

class size(attr.sortbeforeattr, textattr):
    "font size"

    def __init__(self, sizeindex=None, sizename=None, sizelist=defaultsizelist):
        if (sizeindex is None and sizename is None) or (sizeindex is not None and sizename is not None):
            raise ValueError("either specify sizeindex or sizename")
        attr.sortbeforeattr.__init__(self, [_mathmode, _vshift])
        if sizeindex is not None:
            if sizeindex >= 0 and sizeindex < sizelist.index(None):
                self.size = sizelist[sizeindex]
            elif sizeindex < 0 and sizeindex + len(sizelist) > sizelist.index(None):
                self.size = sizelist[sizeindex]
            else:
                raise IndexError("index out of sizelist range")
        else:
            self.size = sizename

    def apply(self, expr):
        return r"\%s{}%s" % (self.size, expr)

size.tiny = size(-4)
size.scriptsize = size.script = size(-3)
size.footnotesize = size.footnote = size(-2)
size.small = size(-1)
size.normalsize = size.normal = size(0)
size.large = size(1)
size.Large = size(2)
size.LARGE = size(3)
size.huge = size(4)
size.Huge = size(5)
size.clear = attr.clearclass(size)


###############################################################################
# textengines
###############################################################################


class MonitorOutput(threading.Thread):

    def __init__(self, name, output):
        """Deadlock-safe output stream reader and monitor.

        An instance of this class creates a thread to continously read lines
        from a stream. By that a deadlock due to a full pipe is prevented. In
        addition, the stream content can be monitored for containing a certain
        string (see :meth:`expect` and :meth:`wait`) and return all the
        collected output (see :meth:`read`).

        :param string name: name to be used while logging in :meth:`wait` and
            :meth:`done`
        :param file output: output stream

        """
        self.output = output
        self._expect = queue.Queue(1)
        self._received = threading.Event()
        self._output = queue.Queue()
        threading.Thread.__init__(self, name=name)
        self.daemon = True
        self.start()

    def expect(self, s):
        """Expect a string on a **single** line in the output.

        This method must be called **before** the output occurs, i.e. before
        the input is written to the TeX/LaTeX process.

        :param s: expected string or ``None`` if output is expected to become
            empty
        :type s: str or None

        """
        self._expect.put_nowait(s)

    def read(self):
        """Read all output collected since its previous call.

        The output reading should be synchronized by the :meth:`expect`
        and :meth:`wait` methods.

        :returns: collected output from the stream
        :rtype: str

        """
        l = []
        try:
            while True:
                l.append(self._output.get_nowait())
        except queue.Empty:
            pass
        return "".join(l).replace("\r\n", "\n").replace("\r", "\n")

    def _wait(self, waiter, checker):
        """Helper method to implement :meth:`wait` and :meth:`done`.

        Waits for an event using the *waiter* and *checker* functions while
        providing user feedback to the ``pyx``-logger using the warning level
        according to the ``wait`` and ``showwait`` from the ``text`` section of
        the pyx :mod:`config`.

        :param function waiter: callback to wait for (the function gets called
            with a timeout parameter)
        :param function checker: callback returing ``True`` if
            waiting was successful
        :returns: ``True`` when wait was successful
        :rtype: bool

        """
        wait = config.getint("text", "wait", 60)
        showwait = config.getint("text", "showwait", 5)
        if showwait:
            waited = 0
            hasevent = False
            while waited < wait and not hasevent:
                if wait - waited > showwait:
                    waiter(showwait)
                    waited += showwait
                else:
                    waiter(wait - waited)
                    waited += wait - waited
                hasevent = checker()
                if not hasevent:
                    if waited < wait:
                        logger.warning("Still waiting for {} "
                                       "after {} (of {}) seconds..."
                                       .format(self.name, waited, wait))
                    else:
                        logger.warning("The timeout of {} seconds expired "
                                       "and {} did not respond."
                                       .format(waited, self.name))
            return hasevent
        else:
            waiter(wait)
            return checker()

    def wait(self):
        """Wait for the expected output to happen.

        Waits either until a line containing the string set by the previous
        :meth:`expect` call is found, or a timeout occurs.

        :returns: ``True`` when the expected string was found
        :rtype: bool

        """
        r = self._wait(self._received.wait, self._received.isSet)
        if r:
            self._received.clear()
        return r

    def done(self):
        """Waits until the output becomes empty.

        Waits either until the output becomes empty, or a timeout occurs.
        The generated output can still be catched by :meth:`read` after
        :meth:`done` was successful.

        In the proper workflow :meth:`expect` should be called with ``None``
        before the output completes, as otherwise a ``ValueError`` is raised
        in the :meth:`run`.

        :returns: ``True`` when the output has become empty
        :rtype: bool

        """
        return self._wait(self.join, lambda self=self: not self.is_alive())

    def _readline(self):
        """Read a line from the output.

        To be used **inside** the thread routine only.

        :returns: one line of the output as a string
        :rtype: str

        """
        while True:
            try:
                return self.output.readline()
            except IOError as e:
                if e.errno != errno.EINTR:
                     raise

    def run(self):
        """Thread routine.

        **Not** to be called from outside.

        :raises ValueError: output becomes empty while some string is expected

        """
        expect = None
        while True:
            line = self._readline()
            if expect is None:
                try:
                    expect = self._expect.get_nowait()
                except queue.Empty:
                    pass
            if not line:
                break
            self._output.put(line)
            if expect is not None:
                found = line.find(expect)
                if found != -1:
                    self._received.set()
                    expect = None
        self.output.close()
        if expect is not None:
            raise ValueError("{} finished unexpectedly".format(self.name))


class textbox_pt(box.rect, baseclasses.canvasitem): pass


class textextbox_pt(textbox_pt):

    def __init__(self, x_pt, y_pt, left_pt, right_pt, height_pt, depth_pt, do_finish, fontmap, singlecharmode, fillstyles):
        """Text output.

        An instance of this class contains the text output generated by PyX. It
        is a :class:`baseclasses.canvasitem` and thus can be inserted into a
        canvas.

        .. A text has a center (x_pt, y_pt) as well as extents in x-direction
        .. (left_pt and right_pt) and y-direction (hight_pt and depth_pt). The
        .. textbox positions the output accordingly and scales it by the
        .. x-scale from the :mod:`unit`.

        .. :param float x_pt: x coordinate of the center in pts
        .. :param float y_pt: y coordinate of the center in pts
        .. :param float left_pt: unscaled left extent in pts
        .. :param float right_pt: unscaled right extent in pts
        .. :param float height_pt: unscaled height in pts
        .. :param float depth_pt: unscaled depth in pts
        .. :param function do_finish: callable to execute :meth:`readdvipage`
        .. :param fontmap: force a fontmap to be used (instead of the default
        ..     depending on the output format)
        .. :type fontmap: None or fontmap
        .. :param bool singlecharmode: position each character separately
        .. :param fillstyles: fill styles to be applied
        .. :type fillstyles: list of fillstyles

        """
        self.left = left_pt*unit.x_pt       #: left extent of the text (PyX length)
        self.right = right_pt*unit.x_pt     #: right extent of the text (PyX length)
        self.width = self.left + self.right #: width of the text (PyX length)
        self.height = height_pt*unit.x_pt   #: height of the text (PyX length)
        self.depth = depth_pt*unit.x_pt     #: height of the text (PyX length)

        self.do_finish = do_finish
        self.fontmap = fontmap
        self.singlecharmode = singlecharmode
        self.fillstyles = fillstyles

        self.texttrafo = trafo.scale(unit.scale["x"]).translated_pt(x_pt, y_pt)
        box.rect_pt.__init__(self, x_pt - left_pt*unit.scale["x"], y_pt - depth_pt*unit.scale["x"],
                                   (left_pt + right_pt)*unit.scale["x"],
                                   (depth_pt + height_pt)*unit.scale["x"],
                                   abscenter_pt = (left_pt*unit.scale["x"], depth_pt*unit.scale["x"]))

        self._dvicanvas = None

    def transform(self, *trafos, keep_anchor=False):
        box.rect.transform(self, *trafos, keep_anchor=keep_anchor)
        for trafo in trafos:
            self.texttrafo = trafo * self.texttrafo
        if self._dvicanvas is not None:
            for trafo in trafos:
                self._dvicanvas.trafo = trafo * self._dvicanvas.trafo

    def readdvipage(self, dvifile, page):
        self._dvicanvas = dvifile.readpage([ord("P"), ord("y"), ord("X"), page, 0, 0, 0, 0, 0, 0],
                                           fontmap=self.fontmap, singlecharmode=self.singlecharmode, attrs=[self.texttrafo] + self.fillstyles)

    @property
    def dvicanvas(self):
        if self._dvicanvas is None:
            self.do_finish()
        return self._dvicanvas

    def marker(self, name):
        """Return the position of a marker.

        :param str name: name of the marker
        :returns: position of the marker
        :rtype: tuple of two PyX lengths

        This method returns the position of the marker of the given name
        within, previously defined by the ``\\PyXMarker{name}`` macro in the
        typeset text. Please do not use the ``@`` character within your name to
        prevent name clashes with PyX internal uses (although we don’t the
        marker feature internally right now).

        Similar to generating actual output, the marker function accesses the
        DVI output, stopping. The :ref:`texipc` feature will allow for this access
        without stopping the TeX interpreter.

        """
        return self.texttrafo.apply(*self.dvicanvas.markers[name])

    def textpath(self):
        textpath = path.path()
        for item in self.dvicanvas.items:
            textpath += item.textpath()
        return textpath.transformed(self.texttrafo)

    def processPS(self, file, writer, context, registry, bbox):
        abbox = bboxmodule.empty()
        self.dvicanvas.processPS(file, writer, context, registry, abbox)
        bbox += box.rect.bbox(self)

    def processPDF(self, file, writer, context, registry, bbox):
        abbox = bboxmodule.empty()
        self.dvicanvas.processPDF(file, writer, context, registry, abbox)
        bbox += box.rect.bbox(self)

    def processSVG(self, xml, writer, context, registry, bbox):
        abbox = bboxmodule.empty()
        self.dvicanvas.processSVG(xml, writer, context, registry, abbox)
        bbox += box.rect.bbox(self)


class _marker:
    pass


class errordetail:
    "Constants defining the verbosity of the :exc:`TexResultError`."
    none = 0    #: Without any input and output.
    default = 1 #: Input and parsed output shortend to 5 lines.
    full = 2    #: Full input and unparsed as well as parsed output.


class Tee(object):

    def __init__(self, *files):
        """Apply write, flush, and close to each of the given files."""
        self.files = files

    def write(self, data):
        for file in self.files:
            file.write(data)

    def flush(self):
        for file in self.files:
            file.flush()

    def close(self):
        for file in self.files:
            file.close()

# The tex engine state represents the next (or current) execute state.
STATE_START, STATE_PREAMBLE, STATE_TYPESET, STATE_DONE = range(4)
PyXBoxPattern = re.compile(r"PyXBox:page=(?P<page>\d+),lt=(?P<lt>-?\d*((\d\.?)|(\.?\d))\d*)pt,rt=(?P<rt>-?\d*((\d\.?)|(\.?\d))\d*)pt,ht=(?P<ht>-?\d*((\d\.?)|(\.?\d))\d*)pt,dp=(?P<dp>-?\d*((\d\.?)|(\.?\d))\d*)pt:")
dvi_pattern = re.compile(r"Output written on .*texput\.dvi \((?P<page>\d+) pages?, \d+ bytes\)\.", re.DOTALL)

class TexDoneError(Exception):
    pass


class SingleEngine:

    #: default :class:`texmessage` parsers at interpreter startup
    texmessages_start_default = [texmessage.start]
    #: default :class:`texmessage` parsers at interpreter shutdown
    texmessages_end_default = [texmessage.end, texmessage.font_warning, texmessage.rerun_warning, texmessage.nobbl_warning]
    #: default :class:`texmessage` parsers for preamble output
    texmessages_preamble_default = [texmessage.load]
    #: default :class:`texmessage` parsers for typeset output
    texmessages_run_default = [texmessage.font_warning, texmessage.box_warning, texmessage.package_warning,
                                      texmessage.load_def, texmessage.load_graphics]

    def __init__(self, cmd,
                       texenc="ascii",
                       usefiles=[],
                       texipc=config.getboolean("text", "texipc", 0),
                       copyinput=None,
                       dvitype=False,
                       errordetail=errordetail.default,
                       texmessages_start=[],
                       texmessages_end=[],
                       texmessages_preamble=[],
                       texmessages_run=[]):
        """Base class for the TeX interface.

        .. note:: This class cannot be used directly. It is the base class for
                  all tex engines and provides most of the implementation.
                  Still, to the end user the parameters except for *cmd*
                  are important, as they are preserved in derived classes
                  usually.

        :param cmd: command and arguments to start the TeX interpreter
        :type cmd: list of str
        :param str texenc: encoding to use in the communication with the TeX
            interpreter
        :param usefiles: list of supplementary files to be copied to and from
            the temporary working directory (see :ref:`debug` for usage
            details)
        :type usefiles: list of str
        :param bool texipc: :ref:`texipc` flag.
        :param copyinput: filename or file to be used to store a copy of all
            the input passed to the TeX interpreter
        :type copyinput: None or str or file
        :param bool dvitype: flag to turn on dvitype-like output
        :param errordetail: verbosity of the :exc:`TexResultError`
        :type errordetail: :class:`errordetail`
        :param texmessages_start: additional message parsers at interpreter
            startup
        :type texmessages_start: list of :class:`texmessage` parsers
        :param texmessages_end: additional message parsers at interpreter
            shutdown
        :type texmessages_end: list of :class:`texmessage` parsers
        :param texmessages_preamble: additional message parsers for preamble
            output
        :type texmessages_preamble: list of :class:`texmessage` parsers
        :param texmessages_run: additional message parsers for typset output
        :type texmessages_run: list of :class:`texmessage` parsers

        """
        self.cmd = cmd
        self.texenc = texenc
        self.usefiles = usefiles
        self.texipc = texipc
        self.copyinput = copyinput
        self.dvitype = dvitype
        self.errordetail = errordetail
        self.texmessages_start = texmessages_start
        self.texmessages_end = texmessages_end
        self.texmessages_preamble = texmessages_preamble
        self.texmessages_run = texmessages_run

        self.state = STATE_START
        self.executeid = 0
        self.page = 0

        self.needdvitextboxes = [] # when texipc-mode off
        self.dvifile = None

    def _cleanup(self):
        """Clean-up TeX interpreter and tmp directory.

        This funtion is hooked up in atexit to quit the TeX interpreter, to
        save the contents of usefiles, and to remove the temporary directory.

        """
        try:
            if self.state > STATE_START:
                if self.state < STATE_DONE:
                    self.do_finish(cleanup=False)
                    if self.state < STATE_DONE: # cleanup while TeX is still running?
                        self.texoutput.expect(None)
                        self.force_done()
                        for f, msg in [(self.texinput.close, "We tried to communicate to %s to quit itself, but this seem to have failed. Trying by terminate signal now ...".format(self.name)),
                                       (self.popen.terminate, "Failed, too. Trying by kill signal now ..."),
                                       (self.popen.kill, "We tried very hard to get rid of the %s process, but we ultimately failed (as far as we can tell). Sorry.".format(self.name))]:
                            f()
                            if self.texoutput.done():
                                break
                            logger.warning(msg)
                self.popen.wait()
                for usefile in self.usefiles:
                    extpos = usefile.rfind(".")
                    try:
                        shutil.move(os.path.join(self.tmpdir, "texput" + usefile[extpos:]), usefile)
                    except EnvironmentError:
                        logger.warning("Could not save '{}'.".format(usefile))
                        if os.path.isfile(usefile):
                            try:
                                os.unlink(usefile)
                            except EnvironmentError:
                                logger.warning("Failed to remove spurious file '{}'.".format(usefile))
        finally:
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _execute(self, expr, texmessages, oldstate, newstate):
        """Execute TeX expression.

        :param str expr: expression to be passed to TeX
        :param texmessages: message parsers to analyse the textual output of
            TeX
        :type texmessages: list of :class:`texmessage` parsers
        :param int oldstate: state of the TeX interpreter prior to the
            expression execution
        :param int newstate: state of the TeX interpreter after to the
            expression execution

        """
        assert STATE_PREAMBLE <= oldstate <= STATE_TYPESET
        assert oldstate == self.state
        assert newstate >= oldstate
        if newstate == STATE_DONE:
            self.texoutput.expect(None)
            self.texinput.write(expr)
        else:

            # test to encode expr early to not pile up expected results
            # if the expression won't make it to the texinput at all
            # (which would otherwise harm a proper cleanup)
            expr.encode(self.texenc)

            if oldstate == newstate == STATE_TYPESET:
                self.page += 1
                expr = "\\ProcessPyXBox{%s%%\n}{%i}" % (expr, self.page)
            self.executeid += 1
            self.texoutput.expect("PyXInputMarker:executeid=%i:" % self.executeid)
            expr += "%%\n\\PyXInput{%i}%%\n" % self.executeid
            self.texinput.write(expr)
        self.texinput.flush()
        self.state = newstate
        if newstate == STATE_DONE:
            wait_ok = self.texoutput.done()
        else:
            wait_ok = self.texoutput.wait()
        try:
            parsed = unparsed = self.texoutput.read()
            if not wait_ok:
                raise TexResultError("TeX didn't respond as expected within the timeout period.")
            if newstate != STATE_DONE:
                parsed, m = remove_string("PyXInputMarker:executeid=%s:" % self.executeid, parsed)
                if not m:
                    raise TexResultError("PyXInputMarker expected")
                if oldstate == newstate == STATE_TYPESET:
                    parsed, m = remove_pattern(PyXBoxPattern, parsed, ignore_nl=False)
                    if not m:
                        raise TexResultError("PyXBox expected")
                    if m.group("page") != str(self.page):
                        raise TexResultError("Wrong page number in PyXBox")
                    extent_pt = [float(x)*72/72.27 for x in m.group("lt", "rt", "ht", "dp")]
                    parsed, m = remove_string("[80.121.88.%s]" % self.page, parsed)
                    if not m:
                        raise TexResultError("PyXPageOutMarker expected")
            else:
                # check for "Output written on ...dvi (1 page, 220 bytes)."
                if self.page:
                    parsed, m = remove_pattern(dvi_pattern, parsed)
                    if not m:
                        raise TexResultError("TeX dvifile messages expected")
                    if m.group("page") != str(self.page):
                        raise TexResultError("wrong number of pages reported")
                else:
                    parsed, m = remove_string("No pages of output.", parsed)
                    if not m:
                        raise TexResultError("no dvifile expected")

            for t in texmessages:
                parsed = t(parsed)
            if parsed.replace(r"(Please type a command or say `\end')", "").replace(" ", "").replace("*\n", "").replace("\n", ""):
                raise TexResultError("unhandled TeX response (might be an error)")
        except TexResultError as e:
            if self.errordetail > errordetail.none:
                def add(msg): e.args = (e.args[0] + msg,)
                add("\nThe expression passed to TeX was:\n{}".format(indent_text(expr.rstrip())))
                if self.errordetail == errordetail.full:
                    add("\nThe return message from TeX was:\n{}".format(indent_text(unparsed.rstrip())))
                if self.errordetail == errordetail.default:
                    if parsed.count('\n') > 6:
                        parsed = "\n".join(parsed.split("\n")[:5] + ["(cut after 5 lines; use errordetail.full for all output)"])
                add("\nAfter parsing the return message from TeX, the following was left:\n{}".format(indent_text(parsed.rstrip())))
            raise e
        if oldstate == newstate == STATE_TYPESET:
            return extent_pt

    def do_start(self):
        """Setup environment and start TeX interpreter."""
        assert self.state == STATE_START
        self.state = STATE_PREAMBLE

        chroot = config.get("text", "chroot", "")
        if chroot:
            chroot_tmpdir = config.get("text", "tmpdir", "/tmp")
            chroot_tmpdir_rel = os.path.relpath(chroot_tmpdir, os.sep)
            base_tmpdir = os.path.join(chroot, chroot_tmpdir_rel)
        else:
            base_tmpdir = config.get("text", "tmpdir", None)
        self.tmpdir = tempfile.mkdtemp(prefix="pyx", dir=base_tmpdir)
        atexit.register(self._cleanup)
        for usefile in self.usefiles:
            extpos = usefile.rfind(".")
            try:
                os.rename(usefile, os.path.join(self.tmpdir, "texput" + usefile[extpos:]))
            except OSError:
                pass
        if chroot:
            tex_tmpdir = os.sep + os.path.relpath(self.tmpdir, chroot)
        else:
            tex_tmpdir = self.tmpdir
        cmd = self.cmd + ['--output-directory', tex_tmpdir]
        if self.texipc:
            cmd.append("--ipc")
        self.popen = config.Popen(cmd, stdin=config.PIPE, stdout=config.PIPE, stderr=config.STDOUT, bufsize=0)
        self.texinput = io.TextIOWrapper(self.popen.stdin, encoding=self.texenc)
        if self.copyinput:
            try:
                self.copyinput.write
            except AttributeError:
                self.texinput = Tee(open(self.copyinput, "w", encoding=self.texenc), self.texinput)
            else:
                self.texinput = Tee(self.copyinput, self.texinput)
        self.texoutput = MonitorOutput(self.name, io.TextIOWrapper(self.popen.stdout, encoding=self.texenc, errors="surrogateescape"))
        self._execute("\\scrollmode\n\\raiseerror%\n" # switch to and check scrollmode
                      "\\def\\PyX{P\\kern-.3em\\lower.5ex\\hbox{Y}\\kern-.18em X}%\n" # just the PyX Logo
                      "\\gdef\\PyXBoxHAlign{0}%\n" # global PyXBoxHAlign (0.0-1.0) for the horizontal alignment, default to 0
                      "\\newbox\\PyXBox%\n" # PyXBox will contain the output
                      "\\newbox\\PyXBoxHAligned%\n" # PyXBox will contain the horizontal aligned output
                      "\\newdimen\\PyXDimenHAlignLT%\n" # PyXDimenHAlignLT/RT will contain the left/right extent
                      "\\newdimen\\PyXDimenHAlignRT%\n" +
                      _textattrspreamble + # insert preambles for textattrs macros
                      "\\long\\def\\ProcessPyXBox#1#2{%\n" # the ProcessPyXBox definition (#1 is expr, #2 is page number)
                      "\\setbox\\PyXBox=\\hbox{{#1}}%\n" # push expression into PyXBox
                      "\\PyXDimenHAlignLT=\\PyXBoxHAlign\\wd\\PyXBox%\n" # calculate the left/right extent
                      "\\PyXDimenHAlignRT=\\wd\\PyXBox%\n"
                      "\\advance\\PyXDimenHAlignRT by -\\PyXDimenHAlignLT%\n"
                      "\\gdef\\PyXBoxHAlign{0}%\n" # reset the PyXBoxHAlign to the default 0
                      "\\immediate\\write16{PyXBox:page=#2," # write page and extents of this box to stdout
                                                  "lt=\\the\\PyXDimenHAlignLT,"
                                                  "rt=\\the\\PyXDimenHAlignRT,"
                                                  "ht=\\the\\ht\\PyXBox,"
                                                  "dp=\\the\\dp\\PyXBox:}%\n"
                      "\\setbox\\PyXBoxHAligned=\\hbox{\\kern-\\PyXDimenHAlignLT\\box\\PyXBox}%\n" # align horizontally
                      "\\ht\\PyXBoxHAligned0pt%\n" # baseline alignment (hight to zero)
                      "{\\count0=80\\count1=121\\count2=88\\count3=#2\\shipout\\box\\PyXBoxHAligned}}%\n" # shipout PyXBox to Page 80.121.88.<page number>
                      "\\def\\PyXInput#1{\\immediate\\write16{PyXInputMarker:executeid=#1:}}%\n" # write PyXInputMarker to stdout
                      "\\def\\PyXMarker#1{\\hskip0pt\\special{PyX:marker #1}}%", # write PyXMarker special into the dvi-file
                      self.texmessages_start_default + self.texmessages_start, STATE_PREAMBLE, STATE_PREAMBLE)

    def do_preamble(self, expr, texmessages):
        """Ensure preamble mode and execute expr."""
        if self.state < STATE_PREAMBLE:
            self.do_start()
        self._execute(expr, texmessages, STATE_PREAMBLE, STATE_PREAMBLE)

    def do_typeset(self, expr, texmessages):
        """Ensure typeset mode and typeset expr."""
        if self.state < STATE_PREAMBLE:
            self.do_start()
        if self.state < STATE_TYPESET:
            self.go_typeset()
        return self._execute(expr, texmessages, STATE_TYPESET, STATE_TYPESET)

    def do_finish(self, cleanup=True):
        """Teardown TeX interpreter and cleanup environment.

        :param bool cleanup: use _cleanup regularly/explicitly (not via atexit)
        """
        if self.state == STATE_DONE:
            return
        if self.state < STATE_TYPESET:
            self.go_typeset()
        self.go_finish()
        assert self.state == STATE_DONE
        self.texinput.close()            # close the input queue and
        self.texoutput.done()            # wait for finish of the output

        if self.needdvitextboxes:
            dvifilename = os.path.join(self.tmpdir, "texput.dvi")
            self.dvifile = dvifile.DVIfile(dvifilename, debug=self.dvitype)
            page = 1
            for box in self.needdvitextboxes:
                box.readdvipage(self.dvifile, page)
                page += 1
        if self.dvifile is not None and self.dvifile.readpage(None) is not None:
            raise ValueError("end of dvifile expected but further pages follow")
        if cleanup:
            atexit.unregister(self._cleanup)
            self._cleanup()

    def preamble(self, expr, texmessages=[]):
        """Execute a preamble.

        :param str expr: expression to be executed
        :param texmessages: additional message parsers
        :type texmessages: list of :class:`texmessage` parsers

        Preambles must not generate output, but are used to load files, perform
        settings, define macros, *etc*. In LaTeX mode, preambles are executed
        before ``\\begin{document}``. The method can be called multiple times,
        but only prior to :meth:`SingleEngine.text` and
        :meth:`SingleEngine.text_pt`.

        """
        texmessages = self.texmessages_preamble_default + self.texmessages_preamble + texmessages
        self.do_preamble(expr, texmessages)

    def text_pt(self, x_pt, y_pt, expr, textattrs=[], texmessages=[], fontmap=None, singlecharmode=False):
        """Typeset text.

        :param float x_pt: x position in pts
        :param float y_pt: y position in pts
        :param expr: text to be typeset
        :type expr: str or :class:`MultiEngineText`
        :param textattrs: styles and attributes to be applied to the text
        :type textattrs: list of  :class:`textattr, :class:`trafo.trafo_pt`,
            and :class:`style.fillstyle`
        :param texmessages: additional message parsers
        :type texmessages: list of :class:`texmessage` parsers
        :param fontmap: force a fontmap to be used (instead of the default
            depending on the output format)
        :type fontmap: None or fontmap
        :param bool singlecharmode: position each character separately
        :returns: text output insertable into a canvas.
        :rtype: :class:`textextbox_pt`
        :raises: :exc:`TexDoneError`: when the TeX interpreter has been
            terminated already.

        """
        if self.state == STATE_DONE:
            raise TexDoneError("typesetting process was terminated already")
        textattrs = attr.mergeattrs(textattrs) # perform cleans
        attr.checkattrs(textattrs, [textattr, trafo.trafo_pt, style.fillstyle])
        trafos = attr.getattrs(textattrs, [trafo.trafo_pt])
        fillstyles = attr.getattrs(textattrs, [style.fillstyle])
        textattrs = attr.getattrs(textattrs, [textattr])
        if isinstance(expr, MultiEngineText):
            expr = expr.tex
        for ta in textattrs[::-1]:
            expr = ta.apply(expr)
        first = self.state < STATE_TYPESET
        left_pt, right_pt, height_pt, depth_pt = self.do_typeset(expr, self.texmessages_run_default + self.texmessages_run + texmessages)
        if self.texipc and first:
            self.dvifile = dvifile.DVIfile(os.path.join(self.tmpdir, "texput.dvi"), debug=self.dvitype)
        box = textextbox_pt(x_pt, y_pt, left_pt, right_pt, height_pt, depth_pt, self.do_finish, fontmap, singlecharmode, fillstyles)
        for t in trafos:
            box.reltransform(t) # TODO: should trafos really use reltransform???
                                #       this is quite different from what we do elsewhere!!!
                                #       see https://sourceforge.net/mailarchive/forum.php?thread_id=9137692&forum_id=23700
        if self.texipc:
            box.readdvipage(self.dvifile, self.page)
        else:
            self.needdvitextboxes.append(box)
        return box

    def text(self, x, y, *args, **kwargs):
        """Typeset text.

        This method is identical to :meth:`text_pt` with the only difference of
        using PyX lengths to position the output.

        :param x: x position
        :type x: PyX length
        :param y: y position
        :type y: PyX length

        """
        return self.text_pt(unit.topt(x), unit.topt(y), *args, **kwargs)


class SingleTexEngine(SingleEngine):

    def __init__(self, cmd=config.getlist("text", "tex", ["tex"]), lfs="10pt", **kwargs):
        """Plain TeX interface.

        This class adjusts the :class:`SingleEngine` to use plain TeX.

        :param cmd: command and arguments to start the TeX interpreter
        :type cmd: list of str
        :param lfs: resemble LaTeX font settings within plain TeX by loading a
            lfs-file
        :type lfs: str or None
        :param kwargs: additional arguments passed to :class:`SingleEngine`

        An lfs-file is a file defining a set of font commands like ``\\normalsize``
        by font selection commands in plain TeX. Several of those files
        resembling standard settings of LaTeX are distributed along with PyX in
        the ``pyx/data/lfs`` directory. This directory also contains a LaTeX
        file to create lfs files for different settings (LaTeX class, class
        options, and style files).

        """
        super().__init__(cmd=cmd, **kwargs)
        self.lfs = lfs
        self.name = "TeX"

    def go_typeset(self):
        assert self.state == STATE_PREAMBLE
        self.state = STATE_TYPESET

    def go_finish(self):
        self._execute("\\end%\n", self.texmessages_end_default + self.texmessages_end, STATE_TYPESET, STATE_DONE)

    def force_done(self):
        self.texinput.write("\n\\end\n")

    def do_start(self):
        super().do_start()
        if self.lfs:
            if not self.lfs.endswith(".lfs"):
                self.lfs = "%s.lfs" % self.lfs
            with config.open(self.lfs, [config.format.pyx]) as lfsfile:
                lfsdef = lfsfile.read().decode("ascii")
            self._execute(lfsdef, [], STATE_PREAMBLE, STATE_PREAMBLE)
            self._execute("\\normalsize%\n", [], STATE_PREAMBLE, STATE_PREAMBLE)
        self._execute("\\newdimen\\linewidth\\newdimen\\textwidth%\n", [], STATE_PREAMBLE, STATE_PREAMBLE)


class SingleLatexEngine(SingleEngine):

    #: default :class:`texmessage` parsers at LaTeX class loading
    texmessages_docclass_default = [texmessage.load]
    #: default :class:`texmessage` parsers at ``\begin{document}``
    texmessages_begindoc_default = [texmessage.load, texmessage.no_aux]

    def __init__(self, cmd=config.getlist("text", "latex", ["latex"]),
                       docclass="article", docopt=None, pyxgraphics=True,
                       texmessages_docclass=[], texmessages_begindoc=[], **kwargs):
        """LaTeX interface.

        This class adjusts the :class:`SingleEngine` to use LaTeX.

        :param cmd: command and arguments to start the TeX interpreter
            in LaTeX mode
        :type cmd: list of str
        :param str docclass: document class
        :param docopt: document loading options
        :type docopt: str or None
        :param bool pyxgraphics: activate graphics bundle support, see
            :ref:`pyxgraphics`
        :param texmessages_docclass: additional message parsers at LaTeX class
            loading
        :type texmessages_docclass: list of :class:`texmessage` parsers
        :param texmessages_begindoc: additional message parsers at
            ``\\begin{document}``
        :type texmessages_begindoc: list of :class:`texmessage` parsers
        :param kwargs: additional arguments passed to :class:`SingleEngine`

        """
        super().__init__(cmd=cmd, **kwargs)
        self.docclass = docclass
        self.docopt = docopt
        self.pyxgraphics = pyxgraphics
        self.texmessages_docclass = texmessages_docclass
        self.texmessages_begindoc = texmessages_begindoc
        self.name = "LaTeX"

    def go_typeset(self):
        self._execute("\\begin{document}", self.texmessages_begindoc_default + self.texmessages_begindoc, STATE_PREAMBLE, STATE_TYPESET)

    def go_finish(self):
        self._execute("\\end{document}%\n", self.texmessages_end_default + self.texmessages_end, STATE_TYPESET, STATE_DONE)

    def force_done(self):
        self.texinput.write("\n\\catcode`\\@11\\relax\\@@end\n")

    def do_start(self):
        super().do_start()
        if self.pyxgraphics:
            with config.open("pyx.def", [config.format.pyx]) as source, open(os.path.join(self.tmpdir, "pyx.def"), "wb") as dest:
                dest.write(source.read())
            self._execute("\\makeatletter%\n"
                          "\\let\\saveProcessOptions=\\ProcessOptions%\n"
                          "\\def\\ProcessOptions{%\n"
                          "\\def\\Gin@driver{" + self.tmpdir.replace(os.sep, "/") + "/pyx.def}%\n"
                          "\\def\\c@lor@namefile{dvipsnam.def}%\n"
                          "\\saveProcessOptions}%\n"
                          "\\makeatother",
                          [], STATE_PREAMBLE, STATE_PREAMBLE)
        if self.docopt is not None:
            self._execute("\\documentclass[%s]{%s}" % (self.docopt, self.docclass),
                          self.texmessages_docclass_default + self.texmessages_docclass, STATE_PREAMBLE, STATE_PREAMBLE)
        else:
            self._execute("\\documentclass{%s}" % self.docclass,
                          self.texmessages_docclass_default + self.texmessages_docclass, STATE_PREAMBLE, STATE_PREAMBLE)


def reset_for_tex_done(f):
    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except TexDoneError:
            self.reset(reinit=True)
            return f(self, *args, **kwargs)
    return wrapped


class MultiEngine:

    def __init__(self, cls, *args, **kwargs):
        """A restartable :class:`SingleEngine` class

        :param cls: the class being wrapped
        :type cls: :class:`SingleEngine` class
        :param list args: args at class instantiation
        :param dict kwargs: keyword args at at class instantiation

        """
        self.cls = cls
        self.args = args
        self.kwargs = kwargs
        self.reset()

    def preamble(self, expr, texmessages=[]):
        "resembles :meth:`SingleEngine.preamble`"
        self.preambles.append((expr, texmessages))
        self.instance.preamble(expr, texmessages)

    @reset_for_tex_done
    def text_pt(self, *args, **kwargs):
        "resembles :meth:`SingleEngine.text_pt`"
        return self.instance.text_pt(*args, **kwargs)

    @reset_for_tex_done
    def text(self, *args, **kwargs):
        "resembles :meth:`SingleEngine.text`"
        return self.instance.text(*args, **kwargs)

    def reset(self, reinit=False):
        """Start a new :class:`SingleEngine` instance

        :param bool reinit: replay :meth:`preamble` calls on the new instance

        After executing this function further preamble calls are allowed,
        whereas once a text output has been created, :meth:`preamble` calls are
        forbidden.

        """
        self.instance = self.cls(*self.args, **self.kwargs)
        if reinit:
            for expr, texmessages in self.preambles:
                self.instance.preamble(expr, texmessages)
        else:
            self.preambles = []


class TexEngine(MultiEngine):

    def __init__(self, *args, **kwargs):
        """A restartable :class:`SingleTexEngine` class

        :param list args: args at class instantiation
        :param dict kwargs: keyword args at at class instantiation

        """
        super().__init__(SingleTexEngine, *args, **kwargs)


class LatexEngine(MultiEngine):

    def __init__(self, *args, **kwargs):
        """A restartable :class:`SingleLatexEngine` class

        :param list args: args at class instantiation
        :param dict kwargs: keyword args at at class instantiation

        """
        super().__init__(SingleLatexEngine, *args, **kwargs)


from pyx import deco
from pyx.font import T1font
from pyx.font.t1file import T1File
from pyx.font.afmfile import AFMfile


class MultiEngineText:

    def __init__(self, tex, unicode):
        """Container for text to be typeset for both, TeX based engines and the
        UnicodeEngine.

        :param str tex: text for TeX based engines
        :param unicode: text for the :class:`UnicodeEngine`
        :type unicode: str, :class:`Text`, or :class:`StackedText or a list of those

        """
        self.tex = tex
        self.unicode = unicode


class Text:

    def __init__(self, text, scale=1, shift=0):
        """Text for the UnicodeEngine with basic typesetting features

        :param str text: text to be typeset
        :param float scale: scale
        :param float shift: vertical shift in units of the text size (without the scale)

        """
        self.text = text
        self.scale = scale
        self.shift = shift


class StackedText:

    def __init__(self, texts, frac=False, align=0):
        """Stack text above each other for the UnicodeEngine

        :param list texts: texts to be typeset above each other
        :param bool frac: add a fractional line (for two texts only)
        :param float align: horizontal alignment of the text where
            0 is left, 0.5 is centered, and 1 is right

        """
        assert not frac or len(texts) == 2
        self.texts = texts
        self.frac = frac
        self.align = align


class unicodetextbox_pt(textbox_pt):

    def __init__(self, x_pt, y_pt, texts, font, size, mathmode=False):
        self.font = font
        self.size = size
        self.canvas = canvas.canvas()
        self.texttrafo = trafo.scale(unit.scale["x"]).translated_pt(x_pt, y_pt)

        if isinstance(texts, (str, Text, StackedText)):
            texts = [texts]

        x_pt = 0
        for text in texts:
            if isinstance(text, str):
                text = Text(text)
            if isinstance(text, Text):
                if mathmode:
                    text_fragments = text.text.split('-')
                else:
                    text_fragments = [text.text]
                for i, text_fragment in enumerate(text_fragments):
                    if i:
                        self.canvas.fill(path.rect_pt(x_pt+0.5*(self.minuswidth_pt-self.minuslength_pt), self.mathaxis_pt-0.5*self.minusthickness_pt, self.minuslength_pt, self.minusthickness_pt))
                        x_pt += self.minuswidth_pt
                    if text_fragment:
                        try:
                            t = self.font.text_pt(x_pt, text.shift*self.size, text_fragment, text.scale*self.size)
                            x_pt += t.bbox().width_pt()
                        except:
                            assert '·' in text_fragment
                            t = self.font.text_pt(x_pt, text.shift*self.size, text_fragment.replace('·', 'x'), text.scale*self.size)
                            x_pt += t.bbox().width_pt()
                        self.canvas.insert(t)
            else:
                assert isinstance(text, StackedText)
                shift = self.mathaxis_pt if text.frac else 0
                ts = [self.font.text_pt(x_pt, text.shift*self.size+shift, text.text, text.scale*self.size)
                      for text in text.texts]
                width_pt = max(t.bbox().width_pt() for t in ts)
                if text.frac:
                    self.canvas.fill(path.rect_pt(x_pt, self.mathaxis_pt-0.5*self.minusthickness_pt, width_pt, self.minusthickness_pt))
                for t in ts:
                    self.canvas.insert(t, [trafo.translate_pt(text.align*(width_pt-t.bbox().width_pt()), 0)] if text.align else [])
                x_pt += width_pt

        bbox = self.canvas.bbox()
        bbox.includepoint_pt(0, 0)
        bbox.includepoint_pt(x_pt, 0)
        box.rect_pt.__init__(self, bbox.llx_pt, bbox.lly_pt, bbox.urx_pt-bbox.llx_pt, bbox.ury_pt-bbox.lly_pt, abscenter_pt = (0, 0))
        box.rect.transform(self, self.texttrafo)

    def _extract_minus_properties(self):
        minus_path = self.font.text_pt(0, 0, '=', 1).textpath().normpath()
        minus_path.normsubpaths = [normsubpath for normsubpath in minus_path.normsubpaths if normsubpath]
        self.font.minusthickness_pt = max(normsubpath.bbox().height_pt() for normsubpath in minus_path.normsubpaths)
        self.font.halfminuswidth_pt, self.font.mathaxis_pt = minus_path.bbox().center_pt()
        self.font.minuslength_pt = minus_path.bbox().width_pt()

    @property
    def mathaxis_pt(self):
        if not hasattr(self.font, "mathaxis_pt"):
            self._extract_minus_properties()
        return self.font.mathaxis_pt*self.size

    @property
    def minuswidth_pt(self):
        if not hasattr(self.font, "halfminuswidth_pt"):
            self._extract_minus_properties()
        return 2*self.font.halfminuswidth_pt*self.size

    @property
    def minuslength_pt(self):
        if not hasattr(self.font, "minuslength_pt"):
            self._extract_minus_properties()
        return self.font.minuslength_pt*self.size

    @property
    def minusthickness_pt(self):
        if not hasattr(self.font, "minusthickness_pt"):
            self._extract_minus_properties()
        return self.font.minusthickness_pt*self.size

    def transform(self, *trafos, keep_anchor=False):
        box.rect.transform(self, *trafos, keep_anchor=keep_anchor)
        for trafo in trafos:
            self.texttrafo = trafo * self.texttrafo

    def bbox(self):
        return self.canvas.bbox().transformed(self.texttrafo)

    def textpath(self):
        r = path.path()
        for item in self.canvas.items:
            if isinstance(item, canvas.canvas):
                for subitem in item.items:
                    r += subitem.textpath().transformed(item.trafo)
            elif isinstance(item, deco.decoratedpath):
                r += item.path
            else:
                r += item.textpath()
        return r.transformed(self.texttrafo)

    def processPS(self, file, writer, context, registry, bbox):
        c = canvas.canvas([self.texttrafo])
        c.insert(self.canvas)
        c.processPS(file, writer, context, registry, bbox)

    def processPDF(self, file, writer, context, registry, bbox):
        c = canvas.canvas([self.texttrafo])
        c.insert(self.canvas)
        c.processPDF(file, writer, context, registry, bbox)

    def processSVG(self, xml, writer, context, registry, bbox):
        c = canvas.canvas([self.texttrafo])
        c.insert(self.canvas)
        c.processSVG(xml, writer, context, registry, bbox)


class UnicodeEngine:

    def __init__(self, fontname="cmr10", size=10):
        with config.open(fontname, [config.format.type1]) as f:
            t1file = T1File.from_PF_bytes(f.read())
        with config.open(fontname, [config.format.afm], ascii=True) as f:
            afmfile = AFMfile(f)
        self.font = T1font(t1file, afmfile)
        self.size = size

    def preamble(self):
        raise NotImplemented()

    def reset(self):
        raise NotImplemented()

    def text_pt(self, x_pt, y_pt, text, textattrs=[], texmessages=[], fontmap=None, singlecharmode=False):

        textattrs = attr.mergeattrs(textattrs) # perform cleans
        attr.checkattrs(textattrs, [textattr, trafo.trafo_pt, style.fillstyle])
        trafos = attr.getattrs(textattrs, [trafo.trafo_pt])
        fillstyles = attr.getattrs(textattrs, [style.fillstyle])
        textattrs = attr.getattrs(textattrs, [textattr])
        mathmode = bool(attr.getattrs(textattrs, [_mathmode]))

        if isinstance(text, MultiEngineText):
            text = text.unicode
        output = unicodetextbox_pt(x_pt, y_pt, text, self.font, self.size, mathmode=mathmode)
        for ta in textattrs: # reverse?!
            ta.apply_trafo(output)

        return output

    def text(self, x, y, *args, **kwargs):
        return self.text_pt(unit.topt(x), unit.topt(y), *args, **kwargs)


# from pyx.font.otffile import OpenTypeFont
# 
# class OTFUnicodeText:
# 
#     def __init__(self, fontname, size=10):
#         self.font = OpenTypeFont(config.open(fontname, [config.format.ttf]))
#         self.size = size
# 
#     def preamble(self):
#         raise NotImplemented()
# 
#     def reset(self):
#         raise NotImplemented()
# 
#     def text_pt(self, x_pt, y_pt, text, textattrs=[], texmessages=[], fontmap=None, singlecharmode=False):
#     # def text_pt(self, x_pt, y_pt, text, *args, **kwargs):
#         return unicodetextbox_pt(x_pt, y_pt, text, self.font, self.size)
# 
#     def text(self, x, y, *args, **kwargs):
#         return self.text_pt(unit.topt(x), unit.topt(y), *args, **kwargs)


# old, deprecated names:
texrunner = TexRunner = TexEngine
latexrunner = LatexRunner = LatexEngine

# module level interface documentation for autodoc
# the actual values are setup by the set function

#: the current :class:`MultiEngine` instance for the module level functions
defaulttextengine = None

#: defaulttextengine.preamble (bound method)
preamble = None

#: defaulttextengine.text_pt (bound method)
text_pt = None

#: defaulttextengine.text (bound method)
text = None

#: defaulttextengine.reset (bound method)
reset = None

def set(engine=None, cls=None, mode=None, *args, **kwargs):
    """Setup a new module level :class:`MultiEngine`

    :param engine: the module level engine object to be used, i.e.
        :class:`TexEngine`, :class:`LatexEngine`, or :class:`UnicodeEngine`
    :type cls: Engine object, not instance
    :param cls: identical to *engine*

        :deprecated: use the engine argument instead
    :param mode: ``"tex"`` for :class:`TexEngine` or ``"latex"`` for
        :class:`LatexEngine` with arbitraty capitalization

        :deprecated: use the engine argument instead
    :type mode: str or None
    :param list args: args at class instantiation
    :param dict kwargs: keyword args at at class instantiation

    """
    global defaulttextengine, reset, preamble, text, text_pt
    if mode is not None:
        logger.warning("mode setting is deprecated, use the engine argument instead")
        assert cls is None
        assert engine is None
        engine = {"tex": TexEngine, "latex": LatexEngine}[mode.lower()]
    elif cls is not None:
        logger.warning("cls setting is deprecated, use the engine argument instead")
        assert not engine
        engine = cls
    defaulttextengine = engine(*args, **kwargs)
    preamble = defaulttextengine.preamble
    text_pt = defaulttextengine.text_pt
    text = defaulttextengine.text
    reset = defaulttextengine.reset

# initialize defaulttextengine
set({"TexEngine": TexEngine, "LatexEngine": LatexEngine, "UnicodeEngine": UnicodeEngine}[config.get('text', 'defaulttextengine', 'TexEngine')])


def escapestring(s, replace={" ": "~",
                             "$": r"\$",
                             "&": r"\&",
                             "#": r"\#",
                             "_": r"\_",
                             "%": r"\%",
                             "^": r"\string^",
                             "~": r"\string~",
                             "<": "{$<$}",
                             ">": "{$>$}",
                             "{": r"{$\{$}",
                             "}": r"{$\}$}",
                             "\\": r"{$\setminus$}",
                             "|": r"{$\mid$}"}):
    "Escapes ASCII characters such that they can be typeset by TeX/LaTeX"""
    i = 0
    while i < len(s):
        if not 32 <= ord(s[i]) < 127:
            raise ValueError("escapestring function handles ascii strings only")
        c = s[i]
        try:
            r = replace[c]
        except KeyError:
            i += 1
        else:
            s = s[:i] + r + s[i+1:]
            i += len(r)
    return s
