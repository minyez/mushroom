# -*- coding: utf-8 -*-
# pylint: disable=too-few-public-methods,missing-function-docstring
r"""A high-level Python interface to the Grace plotting package

The main purpose of this implementation is to write grace plot file
with similar methods to matplotlib, and without any concern about
whether xmgrace is installed or not.
Therefore, platform-related functions are generally discarded. (minyez)
"""
import sys
import time
from io import TextIOWrapper, StringIO
from collections.abc import Iterable
from copy import deepcopy
from numpy import shape, absolute, loadtxt

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
    _map = None
    _format = '{:s}'

    def __init__(self, marker, mapdict, form):
        self._marker = marker
        self._map = deepcopy(mapdict)
        self._format = form

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

    # add user defined color_map
    try:
        from mushroom.__config__ import color_map
        for c in color_map:
            _valid_rgb(*c)
            _colors.append(c)
        del color_map
    except (TypeError, ValueError):
        _logger.warning("user color_map is not loaded correctly")
    except ImportError:
        pass

    # check validity of pre-defined colormap
    # check if predefined rgb are valid, and there is no duplicate names
    _color_names = [i[3] for i in _colors]
    for color in _colors:
        _valid_rgb(*color)
    if len(_color_names) != len(set(_color_names)):
        raise ValueError('found duplicate color names')

    _map = {}
    for i, color in enumerate(_colors):
        _map[i] = color

    def __init__(self):
        _MapOutput.__init__(self, 'color', _ColorMap._map, _ColorMap._format)
        self._cn = _ColorMap._color_names

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

    def get(self, color):
        """return the color code

        Args:
            color (str, int)

        Returns:
            int
        """
        if isinstance(color, str):
            return self._get_color_code(color)
        if isinstance(color, int):
            if color in self._map:
                return color
            raise ValueError("color {:d} is not defined in the color map".format(color))
        raise TypeError("color input is not valid, use str or int", color)

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

    def _get_color_code(self, name):
        """get the map code of color `name`

        Args:
            name (str) : name of color, case-insensitive
        """
        try:
            return self._cn.index(name.lower())
        except ValueError:
            raise ValueError("color name {:s} is not found".format(name))

    def get_rgb(self, i):
        """get the rgb value of color with its code"""
        r, g, b, _ = self._map[i]
        return r, g, b

    def has_color(self, name):
        """Check if the color name is already defined"""
        return name in self._cn

plot_colormap = _ColorMap()


def _get_int_const(name, pair, marker):
    """get the integer constant in the pair for an integer constant mapping `name`

    Args:
        name (str) : name for the integer constant mapping
        pair (dict)
        marker (str or int): the marker of the constant.
            If str, it should be registered in pair.
            If int, it will be directly returned
    Raises:
        TypeError for other type
        ValueError for unknown constant

    Returns:
        int
    """

    if marker is None:
        return None
    if isinstance(marker, str):
        try:
            return pair.get(marker.lower())
        except KeyError:
            return ValueError("unknown marker \"{:s}\" for {:s}".format(marker.lower(), name))
    if isinstance(marker, int):
        return marker
    raise TypeError("should be str or int")


class Color:
    """Predefined color constant"""
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
    pair = {
        "white": WHITE, "w": WHITE,
        "black": BLACK, "k": BLACK,
        "red": RED, "r": RED,
        "green": GREEN, "g": GREEN,
        "blue": BLUE, "b": BLUE,
        "yellow": YELLOW, "y": YELLOW,
        "brown": BROWN,
        "grey": GREY, "gray": GREY, "e": GREY,
        "violet": VIOLET,
        "cyan": CYAN,
        "magenta": MAGENTA,
        "orange": ORANGE,
        "indigo": INDIGO,
        "maroon": MAROON,
        "turquoise": TURQUOISE,
        "green4": GREEN4,
        }
    @classmethod
    def get(cls, marker):
        if marker is None:
            return None
        try:
            return _get_int_const(cls.__name__, cls.pair, marker)
        except ValueError:
            return plot_colormap.get(marker)
        raise ValueError


class Pattern:
    """Pattern"""
    NONE = 0
    SOLID = 1
    pair = {
        "none" : NONE,
        "solid": SOLID,
        }
    @classmethod
    def get(cls, marker):
        return _get_int_const(cls.__name__, cls.pair, marker)


class Font(_MapOutput):
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

    def __init__(self):
        _MapOutput.__init__(self, Font._marker, Font._map, Font._format)

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

    pair = {
        "none" : NONE,
        "solid": SOLID, "-": SOLID,
        "dotted": DOTTED, "..": DOTTED,
        "dashed": DASHED, "--": DASHED,
        "longdashed": LONGDASHED, "---": LONGDASHED,
        "dotdashed": DOTDASHED, ".-": DOTDASHED,
        }

    @classmethod
    def get(cls, marker):
        return _get_int_const(cls.__name__, cls.pair, marker)


class Justf:
    """Justification of text"""
    LEFT = 0
    CENTER = 1
    RIGHT = 2

    pair = {
        "left" : LEFT,
        "center": CENTER,
        "right": RIGHT,
        }
    @classmethod
    def get(cls, marker):
        return _get_int_const(cls.__name__, cls.pair, marker)


class Switch:
    """Class for switch control"""
    ON = 1
    AUTO = -1
    OFF = 0
    pair = {"on": ON, "auto": AUTO, "off": OFF}

    @classmethod
    def get(cls, marker):
        if isinstance(marker, bool):
            return {True: cls.ON, False: cls.OFF}[marker]
        return _get_int_const(cls.__name__, cls.pair, marker)


    @classmethod
    def get_str(cls, i):
        """get the corresponding attribute string"""
        d = {cls.ON: "on", cls.AUTO: "auto", cls.OFF: "off",
             True: "on", False: "off", None: "off"}
        return d.get(i)


class Position:
    """Class for position contorl"""
    IN = -1
    BOTH = 0
    OUT = 1
    AUTO = 2
    pair = {
        "in": IN,
        "both": BOTH,
        "out": OUT,
        "auto": AUTO,
        }
    @classmethod
    def get(cls, marker):
        return _get_int_const(cls.__name__, cls.pair, marker)

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
    """abstract class for initializing and printing element object

    _attrs and _marker must be redefined,
    with _attrs as a tuple, each member a 4-member tuple, as
    name, type, default value, print format for each attribute

    When type is bool, it will be treated invidually as a special
    attribute.
    """
    _attrs = {None: [None, None, None]}
    _marker = ''

    def __init__(self, **kwargs):
        assert isinstance(self._attrs, dict)
        for x in self._attrs.values():
            assert len(x) == 3
        assert isinstance(self._marker, str)
        for attr, (typ, default, _) in self._attrs.items():
            _logger.debug("attr: %s type: %s", attr, typ)
            v = kwargs.get(attr, None)
            if v is None:
                v = default
            try:
                self.__getattribute__(attr)
            except AttributeError:
                if typ is not bool:
                    v = typ(v)
                elif attr.endswith('_location'):
                    v = list(v)
                self.__setattr__(attr, v)

    def _set(self, **kwargs):
        """backend method to set attributes"""
        if kwargs:
            if len(kwargs) < len(self._attrs):
                for k, v in kwargs.items():
                    _logger.debug("setting %s to %s", k, str(v))
                    if k in self._attrs and v is not None:
                        self.__setattr__(k, v)
            else:
                for k in self._attrs:
                    v = kwargs.get(k, None)
                    if v is not None:
                        self.__setattr__(k, v)
                        _logger.debug("setting %s to %s", k, str(v))

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

class Region(_Region):
    """user interface of region"""
    def __init__(self, index, switch=None, ls=None, lw=None, rt=None,
                 color=None, line=None, **kwargs):
        _Region.__init__(self, index, r_switch=Switch.get(switch), linestyle=LineStyle.get(ls),
                         linewidth=lw, type=rt, color=Color.get(color), line=line)
        _raise_unknown_attr(self, *kwargs)

    def set(self, switch=None, ls=None, lw=None, rt=None,
            color=None, line=None, **kwargs):
        self._set(r_switch=Switch.get(switch), linestyle=LineStyle.get(ls), linewidth=lw,
                  type=rt, color=Color.get(color), line=line)
        _raise_unknown_attr(self, *kwargs)


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

class Title(_Title):
    """user interface of title"""
    def __init__(self, title=None, font=None, fontsize=None, color=None, **kwargs):
        _Title.__init__(self, title_comment=title, size=fontsize,
                        color=Color.get(color), font=font)
        _raise_unknown_attr(self, *kwargs)
    
    def set(self, title=None, font=None, fontsize=None, color=None, **kwargs):
        self._set(title_comment=title, size=fontsize, color=Color.get(color), font=font)
        _raise_unknown_attr(self, *kwargs)

class _SubTitle(_TitleLike):
    """title of graph"""
    _marker = 'subtitle'
    _attrs = dict(**_TitleLike._attrs)
    _attrs[_marker+'_comment'] = (bool, "", "\"{:s}\"")

