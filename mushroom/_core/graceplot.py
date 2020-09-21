# -*- coding: utf-8 -*-
# pylint: disable=too-few-public-methods,missing-function-docstring
r"""A high-level Python interface to the Grace plotting package

Lastest adapted from `jscatter` graceplot
see https://gitlab.com/biehl/jscatter/-/blob/master/src/jscatter/graceplot.py ,
commit d482bf214b8ef43.1fa853491d57b3ccbee02e5728

Originally, this code of GracePlot started out from Nathaniel Gray <n8gray@caltech.edu>,
updated by Marcus H. Mendenhall, MHM ,John Kitchin, Marus Mendenhall, Ralf Biehl (jscatter)

The main purpose of this implementation is to write grace plot file elegantly,
without any concern about whether xmgrace is installed or not.
Therefore, platform-related functions are discarded. (minyez)

"""
import sys
import time
from io import TextIOWrapper
from copy import deepcopy

from mushroom._core.data import Data
from mushroom._core.logger import create_logger

_logger = create_logger(__name__)
del create_logger

# pylint: disable=bad-whitespace
def encode_str(string):
    """encode a string to grace format"""
    raise NotImplementedError

def decode_agr(agr):
    """decode grace format string to a normal string"""
    raise NotImplementedError

def _valid_rgb(r, g, b, name):
    """Check if RGB value is valid. Give warning if it is not"""
    d = {"R": r, "G": g, "B": b}
    for k, v in d.items():
        if v not in range(256):
            _logger.warning("%s (%s value of %s) is not a valid RGB", v, k, name)

class _MapOutput:
    """class for write map output, e.g. font, colormap

    the main attribute is a private dictionary, _map and an output format _format
    for the mapped values

    key : int/str/float, identifier of mapping
    value : tuple/list, value mapped

    """
    _marker = None
    _map = {None: (None,)}
    _format = '{:s}'

    def export(self):
        slist = []
        for k, v in self._map.items():
            s = "map {:s} {:s} to ".format(self._marker, str(k)) + self._format.format(*v)
            slist.append(s)
        return slist


class _ColorMap(_MapOutput):
    """Class to map the color
    
    Private attribute:
        _map (dict) : color map
        _cn (dict) : color names

    TODO add system configure
    """
    _marker = 'color'
    _format = '({:d}, {:d}, {:d}), \"{:s}\"'
    # a pre-defined color map list
    _colors = [
        (255, 255, 255, "white"),
        (  0,   0,   0, "black"),
        (255,   0,   0, "red"),
        (  0, 255,   0, "green"),
        (  0,   0, 255, "blue"),
        (255, 255,   0, "yellow"),
        (188, 143, 143, "brown"),
        (220, 220, 220, "grey"),
        (148,   0, 211, "violet"),
        (  0, 255, 255, "cyan"),
        (255,   0, 255, "magenta"),
        (255, 165,   0, "orange"),
        (114,  33, 188, "indigo"),
        (103,   7,  72, "maroon"),
        ( 64, 224, 208, "turquoise"),
        (  0, 139,   0, "green4"),
        ]

    # check validity of pre-defined colormap
    # check if predefined rgb are valid, and there is no duplicate names
    _color_names = [i[3] for i in _colors]
    for color in _colors:
        _valid_rgb(*color)
    assert len(_color_names) == len(set(_color_names))

    def __init__(self):
        self._map = {}
        for i, color in enumerate(self._colors):
            self._map[i] = color
        self._cn = self._color_names
        # add user defined color_map
        try:
            from mushroom.__config__ import color_map
            for r, g, b, name in color_map:
                self.add(r, g, b, name)
            del color_map
        except (ImportError, TypeError, ValueError):
            _logger.warning("user color_map not loaded")

    def __getitem__(self, i):
        return self._map[i][3]

    def __str__(self):
        return '\n'.join(self.export())

    def export(self):
        """export color maps

        Returns
            list
        """
        return _MapOutput.export(self)

    @property
    def n(self):
        """Number of available colors"""
        return len(self._cn)

    def add(self, r, g, b, name=None):
        """Add a new color with its RGB value

        Args:
            r, g, b (int)
        """
        if name is None:
            name = 'color' + str(self.n)
        elif name in self._cn:
            msg = "color {:s} has been defined with code {:s}".format(name, self._cn.index(name))
            raise ValueError(msg)
        color = (r, g, b, name)
        _valid_rgb(*color)
        if self._colors is _ColorMap._colors:
            self._colors = deepcopy(_ColorMap._colors)
        self._colors.append(color)
        self._map[self.n] = color
        self._cn.append(name)

    def get_color_code(self, name):
        """get the map code of color `name`"""
        try:
            return self._cn.index(name)
        except ValueError:
            raise ValueError("colro name {:s} is not found".format(name))

    def get_color_name(self, code):
        """get the name of color `code`"""
        try:
            return self._cm[code][3]
        except IndexError:
            raise ValueError("color code {:d} is not defined".format(code))

    def get_rgb(self, i):
        """get the rgb value of color with its code"""
        r, g, b, _ = self._cm[i]
        return r, g, b

    def has_color(self, name):
        """Check if the color name is already defined"""
        return name in self._cn


