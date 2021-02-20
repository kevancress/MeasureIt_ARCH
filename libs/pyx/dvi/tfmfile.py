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

class char_info_word:

    def __init__(self, word):
        self.width_index  = int((word & 0xFF000000) >> 24) #make sign-safe
        self.height_index = (word & 0x00F00000) >> 20
        self.depth_index  = (word & 0x000F0000) >> 16
        self.italic_index = (word & 0x0000FC00) >> 10
        self.tag          = (word & 0x00000300) >> 8
        self.remainder    = (word & 0x000000FF)


class TFMfile:

    def __init__(self, file, debug=0):
        with reader.bytesreader(file.read()) as file:

            #
            # read pre header
            #

            self.lf = file.readint16()
            self.lh = file.readint16()
            self.bc = file.readint16()
            self.ec = file.readint16()
            self.nw = file.readint16()
            self.nh = file.readint16()
            self.nd = file.readint16()
            self.ni = file.readint16()
            self.nl = file.readint16()
            self.nk = file.readint16()
            self.ne = file.readint16()
            self.np = file.readint16()

            if not (self.bc-1 <= self.ec <= 255 and
                    self.ne <= 256 and
                    self.lf == 6+self.lh+(self.ec-self.bc+1)+self.nw+self.nh+self.nd
                    +self.ni+self.nl+self.nk+self.ne+self.np):
                raise RuntimeError("error in TFM pre-header")

            if debug:
                print("lh=%d" % self.lh)

            #
            # read header
            #

            self.checksum = file.readint32()
            self.designsize = file.readint32()
            assert self.designsize > 0, "invald design size"
            if self.lh > 2:
                assert self.lh > 11, "inconsistency in TFM file: incomplete field"
                self.charcoding = file.readstring(40)
            else:
                self.charcoding = None

            if self.lh > 12:
                assert self.lh > 16, "inconsistency in TFM file: incomplete field"
                self.fontfamily = file.readstring(20)
            else:
                self.fontfamily = None

            if debug:
                print("(FAMILY %s)" % self.fontfamily)
                print("(CODINGSCHEME %s)" % self.charcoding)
                print("(DESINGSIZE R %f)" % (16.0*self.designsize/16777216))

            if self.lh > 17:
                self.sevenbitsave = file.readuchar()
                # ignore the following two bytes
                file.readint16()
                facechar = file.readuchar()
                # decode ugly face specification into the Knuth suggested string
                if facechar < 18:
                    if facechar >= 12:
                        self.face = "E"
                        facechar -= 12
                    elif facechar >= 6:
                        self.face = "C"
                        facechar -= 6
                    else:
                        self.face = "R"

                    if facechar >= 4:
                        self.face = "L" + self.face
                        facechar -= 4
                    elif facechar >= 2:
                        self.face = "B" + self.face
                        facechar -= 2
                    else:
                        self.face = "M" + self.face

                    if facechar == 1:
                        self.face = self.face[0] + "I" + self.face[1]
                    else:
                        self.face = self.face[0] + "R" + self.face[1]

                else:
                    self.face = None
            else:
                self.sevenbitsave = self.face = None

            if self.lh > 18:
                # just ignore the rest
                print(file.read((self.lh-18)*4))

            #
            # read char_info
            #

            self.char_info = [None]*(self.ec+1)
            for charcode in range(self.bc, self.ec+1):
                self.char_info[charcode] = char_info_word(file.readint32())
                if self.char_info[charcode].width_index == 0:
                    # disable character if width_index is zero
                    self.char_info[charcode] = None

            #
            # read widths
            #

            self.width = [None for width_index in range(self.nw)]
            for width_index in range(self.nw):
                self.width[width_index] = file.readint32()

            #
            # read heights
            #

            self.height = [None for height_index in range(self.nh)]
            for height_index in range(self.nh):
                self.height[height_index] = file.readint32()

            #
            # read depths
            #

            self.depth = [None for depth_index in range(self.nd)]
            for depth_index in range(self.nd):
                self.depth[depth_index] = file.readint32()

            #
            # read italic
            #

            self.italic = [None for italic_index in range(self.ni)]
            for italic_index in range(self.ni):
                self.italic[italic_index] = file.readint32()

            #
            # read lig_kern
            #

            # XXX decode to lig_kern_command

            self.lig_kern = [None for lig_kern_index in range(self.nl)]
            for lig_kern_index in range(self.nl):
                self.lig_kern[lig_kern_index] = file.readint32()

            #
            # read kern
            #

            self.kern = [None for kern_index in range(self.nk)]
            for kern_index in range(self.nk):
                self.kern[kern_index] = file.readint32()

            #
            # read exten
            #

            # XXX decode to extensible_recipe

            self.exten = [None for exten_index in range(self.ne)]
            for exten_index in range(self.ne):
                self.exten[exten_index] = file.readint32()

            #
            # read param
            #

            # XXX decode

            self.param = [None for param_index in range(self.np)]
            for param_index in range(self.np):
                self.param[param_index] = file.readint32()
