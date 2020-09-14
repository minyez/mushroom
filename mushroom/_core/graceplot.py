# -*- coding: utf-8 -*-
# pylint: disable=too-few-public-methods,missing-function-docstring
r"""A high-level Python interface to the Grace plotting package

Lastest adapted from `jscatter` graceplot
see https://gitlab.com/biehl/jscatter/-/blob/master/src/jscatter/graceplot.py ,
commit d482bf214b8ef43fa853491d57b3ccbee02e5728

Originally, this code of GracePlot started out from Nathaniel Gray <n8gray@caltech.edu>,
updated by Marcus H. Mendenhall, MHM ,John Kitchin, Marus Mendenhall, Ralf Biehl (jscatter)

The main purpose of this re-implementation is to write grace plot file elegantly,
without any concern about whether xmgrace is installed or not.
Therefore, platform-related functions are discarded. (minyez)"""
import sys
from io import TextIOWrapper
from abc import abstractmethod
from copy import deepcopy

from numpy import shape
from mushroom._core.data import Data

# pylint: disable=bad-whitespace
_COLOR_MAP = {
        0:  (255, 255, 255, "white"),
        1:  (  0,   0,   0, "black"),
        2:  (255,   0,   0, "red"),
        3:  (  0, 255,   0, "green"),
        4:  (  0,   0, 255, "blue"),
        5:  (255, 255,   0, "yellow"),
        6:  (188, 143, 143, "brown"),
        7:  (220, 220, 220, "grey"),
        8:  (148,   0, 211, "violet"),
        9:  (  0, 255, 255, "cyan"),
        10: (255,   0, 255, "magenta"),
        11: (255, 165,   0, "orange"),
        12: (114,  33, 188, "indigo"),
        13: (103,   7,  72, "maroon"),
        14: ( 64, 224, 208, "turquoise"),
        15: (  0, 139,   0, "green4"),
        }
_PREDEF_COLOR_NAMES = {name: code for code, (_, _, _, name) in _COLOR_MAP.items()}
_N_COLOR_MAP = len(_COLOR_MAP.keys())

def _valid_rgb(r, g, b):
    """Check if RGB value is valid"""
    for v in [r, g, b]:
        if v not in range(256):
            raise ValueError(f"Invalid RGB value {r} {g} {b}")
    return True

class ColorMap:
    """Object to map the color
    
    Private attribute:
        _cm (dict) : color map
        _cn (dict) : color names

    TODO add system configure
    """
    # check validity of pre-defined colormap
    # no duplicate
    assert _N_COLOR_MAP == len(_PREDEF_COLOR_NAMES.keys())
    # code are in order
    for i in range(_N_COLOR_MAP):
        assert i in _COLOR_MAP.keys()
        r, g, b = _COLOR_MAP[i][:3]
        _valid_rgb(r, g, b)

    def __init__(self):
        self._cm = _COLOR_MAP
        self._cn = _PREDEF_COLOR_NAMES
        self._n = _N_COLOR_MAP

    def __str__(self):
        s = ""
        for i in range(self._n):
            r, g, b, n = self._cm[i]
            s += f"@map color {i} to ({r}, {g}, {b}), \"{n}\"\n"
        return s

    @property
    def n(self):
        """Number of available colors"""
        return len(self._cm.keys())

    def add(self, r, g, b, name=None):
        """Add a new color with its RGB value"""
        self._valid_rgb(r, g, b)
        if name is None:
            name = 'color' + str(self.n)
        elif self._check_color_name(name):
            raise ValueError(f"color {name} has been defined with code {self._cn[name]}")
        if self._cm is _COLOR_MAP:
            self._cm = deepcopy(_COLOR_MAP)
            self._cn = deepcopy(_PREDEF_COLOR_NAMES)
        n = self.n
        self._cm[n] = (r, g, b, name)
        self._cn[name] = n

    def _check_color_name(self, name):
        """Check if the color name is already defined"""
        return name in self._cn.keys()

    def get_color_code(self, name):
        """get the map code of color `name`"""
        if isinstance(name, str) and self._check_color_name(name):
            return self._cn[name]
        raise ValueError("name should be a string")

    def get_color_name(self, code):
        """get the name of color `code`"""
        if isinstance(code, int):
            try:
                return self._cm[code][3]
            except KeyError:
                raise IndexError(f"color code {code} is not defined")
        raise ValueError("code should be an integer")

    def get_rgb(self, i):
        """get the rgb value of color with its code"""
        r, g, b, _ = self._cm[i]
        return r, g, b

    def has_color(self, name):
        """Check if the color name is already defined"""
        return self._check_color_name(name)