class Color:
    """color
    Args:
        color (str or int)
    """
    WHITE = 0
    BLACK = 1
    RED = 2
    GREEN = 3
    BLUE = 4
    YELLOW = 5
    BROWN = 6
    GREY = 7
    VIOLET = 8
    CYAN = 9
    MAGENTA = 10
    ORANGE = 11
    INDIGO = 12
    MAROON = 13
    TURQUOISE = 14
    GREEN4 = 15


class Pattern:
    """Pattern"""
    NONE = 0
    SOLID = 1

    @classmethod
    def get(cls, s):
        """get the pattern code from string s"""
        d = {
            "left" : cls.LEFT,
            "center": cls.CENTER,
            "right": cls.RIGHT,
            }
        return d.get(str(s).lower(), 1)

class _Font(_MapOutput):
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
    _marker = 'font'
    _format = "\"{:s}\", \"{:s}\""
    _map = {}
    for i, f in enumerate(_FONTS):
        _map[i] = (f, f)

    def export(self):
        """return a list of font map strings"""
        return _MapOutput.export(self)

    def __str__(self):
        return "\n".join(self.export())

class LineStyle:
    """line style
    
    Args:
        ls (int or str)"""
    NONE = 0
    SOLID = 1
    DOTTED = 2
    DASHED = 3
    LONGDASHED = 4
    DOTDASHED = 5

    DEFAULT = SOLID
    PAIR = {
        "none" : NONE,
        "solid": SOLID,
        "dotted": DOTTED,
        "dashed": DASHED,
        "longdashed": LONGDASHED,
        "dotdashed": DOTDASHED,
        }

    def __init__(self, ls=DEFAULT):
        if isinstance(ls, int):
            self._ls = ls
        elif isinstance(ls, str) or ls is None:
            try:
                self._ls = LineStyle.PAIR.get(str(ls).lower())
            except KeyError:
                _logger.warning("unrecognized linestyle: %s. Use default", ls)
                self._ls = LineStyle.DEFAULT

    def __str__(self):
        return str(self._ls)

    def __repr__(self):
        return self.__str__()

class Justf:
    """Justification of text"""
    LEFT = 0
    CENTER = 1
    RIGHT = 2

    @classmethod
    def get(cls, s):
        """get the text justification code from string s"""
        d = {
            "left" : cls.LEFT,
            "center": cls.CENTER,
            "right": cls.RIGHT,
            }
        return d.get(str(s).lower(), 1)


class Switch:
    """Class for switch control"""
    ON = 1
    AUTO = -1
    OFF = 0

    @classmethod
    def get_str(cls, i):
        """get the correspond attribute string"""
        d = {cls.ON: "on", cls.AUTO: "auto", cls.OFF: "off", True: "on", False: "off"}
        return d.get(i)

    @classmethod
    def get(cls, s):
        """get the attribute code from string"""
        d = { "on": cls.ON, "auto": cls.AUTO, "off": cls.OFF}
        return d.get(s)


class Position:
    """Class for position contorl"""
    IN = -1
    BOTH = 0
    OUT = 1
    AUTO = 2
    @classmethod
    def get_str(cls, i):
        """get the correspond attribute string"""
        d = {cls.IN: "in", cls.BOTH: "both", cls.OUT: "out", cls.AUTO: "auto"}
        return d.get(i)

class _Affix:
    """object to dataset (s0,s1...), graph (g0,g1...), axis (x,y,altx,alty), etc.

    Args:
        affix (str) : the content to add as the affix, 0,1,2 or x,y,altx,alty
        is_prefix (bool) : if True, the content will be added as prefix. Otherwise as suffix
    """
    _marker = ""

    def __init__(self, affix, is_prefix=False):
        self._affix = str(affix)
        self._is_prefix = is_prefix
    

