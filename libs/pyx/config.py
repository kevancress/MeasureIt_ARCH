# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2003-2011 Jörg Lehmann <joerg@pyx-project.org>
# Copyright (C) 2003-2011 André Wobst <wobsta@pyx-project.org>
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

import configparser, io, logging, os, pkgutil, subprocess, shutil

logger = logging.getLogger("pyx")
logger_execute = logging.getLogger("pyx.execute")
logger_filelocator = logging.getLogger("pyx.filelocator")

builtinopen = open

try:
    import pykpathsea as pykpathsea_module
    has_pykpathsea = True
except ImportError:
    has_pykpathsea = False


# Locators implement an open method which returns a list of functions
# by searching for a file according to a specific rule. Each of the functions
# returned can be called (multiple times) and return an open file. The
# opening of the file might fail with a IOError which indicates, that the
# file could not be found at the given location.
# formats is a list of kpsewhich formats to be used for searching.

class format:
    def __init__(self, name, extensions):
        self.name = name
        self.extensions = extensions

format.tfm = format("tfm", [".tfm"])
format.afm = format("afm", [".afm"])
format.fontmap = format("map", [".map"])
format.pict = format("graphic/figure", [".eps", ".epsi"])
format.tex_ps_header = format("PostScript header", ["", ".pro"])                    # contains also: enc files
format.type1 = format("type1 fonts", [".pfa", ".pfb"])
format.vf = format("vf", [".vf"])
format.dvips_config = format("dvips config", [])
format.ttf = format("truetype fonts", [".ttf", ".ttc", ".TTF", ".TTC", ".dfont"])
format.t42 = format("type42 fonts", [".t42", ".T42"])
format.otf = format("opentype fonts", [".otf"])
format.pyx = format("PyX", [])

locator_classes = {}

def full_filenames(filename, formats):
    # If filename ends with one of the extensions, return the filename.
    for format in formats:
        for extension in format.extensions:
            if filename.endswith(extension):
                yield filename
                return

    # Otherwise return all possible combinations of filename and extensions.
    # When no extention is defined, the unchanged filename is included.
    result = []
    for format in formats:
        if format.extensions:
            for extension in format.extensions:
                yield filename+extension
        else:
            yield filename


class local:
    """locates files in the current directory"""

    def openers(self, filename, formats):
        return [lambda: builtinopen(full_filename, "rb") for full_filename in full_filenames(filename, formats)]

locator_classes["local"] = local


class internal:
    """locates files within the PyX data tree"""

    def openers(self, filename, formats):
        for full_filename in full_filenames(filename, formats):
            dir = os.path.splitext(full_filename)[1][1:]
            try:
                data = pkgutil.get_data("pyx", "data/%s/%s" % (dir, full_filename))
            except IOError:
                pass
            else:
                if data:
                    return [lambda: io.BytesIO(data)]
        return []

locator_classes["internal"] = internal


class recursivedir:
    """locates files by searching recursively in a list of directories"""

    def __init__(self):
        self.dirs = getlist("filelocator", "recursivedir")
        self.path_cache = {}

    def openers(self, filename, formats):
        filenames = list(full_filenames(filename, formats))
        for filename in filenames:
            if filename in self.path_cache:
                return [lambda: builtinopen(self.path_cache[filename], "rb")]
        found = None
        while self.dirs:
            dir = self.dirs.pop(0)
            for item in os.listdir(dir):
                full_item = os.path.join(dir, item)
                if os.path.isdir(full_item):
                    self.dirs.insert(0, full_item)
                else:
                    self.path_cache[item] = full_item
                    if item in filenames:
                        found = item
            if found:
                return [lambda: builtinopen(self.path_cache[found], "rb")]
        return []

locator_classes["recursivedir"] = recursivedir


class ls_R:
    """locates files by searching a list of ls-R files"""

    def __init__(self):
        self.path_cache = {}

    def openers(self, filename, formats):
        if not self.path_cache:
            for lsr in getlist("filelocator", "ls-R"):
                base_dir = os.path.dirname(lsr)
                first = True
                with builtinopen(lsr, "r", encoding="ascii", errors="surrogateescape") as lsrfile:
                    for line in lsrfile:
                        line = line.rstrip()
                        if first and line.startswith("%"):
                            continue
                        first = False
                        if line.endswith(":"):
                            dir = os.path.join(base_dir, line[:-1])
                            # TODO: remove this line from the path_cache
                        elif line and line not in self.path_cache:
                            self.path_cache[line] = os.path.join(dir, line)
        for filename in full_filenames(filename, formats):
            if filename in self.path_cache:
                return [lambda: builtinopen(self.path_cache[filename], "rb")]
        return []

locator_classes["ls-R"] = ls_R


class pykpathsea:
    """locate files by pykpathsea (a C extension module wrapping libkpathsea)"""

    def openers(self, filename, formats):
        if not has_pykpathsea:
            return []
        for format in formats:
            full_filename = pykpathsea_module.find_file(filename, format.name)
            if full_filename:
                break
        else:
            return []
        def _opener():
            try:
                return builtinopen(full_filename, "rb")
            except IOError:
                logger.warning("'%s' should be available at '%s' according to libkpathsea, "
                            "but the file is not available at this location; "
                            "update your kpsewhich database" % (filename, full_filename))
        return [_opener]

locator_classes["pykpathsea"] = pykpathsea


# class libkpathsea:
#     """locate files by libkpathsea using ctypes"""
# 
#     def openers(self, filename, formats):
#         raise NotImplemented
# 
# locator_classes["libpathsea"] = libkpathsea

