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


import io, struct


class reader:

    def __init__(self, filename):
        self.file = open(filename, "rb")

    def tell(self):
        return self.file.tell()

    def eof(self):
        return self.file.eof()

    def read(self, bytes):
        return self.file.read(bytes)

    def readint(self, bytes=4, signed=0):
        first = 1
        result = 0
        while bytes:
            value = ord(self.file.read(1))
            if first and signed and value > 127:
                value -= 256
            first = 0
            result = 256 * result + value
            bytes -= 1
        return result

    def readint32(self):
        return struct.unpack(">l", self.file.read(4))[0]

    def readuint32(self):
        return struct.unpack(">L", self.file.read(4))[0]

    def readint24(self):
        return struct.unpack(">l", b"\0"+self.file.read(3))[0]

    def readuint24(self):
        return struct.unpack(">L", b"\0"+self.file.read(3))[0]

    def readint16(self):
        return struct.unpack(">h", self.file.read(2))[0]

    def readuint16(self):
        return struct.unpack(">H", self.file.read(2))[0]

    def readchar(self):
        return struct.unpack("b", self.file.read(1))[0]

    def readuchar(self):
        return struct.unpack("B", self.file.read(1))[0]

    def readstring(self, bytes):
        l = self.readuchar()
        assert l <= bytes-1, "inconsistency in file: string too long"
        return self.file.read(bytes-1)[:l]

    def close(self):
        self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self.file.__exit__(exc_type, exc_value, traceback)


class bytesreader(reader):

    def __init__(self, b):
        self.file = io.BytesIO(b)


class PStokenizer:
    """cursor to read a string token by token"""

    def __init__(self, data, startstring=None, eattokensep=1,
                 tokenseps=" \t\r\n", tokenstarts="()<>[]{}/%",
                 commentchar="%", newlinechars="\r\n"):
        """creates a cursor for the string data

        startstring is a string at which the cursor should start at. The first
        ocurance of startstring is used. When startstring is not in data, an
        exception is raised, otherwise the cursor is set to the position right
        after the startstring. When eattokenseps is set, startstring must be
        followed by a tokensep and this first tokensep is also consumed.
        tokenseps is a string containing characters to be used as token
        separators. tokenstarts is a string containing characters which 
        directly (even without intermediate token separator) start a new token.
        """
        self.data = data
        if startstring is not None:
            self.pos = self.data.index(startstring) + len(startstring)
        else:
            self.pos = 0
        self.tokenseps = tokenseps
        self.tokenstarts = tokenstarts
        self.commentchar = commentchar
        self.newlinechars = newlinechars
        if eattokensep:
            if self.data[self.pos] not in self.tokenstarts:
                if self.data[self.pos] not in self.tokenseps:
                    raise ValueError("cursor initialization string is not followed by a token separator")
                self.pos += 1

    def gettoken(self):
        """get the next token

        Leading token separators and comments are silently consumed. The first token
        separator after the token is also silently consumed."""
        while self.data[self.pos] in self.tokenseps:
            self.pos += 1
        # ignore comments including subsequent whitespace characters
        while self.data[self.pos] == self.commentchar:
            while self.data[self.pos] not in self.newlinechars:
                self.pos += 1
            while self.data[self.pos] in self.tokenseps:
                self.pos += 1
        startpos = self.pos
        while self.data[self.pos] not in self.tokenseps:
            # any character in self.tokenstarts ends the token
            if self.pos>startpos and self.data[self.pos] in self.tokenstarts:
                break
            self.pos += 1
        result = self.data[startpos:self.pos]
        if self.data[self.pos] in self.tokenseps:
            self.pos += 1 # consume a single tokensep
        return result

    def getint(self):
        """get the next token as an integer"""
        return int(self.gettoken())

    def getbytes(self, count):
        """get the next count bytes"""
        startpos = self.pos
        self.pos += count
        return self.data[startpos: self.pos]



class PSbytes_tokenizer(PStokenizer):

    def __init__(self, data, startstring=None, eattokensep=1,
                 tokenseps=b" \t\r\n", tokenstarts=b"()<>[]{}/%",
                 commentchar=b"%", newlinechars=b"\r\n"):
        super().__init__(data, startstring=startstring, eattokensep=eattokensep,
                         tokenseps=tokenseps, tokenstarts=tokenstarts,
                         commentchar=commentchar, newlinechars=newlinechars)