class _BaseOutput:
    """abstract class for printing element object

    _attrs and _marker must be redefined,
    with _attrs as a tuple, each member a 4-member tuple, as
    name, type, default value, print format for each attribute

    When type is bool, it will be treated invidually as a special
    attribute.
    """
    _attrs = {}
    _marker = ''

    def __init__(self, **kwargs):
        assert isinstance(self._attrs, dict)
        for x in self._attrs.values():
            assert len(x) == 3
        assert isinstance(self._marker, str)
        for attr, (typ, default, _) in self._attrs.items():
            _logger.debug("attr: %s type: %s", attr, typ)
            v = kwargs.get(attr, default)
            try:
                self.__getattribute__(attr)
            except AttributeError:
                if typ is not bool:
                    v = typ(v)
                self.__setattr__(attr, v)

    def _set(self, **kwargs):
        """basic functionality to set attributes"""
        if kwargs:
            if len(kwargs) < len(self._attrs):
                for k, v in kwargs.items():
                    _logger.debug("setting %s to %s", k, str(v))
                    if k in self._attrs and v is not None:
                        self.__setattr__(k, v)
            else:
                for k in self._attrs:
                    _logger.debug("setting %s", k)
                    v = kwargs.get(k, None)
                    if v is not None:
                        self.__setattr__(k, v)

    # pylint: disable=R0912
    def export(self):
        """export all object attributes as a list of string

        Each member is a line in agr file"""
        slist = []
        prefix = deepcopy(self._marker).replace("_", " ")
        try:
            affix = self.__getattribute__('_affix')
            is_p = self.__getattribute__('_is_prefix')
            if is_p:
                prefix = str(affix) + prefix
            else:
                prefix += str(affix)
        except (TypeError, AttributeError):
            pass

        for attr, (typ, _, f) in self._attrs.items():
            attrv = self.__getattribute__(attr)
            _logger.debug("parsed export: %s , %s, %r", type(self).__name__, attr, attrv)
            if typ in [list, tuple, set]:
                temps = attr.replace("_", " ") + " " + f.format(*attrv)
            # special property marked by the type as bool
            elif typ is bool:
                # for Symbol
                if attr == "type":
                    temps = f.format(attrv)
                # for on off attribute 
                if attr.endswith("_switch"):
                    temps = attr.replace("_switch", "") + " " + Switch.get_str(attrv)
                # for inout attribute 
                elif attr.endswith("_position"):
                    temps = attr.replace("_position", "") + " " + Position.get_str(attrv)
                # for 2-float location attribute
                elif attr.endswith("_location"):
                    temps = attr.replace("_location", "") + " " + f.format(*attrv)
                # for arbitray string attribute
                elif attr.endswith("_comment"):
                    temps = attr.replace("_comment", "") + " " + f.format(attrv)
                # remove the marker name in the attribute to avoid duplicate
                temps = temps.replace(self._marker, "").replace("_", " ")
            else:
                temps = attr.replace("_", " ") + " " + f.format(attrv)
            s = prefix + " " + temps
            _logger.debug("exporting: %s", s)
            slist.append(s)

        # cover extra lines with an _extra_export attribute
        try:
            slist += self.__getattribute__('_extra_export')
        except (TypeError, AttributeError):
            pass

        return slist

    def __str__(self):
        return "\n".join(self.export())

    def __repr__(self):
        return self.__str__()

class _Region(_BaseOutput, _Affix):
    """Region of plot, i.e. the `r` part"""
    _marker = 'r'
    _attrs = {
        'r_switch': (bool, Switch.OFF, '{:s}'),
        'linestyle': (int, LineStyle.SOLID, '{:d}'),
        'linewidth': (float, 1.0, '{:3.1f}'),
        'type': (str, "above", '{:s}'),
        'color': (int, Color.BLACK, '{:d}'),
        'line': (list, [0., 0., 0., 0.], '{:f}, {:f}, {:f}, {:f}'),
        }

    def __init__(self, index, **kwargs):
        _BaseOutput.__init__(self, **kwargs)
        _Affix.__init__(self, index, is_prefix=False)
        self._link_ig = "0"

    def set_link(self, ig):
        """set the graph to which the region is linked to"""
        self._link_ig = str(ig)

    def export(self):
        """export as a list of string"""
        slist = ["link " + self._marker + self._affix + " to g" + self._link_ig]
        slist += _BaseOutput.export(self)
        return slist


class _TitleLike(_BaseOutput):
    """title and subtitle of graph"""
    _attrs = {
        'font': (int, 0, "{:d}"),
        'size': (float, 1.5, "{:8f}"),
        'color': (int, Color.BLACK, "{:d}"),
        }

class _Title(_TitleLike):
    """title of graph"""
    _marker = 'title'
    _attrs = dict(**_TitleLike._attrs)
    _attrs[_marker+'_comment'] = (bool, "", "\"{:s}\"")

class _SubTitle(_TitleLike):
    """title of graph"""
    _marker = 'subtitle'
    _attrs = dict(**_TitleLike._attrs)
    _attrs[_marker+'_comment'] = (bool, "", "\"{:s}\"")

def _set_loclike_attr(marker, form, *args):
    f = [form,] * len(args)
    return {marker + '_location': (bool, list(args), ', '.join(f))}

def _set_xy_extreme(loclike, corner, value):
    """set xmin, ymin, xmax or ymax"""
    assert len(loclike) == 4
    try:
        i = {'xmin':0, 'ymin':1, 'xmax':2, 'ymax':3}.get(corner)
        loclike[i] = value
    except KeyError:
        raise ValueError("invalid corner name ", corner)

class _World(_BaseOutput):
    """world of graph"""
    _marker = 'world'
    _attrs = _set_loclike_attr('world', '{:8f}', 0., 0., 1., 1.)
    def set(self, corner, value):
        _set_xy_extreme(self.world_location, corner, value)

class _StackWorld(_BaseOutput):
    """stack world of graph"""
    _marker = 'stack_world'
    _attrs = _set_loclike_attr('stack_world', '{:8f}', 0., 1., 0., 1.)
    def set(self, corner, value):
        _set_xy_extreme(self.stack_world_location, corner, value)