class SubTitle(_SubTitle):
    """user interface of title"""
    def __init__(self, subtitle=None, font=None, fontsize=None, color=None, **kwargs):
        _SubTitle.__init__(self, subtitle_comment=subtitle, size=fontsize,
                           color=Color.get(color), font=font)
        _raise_unknown_attr(self, *kwargs)

    def set(self, subtitle=None, font=None, fontsize=None, color=None, **kwargs):
        self._set(subtitle_comment=subtitle, size=fontsize, color=Color.get(color), font=font)
        _raise_unknown_attr(self, *kwargs)

def _set_loclike_attr(marker, form, *args, sep=', '):
    f = [form,] * len(args)
    return {marker + '_location': (bool, list(args), sep.join(f))}

def _get_corner(corner):
    try:
        return {'xmin':0, 'ymin':1, 'xmax':2, 'ymax':3}.get(corner)
    except KeyError:
        raise ValueError("invalid corner name ", corner)

class _WorldLike(_BaseOutput):
    """super class for object with only one attribute whose
    value is floats separated by comma

    """
    _marker = ''

    def get(self):
        return self.__getattribute__(self._marker + '_location')

    def set(self, loc):
        self.__setattr__(self._marker + '_location', loc)

class World(_WorldLike):
    """world of graph"""
    _marker = 'world'
    _attrs = _set_loclike_attr(_marker, '{:8f}', 0., 0., 1., 1.)

    def __init__(self, **kwargs):
        _WorldLike.__init__(self, **kwargs)
        self.set_world = self.set
        self.get_world = self.get

class StackWorld(_WorldLike):
    """stack world of graph"""
    _marker = 'stack_world'
    _attrs = _set_loclike_attr(_marker, '{:8f}', 0., 1., 0., 1.)

class View(_WorldLike):
    """View of graph on the image canvas """
    _marker = 'view'
    _attrs = _set_loclike_attr(_marker, '{:8f}', 0.15, 0.10, 1.20, 0.85)

    def __init__(self, **kwargs):
        _WorldLike.__init__(self, **kwargs)
        self.set_view = self.set
        self.get_view = self.get

class Znorm(_WorldLike):
    """stack world of graph"""
    _marker = 'znorm'
    _attrs = _set_loclike_attr('znorm', '{:d}', 1)

def _raise_unknown_attr(obj, *attrs):
    if attrs:
        raise ValueError("unsupported attributes for {:s}:".format(type(obj).__name__),
                         *attrs)

class _Line(_BaseOutput):
    """Line object of dataset"""
    _marker = 'line'
    _attrs = {
        'type': (int, 1, "{:d}"),
        'linestyle': (int, LineStyle.SOLID, "{:d}"),
        'linewidth': (float, 1.5, "{:3.1f}"),
        'color': (int, Color.BLACK, "{:d}"),
        'pattern': (int, 1, "{:d}"),
        }
    
