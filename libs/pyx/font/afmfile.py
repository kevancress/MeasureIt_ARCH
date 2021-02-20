# -*- encoding: utf-8 -*-
#
#
# Copyright (C) 2006-2011 Jörg Lehmann <joerg@pyx-project.org>
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

import string
from . import metric

unicodestring = {" ": "space",
                 "!": "exclam",
                 "\"": "quotedbl",
                 "#": "numbersign",
                 "$": "dollar",
                 "%": "percent",
                 "&": "ampersand",
                 "'": "quotesingle",
                 "(": "parenleft",
                 ")": "parenright",
                 "*": "asterisk",
                 "+": "plus",
                 ",": "comma",
                 "-": "hyphen",
                 ".": "period",
                 "/": "slash",
                 "0": "zero",
                 "1": "one",
                 "2": "two",
                 "3": "three",
                 "4": "four",
                 "5": "five",
                 "6": "six",
                 "7": "seven",
                 "8": "eight",
                 "9": "nine",
                 ":": "colon",
                 ";": "semicolon",
                 "<": "less",
                 "=": "equal",
                 ">": "greater",
                 "?": "question",
                 "@": "at",
                 "A": "A",
                 "B": "B",
                 "C": "C",
                 "D": "D",
                 "E": "E",
                 "F": "F",
                 "G": "G",
                 "H": "H",
                 "I": "I",
                 "J": "J",
                 "K": "K",
                 "L": "L",
                 "M": "M",
                 "N": "N",
                 "O": "O",
                 "P": "P",
                 "Q": "Q",
                 "R": "R",
                 "S": "S",
                 "T": "T",
                 "U": "U",
                 "V": "V",
                 "W": "W",
                 "X": "X",
                 "Y": "Y",
                 "Z": "Z",
                 "[": "bracketleft",
                 "\\": "backslash",
                 "]": "bracketright",
                 "^": "asciicircum",
                 "_": "underscore",
                 "`": "grave",
                 "a": "a",
                 "b": "b",
                 "c": "c",
                 "d": "d",
                 "e": "e",
                 "f": "f",
                 "g": "g",
                 "h": "h",
                 "i": "i",
                 "j": "j",
                 "k": "k",
                 "l": "l",
                 "m": "m",
                 "n": "n",
                 "o": "o",
                 "p": "p",
                 "q": "q",
                 "r": "r",
                 "s": "s",
                 "t": "t",
                 "u": "u",
                 "v": "v",
                 "w": "w",
                 "x": "x",
                 "y": "y",
                 "z": "z",
                 "{": "braceleft",
                 "|": "bar",
                 "}": "braceright",
                 "~": "asciitilde",
                 "\xa0": "space",
                 "\xa1": "exclamdown",
                 "\xa2": "cent",
                 "\xa3": "sterling",
                 "\xa4": "currency",
                 "\xa5": "yen",
                 "\xa6": "brokenbar",
                 "\xa7": "section",
                 "\xa8": "dieresis",
                 "\xa9": "copyright",
                 "\xaa": "ordfeminine",
                 "\xab": "guillemotleft",
                 "\xac": "logicalnot",
                 "\xad": "hyphen",
                 "\xae": "registered",
                 "\xaf": "macron",
                 "\xb0": "degree",
                 "\xb1": "plusminus",
                 "\xb4": "acute",
                 "\xb6": "paragraph",
                 "\xb7": "periodcentered",
                 "\xb8": "cedilla",
                 "\xba": "ordmasculine",
                 "\xbb": "guillemotright",
                 "\xbc": "onequarter",
                 "\xbd": "onehalf",
                 "\xbe": "threequarters",
                 "\xbf": "questiondown",
                 "\xc0": "Agrave",
                 "\xc1": "Aacute",
                 "\xc2": "Acircumflex",
                 "\xc3": "Atilde",
                 "\xc4": "Adieresis",
                 "\xc5": "Aring",
                 "\xc6": "AE",
                 "\xc7": "Ccedilla",
                 "\xc8": "Egrave",
                 "\xc9": "Eacute",
                 "\xca": "Ecircumflex",
                 "\xcb": "Edieresis",
                 "\xcc": "Igrave",
                 "\xcd": "Iacute",
                 "\xce": "Icircumflex",
                 "\xcf": "Idieresis",
                 "\xd0": "Eth",
                 "\xd1": "Ntilde",
                 "\xd2": "Ograve",
                 "\xd3": "Oacute",
                 "\xd4": "Ocircumflex",
                 "\xd5": "Otilde",
                 "\xd6": "Odieresis",
                 "\xd7": "multiply",
                 "\xd8": "Oslash",
                 "\xd9": "Ugrave",
                 "\xda": "Uacute",
                 "\xdb": "Ucircumflex",
                 "\xdc": "Udieresis",
                 "\xdd": "Yacute",
                 "\xde": "Thorn",
                 "\xdf": "germandbls",
                 "\xe0": "agrave",
                 "\xe1": "aacute",
                 "\xe2": "acircumflex",
                 "\xe3": "atilde",
                 "\xe4": "adieresis",
                 "\xe5": "aring",
                 "\xe6": "ae",
                 "\xe7": "ccedilla",
                 "\xe8": "egrave",
                 "\xe9": "eacute",
                 "\xea": "ecircumflex",
                 "\xeb": "edieresis",
                 "\xec": "igrave",
                 "\xed": "iacute",
                 "\xee": "icircumflex",
                 "\xef": "idieresis",
                 "\xf0": "eth",
                 "\xf1": "ntilde",
                 "\xf2": "ograve",
                 "\xf3": "oacute",
                 "\xf4": "ocircumflex",
                 "\xf5": "otilde",
                 "\xf6": "odieresis",
                 "\xf7": "divide",
                 "\xf8": "oslash",
                 "\xf9": "ugrave",
                 "\xfa": "uacute",
                 "\xfb": "ucircumflex",
                 "\xfc": "udieresis",
                 "\xfd": "yacute",
                 "\xfe": "thorn",
                 "\xff": "ydieresis",
                 "\u0100": "Amacron",
                 "\u0101": "amacron",
                 "\u0102": "Abreve",
                 "\u0103": "abreve",
                 "\u0104": "Aogonek",
                 "\u0105": "aogonek",
                 "\u0106": "Cacute",
                 "\u0107": "cacute",
                 "\u0108": "Ccircumflex",
                 "\u0109": "ccircumflex",
                 "\u010a": "Cdotaccent",
                 "\u010b": "cdotaccent",
                 "\u010c": "Ccaron",
                 "\u010d": "ccaron",
                 "\u010e": "Dcaron",
                 "\u010f": "dcaron",
                 "\u0110": "Dcroat",
                 "\u0111": "dcroat",
                 "\u0112": "Emacron",
                 "\u0113": "emacron",
                 "\u0114": "Ebreve",
                 "\u0115": "ebreve",
                 "\u0116": "Edotaccent",
                 "\u0117": "edotaccent",
                 "\u0118": "Eogonek",
                 "\u0119": "eogonek",
                 "\u011a": "Ecaron",
                 "\u011b": "ecaron",
                 "\u011c": "Gcircumflex",
                 "\u011d": "gcircumflex",
                 "\u011e": "Gbreve",
                 "\u011f": "gbreve",
                 "\u0120": "Gdotaccent",
                 "\u0121": "gdotaccent",
                 "\u0122": "Gcommaaccent",
                 "\u0123": "gcommaaccent",
                 "\u0124": "Hcircumflex",
                 "\u0125": "hcircumflex",
                 "\u0126": "Hbar",
                 "\u0127": "hbar",
                 "\u0128": "Itilde",
                 "\u0129": "itilde",
                 "\u012a": "Imacron",
                 "\u012b": "imacron",
                 "\u012c": "Ibreve",
                 "\u012d": "ibreve",
                 "\u012e": "Iogonek",
                 "\u012f": "iogonek",
                 "\u0130": "Idotaccent",
                 "\u0131": "dotlessi",
                 "\u0132": "IJ",
                 "\u0133": "ij",
                 "\u0134": "Jcircumflex",
                 "\u0135": "jcircumflex",
                 "\u0136": "Kcommaaccent",
                 "\u0137": "kcommaaccent",
                 "\u0138": "kgreenlandic",
                 "\u0139": "Lacute",
                 "\u013a": "lacute",
                 "\u013b": "Lcommaaccent",
                 "\u013c": "lcommaaccent",
                 "\u013d": "Lcaron",
                 "\u013e": "lcaron",
                 "\u013f": "Ldot",
                 "\u0140": "ldot",
                 "\u0141": "Lslash",
                 "\u0142": "lslash",
                 "\u0143": "Nacute",
                 "\u0144": "nacute",
                 "\u0145": "Ncommaaccent",
                 "\u0146": "ncommaaccent",
                 "\u0147": "Ncaron",
                 "\u0148": "ncaron",
                 "\u0149": "napostrophe",
                 "\u014a": "Eng",
                 "\u014b": "eng",
                 "\u014c": "Omacron",
                 "\u014d": "omacron",
                 "\u014e": "Obreve",
                 "\u014f": "obreve",
                 "\u0150": "Ohungarumlaut",
                 "\u0151": "ohungarumlaut",
                 "\u0152": "OE",
                 "\u0153": "oe",
                 "\u0154": "Racute",
                 "\u0155": "racute",
                 "\u0156": "Rcommaaccent",
                 "\u0157": "rcommaaccent",
                 "\u0158": "Rcaron",
                 "\u0159": "rcaron",
                 "\u015a": "Sacute",
                 "\u015b": "sacute",
                 "\u015c": "Scircumflex",
                 "\u015d": "scircumflex",
                 "\u015e": "Scedilla",
                 "\u015f": "scedilla",
                 "\u0160": "Scaron",
                 "\u0161": "scaron",
                 "\u0162": "Tcommaaccent",
                 "\u0163": "tcommaaccent",
                 "\u0164": "Tcaron",
                 "\u0165": "tcaron",
                 "\u0166": "Tbar",
                 "\u0167": "tbar",
                 "\u0168": "Utilde",
                 "\u0169": "utilde",
                 "\u016a": "Umacron",
                 "\u016b": "umacron",
                 "\u016c": "Ubreve",
                 "\u016d": "ubreve",
                 "\u016e": "Uring",
                 "\u016f": "uring",
                 "\u0170": "Uhungarumlaut",
                 "\u0171": "uhungarumlaut",
                 "\u0172": "Uogonek",
                 "\u0173": "uogonek",
                 "\u0174": "Wcircumflex",
                 "\u0175": "wcircumflex",
                 "\u0176": "Ycircumflex",
                 "\u0177": "ycircumflex",
                 "\u0178": "Ydieresis",
                 "\u0179": "Zacute",
                 "\u017a": "zacute",
                 "\u017b": "Zdotaccent",
                 "\u017c": "zdotaccent",
                 "\u017d": "Zcaron",
                 "\u017e": "zcaron",
                 "\u017f": "longs",
                 "\u0192": "florin",
                 "\u01a0": "Ohorn",
                 "\u01a1": "ohorn",
                 "\u01af": "Uhorn",
                 "\u01b0": "uhorn",
                 "\u01e6": "Gcaron",
                 "\u01e7": "gcaron",
                 "\u01fa": "Aringacute",
                 "\u01fb": "aringacute",
                 "\u01fc": "AEacute",
                 "\u01fd": "aeacute",
                 "\u01fe": "Oslashacute",
                 "\u01ff": "oslashacute",
                 "\u0218": "Scommaaccent",
                 "\u0219": "scommaaccent",
                 "\u02bc": "afii57929",
                 "\u02bd": "afii64937",
                 "\u02c6": "circumflex",
                 "\u02c7": "caron",
                 "\u02c9": "macron",
                 "\u02d8": "breve",
                 "\u02d9": "dotaccent",
                 "\u02da": "ring",
                 "\u02db": "ogonek",
                 "\u02dc": "tilde",
                 "\u02dd": "hungarumlaut",
                 "\u0300": "gravecomb",
                 "\u0301": "acutecomb",
                 "\u0303": "tildecomb",
                 "\u0309": "hookabovecomb",
                 "\u0323": "dotbelowcomb",
                 "\u0384": "tonos",
                 "\u0385": "dieresistonos",
                 "\u0386": "Alphatonos",
                 "\u0387": "anoteleia",
                 "\u0388": "Epsilontonos",
                 "\u0389": "Etatonos",
                 "\u038a": "Iotatonos",
                 "\u038c": "Omicrontonos",
                 "\u038e": "Upsilontonos",
                 "\u038f": "Omegatonos",
                 "\u0390": "iotadieresistonos",
                 "\u0391": "Alpha",
                 "\u0392": "Beta",
                 "\u0393": "Gamma",
                 "\u0394": "Delta",
                 "\u0395": "Epsilon",
                 "\u0396": "Zeta",
                 "\u0397": "Eta",
                 "\u0398": "Theta",
                 "\u0399": "Iota",
                 "\u039a": "Kappa",
                 "\u039b": "Lambda",
                 "\u039c": "Mu",
                 "\u039d": "Nu",
                 "\u039e": "Xi",
                 "\u039f": "Omicron",
                 "\u03a0": "Pi",
                 "\u03a1": "Rho",
                 "\u03a3": "Sigma",
                 "\u03a4": "Tau",
                 "\u03a5": "Upsilon",
                 "\u03a6": "Phi",
                 "\u03a7": "Chi",
                 "\u03a8": "Psi",
                 "\u03a9": "Omega",
                 "\u03aa": "Iotadieresis",
                 "\u03ab": "Upsilondieresis",
                 "\u03ac": "alphatonos",
                 "\u03ad": "epsilontonos",
                 "\u03ae": "etatonos",
                 "\u03af": "iotatonos",
                 "\u03b0": "upsilondieresistonos",
                 "\u03b1": "alpha",
                 "\u03b2": "beta",
                 "\u03b3": "gamma",
                 "\u03b4": "delta",
                 "\u03b5": "epsilon",
                 "\u03b6": "zeta",
                 "\u03b7": "eta",
                 "\u03b8": "theta",
                 "\u03b9": "iota",
                 "\u03ba": "kappa",
                 "\u03bb": "lambda",
                 "\u03bc": "mu",
                 "\u03bd": "nu",
                 "\u03be": "xi",
                 "\u03bf": "omicron",
                 "\u03c0": "pi",
                 "\u03c1": "rho",
                 "\u03c2": "sigma1",
                 "\u03c3": "sigma",
                 "\u03c4": "tau",
                 "\u03c5": "upsilon",
                 "\u03c6": "phi",
                 "\u03c7": "chi",
                 "\u03c8": "psi",
                 "\u03c9": "omega",
                 "\u03ca": "iotadieresis",
                 "\u03cb": "upsilondieresis",
                 "\u03cc": "omicrontonos",
                 "\u03cd": "upsilontonos",
                 "\u03ce": "omegatonos",
                 "\u03d1": "theta1",
                 "\u03d2": "Upsilon1",
                 "\u03d5": "phi1",
                 "\u03d6": "omega1",
                 "\u0401": "afii10023",
                 "\u0402": "afii10051",
                 "\u0403": "afii10052",
                 "\u0404": "afii10053",
                 "\u0405": "afii10054",
                 "\u0406": "afii10055",
                 "\u0407": "afii10056",
                 "\u0408": "afii10057",
                 "\u0409": "afii10058",
                 "\u040a": "afii10059",
                 "\u040b": "afii10060",
                 "\u040c": "afii10061",
                 "\u040e": "afii10062",
                 "\u040f": "afii10145",
                 "\u0410": "afii10017",
                 "\u0411": "afii10018",
                 "\u0412": "afii10019",
                 "\u0413": "afii10020",
                 "\u0414": "afii10021",
                 "\u0415": "afii10022",
                 "\u0416": "afii10024",
                 "\u0417": "afii10025",
                 "\u0418": "afii10026",
                 "\u0419": "afii10027",
                 "\u041a": "afii10028",
                 "\u041b": "afii10029",
                 "\u041c": "afii10030",
                 "\u041d": "afii10031",
                 "\u041e": "afii10032",
                 "\u041f": "afii10033",
                 "\u0420": "afii10034",
                 "\u0421": "afii10035",
                 "\u0422": "afii10036",
                 "\u0423": "afii10037",
                 "\u0424": "afii10038",
                 "\u0425": "afii10039",
                 "\u0426": "afii10040",
                 "\u0427": "afii10041",
                 "\u0428": "afii10042",
                 "\u0429": "afii10043",
                 "\u042a": "afii10044",
                 "\u042b": "afii10045",
                 "\u042c": "afii10046",
                 "\u042d": "afii10047",
                 "\u042e": "afii10048",
                 "\u042f": "afii10049",
                 "\u0430": "afii10065",
                 "\u0431": "afii10066",
                 "\u0432": "afii10067",
                 "\u0433": "afii10068",
                 "\u0434": "afii10069",
                 "\u0435": "afii10070",
                 "\u0436": "afii10072",
                 "\u0437": "afii10073",
                 "\u0438": "afii10074",
                 "\u0439": "afii10075",
                 "\u043a": "afii10076",
                 "\u043b": "afii10077",
                 "\u043c": "afii10078",
                 "\u043d": "afii10079",
                 "\u043e": "afii10080",
                 "\u043f": "afii10081",
                 "\u0440": "afii10082",
                 "\u0441": "afii10083",
                 "\u0442": "afii10084",
                 "\u0443": "afii10085",
                 "\u0444": "afii10086",
                 "\u0445": "afii10087",
                 "\u0446": "afii10088",
                 "\u0447": "afii10089",
                 "\u0448": "afii10090",
                 "\u0449": "afii10091",
                 "\u044a": "afii10092",
                 "\u044b": "afii10093",
                 "\u044c": "afii10094",
                 "\u044d": "afii10095",
                 "\u044e": "afii10096",
                 "\u044f": "afii10097",
                 "\u0451": "afii10071",
                 "\u0452": "afii10099",
                 "\u0453": "afii10100",
                 "\u0454": "afii10101",
                 "\u0455": "afii10102",
                 "\u0456": "afii10103",
                 "\u0457": "afii10104",
                 "\u0458": "afii10105",
                 "\u0459": "afii10106",
                 "\u045a": "afii10107",
                 "\u045b": "afii10108",
                 "\u045c": "afii10109",
                 "\u045e": "afii10110",
                 "\u045f": "afii10193",
                 "\u0462": "afii10146",
                 "\u0463": "afii10194",
                 "\u0472": "afii10147",
                 "\u0473": "afii10195",
                 "\u0474": "afii10148",
                 "\u0475": "afii10196",
                 "\u0490": "afii10050",
                 "\u0491": "afii10098",
                 "\u04d9": "afii10846",
                 "\u05b0": "afii57799",
                 "\u05b1": "afii57801",
                 "\u05b2": "afii57800",
                 "\u05b3": "afii57802",
                 "\u05b4": "afii57793",
                 "\u05b5": "afii57794",
                 "\u05b6": "afii57795",
                 "\u05b7": "afii57798",
                 "\u05b8": "afii57797",
                 "\u05b9": "afii57806",
                 "\u05bb": "afii57796",
                 "\u05bc": "afii57807",
                 "\u05bd": "afii57839",
                 "\u05be": "afii57645",
                 "\u05bf": "afii57841",
                 "\u05c0": "afii57842",
                 "\u05c1": "afii57804",
                 "\u05c2": "afii57803",
                 "\u05c3": "afii57658",
                 "\u05d0": "afii57664",
                 "\u05d1": "afii57665",
                 "\u05d2": "afii57666",
                 "\u05d3": "afii57667",
                 "\u05d4": "afii57668",
                 "\u05d5": "afii57669",
                 "\u05d6": "afii57670",
                 "\u05d7": "afii57671",
                 "\u05d8": "afii57672",
                 "\u05d9": "afii57673",
                 "\u05da": "afii57674",
                 "\u05db": "afii57675",
                 "\u05dc": "afii57676",
                 "\u05dd": "afii57677",
                 "\u05de": "afii57678",
                 "\u05df": "afii57679",
                 "\u05e0": "afii57680",
                 "\u05e1": "afii57681",
                 "\u05e2": "afii57682",
                 "\u05e3": "afii57683",
                 "\u05e4": "afii57684",
                 "\u05e5": "afii57685",
                 "\u05e6": "afii57686",
                 "\u05e7": "afii57687",
                 "\u05e8": "afii57688",
                 "\u05e9": "afii57689",
                 "\u05ea": "afii57690",
                 "\u05f0": "afii57716",
                 "\u05f1": "afii57717",
                 "\u05f2": "afii57718",
                 "\u060c": "afii57388",
                 "\u061b": "afii57403",
                 "\u061f": "afii57407",
                 "\u0621": "afii57409",
                 "\u0622": "afii57410",
                 "\u0623": "afii57411",
                 "\u0624": "afii57412",
                 "\u0625": "afii57413",
                 "\u0626": "afii57414",
                 "\u0627": "afii57415",
                 "\u0628": "afii57416",
                 "\u0629": "afii57417",
                 "\u062a": "afii57418",
                 "\u062b": "afii57419",
                 "\u062c": "afii57420",
                 "\u062d": "afii57421",
                 "\u062e": "afii57422",
                 "\u062f": "afii57423",
                 "\u0630": "afii57424",
                 "\u0631": "afii57425",
                 "\u0632": "afii57426",
                 "\u0633": "afii57427",
                 "\u0634": "afii57428",
                 "\u0635": "afii57429",
                 "\u0636": "afii57430",
                 "\u0637": "afii57431",
                 "\u0638": "afii57432",
                 "\u0639": "afii57433",
                 "\u063a": "afii57434",
                 "\u0640": "afii57440",
                 "\u0641": "afii57441",
                 "\u0642": "afii57442",
                 "\u0643": "afii57443",
                 "\u0644": "afii57444",
                 "\u0645": "afii57445",
                 "\u0646": "afii57446",
                 "\u0647": "afii57470",
                 "\u0648": "afii57448",
                 "\u0649": "afii57449",
                 "\u064a": "afii57450",
                 "\u064b": "afii57451",
                 "\u064c": "afii57452",
                 "\u064d": "afii57453",
                 "\u064e": "afii57454",
                 "\u064f": "afii57455",
                 "\u0650": "afii57456",
                 "\u0651": "afii57457",
                 "\u0652": "afii57458",
                 "\u0660": "afii57392",
                 "\u0661": "afii57393",
                 "\u0662": "afii57394",
                 "\u0663": "afii57395",
                 "\u0664": "afii57396",
                 "\u0665": "afii57397",
                 "\u0666": "afii57398",
                 "\u0667": "afii57399",
                 "\u0668": "afii57400",
                 "\u0669": "afii57401",
                 "\u066a": "afii57381",
                 "\u066d": "afii63167",
                 "\u0679": "afii57511",
                 "\u067e": "afii57506",
                 "\u0686": "afii57507",
                 "\u0688": "afii57512",
                 "\u0691": "afii57513",
                 "\u0698": "afii57508",
                 "\u06a4": "afii57505",
                 "\u06af": "afii57509",
                 "\u06ba": "afii57514",
                 "\u06d2": "afii57519",
                 "\u06d5": "afii57534",
                 "\u1e80": "Wgrave",
                 "\u1e81": "wgrave",
                 "\u1e82": "Wacute",
                 "\u1e83": "wacute",
                 "\u1e84": "Wdieresis",
                 "\u1e85": "wdieresis",
                 "\u1ef2": "Ygrave",
                 "\u1ef3": "ygrave",
                 "\u200c": "afii61664",
                 "\u200d": "afii301",
                 "\u200e": "afii299",
                 "\u200f": "afii300",
                 "\u2012": "figuredash",
                 "\u2013": "endash",
                 "\u2014": "emdash",
                 "\u2015": "afii00208",
                 "\u2017": "underscoredbl",
                 "\u2018": "quoteleft",
                 "\u2019": "quoteright",
                 "\u201a": "quotesinglbase",
                 "\u201b": "quotereversed",
                 "\u201c": "quotedblleft",
                 "\u201d": "quotedblright",
                 "\u201e": "quotedblbase",
                 "\u2020": "dagger",
                 "\u2021": "daggerdbl",
                 "\u2022": "bullet",
                 "\u2024": "onedotenleader",
                 "\u2025": "twodotenleader",
                 "\u2026": "ellipsis",
                 "\u202c": "afii61573",
                 "\u202d": "afii61574",
                 "\u202e": "afii61575",
                 "\u2030": "perthousand",
                 "\u2032": "minute",
                 "\u2033": "second",
                 "\u2039": "guilsinglleft",
                 "\u203a": "guilsinglright",
                 "\u203c": "exclamdbl",
                 "\u2044": "fraction",
                 "\u20a1": "colonmonetary",
                 "\u20a3": "franc",
                 "\u20a4": "lira",
                 "\u20a7": "peseta",
                 "\u20aa": "afii57636",
                 "\u20ab": "dong",
                 "\u20ac": "Euro",
                 "\u2105": "afii61248",
                 "\u2111": "Ifraktur",
                 "\u2113": "afii61289",
                 "\u2116": "afii61352",
                 "\u2118": "weierstrass",
                 "\u211c": "Rfraktur",
                 "\u211e": "prescription",
                 "\u2122": "trademark",
                 "\u212e": "estimated",
                 "\u2135": "aleph",
                 "\u2153": "onethird",
                 "\u2154": "twothirds",
                 "\u215b": "oneeighth",
                 "\u215c": "threeeighths",
                 "\u215d": "fiveeighths",
                 "\u215e": "seveneighths",
                 "\u2190": "arrowleft",
                 "\u2191": "arrowup",
                 "\u2192": "arrowright",
                 "\u2193": "arrowdown",
                 "\u2194": "arrowboth",
                 "\u2195": "arrowupdn",
                 "\u21a8": "arrowupdnbse",
                 "\u21b5": "carriagereturn",
                 "\u21d0": "arrowdblleft",
                 "\u21d1": "arrowdblup",
                 "\u21d2": "arrowdblright",
                 "\u21d3": "arrowdbldown",
                 "\u21d4": "arrowdblboth",
                 "\u2200": "universal",
                 "\u2202": "partialdiff",
                 "\u2203": "existential",
                 "\u2205": "emptyset",
                 "\u2207": "gradient",
                 "\u2208": "element",
                 "\u2209": "notelement",
                 "\u220b": "suchthat",
                 "\u220f": "product",
                 "\u2211": "summation",
                 "\u2212": "minus",
                 "\u2215": "fraction",
                 "\u2217": "asteriskmath",
                 "\u2219": "periodcentered",
                 "\u221a": "radical",
                 "\u221d": "proportional",
                 "\u221e": "infinity",
                 "\u221f": "orthogonal",
                 "\u2220": "angle",
                 "\u2227": "logicaland",
                 "\u2228": "logicalor",
                 "\u2229": "intersection",
                 "\u222a": "union",
                 "\u222b": "integral",
                 "\u2234": "therefore",
                 "\u223c": "similar",
                 "\u2245": "congruent",
                 "\u2248": "approxequal",
                 "\u2260": "notequal",
                 "\u2261": "equivalence",
                 "\u2264": "lessequal",
                 "\u2265": "greaterequal",
                 "\u2282": "propersubset",
                 "\u2283": "propersuperset",
                 "\u2284": "notsubset",
                 "\u2286": "reflexsubset",
                 "\u2287": "reflexsuperset",
                 "\u2295": "circleplus",
                 "\u2297": "circlemultiply",
                 "\u22a5": "perpendicular",
                 "\u22c5": "dotmath",
                 "\u2302": "house",
                 "\u2310": "revlogicalnot",
                 "\u2320": "integraltp",
                 "\u2321": "integralbt",
                 "\u2329": "angleleft",
                 "\u232a": "angleright",
                 "\u2500": "SF100000",
                 "\u2502": "SF110000",
                 "\u250c": "SF010000",
                 "\u2510": "SF030000",
                 "\u2514": "SF020000",
                 "\u2518": "SF040000",
                 "\u251c": "SF080000",
                 "\u2524": "SF090000",
                 "\u252c": "SF060000",
                 "\u2534": "SF070000",
                 "\u253c": "SF050000",
                 "\u2550": "SF430000",
                 "\u2551": "SF240000",
                 "\u2552": "SF510000",
                 "\u2553": "SF520000",
                 "\u2554": "SF390000",
                 "\u2555": "SF220000",
                 "\u2556": "SF210000",
                 "\u2557": "SF250000",
                 "\u2558": "SF500000",
                 "\u2559": "SF490000",
                 "\u255a": "SF380000",
                 "\u255b": "SF280000",
                 "\u255c": "SF270000",
                 "\u255d": "SF260000",
                 "\u255e": "SF360000",
                 "\u255f": "SF370000",
                 "\u2560": "SF420000",
                 "\u2561": "SF190000",
                 "\u2562": "SF200000",
                 "\u2563": "SF230000",
                 "\u2564": "SF470000",
                 "\u2565": "SF480000",
                 "\u2566": "SF410000",
                 "\u2567": "SF450000",
                 "\u2568": "SF460000",
                 "\u2569": "SF400000",
                 "\u256a": "SF540000",
                 "\u256b": "SF530000",
                 "\u256c": "SF440000",
                 "\u2580": "upblock",
                 "\u2584": "dnblock",
                 "\u2588": "block",
                 "\u258c": "lfblock",
                 "\u2590": "rtblock",
                 "\u2591": "ltshade",
                 "\u2592": "shade",
                 "\u2593": "dkshade",
                 "\u25a0": "filledbox",
                 "\u25a1": "H22073",
                 "\u25aa": "H18543",
                 "\u25ab": "H18551",
                 "\u25ac": "filledrect",
                 "\u25b2": "triagup",
                 "\u25ba": "triagrt",
                 "\u25bc": "triagdn",
                 "\u25c4": "triaglf",
                 "\u25ca": "lozenge",
                 "\u25cb": "circle",
                 "\u25cf": "H18533",
                 "\u25d8": "invbullet",
                 "\u25d9": "invcircle",
                 "\u25e6": "openbullet",
                 "\u263a": "smileface",
                 "\u263b": "invsmileface",
                 "\u263c": "sun",
                 "\u2640": "female",
                 "\u2642": "male",
                 "\u2660": "spade",
                 "\u2663": "club",
                 "\u2665": "heart",
                 "\u2666": "diamond",
                 "\u266a": "musicalnote",
                 "\u266b": "musicalnotedbl",
                 "\ufb01": "fi",
                 "\ufb02": "fl"}