class _View(_BaseOutput):
    """stack world of graph"""
    _marker = 'view'
    _attrs = _set_loclike_attr('view', '{:8f}', 0.15, 0.10, 1.20, 0.90)
    def set(self, corner, value):
        _set_xy_extreme(self.view_location, corner, value)

class _Znorm(_BaseOutput):
    """stack world of graph"""
    _marker = 'znorm'
    _attrs = _set_loclike_attr('znorm', '{:d}', 1)

class Line(_BaseOutput):
    """Line object of dataset"""
    _marker = 'line'
    _attrs = {
        'type': (int, 1, "{:d}"),
        'linestyle': (int, LineStyle.SOLID, "{:d}"),
        'linewidth': (float, 1.0, "{:3.1f}"),
        'color': (int, Color.BLACK, "{:d}"),
        'pattern': (int, 1, "{:d}"),
        }


class _Box(_BaseOutput):
    """_Box of legend"""
    _marker = 'box'
    _attrs = {
        'color': (int, Color.BLACK, '{:d}'),
        'pattern': (int, Pattern.SOLID, '{:d}'),
        'linewidth': (float, 1.0, '{:3.1f}'),
        'linestyle': (int, LineStyle.SOLID, '{:d}'),
        'fill_color': (int, Color.BLACK, '{:d}'),
        'fill_pattern': (int, Pattern.SOLID, '{:d}'),
        }


class _Legend(_BaseOutput):
    """object to control the appearance of graph legend"""
    _marker = 'legend'
    _attrs = {
        'legend_switch': (bool, Switch.ON, '{:d}'),
        'legend_location': (bool, [0.75, 0.50], '{:6f} , {:6f}'),
        'loctype': (str, 'view', '{:s}'),
        'font': (int, 0, '{:d}'),
        'color': (int, Color.BLACK, '{:d}'),
        'length': (int, 4, '{:d}'),
        'vgap': (int, 1, '{:d}'),
        'hgap': (int, 1, '{:d}'),
        'invert': (str, False, '{:s}'),
        'char_size': (float, 1.2, '{:8f}'),
        }

    def __init__(self, **kwargs):
        self.box = _Box()
        _BaseOutput.__init__(self, **kwargs)

    def export(self):
        slist = _BaseOutput.export(self) + \
                [self._marker + " " + i for i in self.box.export()]
        return slist


class _Frame(_BaseOutput):
    """frame"""
    CLOSED = 0
    HALFOPEN = 1
    BREAKTOP = 2
    BREAKBOT = 3
    BREAKLEFT = 4
    BREAKRIGHT = 5

    _marker = "frame"
    _attrs = {
        'type': (int, 0, "{:d}"),
        'linestyle': (int, LineStyle.SOLID, "{:d}"),
        'linewidth': (float, 1.0, "{:3.1f}"),
        'color': (int, Color.BLACK, "{:d}"),
        'pattern': (int, 1, "{:d}"),
        'background_color': (int, Color.WHITE, "{:d}"),
        'background_pattern': (int, 0, "{:d}"),
        }


class _BaseLine(_BaseOutput):
    """baseline of dataset"""
    _marker = 'baseline'
    _attrs = {
        'type': (int, 0, '{:d}'),
        'baseline_switch': (bool, Switch.OFF, '{:s}'),
        }


class _DropLine(_BaseOutput):
    """baseline of dataset"""
    _marker = 'dropline'
    _attrs = {
        'dropline_switch': (bool, Switch.OFF, '{:s}'),
        }


class Fill(_BaseOutput):
    """Fill of dataset"""
    NONE = 0
    SOLID = 1
    OPAQUE = 2

    _marker = 'fill'
    _attrs = {
        'type': (int, NONE, '{:d}'),
        'rule': (int, 0, '{:d}'),
        'color': (int, 1, '{:d}'),
        'pattern': (int, 1, '{:d}'),
        }


class _Default(_BaseOutput):
    """_Default options at head"""
    _marker = "default"
    _attrs = {
        "linewidth": (float, 1., "{:3.1f}"),
        "linestyle": (int, LineStyle.SOLID, "{:d}"),
        "color": (int, 1, "{:d}"),
        "pattern": (int, 1, "{:d}"),
        "font": (int, 0, "{:d}"),
        "char_size": (float, 1., "{:8f}"),
        "symbol_size": (float, 1., "{:8f}"),
        "sformat": (str, "%.8g", "\"{:s}\""),
        }
    def __init__(self, **kwargs):
        _BaseOutput.__init__(self, **kwargs)


class Annotation(_BaseOutput):
    """dataset annotation"""
    _marker = "avalue"
    _attrs = {
        "avalue_switch": (bool, Switch.OFF, "{:s}"),
        "type": (int, 2, "{:d}"),
        "char_size": (float, 1., "{:8f}"),
        "font": (int, 0, "{:d}"),
        "color": (int, 1, "{:d}"),
        "rot": (int, 0, "{:d}"),
        "format": (str, "general", "{:s}"),
        "prec": (int, 3, "{:d}"),
        "append": (str, "\"\"", "{:s}"),
        "prepend": (str, "\"\"", "{:s}"),
        "offset": (list, [0.0, 0.0], "{:8f} , {:8f}"),
        }
    def __init__(self, **kwargs):
        _BaseOutput.__init__(self, **kwargs)