class Font:
    """Object to set up the font

    For now adding fonts is not supported"""
    _FONTS = [
        "Times-Roman",
        "Times-Italic",
        "Times-Bold",
        "Times-BoldItalic",
        "Helvetica",
        "Helvetica-Oblique",
        "Helvetica-Bold",
        "Helvetica-BoldOblique",
        "Courier",
        "Courier-Oblique",
        "Courier-Bold",
        "Courier-BoldOblique",
        "Symbol",
        "ZapfDingbats",
        ]

    def export(self):
        slist = []
        for i, f in enumerate(self._FONTS):
            slist.append(f"map font {i} to \"{f}\", \"{f}\"")
        return slist

    def __str__(self):
        return "\n".join(self.export())



class LineStyle:
    """line style"""
    NONE = 0
    SOLID = 1
    DOTTED = 2
    DASHED = 3
    LONGDASHED = 4
    DOTDASHED = 5


class Fill:
    """Fill of marker"""
    NONE = 0
    SOLID = 1
    OPAQUE = 2


class Justfs:
    """Justification of text"""
    LEFT = 0
    CENTER = 1
    RIGHT = 2
    # is place necessary?


class Legend:
    """Legend"""
    def __init__(self):
        pass


class Frame:
    """frame"""
    CLOSED = 0
    HALFOPEN = 1
    BREAKTOP = 2
    BREAKBOT = 3
    BREAKLEFT = 4
    BREAKRIGHT = 5

class Axis:
    """Axis"""
    def __init__(self):
        self.major = Tick()
        self.minor = Tick()
        self.ticklabel = TickLabel()


class Graph:
    """Graph"""
    def __init__(self):
        self.legend =  Legend()

    def set_xaxis(self):
        pass

    def set_yaxis(self):
        pass

    def print_header(self):
        return ""

    def print_dataset(self):
        return ""

class Line:
    """Line"""

class BaseOutput:
    """abstract class for printing element object

    _attrs and _marker must be redefined,
    with _attrs as a tuple, each member a 4-member tuple, as
    name, type, default value, print format for each attribute
    """
    _attrs = None
    _marker = None

    @abstractmethod
    def __init__(self, **kwargs):
        assert isinstance(self._attrs, tuple)
        for i in self._attrs:
            assert len(i) == 4
        assert isinstance(self._marker, str)
        for attr, typ, default, _ in self._attrs:
            self.__setattr__(attr, typ(kwargs.get(attr, default)))

    def export(self, with_at=False):
        """export all object attributes as a list of string

        Each member is a line in agr file"""
        slist = []
        for attr, typ, _, f in self._attrs:
            s = {True: "@"}.get(with_at, "")
            s += self._marker + " " + attr.replace("_", " ") + " "
            if typ is str:
                s += "\"" + f.format(self.__getattribute__(attr)) + "\""
            elif typ is list:
                s += f.format(*self.__getattribute__(attr))
            else:
                s += f.format(self.__getattribute__(attr))
            slist.append(s)
        return slist

    def __str__(self):
        return "\n".join(self.export(with_at=True))

    def __repr__(self):
        return self.__str__(self)


class Symbol(BaseOutput):
    """Symbols of marker

    Args:
        sym (int) : index of symbol, or use predefined Symbol"""
    NONE = 0
    CIRCLE = 1
    SQUARE = 2
    diamond = 3
    TUP = 4
    TLEFT = 5
    TDOWN = 6
    TRIGHT = 7
    PLUS = 8
    CROSS = 9
    START = 10
    CHARACTER = 11

    def __init__(self, sym, **kwargs):
        self._sym = sym
        self._marker = "symbol"
        self._attrs = (
            ("size", float, 1., "{:8f}"),
            ("color", int, 1, "{:d}"),
            ("pattern", int, 1, "{:d}"),
            ("fill_color", int, 1, "{:d}"),
            ("fill_pattern", int, 1, "{:d}"),
            ("linewidth", float, 1, "{:3f}"),
            ("linestyle", int, 1, "{:d}"),
            ("char", int, 1, "{:d}"),
            ("char_font", int, 0, "{:d}"),
            ("skip", int, 0, "{:d}"),
                )
        BaseOutput.__init__(self, **kwargs)

    def export(self, with_at=False):
        slist = BaseOutput.export(self, with_at=with_at)
        s = {True: "@"}.get(with_at, "")
        s += self._marker + " " + str(sym)
        slist = [s,] + slist
        return slist

