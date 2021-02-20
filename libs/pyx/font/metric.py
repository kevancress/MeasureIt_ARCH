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


class metric:

    def width_ds(self, glyphname):
        raise NotImplementedError()

    def width_pt(self, glyphnames, size_pt):
        raise NotImplementedError()

    def height_pt(self, glyphnames, size_pt):
        raise NotImplementedError()

    def depth_pt(self, glyphnames, size_pt):
        raise NotImplementedError()

    def resolveligatures(self, glyphnames):
        return glyphnames

    def resolvekernings(self, glyphnames, size_pt=None):
        result = [None]*(2*len(glyphnames)-1)
        for i, glyphname in enumerate(glyphnames):
            result[2*i] = glyphname
        return result