class Symbol(_BaseOutput):
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

    _marker = "symbol"
    _attrs = {
        "type": (bool, CIRCLE, "{:d}"),
        "size": (float, 1., "{:8f}"),
        "color": (int, 1, "{:d}"),
        "pattern": (int, 1, "{:d}"),
        "fill_color": (int, 1, "{:d}"),
        "fill_pattern": (int, 1, "{:d}"),
        "linewidth": (float, 1, "{:3.1f}"),
        "linestyle": (int, LineStyle.SOLID, "{:d}"),
        "char": (int, 1, "{:d}"),
        "char_font": (int, 0, "{:d}"),
        "skip": (int, 0, "{:d}"),
        }


class _Page(_BaseOutput):
    """_Page"""
    _marker = "page"
    _attrs = {
        "size": (list, [792, 612], "{:d}, {:d}"),
        "scroll": (float, 0.05, "{:.0%}"),
        "inout": (float, 0.05, "{:.0%}"),
        "background_fill_switch": (bool, Switch.ON, "{:s}"),
        }
    def __init__(self, **kwargs):
        _BaseOutput.__init__(self, **kwargs)


class _TimesStamp(_BaseOutput):
    """Timestamp"""
    _marker = "timestamp"
    _attrs = {
        'timestamp_switch': (bool, Switch.OFF, "{:s}"),
        'color': (int, 1, "{:d}"),
        'rot': (int, 0, "{:d}"),
        'font': (int, 0, "{:d}"),
        'char_size': (float, 1.0, "{:8f}"),
        'def': (str, time.strftime("%a %b %d %H:%M:%S %Y"), "\"{:s}\""),
        }
    def __init__(self, **kwargs):
        _BaseOutput.__init__(self, **kwargs)


class _Tick(_BaseOutput):
    """_Tick of axis

    Args:
        major (float) : value between major ticks
        minor (float) : value between minor ticks
    """
    _marker = 'tick'
    _attrs = {
        'tick_switch': (bool, Switch.ON, "{:s}"),
        'tick_position': (bool, Position.IN, "{:s}"),
        'default': (int, 6, "{:d}"),
        'major': (float, 1., "{:3.1f}"),
        'major_size': (float, 0.5, "{:8f}"),
        'major_color': (float, 1., "{:3.1f}"),
        'major_linewidth': (float, 2.0, "{:3.1f}"),
        'major_linestyle': (int, LineStyle.SOLID, "{:d}"),
        'major_grid_switch': (bool, Switch.OFF, "{:s}"),
        'minor': (float, 1., "{:3.1f}"),
        'minor_color': (float, 1., "{:3.1f}"),
        'minor_size': (float, 1., "{:8f}"),
        'minor_ticks': (int, 1, "{:d}"),
        'minor_grid_switch': (bool, Switch.OFF, "{:s}"),
        'minor_linewidth': (float, 2.0, "{:3.1f}"),
        'minor_linestyle': (int, LineStyle.SOLID, "{:d}"),
        'place_rounded': (str, True, "{:s}"),
        'place_position': (bool, Position.BOTH, "{:s}"),
        'spec_type': (str, None, "{:s}"),
        }

# TODO set custom ticks and its output
    def set_custom_ticks(self):
        """set custom ticks for axis"""
        raise NotImplementedError


class _Bar(_BaseOutput):
    """_Axis bar"""
    _marker = 'bar'
    _attrs = {
        'bar_switch': (bool, Switch.ON, '{:s}'),
        'color': (int, Color.BLACK, '{:d}'),
        'linestyle': (int, LineStyle.SOLID, '{:d}'),
        'linewidth': (float, 2., '{:3.1f}'),
        }


class _Label(_BaseOutput):
    """_Axis label"""
    _marker = 'label'
    _attrs = {
        'layout': (str, 'para', '{:s}'),
        'place_position': (bool, Position.AUTO, '{:s}'),
        'char_size': (float, 1.5, "{:8f}"),
        'font': (int, 0, "{:d}"),
        'color': (int, Color.BLACK, "{:d}"),
        'place': (str, "normal", "{:s}"),
        }

    def __init__(self, label=None, **kwargs):
        if label is None:
            self.label = ""
        self.label = str(self.label)
        _BaseOutput.__init__(self, *kwargs)

    def set_label(self, s):
        """set the label to s

        Args:
            s (str or string-convertable)
        """
        _logger.debug("setting label to %s", s)
        self.label = str(s)
        _logger.debug("label set: %s", self.label)

    def export(self):
        _logger.debug("exporting label: %s", self.label)
        slist = [self._marker + " \"{:s}\"".format(self.label),]
        slist += _BaseOutput.export(self)
        return slist