def Popen(cmd, *args, **kwargs):
    try:
        cmd + ""
    except:
        pass
    else:
        raise ValueError("pyx.config.Popen must not be used with a string cmd")
    info = "PyX executes {} with args {}".format(cmd[0], cmd[1:])
    try:
        shutil.which
    except:
        pass
    else:
        info += " located at {}".format(shutil.which(cmd[0]))
    logger_execute.info(info)
    return subprocess.Popen(cmd, *args, **kwargs)

PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT


def fix_cygwin(full_filename):
    # detect cygwin result on windows python
    if os.name == "nt" and full_filename.startswith("/"):
        with Popen(['cygpath', '-w', full_filename], stdout=subprocess.PIPE).stdout as output:
            return io.TextIOWrapper(output, encoding="ascii", errors="surrogateescape").readline().rstrip()
    return full_filename


class kpsewhich:
    """locate files using the kpsewhich executable"""

    def __init__(self):
        self.kpsewhich = get("filelocator", "kpsewhich", "kpsewhich")

    def openers(self, filename, formats):
        full_filename = None
        for format in formats:
            try:
                with Popen([self.kpsewhich, '--format', format.name, filename], stdout=subprocess.PIPE) as process:
                    with io.TextIOWrapper(process.stdout, encoding="ascii", errors="surrogateescape") as text_output:
                        full_filename = text_output.readline().rstrip()
            except OSError:
                return []
            if full_filename:
                break
        else:
            return []

        full_filename = fix_cygwin(full_filename)

        def _opener():
            try:
                return builtinopen(full_filename, "rb")
            except IOError:
                logger.warning("'%s' should be available at '%s' according to kpsewhich, "
                            "but the file is not available at this location; "
                            "update your kpsewhich database" % (filename, full_filename))
        return [_opener]

locator_classes["kpsewhich"] = kpsewhich


class locate:
    """locate files using a locate executable"""

    def __init__(self):
        self.locate = get("filelocator", "locate", "locate")

    def openers(self, filename, formats):
        full_filename = None
        for extension in extensions:
            with Popen([self.locate, filename+extension], stdout=subprocess.PIPE).stdout as output:
                with io.TextIOWrapper(output, encoding="ascii", errors="surrogateescape") as text_output:
                    for line in text_output:
                        line = line.rstrip()
                        if os.path.basename(line) == filename+extension:
                            full_filename = line
                            break
            if full_filename:
                break
        else:
            return []

        full_filename = fix_cygwin(full_filename)

        def _opener():
            try:
                return builtinopen(full_filename, "rb")
            except IOError:
                logger.warning("'%s' should be available at '%s' according to the locate, "
                            "but the file is not available at this location; "
                            "update your locate database" % (filename+extension, full_filename))
        return [_opener]

locator_classes["locate"] = locate



class _marker: pass

config = configparser.ConfigParser()
config.read_string(locator_classes["internal"]().openers("pyxrc", [format.pyx])[0]().read().decode("utf-8"), source="(internal pyxrc)")
if os.name == "nt":
    user_pyxrc = os.path.join(os.environ['APPDATA'], "pyxrc")
else:
    user_pyxrc = os.path.expanduser("~/.pyxrc")
config.read(user_pyxrc, encoding="utf-8")
if os.environ.get('PYXRC'):
    config.read(os.environ['PYXRC'], encoding="utf-8")

def get(section, option, default=_marker):
    if default is _marker:
        return config.get(section, option)
    else:
        try:
            return config.get(section, option)
        except configparser.Error:
            return default

def getint(section, option, default=_marker):
    if default is _marker:
        return config.getint(section, option)
    else:
        try:
            return config.getint(section, option)
        except configparser.Error:
            return default

def getfloat(section, option, default=_marker):
    if default is _marker:
        return config.getfloat(section, option)
    else:
        try:
            return config.getfloat(section, option)
        except configparser.Error:
            return default

def getboolean(section, option, default=_marker):
    if default is _marker:
        return config.getboolean(section, option)
    else:
        try:
            return config.getboolean(section, option)
        except configparser.Error:
            return default

def getlist(section, option, default=_marker):
    if default is _marker:
        l = config.get(section, option).split()
    else:
        try:
            l = config.get(section, option).split()
        except configparser.Error:
            return default
    if space:
        l = [item.replace(space, " ") for item in l]
    return l


space = get("general", "space", "SPACE")
methods = [locator_classes[method]()
           for method in getlist("filelocator", "methods", ["local", "internal", "pykpathsea", "kpsewhich"])]
opener_cache = {}


def open(filename, formats, ascii=False):
    """returns an open file searched according the list of formats"""

    names = tuple([format.name for format in formats])
    if (filename, names) in opener_cache:
        file = opener_cache[(filename, names)]()
    else:
        for method in methods:
            openers = method.openers(filename, formats)
            for opener in openers:
                try:
                    file = opener()
                except EnvironmentError:
                    file = None
                if file:
                    info = "PyX filelocator found {} by method {}".format(filename, method.__class__.__name__)
                    if hasattr(file, "name"):
                        info += " at {}".format(file.name)
                    logger_filelocator.info(info)
                    opener_cache[(filename, names)] = opener
                    break
            # break two loops here
            else:
                continue
            break
        else:
            logger_filelocator.info("PyX filelocator failed to find {} of formats {}".format(filename, names))
            raise IOError("Could not locate the file '%s'." % filename)
    if ascii:
        return io.TextIOWrapper(file, encoding="ascii", errors="surrogateescape")
    else:
        return file