class AFMError(Exception):
    pass

# reader states
_READ_START       = 0
_READ_MAIN        = 1
_READ_DIRECTION   = 2
_READ_CHARMETRICS = 3
_READ_KERNDATA    = 4
_READ_TRACKKERN   = 5
_READ_KERNPAIRS   = 6
_READ_COMPOSITES  = 7
_READ_END         = 8

# various parsing functions
def _parseint(s):
    try:
        return int(s)
    except:
        raise AFMError("Expecting int, got '%s'" % s)

def _parsehex(s):
    try:
        if s[0] != "<" or s[-1] != ">":
            raise AFMError()
        return int(s[1:-1], 16)
    except:
        raise AFMError("Expecting hexadecimal int, got '%s'" % s)

def _parsefloat(s):
    try:
        return float(s)
    except:
        raise AFMError("Expecting float, got '%s'" % s)

def _parsefloats(s, nos):
    try:
        numbers = s.split()
        result = list(map(float, numbers))
        if len(result) != nos:
            raise AFMError()
    except:
        raise AFMError("Expecting list of %d numbers, got '%s'" % (s, nos))
    return result

def _parsestr(s):
    # XXX: check for invalid characters in s
    return s

def _parsebool(s):
    s = s.rstrip()
    if s == "true":
       return True
    elif s == "false":
       return False
    else:
        raise AFMError("Expecting boolean, got '%s'" % s)