class _TickLabel(_BaseOutput):
    """Label of axis tick"""
    _marker = 'ticklabel'
    _attrs = {
        'ticklabel_switch': (bool, Switch.ON, "{:s}"),
        'format': (str, "general", "{:s}"),
        'formula': (str, "", "\"{:s}\""),
        'append': (str, "", "\"{:s}\""),
        'prepend': (str, "", "\"{:s}\""),
        "prec": (int, 5, "{:d}"),
        'angle': (int, 0, "{:d}"),
        'font': (int, 0, "{:d}"),
        'color': (int, Color.BLACK, "{:d}"),
        'skip': (int, 0, "{:d}"),
        'stagger': (int, 0, "{:d}"),
        'place': (str, "normal", "{:s}"),
        'offset_switch': (bool, Switch.AUTO, "{:s}"),
        'offset': (list, [0.00, 0.01], "{:8f} , {:8f}"),
        'start_type_switch': (bool, Switch.AUTO, "{:s}"),
        'start': (float, 0.0, "{:8f}"),
        'stop_type_switch': (bool, Switch.AUTO, "{:s}"),
        'stop': (float, 0.0, "{:8f}"),
        'char_size': (float, 1.5, "{:8f}"),
        }
    def __init__(self, **kwargs):
        _BaseOutput.__init__(self, **kwargs)

class Errorbar(_BaseOutput):
    """Errorbar of dataset"""
    _marker = 'errorbar'
    _attrs = {
        'errorbar_switch': (bool, Switch.ON, '{:s}'),
        'place_position': (bool, Position.BOTH, '{:s}'),
        'color': (int, Color.BLACK, '{:d}'),
        'pattern': (int, 1, '{:d}'),
        'size': (float, 1.0, '{:8f}'),
        'linewidth': (float, 1.0, '{:3.1f}'),
        'linestyle': (int, LineStyle.SOLID, '{:d}'),
        'riser_linewidth': (float, 1.0, '{:3.1f}'),
        'riser_linestyle': (int, LineStyle.SOLID, '{:d}'),
        'riser_clip_switch': (bool, Switch.OFF, '{:s}'),
        'riser_clip_length': (float, 0.1, '{:8f}'),
        }


class _Axis(_BaseOutput, _Affix):
    """Axis of graph

    Args:
        axis (str) : in ['x', 'y', 'altx', 'alty']
    """
    _marker = 'axis'
    _attrs = {
        'axis_switch': (bool, Switch.ON, '{:s}'),
        'type': (list, ["zero", "false"], '{:s} {:s}'),
        'offset': (list, [0.0, 0.0], '{:8f} , {:8f}'),
        }
    def __init__(self, axis='x', **kwargs):
        assert axis in ['x', 'y', 'altx', 'alty']
        self._bar = _Bar()
        self._tick = _Tick()
        self._ticklabel = _TickLabel()
        self._label = _Label()
        _BaseOutput.__init__(self, **kwargs)
        _Affix.__init__(self, affix=axis, is_prefix=True)

    def export(self):
        if self.axis_switch is Switch.OFF:
            return [self._affix + self._marker + "  " + Switch.get_str(Switch.OFF),]
        slist = _BaseOutput.export(self) 
        header = [self._bar, self._label, self._tick, self._ticklabel]
        for x in header:
            slist += [self._affix + self._marker + " " + i for i in x.export()]
        return slist

    def _set_tick(self, **kwargs):
        self._tick._set(**kwargs)

    def _set_ticklabel(self, **kwargs):
        self._ticklabel._set(**kwargs)

    def _set_label(self, s=None, **kwargs):
        """set the label of axis"""
        if s:
            self._label.set_label(s)
        self._label._set(*kwargs)

    def set_label(self, s=None, **kwargs):
        """set the label of axis

        TODO
            change arguments to emulate matplotlib behavior
        """
        self._set_label(s=s, **kwargs)


class _Axes(_BaseOutput, _Affix):
    """_Axes object for graph

    Args:
        axes ('x' or 'y')
    """
    _marker = 'axes'
    _attrs = {
        'scale': (str, 'Normal', "{:s}"),
        'invert_switch': (bool, Switch.OFF, "{:s}")
        }
    def __init__(self, axes, **kwargs):
        assert axes in ['x', 'y']
        _BaseOutput.__init__(self, **kwargs)
        _Affix.__init__(self, affix=axes, is_prefix=True)


