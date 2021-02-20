# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2002-2005 Jörg Lehmann <joerg@pyx-project.org>
# Copyright (C) 2002-2006 André Wobst <wobsta@pyx-project.org>
# Copyright (C) 2006 Michael Schindler <m-schindler@users.sourceforge.net>
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

"""Python graphics package

PyX is a Python package for the creation of PostScript and PDF files. It
combines an abstraction of the PostScript drawing model with a TeX/LaTeX
interface. Complex tasks like 2d and 3d plots in publication-ready quality are
built out of these primitives.
"""

from . import version
__version__ = version.version

import sys
if sys.hexversion < 0x03020000:
    sys.stderr.write("PyX {} requires Python 3.2 or higher.\n".format(__version__))
    sys.exit()
del sys

__all__ = ["attr", "box", "bitmap", "canvas", "color", "connector", "deco", "deformer", "document",
           "epsfile", "svgfile", "graph", "mesh", "metapost", "path", "pattern", "pdfextra", "style", "trafo", "text", "unit"]

import importlib

# automatically import main modules into pyx namespace
for module in __all__:
    importlib.import_module('.' + module, package='pyx')

def pyxinfo():
    """Make PyX a little verbose (for information or debugging)

    This function enables info level on the ``"pyx"`` logger. It also adds some
    general information about the Python interpreter, the PyX installation, and
    the PyX configuration to the logger.

    """
    import logging, os, sys
    from . import config
    logging.lastResort.setLevel(logging.INFO)
    logger = logging.getLogger("pyx")
    logger.setLevel(logging.INFO)
    logger.info("Platform name is: {}".format(os.name))
    logger.info("Python executable: {}".format(sys.executable))
    logger.info("Python version: %s", sys.version)
    logger.info("PyX comes from: %s", __file__)
    logger.info("PyX version: %s", __version__)
    logger.info("pyxrc %s %s %s", "is" if os.path.isfile(config.user_pyxrc) else "would be" ,"loaded from:", config.user_pyxrc)
    logger.info("pykpathsea: %s", "available" if config.has_pykpathsea else "not available")
    logger.info("file locators in use: %s", ", ".join(method.__class__.__name__ for method in config.methods))

__all__.append("__version__")
__all__.append("pyxinfo")
