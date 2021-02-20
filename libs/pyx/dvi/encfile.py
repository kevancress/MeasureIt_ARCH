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


from pyx import reader

class ENFfileError(Exception):
    pass

class ENCfile:

    def __init__(self, bytes):
        c = reader.PStokenizer(bytes, "")

        # name of encoding
        self.name = c.gettoken()
        token = c.gettoken()
        if token != "[":
            raise ENCfileError("cannot parse encoding file '%s', expecting '[' got '%s'" % (filename, token))
        self.vector = []
        for i in range(256):
            token = c.gettoken()
            if token == "]":
                raise ENCfileError("not enough charcodes in encoding file '%s'" % filename)
            if not token[0] == "/":
                raise ENCfileError("token does not start with / in encoding file '%s'" % filename)
            self.vector.append(token[1:])
        if c.gettoken() != "]":
            raise ENCfileError("too many charcodes in encoding file '%s'" % filename)
        token = c.gettoken()
        if token != "def":
            raise ENCfileError("cannot parse encoding file '%s', expecting 'def' got '%s'" % (filename, token))