class _Dataset(_BaseOutput, _Affix):
    """Object of grace dataset

    Args:
        index (int) : index of the dataset
        *xyz : input data
        datatype (str) :
        label (str) :
        comment (str) :
    """
    _marker = 's'
    _attrs = {
        'hidden': (str, False, '{:s}'),
        'type': (str, 'xy', '{:s}'),
        'legend': (str, "", "\"{:s}\""),
        'comment': (str, "", "\"{:s}\""),
        }
    def __init__(self, index, *xyz, datatype=None, **kwargs):
        # pop out to avoid duplicate arguments
        legend = kwargs.pop("legend", "")
        if legend is None:
            legend = ""
        comment = kwargs.pop("comment", "")
        if comment is None:
            comment = ""
        self.data = Data(*xyz, datatype=datatype,
                         label=legend, comment=comment, **kwargs)
        _BaseOutput.__init__(self, type=self.data.datatype, **kwargs)
        _Affix.__init__(self, affix=index, is_prefix=False)
        # insert back to avoid losing information during superclass init
        self.legend = legend
        self.comment = comment
        self._symbol = Symbol()
        self._line = Line()
        self._baseline = _BaseLine()
        self._dropline = _DropLine()
        self._fill = Fill()
        self._avalue = Annotation()
        self._errorbar = Errorbar()
        kwargs.pop('type', None)

    @property
    def label(self):
        """string. label mark of the dataset"""
        return self.legend

    def export(self):
        """Export the header part of dataset"""
        slists = _BaseOutput.export(self)
        to_exports = [self._symbol,
                      self._line,
                      self._baseline,
                      self._dropline,
                      self._fill,
                      self._avalue,
                      self._errorbar,]
        for ex in to_exports:
            slists += [self._marker + self._affix + " " + i for i in ex.export()]
        return slists

    def export_data(self, igraph):
        """Export the data part"""
        slist = ['@target G' + str(igraph) + '.' + self._marker.upper() + self._affix,
                 '@type ' + self.type,]
        slist.extend(self.data.export())
        slist.append('&')
        return slist


class Dataset(_Dataset):
    """Dataset object for users"""

    def __init__(self, index, *xyz, datatype=None, label=None, comment=None, **kwargs):
        if label is None:
            label = ""
        _Dataset.__init__(self, index, *xyz, datatype=datatype, 
                          legend=label, comment=comment, **kwargs)


class _Graph(_BaseOutput, _Affix):
    """Graph object for internal use

    Args:
        index (int)"""
    _marker = 'g'
    _attrs = {
        'hidden': (str, False, '{:s}'),
        'type': (str, 'XY', '{:s}'),
        'stacked': (str, False, '{:s}'),
        'bar_hgap': (float, 0.0, '{:8f}'),
        'fixedpoint_switch': (bool, Switch.OFF, '{:s}'),
        'fixedpoint_type': (int, 0, '{:d}'),
        'fixedpoint_xy': (list, [0.0, 0.0], '{:8f}, {:8f}'),
        'fixedpoint_format': (list, ['general', 'general'], '{:s} {:s}'),
        'fixedpoint_prec': (list, [6, 6], '{:d}, {:d}'),
        }
    def __init__(self, index, **kwargs):
        self._index = index
        self._world = _World()
        self._stackworld = _StackWorld()
        self._view = _View()
        self._znorm = _Znorm()
        self._title = _Title()
        self._subtitle = _SubTitle()
        self._xaxes = _Axes('x')
        self._yaxes = _Axes('y')
        self._xaxis = _Axis('x')
        self._yaxis = _Axis('y')
        self._altxaxis = _Axis('altx', axis_switch=Switch.OFF)
        self._altyaxis = _Axis('alty', axis_switch=Switch.OFF)
        self._legend = _Legend()
        self._frame = _Frame()
        self._datasets = []
        _BaseOutput.__init__(self, **kwargs)
        _Affix.__init__(self, index, is_prefix=False)

    def __getitem__(self, i):
        return self._datasets[i]

    def export(self):
        """export the header of graph, including `with g` part and data header"""
        slist = []
        slist += _BaseOutput.export(self)
        slist.append("with g" + self._affix)
        header = [self._world, self._stackworld,
                  self._znorm, self._view, self._title,
                  self._subtitle, self._xaxes, self._yaxes,
                  self._xaxis, self._yaxis,
                  self._altxaxis, self._altyaxis,
                  self._legend, self._frame, *self._datasets]
        for x in header:
            _logger.debug("marker: %s", x._marker)
            slist += ["    " + s for s in x.export()]
        return slist

    def export_data(self):
        """export the dataset part"""
        slist = []
        for ds in self._datasets:
            slist += ds.export_data(igraph=self._index)
        return slist


    @property
    def ndata(self):
        """Number of datasets in current graph"""
        return len(self._datasets)

    def _set_axis(self, axis, **kwargs):
        """set axis"""
        d = {'x': self._xaxis, 'y': self._yaxis, 'altx': self._altxaxis, 'alty': self._altyaxis}
        try:
            ax = d.get(axis)
        except KeyError:
            raise ValueError("axis name %s is not supported. %s" % (axis, d.keys()))
        ax._set(**kwargs)

    def set_xlimit(self, xmin=None, xmax=None):
        """set limits of x axis"""
        if xmin:
            self._world.set('xmin', xmin)
        if xmax:
            self._world.set('xmax', xmax)

    def set_ylimit(self, ymin=None, ymax=None):
        """set limits of y axis"""
        if ymin:
            self._world.set('ymin', ymin)
        if ymax:
            self._world.set('ymax', ymax)

    def set_xaxis(self, **kwargs):
        """set x axis"""
        self._set_axis('x', **kwargs)

    def set_yaxis(self, **kwargs):
        """set x axis"""
        self._set_axis('y', **kwargs)

    def add(self, *xyz, datatype=None, label=None, comment=None, **errors):
        """Add dataset"""
        ds = Dataset(self.ndata, *xyz, datatype=datatype, label=label, comment=comment, **errors)
        self._datasets.append(ds)

    def set_xlabel(self, s, **kwargs):
        """set x label of graph to s"""
        self._xaxis.set_label(s, **kwargs)

    def set_ylabel(self, s, **kwargs):
        """set y label of graph to s"""
        self._yaxis.set_label(s, **kwargs)