class Page(BaseOutput):
    def __init__(self, **kwargs):
        self._marker = "page"
        self._attrs = (
            ("size", list, (792, 612), "{:d}, {:d}"),
            ("scroll", float, 0.05, "{:.0%}"),
            ("inout", float, 0.05, "{:.0%}"),
                )
        BaseOutput.__init__(self, **kwargs)


class TimeStamp(BaseOutput):
    """Timestamp"""
    def __init__(self, on=False, **kwargs):
        self.on = on
        self._attrs = (
            ('color', int, 1, "{:d}"),
            ('rot', int, 0, "{:d}"),
            ('font', int, 0, "{:d}"),
            ('char_size', float, 1.0, "{:8f}"),
                )
        self._marker = "timestamp"
        BaseOutput.__init__(self, **kwargs)

    def export(self, with_at=False):
        slist = BaseOutput.export(self, with_at=with_at)
        s = {True: "@"}.get(with_at, "")
        s += self._marker + " " + {True: "on", False: "off"}[self.on]
        slist = [s,] + slist
        return slist


class Tick:
    """Tick of axis"""


class TickLabel:
    """Label of axis tick"""


class Dataset:
    """Object of grace dataset"""

class Plot:
    """the general control object for the grace plot

    Public attributes:

    Public methods:

    Private attributes:
        _head (str)
        _graphs (list)
        _font (Font)
        _use_qtgrace (bool)

    Private methods:
    """
    
    def __init__(self, qtgrace=False):
        self._comment_head = "# Grace project file\n#\n"
        self._head = "version 50122\nlink page off\n"
        self._page = Page()
        self._timestamp = TimeStamp()
        self._graphs = [Graph(),]
        self._font = Font()
        self._use_qtgrace = qtgrace

    def __str__(self):
        """TODO print the whole agr file"""
        header = [self._page, self._font, self._timestamp]
        slist = []
        for h in header:
            slist += h.export()
        s = "\n".join(slist)
        # add @ to each header line
        s = self._comment_head + "@" + "\n@".join(s.split("\n"))
        # export datasets
        return s

    def get_graph(self, i):
        """Get the Graph object of index i"""
        self._check_valid_graph(i)
        return self._graphs[i]

    def add_graph(self, graph=None):
        """add a graph to the plot"""
        if graph is None:
            graph = Graph()
        self._graphs.append(graph)

    def _check_valid_graph(self, i):
        try:
            g = self._graphs[i]
        except IndexError:
            raise IndexError(f"G.{i} does not exist")

    def add_dataset(self, dataset, graph=0):
        """Add a data set to graph `graph`"""
        self._graphs[graph].add_dataset(dataset)

    def set_xaxis(self, graph=0, **kwargs):
        """set up x-axis of graph"""
        self._graphs[graph].set_xaxis(**kwargs)

    def set_yaxis(self, graph=0, **kwargs):
        """set up y-axis of graph"""
        self._graphs[graph].set_yaxis(**kwargs)

    def set_xlimit(self, xmin=None, xmax=None, graph=0):
        """set xlimit of a graph (default 0)"""
        self._graphs[graph].set_xaxis(xmin=xmin, xmax=xmax)

    def set_ylimit(self, ymin=None, ymax=None, graph=0):
        """set ylimit of a graph (default 0)

        Args:
            ymin (float)
            ymax (float)
            graph (int)
        """
        self._graphs[graph].set_yaxis(ymin=ymin, ymax=ymax)

    def export(self, file=sys.stdout):
        """Export grace plot file to `fn`

        Args:
            file (str or file handle)"""
        if isinstance(file, str):
            fp = open(file, 'w')
            print(self.__str__, file=fp)
            fp.close()
            return
        if isinstance(file, TextIOWrapper):
            print(self.__str__, file=file)
            return
        raise ValueError

    @classmethod
    def double_y(cls):
        """Create a double-y-axis plot"""
        raise NotImplementedError


if __name__ == "__main__":
    print(Plot())

