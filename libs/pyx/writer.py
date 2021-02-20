# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2013 Jörg Lehmann <joerg@pyx-project.org>
# Copyright (C) 2013 André Wobst <wobsta@pyx-project.org>
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

class writer:

    def __init__(self, file, encoding="ascii", errors="surrogateescape"):
        self.file = file
        self.encoding = encoding
        self.errors = errors

    def write(self, s):
        self.file.write(s.encode(self.encoding, errors=self.errors))

    def write_bytes(self, b):
        self.file.write(b)

    def tell(self):
        return self.file.tell()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self.file.__exit__(exc_type, exc_value, traceback)