# Class for users

class Graph(_Graph):
    """Graph object for users to operate"""

    def __init__(self, index=0, xmin=None, xmax=None, ymin=None, ymax=None,
                 **kwargs):
        _Graph.__init__(self, index=index, **kwargs)
        self.set_xaxis(xmin=xmin, xmax=xmax)
        self.set_yaxis(ymin=ymin, ymax=ymax)


class Plot:
    """the general control object for the grace plot

    Args:
        qtgrace (bool) : if true, QtGrace comments will be added

    Public attributes:

    Public methods:

    Private attributes:
        _head (str)
        _graphs (list)
        _font (_Font)
        _use_qtgrace (bool)

    Private methods:
    """
    
    def __init__(self, rows=1, cols=1, qtgrace=False):
        self._comment_head = ["# Grace project file", "#"]
        # header that seldom needs to change
        self._head = ["version 50122",
                      "link page off",
                      "reference date 0",
                      "date wrap off",
                      "date wrap year 1950",
                      "background color 0",
                      ]
        self._page = _Page()
        self._regions = [_Region(i) for i in range(5)]
        self._font = _Font()
        self._cm = _ColorMap()
        self._timestamp = _TimesStamp()
        self._default = _Default()
        self._graphs = []
        self._set_graph_alignment(rows, cols)
        self._use_qtgrace = qtgrace

    def _set_graph_alignment(self, rows, cols):
        """Set the graph alignment"""
        n = rows * cols
        for i in range(n):
            self._graphs.append(Graph(index=i))

    def __str__(self):
        """TODO print the whole agr file"""
        slist = [*self._head,]
        headers = [self._page, self._font, self._cm,
                   self._default, self._timestamp, *self._regions]
        for h in headers:
            slist += h.export()
        for g in self._graphs:
            slist += g.export()
        # add @ to each header line
        slist = self._comment_head + ["@" + v for v in slist]
        # export dataset header
        # export all data
        for g in self._graphs:
            slist += g.export_data()
        return "\n".join(slist)

    def set_default(self, **kwargs):
        """set default format"""
        self._default = _Default(**kwargs)

    def __getitem__(self, i):
        return self._get_graph(i)

    def get(self, i):
        """Get the Graph object of index i"""
        return self._get_graph(i)

    def _get_graph(self, i):
        """Get the Graph object of index i"""
        try:
            return self._graphs[i]
        except IndexError:
            raise IndexError(f"G.{i} does not exist")

    def add(self, *xyz, igraph=0, datatype=None, 
            label=None, comment=None, **errors):
        """Add a data set to graph `igraph`"""
        self._graphs[igraph].add(*xyz, datatype=datatype, label=label,
                                 comment=comment, **errors)

    def set_xtick(self, igraph=0, **kwargs):
        """setup ticks of x axis of graph `igraph`"""
        self._graphs[igraph].set_xtick(**kwargs)

    def set_ytick(self, igraph=0, **kwargs):
        """setup ticks of y axis of graph `igraph`"""
        self._graphs[igraph].set_ytick(**kwargs)

    def set_xlabel(self, s, igraph=0, **kwargs):
        """set string s as the label of x axis of graph `igraph`"""
        self._graphs[igraph].set_xlabel(s, **kwargs)

    def set_ylabel(self, s, igraph=0, **kwargs):
        """set string s as the label of y axis of graph `igraph`"""
        self._graphs[igraph].set_ylabel(s, **kwargs)

    def set_xaxis(self, igraph=0, **kwargs):
        """set up x-axis of graph"""
        self._graphs[igraph].set_xaxis(**kwargs)

    def set_yaxis(self, igraph=0, **kwargs):
        """set up y-axis of graph"""
        self._graphs[igraph].set_yaxis(**kwargs)

    def set_xlimit(self, xmin=None, xmax=None, igraph=0):
        """set xlimit of a graph

        Args:
            graph (int)
            xmin (float)
            xmax (float)
        """
        self._graphs[igraph].set_xlimit(xmin=xmin, xmax=xmax)

    def set_ylimit(self, ymin=None, ymax=None, igraph=0):
        """set ylimit of a graph

        Args:
            graph (int)
            ymin (float)
            ymax (float)
        """
        self._graphs[igraph].set_ylimit(ymin=ymin, ymax=ymax)

    def export(self, file=sys.stdout, mode='w'):
        """Export grace plot file to `fn`

        Args:
            file (str or file handle)
            mode (str) : used only when `file` is set to a filename
        """
        if isinstance(file, str):
            fp = open(file, mode)
            print(self.__str__(), file=fp)
            fp.close()
            return
        if isinstance(file, TextIOWrapper):
            print(self.__str__(), file=file)
            return
        raise ValueError

    @classmethod
    def double_y(cls):
        """Create a double-y-axis plot"""
        raise NotImplementedError