class AFMcharmetrics:
    def __init__(self, code, widths=None, vvector=None, name=None, bbox=None, ligatures=None):
        self.code = code
        if widths is None:
            self.widths = [None] * 2
        else:
            self.widths = widths
        self.vvector = vvector
        self.name = name
        self.bbox = bbox
        if ligatures is None:
            self.ligatures = []
        else:
            self.ligatures = ligatures


class AFMtrackkern:
    def __init__(self, degree, min_ptsize, min_kern, max_ptsize, max_kern):
        self.degree = degree
        self.min_ptsize = min_ptsize
        self.min_kern = min_kern
        self.max_ptsize = max_ptsize
        self.max_kern = max_kern


class AFMkernpair:
    def __init__(self, name1, name2, x, y):
        self.name1 = name1
        self.name2 = name2
        self.x = x
        self.y = y


class AFMcomposite:
    def __init__(self, name, parts):
        self.name = name
        self.parts = parts


class AFMfile(metric.metric):

    def __init__(self, file):
       self.afmversion = None                   # version, required
       self.metricssets = 0                     # int, optional
       self.fontname = None                     # str, required
       self.fullname = None                     # str, optional
       self.familyname = None                   # str, optional
       self.weight = None                       # str, optional
       self.fontbbox = None                     # 4 floats, required
       self.version = None                      # str, optional
       self.notice = None                       # str, optional
       self.encodingscheme = None               # str, optional
       self.mappingscheme = None                # int, optional (not present in base font programs)
       self.escchar = None                      # int, required if mappingscheme == 3
       self.characterset = None                 # str, optional
       self.characters = None                   # int, optional
       self.isbasefont = True                   # bool, optional
       self.vvector = None                      # 2 floats, required if metricssets == 2
       self.isfixedv = None                     # bool, default: true if vvector present, false otherwise
       self.capheight = None                    # float, optional
       self.xheight = None                      # float, optional
       self.ascender = None                     # float, optional
       self.descender = None                    # float, optional
       self.stdhw = None                        # float, optional
       self.stdvw = None                        # float, optional
       self.underlinepositions = [None] * 2     # int, optional (for each direction)
       self.underlinethicknesses = [None] * 2   # float, optional (for each direction)
       self.italicangles = [None] * 2           # float, optional (for each direction)
       self.charwidths = [None] * 2             # 2 floats, optional (for each direction)
       self.isfixedpitchs = [None] * 2          # bool, optional (for each direction)
       self.expected_entries = None             # if set, internal variable to verify number of expected entries in a section
       self.charmetrics = None                  # list of character metrics information, optional
       self.charmetricsdict = {}                # helper dictionary mapping glyph names to character metrics information
       self.trackkerns = None                   # list of track kernings, optional
       self.kernpairs = [None] * 2              # list of list of kerning pairs (for each direction), optional
       self.kernpairsdict = {}                  # helper dictionary mapping glyph names to kerning pairs, first direction
       self.kernpairsdict1 = {}                 # helper dictionary mapping glyph names to kerning pairs, second direction
       self.composites = None                   # list of composite character data sets, optional
       self.parse(file)
       if self.isfixedv is None:
           self.isfixedv = self.vvector is not None
       # XXX we should check the constraints on some parameters

    # the following methods process a line when the reader is in the corresponding
    # state and return the new state
    def _processline_start(self, line):
        key, args = line.split(None, 1)
        if key != "StartFontMetrics":
            raise AFMError("Expecting StartFontMetrics, no found")
        self.afmversion = tuple(map(int, args.split(".")))
        return _READ_MAIN, None

    def _processline_main(self, line):
        try:
            key, args = line.split(None, 1)
        except ValueError:
            key = line
            args = None
        if key == "Comment":
            return _READ_MAIN, None
        elif key == "MetricsSets":
            self.metricssets = _parseint(args)
            if direction is not None:
                raise AFMError("MetricsSets not allowed after first (implicit) StartDirection")
        elif key == "FontName":
            self.fontname = _parsestr(args)
        elif key == "FullName":
            self.fullname = _parsestr(args)
        elif key == "FamilyName":
            self.familyname = _parsestr(args)
        elif key == "Weight":
            self.weight = _parsestr(args)
        elif key == "FontBBox":
            self.fontbbox = _parsefloats(args, 4)
        elif key == "Version":
            if args is not None:
                self.version = _parsestr(args)
        elif key == "Notice":
            self.notice = _parsestr(args)
        elif key == "EncodingScheme":
            self.encodingscheme = _parsestr(args)
        elif key == "MappingScheme":
            self.mappingscheme = _parseint(args)
        elif key == "EscChar":
            self.escchar = _parseint(args)
        elif key == "CharacterSet":
            self.characterset = _parsestr(args)
        elif key == "Characters":
            self.characters = _parseint(args)
        elif key == "IsBaseFont":
            self.isbasefont = _parsebool(args)
        elif key == "VVector":
            self.vvector = _parsefloats(args, 2)
        elif key == "IsFixedV":
            self.isfixedv = _parsebool(args)
        elif key == "CapHeight":
            self.capheight = _parsefloat(args)
        elif key == "XHeight":
            self.xheight = _parsefloat(args)
        elif key == "Ascender":
            self.ascender = _parsefloat(args)
        elif key == "Descender":
            self.descender = _parsefloat(args)
        elif key == "StdHW":
            self.stdhw = _parsefloat(args)
        elif key == "StdVW":
            self.stdvw = _parsefloat(args)
        elif key == "StartDirection":
            direction = _parseint(args)
            if 0 <= direction <= 2:
                return _READ_DIRECTION, direction
            else:
                raise AFMError("Wrong direction number %d" % direction)
        elif (key == "UnderlinePosition" or key == "UnderlineThickness" or key == "ItalicAngle" or
              key == "Charwidth" or key == "IsFixedPitch"):
            # we implicitly entered a direction section, so we should process the line again
            return self._processline_direction(line, 0)
        elif key == "StartCharMetrics":
            if self.charmetrics is not None:
                raise AFMError("Multiple character metrics sections")
            if self.afmversion >= (2, 0):
                self.expected_entries = _parseint(args)
            else:
                self.expected_entries = None
            self.charmetrics = []
            return _READ_CHARMETRICS, 0
        elif key == "StartKernData":
            return _READ_KERNDATA, None
        elif key == "StartComposites":
            if self.composites is not None:
                raise AFMError("Multiple composite character data sections")
            if args is not None:
                self.expected_entries = _parseint(args)
            else:
                self.expected_entries = None
            self.composites = []
            return _READ_COMPOSITES, 0
        elif key == "EndFontMetrics":
            return _READ_END, None
        elif key[0] in string.ascii_lowercase:
            # ignoring private commands
            pass
        else:
            # and according to the AFM specs also all other unknown keys
            pass
        return _READ_MAIN, None

    def _processline_direction(self, line, direction):
        try:
            key, args = line.split(None, 1)
        except ValueError:
            key = line.strip()
        if key == "UnderlinePosition":
            self.underlinepositions[direction] = _parsefloat(args)
        elif key == "UnderlineThickness":
            self.underlinethicknesses[direction] = _parsefloat(args)
        elif key == "ItalicAngle":
            self.italicangles[direction] = _parsefloat(args)
        elif key == "Charwidth":
            self.charwidths[direction] = _parsefloats(args, 2)
        elif key == "IsFixedPitch":
            self.isfixedpitchs[direction] = _parsebool(args)
        elif key == "EndDirection":
            return _READ_MAIN, None
        else:
            # we assume that we are implicitly leaving the direction section again,
            # so try to reprocess the line in the header reader state
            return self._processline_main(line)
        return _READ_DIRECTION, direction

    def _processline_charmetrics(self, line, charno):
        if line.rstrip() == "EndCharMetrics":
            if self.expected_entries is not None and charno != self.expected_entries:
                # This seems to be a rather common error in AFM files, so we do not raise
                # an exception here, but just graticiously accept the file
                pass
                # raise AFMError("Fewer character metrics than expected")
            return _READ_MAIN, None

        has_name = False
        char = None
        for s in line.split(";"):
            s = s.strip()
            if not s:
               continue
            key, args = s.split(None, 1)
            if key == "C":
                if char is not None:
                    raise AFMError("Cannot define char code twice")
                char = AFMcharmetrics(_parseint(args))
            elif key == "CH":
                if char is not None:
                    raise AFMError("Cannot define char code twice")
                char = AFMcharmetrics(_parsehex(args))
            elif key == "WX" or key == "W0X":
                char.widths[0] = _parsefloat(args), 0
            elif key == "W1X":
                char.widths[1] = _parsefloat(args), 0
            elif key == "WY" or key == "W0Y":
                char.widths[0] = 0, _parsefloat(args)
            elif key == "W1Y":
                char.widths[1] = 0, _parsefloat(args)
            elif key == "W" or key == "W0":
                char.widths[0] = _parsefloats(args, 2)
            elif key == "W1":
                char.widths[1] = _parsefloats(args, 2)
            elif key == "VV":
                char.vvector = _parsefloats(args, 2)
            elif key == "N":
                # XXX: we should check that name is valid (no whitespace, etc.)
                has_name = True
                char.name = _parsestr(args)
            elif key == "B":
                char.bbox = _parsefloats(args, 4)
            elif key == "L":
                successor, ligature = args.split(None, 1)
                char.ligatures.append((_parsestr(successor), ligature))
            else:
                raise AFMError("Undefined command in character widths specification: '%s'", s)
        if char is None:
            raise AFMError("Character metrics not defined")

        self.charmetrics.append(char)
        if has_name:
            self.charmetricsdict[char.name] = char
        return _READ_CHARMETRICS, charno+1

    def _processline_kerndata(self, line):
        try:
            key, args = line.split(None, 1)
        except ValueError:
            key = line
            args = None
        if key == "Comment":
            return _READ_KERNDATA, None
        if key == "StartTrackKern":
            if self.trackkerns is not None:
                raise AFMError("Multiple track kernings data sections")
            self.trackkerns = [None] * _parseint(args)
            return _READ_TRACKKERN, 0
        elif key == "StartKernPairs" or key == "StartKernPairs0":
            if self.kernpairs[0] is not None:
                raise AFMError("Multiple kerning pairs data sections for direction 0")
            if args is not None:
                self.expected_entries = _parseint(args)
            else:
                self.expected_entries = None
            self.kernpairs[0] = []
            return _READ_KERNPAIRS, (0, 0)
        elif key == "StartKernPairs1":
            if self.kernpairs[1] is not None:
                raise AFMError("Multiple kerning pairs data sections for direction 1")
            self.expected_entries = _parseint(args)
            self.kernpairs[1] = []
            return _READ_KERNPAIRS, (1, 0)
        elif key == "EndKernData":
            return _READ_MAIN, None
        else:
            raise AFMError("Unsupported key %s in kerning data section" % key)

    def _processline_trackkern(self, line, i):
        try:
            key, args = line.split(None, 1)
        except ValueError:
            key = line
        if key == "Comment":
            return _READ_TRACKKERN, i
        elif key == "TrackKern":
            if i >= len(self.trackkerns):
                raise AFMError("More track kerning data sets than expected")
            degrees, args = args.split(None, 1)
            self.trackkerns[i] = AFMtrackkern(int(degrees), *_parsefloats(args, 4))
            return _READ_TRACKKERN, i+1
        elif key == "EndTrackKern":
            if i < len(self.trackkerns):
                raise AFMError("Fewer track kerning data sets than expected")
            return _READ_KERNDATA, None
        else:
            raise AFMError("Unsupported key %s in kerning data section" % key)

    def _processline_kernpairs(self, line, xxx_todo_changeme):
        (direction, i) = xxx_todo_changeme
        try:
            key, args = line.split(None, 1)
        except ValueError:
            key = line
        if key == "Comment":
            return _READ_KERNPAIRS, (direction, i)
        elif key == "EndKernPairs":
            if i != self.expected_entries:
                # This seems to be a rather common error in AFM files, so we do not raise
                # an exception here, but just graticiously accept the file
                pass
                # raise AFMError("Fewer kerning pairs than expected")
            return _READ_KERNDATA, None
        else:
            if key == "KP":
                try:
                    name1, name2, x, y = args.split()
                except:
                    raise AFMError("Expecting name1, name2, x, y, got '%s'" % args)
                x = _parsefloat(x)
                y = _parsefloat(y)
            elif key == "KPH":
                try:
                    hex1, hex2, x, y = args.split()
                except:
                    raise AFMError("Expecting <hex1>, <hex2>, x, y, got '%s'" % args)
                name1 = _parsehex(hex1)
                name2 = _parsehex(hex2)
                x = _parsefloat(x)
                y = _parsefloat(y)
            elif key == "KPX":
                try:
                    name1, name2, x = args.split()
                except:
                    raise AFMError("Expecting name1, name2, x, got '%s'" % args)
                x = _parsefloat(x)
                y = 0
            elif key == "KPY":
                try:
                    name1, name2, y = args.split()
                except:
                    raise AFMError("Expecting name1, name2, y, got '%s'" % args)
                x = 0
                y = _parsefloat(y)
            else:
                raise AFMError("Unknown key '%s' in kern pair section" % key)
            kernpair = AFMkernpair(name1, name2, x, y)
            self.kernpairs[direction].append(kernpair)
            if direction:
                self.kernpairsdict1[name1, name2] = kernpair
            else:
                self.kernpairsdict[name1, name2] = kernpair
            return _READ_KERNPAIRS, (direction, i+1)

    def _processline_composites(self, line, i):
        if line == "EndComposites":
            if self.expected_entries is not None and i != self.expected_entries:
                raise AFMError("Fewer composites than expected")
            return _READ_MAIN, None

        name = None
        no = None
        parts = []
        for s in line.split(";"):
            s = s.strip()
            if not s:
               continue
            key, args = s.split(None, 1)
            if key == "CC":
                try:
                    name, no = args.split()
                except:
                    raise AFMError("Expecting name number, got '%s'" % args)
                no = _parseint(no)
            elif key == "PCC":
                try:
                    name1, x, y = args.split()
                except:
                    raise AFMError("Expecting name x y, got '%s'" % args)
                parts.append((name1, _parsefloat(x), _parsefloat(y)))
            else:
                raise AFMError("Unknown key '%s' in composite character data section" % key)
        if len(parts) != no:
            raise AFMError("Wrong number of composite characters")
        return _READ_COMPOSITES, i+1

    def parse(self, f):
         # state of the reader, consisting of 
         #  - the main state, i.e. the type of the section
         #  - a parameter sstate
         state = _READ_START, None
         # Note that we do a line by line processing here, since one
         # of the states (_READ_DIRECTION) can be entered implicitly, i.e.
         # without a corresponding StartDirection section and we thus
         # may need to reprocess a line in the context of the new state
         for line in f:
            line = line[:-1].strip()
            mstate, sstate = state
            if mstate == _READ_START:
                state = self._processline_start(line)
            else: 
                # except for the first line, any empty will be ignored
                if not line:
                   continue
                if mstate == _READ_MAIN:
                    state = self._processline_main(line)
                elif mstate == _READ_DIRECTION:
                    state = self._processline_direction(line, sstate)
                elif mstate == _READ_CHARMETRICS:
                    state = self._processline_charmetrics(line, sstate)
                elif mstate == _READ_KERNDATA:
                    state = self._processline_kerndata(line)
                elif mstate == _READ_TRACKKERN:
                    state = self._processline_trackkern(line, sstate)
                elif mstate == _READ_KERNPAIRS:
                    state = self._processline_kernpairs(line, sstate)
                elif mstate == _READ_COMPOSITES:
                    state = self._processline_composites(line, sstate)
                else:
                    raise AFMError("Undefined state in AFM reader")

    def width_ds(self, glyphname):
        return self.charmetricsdict[glyphname].widths[0][0]

    def width_pt(self, glyphnames, size_pt):
        return sum([self.charmetricsdict[glyphname].widths[0][0] for glyphname in glyphnames])*size_pt/1000.0

    def height_pt(self, glyphnames, size_pt):
        return max([self.charmetricsdict[glyphname].bbox[3] for glyphname in glyphnames])*size_pt/1000.0

    def depth_pt(self, glyphnames, size_pt):
        return min([self.charmetricsdict[glyphname].bbox[1] for glyphname in glyphnames])*size_pt/1000.0

    def resolveligatures(self, glyphnames):
        i = 1
        while i < len(glyphnames):
            for glyphname, replacement in self.charmetricsdict[glyphnames[i-1]].ligatures:
                if glyphname == glyphnames[i]:
                    glyphnames[i-1] = replacement
                    del glyphnames[i]
                    break
            else:
                i += 1
        return glyphnames

    def resolvekernings(self, glyphnames, size_pt=None):
        result = [None]*(2*len(glyphnames)-1)
        for i, glyphname in enumerate(glyphnames):
            result[2*i] = glyphname
            if i:
                kernpair = self.kernpairsdict.get((glyphnames[i-1], glyphname))
                if kernpair:
                    if size_pt is not None:
                        result[2*i-1] = kernpair.x*size_pt/1000.0
                    else:
                        result[2*i-1] = kernpair.x
        return result

    def writePDFfontinfo(self, file, seriffont=False, symbolfont=True):
        flags = 0
        if self.isfixedpitchs[0]:
            flags += 1<<0
        if seriffont:
            flags += 1<<1
        if symbolfont:
            flags += 1<<2
        else:
            flags += 1<<5
        if self.italicangles[0]:
            flags += 1<<6
        file.write("/Flags %d\n" % flags)
        if self.italicangles[0] is not None:
            file.write("/ItalicAngle %d\n" % self.italicangles[0])
        if self.ascender is not None:
            ascent = self.ascender
        elif self.fontbbox is not None:
            ascent = self.fontbbox[3]
        else:
            ascent = 1000 # guessed default
        file.write("/Ascent %d\n" % ascent)
        if self.descender is not None:
            descent = self.descender
        elif self.fontbbox is not None:
            descent = self.fontbbox[3]
        else:
            descent = -200 # guessed default
        file.write("/Descent %d\n" % descent)
        if self.fontbbox is not None:
            file.write("/FontBBox [%d %d %d %d]\n" % tuple(self.fontbbox))
        else:
            # the fontbbox is required, so we have to have to provide some default
            file.write("/FontBBox [0 %d 1000 %d]\n" % (descent, ascent))
        if self.capheight is not None:
            file.write("/CapHeight %d\n" % self.capheight)
        else:
            # the CapHeight is required, so we have to have to provide some default
            file.write("/CapHeight %d\n" % ascent)
        if self.stdvw is not None:
            stemv = self.stdvw
        elif self.weight is not None and ("bold" in self.weight.lower() or "black" in self.weight.lower()):
            stemv = 120 # guessed default
        else:
            stemv = 70 # guessed default
        file.write("/StemV %d\n" % stemv)