class Line(_Line):
    """User interface of line object"""
    def __init__(self, lt=None, color=None, pattern=None, width=None, style=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _Line.__init__(self, type=lt, color=Color.get(color), pattern=Pattern.get(pattern),
                       linewidth=width, linestyle=LineStyle.get(style))

    def set(self, lt=None, color=None, pattern=None, width=None, style=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(type=lt, color=Color.get(color), pattern=Pattern.get(pattern),
                  linewidth=width, linestyle=LineStyle.get(style))


class _Box(_BaseOutput):
    """Box of legend for internal use"""
    _marker = 'box'
    _attrs = {
        'color': (int, Color.BLACK, '{:d}'),
        'pattern': (int, Pattern.SOLID, '{:d}'),
        'linewidth': (float, 1.0, '{:3.1f}'),
        'linestyle': (int, LineStyle.SOLID, '{:d}'),
        'fill_color': (int, Color.BLACK, '{:d}'),
        'fill_pattern': (int, Pattern.NONE, '{:d}'),
        }


class Box(_Box):
    """User interface of box of legend"""
    def __init__(self, color=None, pattern=None, lw=None, ls=None,
                 fc=None, fp=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _Box.__init__(self, color=Color.get(color), pattern=Pattern.get(pattern), linewidth=lw,
                      linestyle=LineStyle.get(ls), fill_color=Color.get(fc),
                      fill_pattern=Pattern.get(fp))

    def set(self, color=None, pattern=None, lw=None, ls=None,
            fc=None, fp=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(color=Color.get(color), pattern=Pattern.get(pattern), linewidth=lw,
                  linestyle=LineStyle.get(ls), fill_color=Color.get(fc),
                  fill_pattern=Pattern.get(fp))


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

# pylint: disable=too-many-locals
class Legend(_Legend):
    """User interface of legend object"""
    def __init__(self, switch=None, loc=None, loctype=None, font=None,
                 color=None, length=None, vgap=None, hgap=None, invert=None,
                 charsize=None,
                 bc=None, bp=None, blw=None, bls=None, bfc=None, bfp=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _Legend.__init__(self, legend_switch=Switch.get(switch), legend_location=loc,
                         loctype=loctype, font=font, color=Color.get(color),
                         length=length, vgap=vgap, hgap=hgap, invert=invert, char_size=charsize)
        self.box = Box(color=bc, pattern=bp, lw=blw, ls=bls, fc=bfc, fp=bfp)

    def export(self):
        return _Legend.export(self) + [self._marker + " " + i for i in self.box.export()]

    def set(self, switch=None, loc=None, loctype=None, font=None,
            color=None, length=None, vgap=None, hgap=None, invert=None,
            charsize=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(legend_switch=Switch.get(switch), legend_location=loc, loctype=loctype,
                  font=font, color=Color.get(color), length=length, vgap=vgap, hgap=hgap,
                  invert=invert, char_size=charsize)

    def set_box(self, **kwargs):
        """set the attribute of legend box"""
        self.box.set(**kwargs)


class _Frame(_BaseOutput):
    """frame"""
    CLOSED = 0
    HALFOPEN = 1
    BREAKTOP = 2
    BREAKBOT = 3
    BREAKLEFT = 4
    BREAKRIGHT = 5
    pair = {
        "closed": CLOSED,
        "halfopen": HALFOPEN,
        "breaktop": BREAKTOP,
        "breakbot": BREAKBOT,
        "breakleft": BREAKLEFT,
        "breakright": BREAKRIGHT,
        }

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

    @classmethod
    def get(cls, marker):
        return _get_int_const(cls.__name__, cls.pair, marker)

class Frame(_Frame):
    """User interface of frame"""
    def __init__(self, ft=None, ls=None, lw=None, color=None, pattern=None,
                 bgc=None, bgp=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _Frame.__init__(self, type=_Frame.get(ft), linestyle=LineStyle.get(ls), linewidth=lw,
                        color=Color.get(color), pattern=Pattern.get(pattern), 
                        background_pattern=Pattern.get(bgp),
                        background_color=Color.get(bgc))

    def set(self, ft=None, ls=None, lw=None, color=None, pattern=None,
            bgc=None, bgp=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(type=_Frame.get(ft), linestyle=LineStyle.get(ls), linewidth=lw,
                  color=Color.get(color), pattern=Pattern.get(pattern), 
                  background_pattern=Pattern.get(bgp),
                  background_color=Color.get(bgc))


class _BaseLine(_BaseOutput):
    """baseline of dataset"""
    _marker = 'baseline'
    _attrs = {
        'type': (int, 0, '{:d}'),
        'baseline_switch': (bool, Switch.OFF, '{:s}'),
        }

class BaseLine(_BaseLine):
    """User interface of baseline"""
    def __init__(self, lt=None, switch=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _BaseLine.__init__(self, type=lt, baseline_switch=Switch.get(switch))
    
    def set(self, lt=None, switch=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(type=lt, baseline_switch=Switch.get(switch))


class _DropLine(_BaseOutput):
    """baseline of dataset"""
    _marker = 'dropline'
    _attrs = {
        'dropline_switch': (bool, Switch.OFF, '{:s}'),
        }

class DropLine(_DropLine):
    """user interface of dataset baseline"""
    def __init__(self, switch=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _DropLine.__init__(self, dropline_switch=Switch.get(switch))

    def set(self, switch=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(dropline_switch=Switch.get(switch))


class _Fill(_BaseOutput):
    """Fill of dataset"""
    NONE = 0
    SOLID = 1
    OPAQUE = 2
    pair = {
        "none": NONE,
        "solid": SOLID,
        "opaque": OPAQUE,
        }

    _marker = 'fill'
    _attrs = {
        'type': (int, NONE, '{:d}'),
        'rule': (int, 0, '{:d}'),
        'color': (int, Color.BLACK, '{:d}'),
        'pattern': (int, Pattern.SOLID, '{:d}'),
        }

    @classmethod
    def get(cls, marker):
        return _get_int_const(cls.__name__, cls.pair, marker)

class Fill(_Fill):
    """User interface of fill"""
    def __init__(self, ft=None, rule=None, color=None, pattern=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _Fill.__init__(self, type=_Fill.get(ft), rule=rule, color=Color.get(color),
                       pattern=Pattern.get(pattern))
    
    def set(self, ft=None, rule=None, color=None, pattern=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(type=_Fill.get(ft), rule=rule, color=Color.get(color),
                  pattern=Pattern.get(pattern))


class _Default(_BaseOutput):
    """_Default options at head"""
    _marker = "default"
    _attrs = {
        "linewidth": (float, 1.5, "{:3.1f}"),
        "linestyle": (int, LineStyle.SOLID, "{:d}"),
        "color": (int, Color.BLACK, "{:d}"),
        "pattern": (int, 1, "{:d}"),
        "font": (int, 0, "{:d}"),
        "char_size": (float, 1.5, "{:8f}"),
        "symbol_size": (float, 1., "{:8f}"),
        "sformat": (str, "%.8g", "\"{:s}\""),
        }

class Default(_Default):
    """User interface of default setup"""
    def __init__(self, lw=None, ls=None, color=None, pattern=None, font=None,
                 charsize=None, symbolsize=None, sformat=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _Default.__init__(self, linewidth=lw, linestyle=LineStyle.get(ls),
                          pattern=Pattern.get(pattern), color=Color.get(color),
                          font=font, char_size=charsize, symbol_size=symbolsize,
                          sformat=sformat)

    def set(self, lw=None, ls=None, color=None, pattern=None, font=None,
            charsize=None, symbolsize=None, sformat=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(linewidth=lw, linestyle=LineStyle.get(ls),
                  pattern=Pattern.get(pattern), color=Color.get(color),
                  font=font, char_size=charsize, symbol_size=symbolsize,
                  sformat=sformat)


class _Annotation(_BaseOutput):
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

class Annotation(_Annotation):
    """user interface of data annotation"""
    def __init__(self, switch=None, at=None, rot=None, color=None, prec=None, font=None,
                 charsize=None, offset=None, append=None, prepend=None, af=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _Annotation.__init__(self, avalue_switch=Switch.get(switch), type=at, char_size=charsize,
                             font=font, color=Color.get(color), rot=rot, format=af, prec=prec,
                             append=append, prepend=prepend, offset=offset)

    def set(self, switch=None, at=None, rot=None, color=None, prec=None, font=None,
            charsize=None, offset=None, append=None, prepend=None, af=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(avalue_switch=Switch.get(switch), type=at, char_size=charsize,
                  font=font, color=Color.get(color), rot=rot, format=af, prec=prec,
                  append=append, prepend=prepend, offset=offset)


class _Symbol(_BaseOutput):
    """Symbols of marker

    Args:
        sym (int) : index of symbol, or use predefined Symbol"""
    NONE = 0
    CIRCLE = 1
    SQUARE = 2
    DIAMOND = 3
    TUP = 4
    TLEFT = 5
    TDOWN = 6
    TRIGHT = 7
    PLUS = 8
    CROSS = 9
    STAR  = 10
    CHARACTER = 11

    pair = {
        "none": NONE,
        "circle": CIRCLE,
        "o": CIRCLE,
        "square": SQUARE,
        "diamond": DIAMOND,
        "tup": TUP,
        "^": TUP,
        "tleft": TLEFT,
        "<": TLEFT,
        "tdown": TDOWN,
        "v": TDOWN,
        "tright": TRIGHT,
        ">": TRIGHT,
        "plus": PLUS,
        "+": PLUS,
        "cross": CROSS,
        "x": CROSS,
        "star": STAR,
        "character": CHARACTER,
    }

    _marker = "symbol"
    _attrs = {
        "type": (bool, CIRCLE, "{:d}"),
        "size": (float, 1., "{:8f}"),
        "color": (int, Color.BLACK, "{:d}"),
        "pattern": (int, 1, "{:d}"),
        "fill_color": (int, Color.BLACK, "{:d}"),
        "fill_pattern": (int, 1, "{:d}"),
        "linewidth": (float, 1, "{:3.1f}"),
        "linestyle": (int, LineStyle.SOLID, "{:d}"),
        "char": (int, 1, "{:d}"),
        "char_font": (int, 0, "{:d}"),
        "skip": (int, 0, "{:d}"),
        }

    @classmethod
    def get(cls, marker):
        return _get_int_const(cls.__name__, cls.pair, marker)

class Symbol(_Symbol):
    """user interface of symbol"""
    def __init__(self, st=None, size=None, color=None, pattern=None,
                 fc=None, fp=None, lw=None, ls=None, char=None, charfont=None, skip=None,
                 **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _Symbol.__init__(self, type=_Symbol.get(st), size=size, color=Color.get(color),
                         pattern=Pattern.get(pattern), fill_color=Color.get(fc),
                         fill_pattern=Pattern.get(fp), linewidth=lw, linestyle=LineStyle.get(ls),
                         char=char, char_font=charfont, skip=skip)

    def set(self, st=None, size=None, color=None, pattern=None,
            fc=None, fp=None, lw=None, ls=None, char=None, charfont=None, skip=None,
            **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(type=st, size=size, color=Color.get(color),
                  pattern=Pattern.get(pattern), fill_color=Color.get(fc),
                  fill_pattern=Pattern.get(fp), linewidth=lw, linestyle=LineStyle.get(ls),
                  char=char, char_font=charfont, skip=skip)


class _Page(_BaseOutput):
    """Page"""
    _marker = "page"
    _attrs = {
        "size": (list, [792, 612], "{:d}, {:d}"),
        "scroll": (float, 0.05, "{:.0%}"),
        "inout": (float, 0.05, "{:.0%}"),
        "background_fill_switch": (bool, Switch.ON, "{:s}"),
        }

class Page(_Page):
    """user interface of page"""
    def __init__(self, size=None, scroll=None, inout=None, bgfill=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _Page.__init__(self, size=size, scroll=scroll, inout=inout,
                       background_fill_switch=Switch.get(bgfill))

    def set(self, size=None, scroll=None, inout=None, bgfill=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(size=size, scroll=scroll, inout=inout,
                  background_fill_switch=Switch.get(bgfill))


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

class TimesStamp(_TimesStamp):
    """User interface of timestamp"""
    def __init__(self, switch=None, color=None, rot=None, font=None, charsize=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _TimesStamp.__init__(self, timestamp_switch=Switch.get(switch), color=Color.get(color),
                             rot=rot, font=font, char_size=charsize)

    def set(self, switch=None, color=None, rot=None, font=None, charsize=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(timestamp_switch=Switch.get(switch), color=Color.get(color),
                  rot=rot, font=font, char_size=charsize)


class _Tick(_BaseOutput):
    """Tick of axis
    """
    _marker = 'tick'
    _attrs = {
        'tick_switch': (bool, Switch.ON, "{:s}"),
        'tick_position': (bool, Position.IN, "{:s}"),
        'default': (int, 6, "{:d}"),
        'major': (float, 1., "{:3.1f}"),
        'major_size': (float, 0.5, "{:8f}"),
        'major_color': (float, 1., "{:3.1f}"),
        'major_linewidth': (float, 1.5, "{:3.1f}"),
        'major_linestyle': (int, LineStyle.SOLID, "{:d}"),
        'major_grid_switch': (bool, Switch.OFF, "{:s}"),
        'minor_color': (float, 1., "{:3.1f}"),
        'minor_size': (float, 1., "{:8f}"),
        'minor_ticks': (int, 1, "{:d}"),
        'minor_grid_switch': (bool, Switch.OFF, "{:s}"),
        'minor_linewidth': (float, 1.5, "{:3.1f}"),
        'minor_linestyle': (int, LineStyle.SOLID, "{:d}"),
        'place_rounded': (str, True, "{:s}"),
        'place_position': (bool, Position.BOTH, "{:s}"),
        'spec_type': (str, None, "{:s}"),
        }

    def __init__(self, **kwargs):
        _BaseOutput.__init__(self, **kwargs)
        self.spec_ticks = []
        self.spec_labels = []
        self.spec_majors = []

    def export(self):
        slist = _BaseOutput.export(self)
        if self.__getattribute__("spec_type") in ["ticks", "both"]:
            slist.append("{:s} spec {:d}".format(self._marker, len(self.spec_ticks)))
            for i, (loc, m) in enumerate(zip(self.spec_ticks, self.spec_majors)):
                slist.append("{:s} {:s} {:d}, {:.3f}".format(self._marker, m, i, loc))
        if self.__getattribute__("spec_type") == "both":
            for i, (label, m) in enumerate(zip(self.spec_labels, self.spec_majors)):
                if m == "major":
                    slist.append("ticklabel {:d}, \"{:s}\"".format(i, label))
        return slist

class Tick(_Tick):
    """User interface of axis tick"""
    def __init__(self, major=None, mjc=None, mjs=None, mjlw=None, mjls=None, mjg=None,
                 mic=None, mis=None, mit=None,
                 milw=None, mils=None, mig=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _Tick.__init__(self, major=major, major_color=Color.get(mjc), major_size=mjs,
                       major_grid_switch=Switch.get(mjg), major_linewidth=mjlw,
                       major_linestyle=LineStyle.get(mjls),
                       minor_color=Color.get(mic), minor_size=mis, minor_ticks=mit,
                       minor_grid_switch=Switch.get(mig), minor_linewidth=milw,
                       minor_linestyle=LineStyle.get(mils))

    def set(self, major=None, mjc=None, mjs=None, mjlw=None, mjls=None, mjg=None,
            mic=None, mis=None, mit=None, milw=None, mils=None,
            mig=None, **kwargs):
        """setup axis ticks
        Args:
            major (float) : distance between major ticks
            mjc, mic (str or int) : color of major and minor ticks
            mjs, mis (str or int) : tick style of major and minor ticks
        """
        _raise_unknown_attr(self, *kwargs)
        self._set(major=major, major_color=Color.get(mjc), major_size=mjs,
                  major_grid_switch=Switch.get(mjg), major_linewidth=mjlw,
                  major_linestyle=LineStyle.get(mjls),
                  minor_color=Color.get(mic), minor_size=mis, minor_ticks=mit,
                  minor_grid_switch=Switch.get(mig), minor_linewidth=milw,
                  minor_linestyle=LineStyle.get(mils))

    def set_major(self, major=None, color=None, size=None,
                  lw=None, ls=None, grid=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(major=major, major_color=Color.get(color), major_size=size,
                  major_grid_switch=Switch.get(grid),
                  major_linewidth=lw, major_linestyle=LineStyle.get(ls))

    def set_minor(self, color=None,
                  size=None, ticks=None, grid=None,
                  lw=None, ls=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(minor_color=Color.get(color), minor_size=size,
                  minor_ticks=ticks, minor_grid_switch=Switch.get(grid),
                  minor_linewidth=lw, minor_linestyle=LineStyle.get(ls))

    def set_place(self, rounded=None, place=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(place_rounded=rounded, place_position=Position.get(place))

    def set_spec(self, locs, labels=None, use_minor=None):
        """set custom specific ticks on axis.

        Note that locs should have same length as labels

        Args:
            locs (Iterable) : locations of custom ticks on the axis
            labels (Iterable) : labels of custom ticks
            use_minor (Iterable) : index of labels to use minor tick
        """
        if not isinstance(locs, Iterable):
            raise TypeError("locs should be Iterable, but got ", type(locs))
        # return immediately with empty tick locations
        if not locs:
            return
        self.__setattr__("spec_type", "ticks")
        spec_ticks = locs
        if labels:
            if len(labels) != len(locs):
                raise ValueError("labels should have the same length as locs")
            self.__setattr__("spec_type", "both")
        spec_major = ["major" for _ in labels]
        if use_minor:
            for i in use_minor:
                spec_major[i] = "minor"
        self.spec_ticks.extend(spec_ticks)
        self.spec_majors.extend(spec_major)
        self.spec_labels.extend(str(l) for l in labels)


class _Bar(_BaseOutput):
    """_Axis bar"""
    _marker = 'bar'
    _attrs = {
        'bar_switch': (bool, Switch.ON, '{:s}'),
        'color': (int, Color.BLACK, '{:d}'),
        'linestyle': (int, LineStyle.SOLID, '{:d}'),
        'linewidth': (float, 1.5, '{:3.1f}'),
        }

class Bar(_Bar):
    """User interface of axis bar"""
    def __init__(self, switch=None, color=None, ls=None, lw=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _Bar.__init__(self, bar_switch=switch, color=color, linestyle=ls, linewidth=lw)

    def set(self, switch=None, color=None, ls=None, lw=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(bar_switch=Switch.get(switch),
                  color=Color.get(color), linestyle=LineStyle.get(ls), linewidth=lw)


class _Label(_BaseOutput):
    """Axis label"""
    _marker = 'label'
    _attrs = {
        'layout': (str, 'para', '{:s}'),
        'place_position': (bool, Position.AUTO, '{:s}'),
        'char_size': (float, 1.5, "{:8f}"),
        'font': (int, 0, "{:d}"),
        'color': (int, Color.BLACK, "{:d}"),
        'place': (str, "normal", "{:s}"),
        }

class Label(_Label):
    """user interface of axis label"""
    def __init__(self, label=None, layout=None, position=None, charsize=None,
                 font=None, color=None, place=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self.label = label
        if label is None:
            self.label = ""
        self.label = str(self.label)
        _Label.__init__(self, layout=layout, place_position=Position.get(position),
                        char_size=charsize, font=font, color=Color.get(color), place=place)

    def set(self, s=None, layout=None, position=None, charsize=None, font=None,
            color=None, place=None, **kwargs):
        """set the label to s

        Args:
            s (str or string-convertable) : the label of the axis
        """
        _raise_unknown_attr(self, *kwargs)
        if s:
            self.label = str(s)
        self._set(layout=layout, color=Color.get(color),
                  place_position=Position.get(position), char_size=charsize,
                  font=font, place=place)

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

# pylint: disable=too-many-locals
class TickLabel(_TickLabel):
    """user interface of label of axis tick

    Args:
        switch (bool) : switch of tick label
        tlf (str) : ticklabel format
        formular (str)
    """
    def __init__(self, switch=None, tlf=None, formula=None, append=None, prepend=None, prec=None,
                 angle=None, font=None, color=None, skip=None, stagger=None,
                 place=None, offset=None, offset_switch=None, charsize=None,
                 start=None, stop=None, start_switch=None, stop_switch=None,
                 **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _TickLabel.__init__(self, ticklabel_switch=Switch.get(switch),
                            format=tlf, formula=formula,
                            append=append, prepend=prepend, prec=prec, angle=angle, font=font,
                            color=Color.get(color), skip=skip, stagger=stagger, place=place,
                            offset_switch=Switch.get(offset_switch), offset=offset,
                            char_size=charsize, start=start,
                            start_type_switch=Switch.get(start_switch),
                            stop=stop, stop_type_switch=Switch.get(stop_switch))

    def set(self, switch=None, tlf=None, formula=None, append=None, prepend=None, prec=None,
            angle=None, font=None, color=None, skip=None, stagger=None,
            place=None, offset=None, offset_switch=None, charsize=None,
            start=None, stop=None, start_switch=None, stop_switch=None,
            **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(ticklabel_switch=Switch.get(switch), format=tlf, formula=formula, append=append,
                  prepend=prepend, prec=prec, angle=angle, font=font, color=Color.get(color),
                  skip=skip, stagger=stagger, place=place, offset_switch=Switch.get(offset_switch),
                  offset=offset, start=start, start_type_switch=Switch.get(start_switch),
                  stop=stop, stop_type_switch=Switch.get(stop_switch), char_size=charsize)


class _Errorbar(_BaseOutput):
    """Errorbar of dataset"""
    _marker = 'errorbar'
    _attrs = {
        'errorbar_switch': (bool, Switch.ON, '{:s}'),
        'place_position': (bool, Position.BOTH, '{:s}'),
        'color': (int, Color.BLACK, '{:d}'),
        'pattern': (int, 1, '{:d}'),
        'size': (float, 1.0, '{:8f}'),
        'linewidth': (float, 1.5, '{:3.1f}'),
        'linestyle': (int, LineStyle.SOLID, '{:d}'),
        'riser_linewidth': (float, 1.5, '{:3.1f}'),
        'riser_linestyle': (int, LineStyle.SOLID, '{:d}'),
        'riser_clip_switch': (bool, Switch.OFF, '{:s}'),
        'riser_clip_length': (float, 0.1, '{:8f}'),
        }

class Errorbar(_Errorbar):
    """User interface of dataset errorbar appearance"""
    def __init__(self, switch=None, position=None, color=None, pattern=None, size=None,
                 lw=None, ls=None, rlw=None, rls=None, rc=None, rcl=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _Errorbar.__init__(self, errorbar_switch=Switch.get(switch),
                           place_position=Position.get(position), color=Color.get(color),
                           pattern=Pattern.get(pattern), size=size, linewidth=lw,
                           linestyle=LineStyle.get(ls), riser_linewidth=rlw,
                           riser_linestyle=LineStyle.get(rls), riser_clip_switch=Switch.get(rc),
                           riser_clip_length=rcl)

    def set(self, switch=None, position=None, color=None, pattern=None, size=None,
            lw=None, ls=None, rlw=None, rls=None, rc=None, rcl=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(errorbar_switch=Switch.get(switch),
                  place_position=Position.get(position), color=Color.get(color),
                  pattern=Pattern.get(pattern), size=size, linewidth=lw,
                  linestyle=LineStyle.get(ls), riser_linewidth=rlw,
                  riser_linestyle=LineStyle.get(rls), riser_clip_switch=Switch.get(rc),
                  riser_clip_length=rcl)


class _Axis(_BaseOutput, _Affix):
    """Axis of graph
    """
    _marker = 'axis'
    _attrs = {
        'axis_switch': (bool, Switch.ON, '{:s}'),
        'type': (list, ["zero", "false"], '{:s} {:s}'),
        'offset': (list, [0.0, 0.0], '{:8f} , {:8f}'),
        }
    def __init__(self, axis, **kwargs):
        assert axis in ['x', 'y', 'altx', 'alty']
        _BaseOutput.__init__(self, **kwargs)
        _Affix.__init__(self, axis, is_prefix=True)

class Axis(_Axis):
    """user interface of graph axis apperance

    Args:
        axis (str) : in ['x', 'y', 'altx', 'alty']
        switch (bool): 
        at (str) : axis type
        offset (2-member list):
        bar (bool)
        bc (str/int) : bar color
        bls (str/int) : bar line style
        blw (number)
        mjls (str/int) : major tick line style
    """

    ## pylint: disable=W0613
    #def __new__(cls, axis, **kwargs):
    #    inst = _Axis.__new__(cls)
    #    cls.created[axis].append(inst)
    #    return inst

    def __init__(self, axis, switch=None, at=None, offset=None,
                 bar=None, bc=None, bls=None, blw=None,
                 major=None, mjc=None, mjs=None, mjlw=None, mjls=None, mjg=None,
                 minor=None, mic=None, mis=None, mit=None,
                 milw=None, mils=None, mig=None,
                 label=None, layout=None, position=None, lsize=None,
                 lfont=None, lc=None, lplace=None,
                 ticklabel=None, tlf=None, formula=None, append=None, prepend=None,
                 angle=None, tlfont=None, tlc=None, skip=None, stagger=None,
                 tlplace=None, tloffset=None, tlo_switch=None, tlsize=None,
                 start=None, stop=None, start_switch=None, stop_switch=None,
                 **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _Axis.__init__(self, axis, axis_switch=Switch.get(switch), type=at, offset=offset)
        self._bar = Bar(switch=bar, color=bc, ls=bls, lw=blw)
        self._tick = Tick(major=major, mjc=mjc, mjs=mjs, mjlw=mjlw, mjls=mjls, mjg=mjg,
                          mic=mic, mis=mis, mit=mit, milw=milw, mils=mils, mig=mig)
        self._label = Label(label=label, layout=layout, position=position, charsize=lsize,
                            font=lfont, color=lc, place=lplace)
        self._ticklabel = TickLabel(switch=ticklabel, tlf=tlf, formula=formula, append=append,
                                    prepend=prepend, angle=angle, font=tlfont, color=tlc,
                                    skip=skip, stagger=stagger, offset=tloffset, charsize=tlsize,
                                    offset_switch=tlo_switch, start=start, stop=stop, place=tlplace,
                                    start_switch=start_switch, stop_switch=stop_switch)

    def set(self, switch=None, at=None, offset=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(axis_switch=Switch.get(switch), type=at, offset=offset)

    def export(self):
        if self.axis_switch is Switch.OFF:
            return [self._affix + self._marker + "  " + Switch.get_str(Switch.OFF),]
        slist = _BaseOutput.export(self) 
        header = [self._bar, self._label, self._tick, self._ticklabel]
        for x in header:
            slist += [self._affix + self._marker + " " + i for i in x.export()]
        return slist

    def bind(self, *axis):
        """Bind Axis objects

        Args:
            axis (Axis) : 
        """

    def set_major(self, **kwargs):
        """set major ticks"""
        self._tick.set_major(**kwargs)

    def set_minor(self, **kwargs):
        """set minor ticks"""
        self._tick.set_minor(**kwargs)

    def set_bar(self, **kwargs):
        self._bar.set(**kwargs)

    def set_tick(self, **kwargs):
        self._tick.set(**kwargs)

    def set_ticklabel(self, **kwargs):
        self._ticklabel.set(**kwargs)

    def set_label(self, s=None, **kwargs):
        """set the label of axis"""
        self._label.set(s, **kwargs)

    def set_spec(self, locs, labels=None, use_minor=False):
        """set specific tick marks and labels

        Args:
            locs (Iterable)
            labels (Iterable)
        """
        self._tick.set_spec(locs, labels=labels, use_minor=use_minor)


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
        _Affix.__init__(self, axes, is_prefix=True)

class Axes(_Axes):
    """User interface of axes"""
    def __init__(self, axes, scale=None, invert=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _Axes.__init__(self, axes, scale=scale, invert_switch=Switch.get(invert))

    def set(self, scale=None, invert=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(scale=scale, invert_switch=Switch.get(invert))


class _Dataset(_BaseOutput, _Affix):
    """Object of grace dataset

    Args:
        index (int) : index of the dataset
        *xyz : input data
        datatype (str) :
        legend (str) :
        comment (str) :
    """
    _marker = 's'
    _attrs = {
        'hidden': (str, False, '{:s}'),
        'type': (str, 'xy', '{:s}'),
        'legend': (str, "", "\"{:s}\""),
        'comment': (str, "", "\"{:s}\""),
        }
    def __init__(self, index, **kwargs):
        _BaseOutput.__init__(self, **kwargs)
        _Affix.__init__(self, index, is_prefix=False)

class Dataset(_Dataset):
    """User interface of dataset object
    
    Args:
        index
        xyz (arraylike)
        label (str)
        datatype (str)
        color (str) : global color control
        comment (str)
        symbol (str) : symbol type
        ssize (number) : symbol size
        sc (str) : symbol color
        sp (str) : symbol pattern
        line (str) : line type
        lw (number) : linewidth
        ls (str/int) : line style
        lp (str/int) : line pattern
        lc (str/int) : line color
        keyword arguments (arraylike): error data
    """
    def __init__(self, index, *xyz, label=None, color=None, datatype=None, comment=None,
                 symbol=None, ssize=None, sc=None, sp=None, sfc=None, sfp=None,
                 slw=None, sls=None, char=None, charfont=None, skip=None,
                 line=None, lw=None, lc=None, ls=None, lp=None,
                 baseline=None, blt=None, dropline=None, ft=None, rule=None, fc=None, fp=None,
                 anno=None, at=None, asize=None, ac=None, rot=None, font=None, af=None, prec=None,
                 prepend=None, append=None, offset=None,
                 errorbar=None, ebpos=None, ebc=None, ebp=None, ebsize=None, eblw=None,
                 ebls=None, ebrlw=None, ebrls=None, ebrc=None, ebrcl=None,
                 **errs):
        # pop comment and legend out to avoid duplicate arguments
        if label is None:
            label = ""
        if comment is None:
            comment = ""
        self.data = Data(*xyz, datatype=datatype,
                         label=label, comment=comment, **errs)
        _Dataset.__init__(self, index, type=self.data.datatype, comment=comment, legend=label)
        if sc is None:
            sc = color
        if sfc is None:
            sfc = color
        self._symbol = Symbol(st=symbol, color=sc, size=ssize, pattern=sp, fc=sfc, fp=sfp, lw=slw,
                              ls=sls, char=char, charfont=charfont, skip=skip)
        if lc is None:
            lc = color
        self._line = Line(lt=line, color=lc, width=lw, style=ls, pattern=lp)
        self._baseline = BaseLine(lt=blt, switch=baseline)
        self._dropline = DropLine(switch=dropline)
        if fc is None:
            fc = color
        self._fill = Fill(ft=ft, rule=rule, color=fc, pattern=fp)
        if ac is None:
            ac = color
        self._avalue = Annotation(switch=anno, at=at, rot=rot, charsize=asize, color=ac, font=font,
                                  af=af, append=append, prepend=prepend, prec=prec, offset=offset)
        if ebc is None:
            ebc = color
        self._errorbar = Errorbar(switch=errorbar, position=ebpos, color=ebc, pattern=ebp,
                                  size=ebsize, lw=eblw, ls=ebls, rlw=ebrlw, rls=ebrls, rc=ebrc,
                                  rcl=ebrcl)
    
    def xmin(self):
        """get the minimal value of abscissa"""
        return self.data.xmin()

    def xmax(self):
        """get the maximal value of abscissa"""
        return self.data.xmax()

    def min(self):
        """get the minimal value of data"""
        return self.data.min()

    def max(self):
        """get the maximal value of data"""
        return self.data.max()

    def set_symbol(self, **kwargs):
        self._symbol.set(**kwargs)

    def set_line(self, **kwargs):
        """set attributes of data line"""
        self._line.set(**kwargs)

    def set_baseline(self, **kwargs):
        """set attributes of baseline"""
        self._baseline.set(**kwargs)

    def set_dropline(self, **kwargs):
        """set attributes of dropline"""
        self._dropline.set(**kwargs)

    def set_fill(self, **kwargs):
        """set attributes of marker fill"""
        self._fill.set(**kwargs)

    def set_annotation(self, **kwargs):
        """set attributes of data annotation"""
        self._avalue.set(**kwargs)

    def set_errorbar(self, **kwargs):
        """set attributes of error bar"""
        self._errorbar.set(**kwargs)

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
            _logger.debug(type(ex).__name__)
            slists += [self._marker + self._affix + " " + i for i in ex.export()]
        return slists

    def export_data(self, igraph):
        """Export the data part"""
        slist = ['@target G' + str(igraph) + '.' + self._marker.upper() + self._affix,
                 '@type ' + self.type,]
        slist.extend(self.data.export())
        slist.append('&')
        return slist


class _Graph(_BaseOutput, _Affix):
    """Graph object, similar to Axes in matplotlib
    """
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
        _BaseOutput.__init__(self, **kwargs)
        _Affix.__init__(self, index, is_prefix=False)

# pylint: disable=too-many-locals
class Graph(_Graph):
    """user interface of grace graph

    Args:
        index (int)
        xmin, ymin, xmax, ymax
        gt : graph type
        title : title string
        subtitle : subtitle string
        tc : title color
        stc : subtitle color
    """
    def __init__(self, index, xmin=None, ymin=None, xmax=None, ymax=None,
                 hidden=None, gt=None, stacked=None, barhgap=None,
                 fp=None, fpt=None, fpxy=None, fpform=None, fpprec=None,
                 title=None, subtitle=None, tsize=None, stsize=None,
                 tc=None, stc=None,
                 **kwargs):
        _raise_unknown_attr(self, *kwargs)
        _Graph.__init__(self, index, hidden=hidden, type=gt, stacked=stacked, bar_hgap=barhgap,
                        fixedpoint_switch=Switch.get(fp), fixedpoint_type=fpt, fixedpoint_xy=fpxy,
                        fixedpoint_format=fpform, fixedpoint_prec=fpprec)
        self._world = World()
        self._if_xlim_set = any([xmin, xmax])
        self._if_ylim_set = any([ymin, ymax])
        self.set_lim(xmin, ymin, xmax, ymax)
        self._stackworld = StackWorld()
        self._view = View()
        self._znorm = Znorm()
        self._title = Title(title=title, fontsize=tsize, color=tc)
        self._subtitle = SubTitle(subtitle=subtitle, fontsize=stsize, color=stc)
        self._if_xtick_set = False
        self._if_ytick_set = False
        self._xaxes = _Axes('x')
        self._yaxes = _Axes('y')
        #self._altxaxes = _Axes('altx', switch=Switch.OFF)
        #self._altyaxes = _Axes('alty', switch=Switch.OFF)
        self._xaxis = Axis('x')
        self._yaxis = Axis('y')
        self._altxaxis = Axis('altx', switch=Switch.OFF)
        self._altyaxis = Axis('alty', switch=Switch.OFF)
        self._legend = Legend()
        self._frame = Frame()
        self._datasets = []

    def set(self, hidden=None, gt=None, stacked=None, barhgap=None,
            fp=None, fpt=None, fpxy=None, fpform=None, fpprec=None, **kwargs):
        _raise_unknown_attr(self, *kwargs)
        self._set(hidden=hidden, type=gt, stacked=stacked, bar_hgap=barhgap,
                  fixedpoint_switch=Switch.get(fp), fixedpoint_type=fpt, fixedpoint_xy=fpxy,
                  fixedpoint_format=fpform, fixedpoint_prec=fpprec)

    def __getitem__(self, i):
        return self._datasets[i]

    def xmin(self):
        """get the minimal value of x-data"""
        v = 0
        if self._datasets:
            v = min(ds.xmin() for ds in self._datasets)
        return v

    def xmax(self):
        """get the maximal value of x-data"""
        v = 1
        if self._datasets:
            v = max(ds.xmax() for ds in self._datasets)
        return v

    def min(self):
        """get the minimal value of y/z-data"""
        v = 0
        if self._datasets:
            v = min(ds.min() for ds in self._datasets)
        return v

    def max(self):
        """get the maximal value of y/z-data"""
        v = 1
        if self._datasets:
            v = max(ds.max() for ds in self._datasets)
        return v

    def tight_graph(self, nxticks=5, nyticks=5, xscale=1.1, yscale=1.1):
        """make the graph looks tight by adopting x/y min/max as axis extremes"""
        self.set_lim(xmin=self.xmin()-absolute(self.xmin())*(xscale-1.0),
                     xmax=self.xmax()+absolute(self.xmax())*(xscale-1.0),
                     ymin=self.min()-absolute(self.min())*(yscale-1.0),
                     ymax=self.max()+absolute(self.max())*(yscale-1.0))
        xmin, ymin, xmax, ymax = self.get_lim()
        # TODO optimize major tick determination
        if not self._if_xtick_set:
            self._xaxis.set_major(major=(xmax-xmin)/nxticks)
        if not self._if_ytick_set:
            self._yaxis.set_major(major=(ymax-ymin)/nyticks)
        
    def export(self):
        """export the header of graph, including `with g` part and data header"""
        slist = []
        slist += _BaseOutput.export(self)
        slist.append("with g" + self._affix)
        header = [self._world, self._stackworld,
                  self._znorm, self._view, self._title, self._subtitle,
                  self._xaxes, self._yaxes,
                  #self._altxaxes, self._altyaxes,
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

    def set_axis(self, axis, **kwargs):
        """set axis"""
        d = {'x': self._xaxis, 'y': self._yaxis, 'altx': self._altxaxis, 'alty': self._altyaxis}
        try:
            ax = d.get(axis)
        except KeyError:
            raise ValueError("axis name %s is not supported. %s" % (axis, d.keys()))
        ax.set(**kwargs)

    def get_axis(self, axis):
        """set axis
        
        Args:
            axis (str) : x, y, altx, alty
        """
        d = {'x': self._xaxis, 'y': self._yaxis, 'altx': self._altxaxis, 'alty': self._altyaxis}
        try:
            ax = d.get(axis)
        except KeyError:
            raise ValueError("axis name %s is not supported. %s" % (axis, d.keys()))
        return ax

    def set_xlim(self, xmin=None, xmax=None):
        """set limits of x axis"""
        self.set_lim(xmin=xmin, xmax=xmax)

    def set_ylim(self, ymin=None, ymax=None):
        """set limits of y axis"""
        self.set_lim(ymin=ymin, ymax=ymax)

    def set_lim(self, xmin=None, ymin=None, xmax=None, ymax=None):
        """set the limits (world) of graph"""
        pre = self._world.get_world()
        for i, v in enumerate([xmin, ymin, xmax, ymax]):
            if v is not None:
                pre[i] = v
        self._world.set_world(pre)

    def get_lim(self):
        """get the limits (world) of graph

        Returns
            tuple. xmin, ymin, xmax, ymax
        """
        return self._world.get_world()

    def set_view(self, xmin=None, ymin=None, xmax=None, ymax=None):
        """set the view (apperance in the plot) of graph on the plot"""
        pre = self._view.get_view()
        _logger.debug("view before %8f %8f %8f %8f", *pre)
        for i, v in enumerate([xmin, ymin, xmax, ymax]):
            if v is not None:
                pre[i] = v
        self._view.set_view(pre)
        _logger.debug("view after %8f %8f %8f %8f", *self._view.get_view())

    @property
    def x(self):
        """x axis"""
        return self._xaxis

    @property
    def y(self):
        """y axis"""
        return self._yaxis

    def set_xaxis(self, **kwargs):
        """set x axis"""
        self.set_axis(axis='x', **kwargs)

    def set_yaxis(self, **kwargs):
        """set x axis"""
        self.set_axis(axis='y', **kwargs)

    def set_altxaxis(self, **kwargs):
        """set x axis"""
        self.set_axis(axis='altx', **kwargs)

    def set_altyaxis(self, **kwargs):
        """set x axis"""
        self.set_axis(axis='alty', **kwargs)

    def plot(self, *xyz, **kwargs):
        """plot a dataset
        
        multiple y can be parsed along with one x.
        In this case, the keyword arguments except `label`
        will be parsed for each y. `label` will be parsed
        only for the first set
        """
        # check if a band structure like `y` data is parsed
        if len(xyz) == 2 and len(shape(xyz[1])) == 2:
            n = self.ndata
            ds = [Dataset(n, xyz[0], xyz[1][0], **kwargs),]
            kwargs.pop("label", None)
            for i, y in enumerate(xyz[1][1:]):
                ds.append(Dataset(n+i+1, xyz[0], y, **kwargs))
            self._datasets.extend(ds)
        else: 
            ds = Dataset(self.ndata, *xyz, **kwargs)
            self._datasets.append(ds)

    def set_legend(self, **kwargs):
        """set up the legend. For arguments, see Legend

        Particularly, a string can be parsed to loc, e.g. 'upper left',
        'lower right'. Available token:
            lower, middle, upper;
            left, center, right;
        """
        x = None
        y = None
        try:
            loc_token = kwargs["loc"]
            int(loc_token)
        except ValueError:
            try:
                loctype = kwargs.get("loctype")
                assert loctype == "world"
                xmin, ymin, xmax, ymax = self._world.get_world()
            except (KeyError, AssertionError):
                xmin, ymin, xmax, ymax = self._view.get_view()

            if loc_token.endswith("left"):
                x = 0.8 * xmin + 0.2 * xmax
            elif loc_token.endswith("right"):
                x = 0.3 * xmin + 0.7 * xmax
            elif loc_token.endswith("center"):
                x = 0.6 * xmin + 0.4 * xmax

            if loc_token.startswith("lower") or loc_token.startswith("bottom"):
                y = 0.9 * ymin + 0.1 * ymax
            elif loc_token.startswith("upper") or loc_token.startswith("top"):
                y = 0.1 * ymin + 0.9 * ymax
            elif loc_token.startswith("middle"):
                y = 0.5 * ymin + 0.5 * ymax

            loc = (x, y)
            if x is None or y is None:
                raise ValueError("invalid location token for legend: {}".format(kwargs["loc"]))
            kwargs["loc"] = loc
        except KeyError:
            pass

        self._legend.set(**kwargs)

    def set_legend_box(self, **kwargs):
        """set up the legend box"""
        self._legend.set_box(**kwargs)

    def set_xlabel(self, s, **kwargs):
        """set x label of graph to s"""
        self._xaxis.set_label(s, **kwargs)

    def set_ylabel(self, s, **kwargs):
        """set y label of graph to s"""
        self._yaxis.set_label(s, **kwargs)

    def set_xticklabel(self, **kwargs):
        """set x label of graph"""
        self._xaxis.set_ticklabel(**kwargs)

    def set_yticklabel(self, **kwargs):
        """set y label of graph"""
        self._yaxis.set_ticklabel(**kwargs)

    def set_title(self, title=None, **kwargs):
        """set the title string or its attributes"""
        if title:
            self._title.__setattr__('title_comment', title)
        self._title._set(**kwargs)

    def set_subtitle(self, subtitle=None, **kwargs):
        """set the subtitle string or its attributes"""
        if subtitle:
            self._subtitle.__setattr__('subtitle_comment', subtitle)
        self._subtitle._set(**kwargs)

class Arrow:
    """type of line arrow"""
    NONE = 0
    START = 1
    END = 2
    LINE = 0
    FILLED = 1
    OPAQUE = 2
    pair = {
        "none": NONE,
        "start": START,
        "end": END,
        "line": LINE,
        "filled": FILLED,
        "opaque": OPAQUE,
        }
    @classmethod
    def get(cls, marker):
        return _get_int_const(cls.__name__, cls.pair, marker)
    

class _DrawString(_BaseOutput):
    """class for string drawing"""
    _marker = 'string'
    _attrs = {
        "string_switch": (bool, Switch.ON, '{:s}'),
        # graph number when using for world coordinate
        "string_comment": (bool, 0, '{:s}'),
        "loctype": (str, "view", '{:s}'),
        "color": (int, Color.BLACK, '{:d}'),
        "rot": (int, 0, '{:d}'),
        "font": (int, 0, '{:d}'),
        "just": (int, Justf.LEFT, '{:d}'),
        "char_size": (float, 1.0, '{:.8f}'),
        "def": (str, "", '\"{:s}\"'),
        }
    # add string_location
    _attrs.update(_set_loclike_attr(_marker, '{:10f}', 0.0, 0.0))

class DrawString(_DrawString):
    """user interface of string drawing

    Args:
        s (str) : content of string
        xy (2-member list) : location of string
    """
    def __init__(self, s, xy, ig=None, color=None, just=None, charsize=None,
                 rot=None, font=None, **kwargs):
        loctype = "view"
        if ig:
            loctype = "world"
            ig = "g" + str(ig)
        _DrawString.__init__(self, loctype=loctype, color=Color.get(color), string_comment=ig,
                             just=Justf.get(just), rot=rot, char_size=charsize, font=font,
                             string_location=xy)
        self.__setattr__("def", s)
        _raise_unknown_attr(self, *kwargs)

    def export(self):
        return ["with " + self._marker,] + \
               ["    {:s}".format(s) for s in _DrawString.export(self)]


class _DrawLine(_BaseOutput):
    """class for line drawing"""
    _marker = 'line'
    _attrs = {
        "line_switch": (bool, Switch.ON, '{:s}'),
        # graph number when using for world coordinate
        "line_comment": (bool, 0, '{:s}'),
        "loctype": (str, "view", '{:s}'),
        "color": (int, Color.BLACK, '{:d}'),
        "linestyle": (int, LineStyle.SOLID, '{:d}'),
        "linewidth": (float, 1.5, '{:8f}'),
        "arrow": (int, Arrow.NONE, '{:d}'),
        "arrow_type": (int, Arrow.LINE, '{:d}'),
        "arrow_length": (float, 1.0, '{:8f}'),
        "arrow_layout": (list, [1.0, 1.0], '{:8f}, {:8}'),
        }
    # add string_location
    _attrs.update(_set_loclike_attr(_marker, '{:10f}', 0.0, 0.0, 0.0, 0.0))

class DrawLine(_DrawLine):
    """user interface of drawing line object

    Args:
        start, end (2-member Iterable)
    """
    def __init__(self, start, end, ig=None, color=None, lw=None, ls=None,
                 arrow=None, at=None, length=None, layout=None, **kwargs):
        loctype = "view"
        if ig:
            loctype = "world"
            ig = "g" + str(ig)
        if len(start) != 2 or len(end) != 2:
            raise TypeError("Endpoint of line should have both x and y")
        _DrawLine.__init__(self, loctype=loctype, color=Color.get(color), line_comment=ig,
                           linestyle=LineStyle.get(ls), linewidth=lw,
                           arrow=Arrow.get(arrow), arrow_type=Arrow.get(at),
                           arrow_length=length, arrow_layout=layout, line_location=(*start, *end))
        _raise_unknown_attr(self, *kwargs)

    def export(self):
        return ["with " + self._marker,] + ["    {:s}".format(s) for s in _DrawLine.export(self)] \
               + [self._marker + " def"]


class _DrawEllipse(_BaseOutput):
    """class for line drawing"""
    _marker = 'ellipse'
    _attrs = {
        _marker + "_switch": (bool, Switch.ON, '{:s}'),
        # graph number `gn` when using world coordinate
        _marker + "_comment": (bool, 0, '{:s}'),
        "loctype": (str, "view", '{:s}'),
        "color": (int, Color.BLACK, '{:d}'),
        "linestyle": (int, LineStyle.SOLID, '{:d}'),
        "linewidth": (float, 1.5, '{:8f}'),
        "fill_color": (int, Color.BLACK, '{:d}'),
        "fill_pattern": (int, Pattern.SOLID, '{:d}'),
        }
    # add string_location
    _attrs.update(_set_loclike_attr(_marker, '{:10f}', 0.0, 0.0, 0.0, 0.0))

class DrawEllipse(_DrawEllipse):
    """user interface of drawing line object
    
    Args:
        xy (2-member Iterable) : location of center
        width (float) : width of ellipse
        heigh (float) : height of ellipse. Use width if not set
    """
    def __init__(self, xy, width, heigh=None, ig=None, color=None, lw=None, ls=None,
                 fc=None, fp=None, **kwargs):
        loctype = "view"
        if ig:
            loctype = "world"
            ig = "g" + str(ig)
        if heigh is None:
            heigh = width
        x, y = xy
        _DrawEllipse.__init__(self, loctype=loctype, color=Color.get(color), ellipse_comment=ig,
                              linestyle=LineStyle.get(ls), linewidth=lw,
                              ellipse_location=(x-width/2, y+heigh/2, x+width/2, y-heigh/2),
                              fill_color=Color.get(fc),
                              fill_pattern=Pattern.get(fp))
        _raise_unknown_attr(self, *kwargs)

    def export(self):
        return ["with " + self._marker,] \
               + ["    {:s}".format(s) for s in _DrawEllipse.export(self)] \
               + [self._marker + " def"]

# ===== functions related to graph alignment =====
def __ga_regular(rows, cols, hgap, vgap, width_ratios=None, heigh_ratios=None):
    """regular graph alignment.

    By regular means graphs in the same column have the same width,
    and those in the same row have the same height.

    Args:
        rows, cols (int)
        hgap, vgap (float or Iterable)
        width_ratios, heigh_ratios (string): ratios of width/height, separated by colon.

    Returns:
        3 list, each has rows*cols members
    """
    if not isinstance(hgap, Iterable):
        hgap = [hgap,] * (cols-1)
    if not isinstance(vgap, Iterable):
        vgap = [vgap,] * (rows-1)
    if len(hgap) != cols-1 or len(vgap) != rows-1:
        raise ValueError("inconsistent number of rows/cols with vgap/hgap")

    # default global min and max
    gxmin, gymin, gxmax, gymax = View._attrs['view_location'][1]
    widths_all = gxmax - gxmin - sum(hgap)
    heighs_all = gymax - gymin - sum(vgap)
    if width_ratios:
        ws_cols = list(map(float, width_ratios.split(":")))
        ws_cols = [w * widths_all / sum(ws_cols) for w in ws_cols]
    else:
        ws_cols = [widths_all / cols,] * cols
    if heigh_ratios:
        hs_rows = list(map(float, heigh_ratios.split(":")))
        hs_rows = [h * heighs_all / sum(hs_rows) for h in hs_rows]
    else:
        hs_rows = [heighs_all / rows,] * rows
    if len(hs_rows) != rows or len(ws_cols) != cols:
        raise ValueError("inconsistent number of rows/cols with heighs/width_ratios")
    left_tops = []
    ws = []
    hs = []
    for row in range(rows):
        for col in range(cols):
            left = gxmin + sum(hgap[:col]) + sum(ws_cols[:col])
            top = gymax - sum(vgap[:row]) - sum(hs_rows[:row])
            left_tops.append((left, top))
            ws.append(ws_cols[col])
            hs.append(hs_rows[row])
    return left_tops, ws, hs

# pylint: disable=too-many-locals
def _set_graph_alignment(rows, cols, hgap=0.02, vgap=0.02, width_ratios=None, heigh_ratios=None,
                         **kwargs):
    """Set the graph alignment

    Args:
        rows, cols (int)
        hgap, vgap (float or Iterable)

    TODO:
        intricate handling of graph view with kwargs
    """
    # graphs from left to right, upper to lower
    if rows * cols == 0:
        raise ValueError("no graph is set!")

    graphs = []
    if not kwargs:
        left_up_corners, widths, heighs = __ga_regular(rows, cols, hgap, vgap,
                                                       width_ratios=width_ratios,
                                                       heigh_ratios=heigh_ratios)
    else:
        raise NotImplementedError("keywords for graph alignment not supported:", *kwargs)

    for i, ((left, top), w, h) in enumerate(zip(left_up_corners, widths, heighs)):
        g = Graph(index=i)
        g.set_view(xmin=left, xmax=left+w, ymin=top-h, ymax=top)
        graphs.append(g)
    for i, g in enumerate(graphs):
        _logger.debug("initializting graphs %d done, view %8f %8f %8f %8f",
                      i, *g._view.view_location)
    return graphs

# ===== main object =====
class Plot:
    """the general control object for the grace plot

    Args:
        rows, cols (int) : graph alignment
        hgap, vgap (float or Iterable) : horizontal and vertical gap between graphs
        lw (number) : default linewidth
        ls (str/int) : default line style
        color (str/int) : default color
        qtgrace (bool) : if true, QtGrace comments will be added 
    """
    def __init__(self, rows=1, cols=1, hgap=0.02, vgap=0.02,
                 lw=None, ls=None, color=None, pattern=None, font=None,
                 charsize=None, symbolsize=None, sformat=None,
                 width_ratios=None, heigh_ratios=None,
                 qtgrace=False, **kwargs):
        self._comment_head = ["# Grace project file", "#"]
        # header that seldom needs to change
        self._head = ["version 50122",
                      "link page off",
                      "reference date 0",
                      "date wrap off",
                      "date wrap year 1950",
                      "background color 0",
                      ]
        self._page = Page()
        self._regions = [_Region(i) for i in range(5)]
        self._font = Font()
        self._cm = plot_colormap
        self._timestamp = TimesStamp()
        self._default = Default(lw=lw, ls=ls, color=color, pattern=pattern,
                                font=font, charsize=charsize, symbolsize=symbolsize,
                                sformat=sformat)
        # drawing objects
        self._objects = []
        # set the graphs by alignment
        self._graphs = _set_graph_alignment(rows=rows, cols=cols, hgap=hgap, vgap=vgap,
                                            width_ratios=width_ratios, heigh_ratios=heigh_ratios,
                                            **kwargs)
        self._use_qtgrace = qtgrace

    def __str__(self):
        """print the whole agr file"""
        slist = [*self._head,]
        headers = [self._page, self._font, self._cm,
                   self._default, self._timestamp, *self._regions]
        for h in headers:
            slist += h.export()
        for g in self._graphs:
            slist += g.export()
        for o in self._objects:
            slist += o.export()
        # add @ to each header line
        slist = self._comment_head + ["@" + v for v in slist]
        # export all data
        for g in self._graphs:
            slist += g.export_data()
        return "\n".join(slist)

    def set_default(self, **kwargs):
        """set default format"""
        self._default.set(**kwargs)

    def __getitem__(self, i):
        return self._get_graph(i)

    def get(self, i: int = None):
        """Get the Graph object of index i
        
        Args:
            i (int) : index of graph.
                If not specified, all graphs are returned in a list
        """
        if i:
            return self._get_graph(i)
        return self._graphs

    def _get_graph(self, i: int) -> Graph:
        """Get the Graph object of index i"""
        try:
            return self._graphs[i]
        except IndexError:
            raise IndexError(f"G.{i} does not exist")

    def plot(self, *xyz, igraph=0, **kwargs):
        """plot a data set to graph `igraph`

        Args:
            positional *xyz (arraylike): x, y data. Error should be parsed to keyword arguments
            igraph (int) : index of graph to plot
            keyword arguments will parsed to Graph object
        """
        self._graphs[igraph].plot(*xyz, **kwargs)

    def text(self, s, xy, **kwargs):
        """add string text to the plot
        Args:
            s (str)
            xy (2-member list) : the location of text string
        """
        o = DrawString(s, xy, **kwargs)
        self._objects.append(o)

    def circle(self, xy, width, heigh=None, ig=None, color=None,
               lw=None, ls=None, fc=None, fp=None, **kwargs):
        """draw a circle on the plot

        Args:
            xy (2-member list)
            width (float)
            heigh (float)
            ig (int) : index of graph where the circle is drawn on
                If not None, the world coordinate will be used
            color (str/int)
            lw (float) : line width
            ls (str/int) : line style
            fc (str/int) : fill color
            fp (str/int) : fill pattern
        """
        o = DrawEllipse(xy, width, heigh=heigh, ig=ig, color=color, lw=lw,
                        ls=ls, fc=fc, fp=fp, **kwargs)
        self._objects.append(o)

    def axhline(self, y, xmin=None, xmax=None, **kwargs):
        """add a horizontal line"""

    def axvline(self, x, ymin=None, ymax=None, **kwargs):
        """add a vertical line"""

    def axline(self, start, end, **kwargs):
        """add a custom line"""
        o = DrawLine(start, end, **kwargs)
        self._objects.append(o)

    def title(self, title=None, igraph=0, **kwargs):
        """set the title of graph `igraph`"""
        self._graphs[igraph].set_title(title=title, **kwargs)

    def subtitle(self, subtitle=None, igraph=0, **kwargs):
        """set the subtitle of graph `igraph`"""
        self._graphs[igraph].set_subtitle(subtitle=subtitle, **kwargs)

    def xticks(self, **kwargs):
        """setup ticks of x axis of all graphs"""
        for g in self._graphs:
            g.xticks(**kwargs)

    def yticks(self, **kwargs):
        """setup ticks of y axis of all graphs"""
        for g in self._graphs:
            g.yticks(**kwargs)

    def xlabel(self, s, **kwargs):
        """set xlabel of all graphs. emulate pylab.xlabel"""
        for g in self._graphs:
            g.set_xlabel(s, **kwargs)

    def ylabel(self, s, **kwargs):
        """set ylabel of all graphs. emulate pylab.ylabel"""
        for g in self._graphs:
            g.set_ylabel(s, **kwargs)

    def set_xaxis(self, **kwargs):
        """set up x-axis of all graph"""
        for g in self._graphs:
            g.set_xaxis(**kwargs)

    def set_yaxis(self, **kwargs):
        """set up y-axis of all graphs"""
        for g in self._graphs:
            g.set_yaxis(**kwargs)

    def set_xlim(self, xmin=None, xmax=None):
        """set xlimit of all graphs

        Args:
            graph (int)
            xmin (float)
            xmax (float)
        """
        for g in self._graphs:
            g.set_xlim(xmin=xmin, xmax=xmax)

    def set_ylim(self, ymin=None, ymax=None):
        """set ylimit of all graphs

        Args:
            graph (int)
            ymin (float)
            ymax (float)
        """
        for g in self._graphs:
            g.set_ylim(ymin=ymin, ymax=ymax)

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
        raise TypeError("should be str or TextIOWrapper type")

    def tight_layout(self):
        """tight the layout of graph arrangments"""
        raise NotImplementedError

    def tight_graph(self, nxticks=5, nyticks=5, xscale=1.1, yscale=1.1):
        """make graph axis tight"""
        for g in self._graphs:
            g.tight_graph(nxticks=nxticks, nyticks=nyticks,
                          xscale=xscale, yscale=yscale)

    def savefig(self, figname, dpi=300):
        """save as figure file to `figname`
        """
        raise NotImplementedError

    # Templates
    # TODO write more and concrete templates
    @classmethod
    def bandstructure(cls):
        """template for a typical band structure plot"""
        p = Plot(1, 1)
        p[0].x.set_major(grid="on")
        return p

    @classmethod
    def dos(cls):
        """template for a typical dos plot"""
        p = Plot(1, 1)
        return p

    @classmethod
    def band_dos(cls, ratio="2:1"):
        """template of a plot with band graph on the left and dos on the right

        Args:
            ratio (str) : the ratio between widths of band and dos graphs
        """
        p = Plot(1, 2, hgap=0.0, width_ratios=ratio)
        # turn off band structure legend
        p[0].set_legend(switch=False)
        p[0].x.set_major(grid="on")
        # turn off y axis label (energy) in dos
        p[1].set_yticklabel(switch=False)
        return p

    @classmethod
    def double_yaxis(cls):
        """template for a double-yaxis plot"""
        p = Plot(1, 2)
        return p


def extract_data_from_agr(pagr):
    """extract all data from agr file

    Args:
        pagr (str) : path to the agr file

    Returns:
        list, type of each dataset; list, each member is a dataset as a 2d-array
    """
    starts = []
    ends = []
    types = []
    with open(pagr, 'r') as h:
        for i, l in enumerate(h.readlines()):
            if l.startswith("@type"):
                # exclude @type line
                starts.append(i+1)
                types.append(l.split()[-1].lower())
            if l == "&\n":
                ends.append(i)
    data = []
    
    with open(pagr, 'r') as h:
        lines = h.readlines()
        for i, (start, end) in enumerate(zip(starts, ends)):
            s = StringIO("".join(lines[start:end]))
            data.append(loadtxt(s, unpack=True))
    return types, data

