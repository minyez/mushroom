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
from collections.abc import Iterable
from copy import deepcopy
from numpy import shape

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

    def get_color(self, color):
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
            raise ValueError("colro name {:s} is not found".format(name))

    def get_rgb(self, i):
        """get the rgb value of color with its code"""
        r, g, b, _ = self._map[i]
        return r, g, b

    def has_color(self, name):
        """Check if the color name is already defined"""
        return name in self._cn

plot_colormap = _ColorMap()


class _IntConstMap:
    """base class for geting the integer constant from string

    pair should be overwritten for each subclass"""
    pair = {}

    @classmethod
    def get(cls, marker):
        """get the integer constant from s

        Args:
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
                return cls.pair.get(marker.lower())
            except KeyError:
                return ValueError("unknown marker \"{:s}\" for {:s}".format(marker.lower(),
                                                                            cls.__name__))
        if isinstance(marker, int):
            return marker
        raise TypeError("should be str or int")


class Color(_IntConstMap):
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
        "grey": GREY,
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
        marker = plot_colormap.get_color(marker)
        return _IntConstMap(cls, marker)


class Pattern(_IntConstMap):
    """Pattern"""
    NONE = 0
    SOLID = 1
    pair = {
        "none" : NONE,
        "solid": SOLID,
        }


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


class LineStyle(_IntConstMap):
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


class Justf(_IntConstMap):
    """Justification of text"""
    LEFT = 0
    CENTER = 1
    RIGHT = 2

    pair = {
        "left" : LEFT,
        "center": CENTER,
        "right": RIGHT,
        }


class Switch(_IntConstMap):
    """Class for switch control"""
    ON = 1
    AUTO = -1
    OFF = 0
    pair = { "on": ON, "auto": AUTO, "off": OFF}

    @classmethod
    def get_str(cls, i):
        """get the corresponding attribute string"""
        d = {cls.ON: "on", cls.AUTO: "auto", cls.OFF: "off", True: "on", False: "off"}
        return d.get(i)


class Position(_IntConstMap):
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
        _Region.__init__(self, index, r_switch=switch, linestyle=ls, linewidth=lw,
                         type=rt, color=color, line=line)
        _raise_unknown_attr(self, *kwargs)

    def set(self, switch=None, ls=None, lw=None, rt=None,
            color=None, line=None, **kwargs):
        self._set(r_switch=switch, linestyle=ls, linewidth=lw,
                  type=rt, color=color, line=line)
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
    def __init__(self, title=None, font=None, size=None, color=None, **kwargs):
        _Title.__init__(self, title_comment=title, size=size, color=color, font=font)
        _raise_unknown_attr(self, *kwargs)
    
    def set(self, title=None, font=None, size=None, color=None, **kwargs):
        self._set(title_comment=title, size=size, color=color, font=font)
        _raise_unknown_attr(self, *kwargs)
    

class _SubTitle(_TitleLike):
    """title of graph"""
    _marker = 'subtitle'
    _attrs = dict(**_TitleLike._attrs)
    _attrs[_marker+'_comment'] = (bool, "", "\"{:s}\"")

class SubTitle(_SubTitle):
    """user interface of title"""
    def __init__(self, subtitle=None, font=None, size=None, color=None, **kwargs):
        _SubTitle.__init__(self, subtitle_comment=subtitle, size=size, color=color, font=font)
        _raise_unknown_attr(self, *kwargs)

    def set(self, subtitle=None, font=None, size=None, color=None, **kwargs):
        self._set(subtitle_comment=subtitle, size=size, color=color, font=font)
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
    """stack world of graph"""
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
        'linewidth': (float, 1.0, "{:3.1f}"),
        'color': (int, Color.BLACK, "{:d}"),
        'pattern': (int, 1, "{:d}"),
        }
    
class Line(_Line):
    """User interface of line object"""
    def __init__(self, lt=None, color=None, pattern=None, width=None, style=None, **kwargs):
        _Line.__init__(self, type=lt, color=Color.get(color), pattern=Pattern.get(pattern),
                       linewidth=width, linestyle=LineStyle.get(style))
        _raise_unknown_attr(self, *kwargs)

    def set(self, lt=None, color=None, pattern=None, width=None, style=None, **kwargs):
        self._set(type=lt, color=Color.get(color), pattern=Pattern.get(pattern),
                  linewidth=width, linestyle=LineStyle.get(style))
        _raise_unknown_attr(self, *kwargs)


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
        _Box.__init__(self, color=color, pattern=pattern, linewidth=lw,
                      linestyle=ls, fill_color=fc, fill_pattern=fp)
        _raise_unknown_attr(self, *kwargs)

    def set(self, color=None, pattern=None, lw=None, ls=None,
            fc=None, fp=None, **kwargs):
        self._set(color=color, pattern=pattern, linewidth=lw,
                  linestyle=ls, fill_color=fc, fill_pattern=fp)
        _raise_unknown_attr(self, *kwargs)


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
        self.box = Box()
        _BaseOutput.__init__(self, **kwargs)

    def export(self):
        slist = _BaseOutput.export(self) + \
                [self._marker + " " + i for i in self.box.export()]
        return slist

    def set_box(self, **kwargs):
        """set the attribute of legend box"""
        self.box.set(**kwargs)


class Legend(_Legend):
    """User interface of legend object"""
    # TODO Box arguments
    def __init__(self, switch=None, loc=None, loctype=None, font=None,
                 color=None, length=None, vgap=None, hgap=None, invert=None,
                 charsize=None, **kwargs):
        _Legend.__init__(self, legend_switch=switch, legend_location=loc, loctype=loctype,
                         font=font, color=color, length=length, vgap=vgap, hgap=hgap,
                         invert=invert, char_size=charsize)
        _raise_unknown_attr(self, *kwargs)

    def set(self, switch=None, loc=None, loctype=None, font=None,
            color=None, length=None, vgap=None, hgap=None, invert=None,
            charsize=None, **kwargs):
        self._set(legend_switch=switch, legend_location=loc, loctype=loctype,
                  font=font, color=color, length=length, vgap=vgap, hgap=hgap,
                  invert=invert, char_size=charsize)
        _raise_unknown_attr(self, *kwargs)

class _Frame(_BaseOutput, _IntConstMap):
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


class Frame(_Frame):
    """User interface of frame"""
    def __init__(self, ft=None, ls=None, lw=None, color=None, pattern=None,
                 bgc=None, bgp=None, **kwargs):
        _Frame.__init__(self, type=ft, linestyle=ls, linewidth=lw, color=color,
                        pattern=pattern, background_pattern=bgp, background_color=bgc)
        _raise_unknown_attr(self, *kwargs)

    def set(self, ft=None, ls=None, lw=None, color=None, pattern=None,
            bgc=None, bgp=None, **kwargs):
        self._set(type=ft, linestyle=ls, linewidth=lw, color=color,
                  pattern=pattern, background_pattern=bgp, background_color=bgc)
        _raise_unknown_attr(self, *kwargs)


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
        _BaseLine.__init__(self, type=lt, baseline_switch=switch)
        _raise_unknown_attr(self, *kwargs)
    
    def set(self, lt=None, switch=None, **kwargs):
        self._set(type=lt, baseline_switch=switch)
        _raise_unknown_attr(self, *kwargs)


class DropLine(_BaseOutput):
    """baseline of dataset"""
    _marker = 'dropline'
    _attrs = {
        'dropline_switch': (bool, Switch.OFF, '{:s}'),
        }
    def set(self, switch=None, **kwargs):
        self._set(dropline_switch=switch)
        _raise_unknown_attr(self, *kwargs)


class _Fill(_BaseOutput, _IntConstMap):
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

class Fill(_Fill):
    """User interface of fill"""
    def __init__(self, ft=None, rule=None, color=None, pattern=None, **kwargs):
        _Fill.__init__(self, type=ft, rule=rule, color=color, pattern=pattern)
        _raise_unknown_attr(self, *kwargs)
    
    def set(self, ft=None, rule=None, color=None, pattern=None, **kwargs):
        self._set(type=ft, rule=rule, color=color, pattern=pattern)
        _raise_unknown_attr(self, *kwargs)

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

class Default(_Default):
    """User interface of default setup"""
    def __init__(self, lw=None, ls=None, color=None, pattern=None, font=None,
                 charsize=None, symbolsize=None, sformat=None, **kwargs):
        _Default.__init__(self, linewidth=lw, linestyle=ls, pattern=pattern, color=color,
                          font=font, char_size=charsize, symbol_size=symbolsize,
                          sformat=sformat)
        _raise_unknown_attr(self, *kwargs)

    def set(self, lw=None, ls=None, color=None, pattern=None, font=None,
            charsize=None, symbolsize=None, sformat=None, **kwargs):
        self._set(linewidth=lw, linestyle=ls, pattern=pattern, color=color,
                  font=font, char_size=charsize, symbol_size=symbolsize,
                  sformat=sformat)
        _raise_unknown_attr(self, *kwargs)


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
        _Annotation.__init__(self, avalue_switch=switch, type=at, char_size=charsize, font=font,
                             color=color, rot=rot, format=af, prec=prec, append=append,
                             prepend=prepend, offset=offset)
        _raise_unknown_attr(self, *kwargs)

    def set(self, switch=None, at=None, rot=None, color=None, prec=None, font=None,
            charsize=None, offset=None, append=None, prepend=None, af=None, **kwargs):
        self._set(avalue_switch=switch, type=at, char_size=charsize, font=font,
                  color=color, rot=rot, format=af, prec=prec, append=append, prepend=prepend,
                  offset=offset)
        _raise_unknown_attr(self, *kwargs)


class _Symbol(_BaseOutput, _IntConstMap):
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
    START = 10
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
        "start": START,
        "character": CHARACTER,
    }

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


class Symbol(_Symbol):
    """user interface of symbol"""
    def __init__(self, st=None, size=None, color=None, pattern=None,
                 fc=None, fp=None, lw=None, ls=None, char=None, charfont=None, skip=None,
                 **kwargs):
        _Symbol.__init__(self, type=st, size=size, color=color, pattern=pattern,
                         fill_color=fc, fill_pattern=fp, linewidth=lw, linestyle=ls,
                         char=char, char_font=charfont, skip=skip)
        _raise_unknown_attr(self, *kwargs)

    def set(self, st=None, size=None, color=None, pattern=None,
            fc=None, fp=None, lw=None, ls=None, char=None, charfont=None, skip=None,
            **kwargs):
        self._set(type=st, size=size, color=color, pattern=pattern,
                  fill_color=fc, fill_pattern=fp, linewidth=lw, linestyle=ls,
                  char=char, char_font=charfont, skip=skip)
        _raise_unknown_attr(self, *kwargs)


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
        _Page.__init__(self, size=size, scroll=scroll,
                       inout=inout, background_fill_switch=bgfill)
        _raise_unknown_attr(self, *kwargs)

    def set(self, size=None, scroll=None, inout=None, bgfill=None, **kwargs):
        self._set(size=size, scroll=scroll,
                  inout=inout, background_fill_switch=bgfill)
        _raise_unknown_attr(self, *kwargs)


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
        _TimesStamp.__init__(self, timestamp_switch=switch, color=color,
                             rot=rot, font=font, char_size=charsize)
        _raise_unknown_attr(self, *kwargs)

    def set(self, switch=None, color=None, rot=None, font=None, charsize=None, **kwargs):
        self._set(timestamp_switch=switch, color=color, rot=rot, font=font,
                  char_size=charsize)
        _raise_unknown_attr(self, *kwargs)

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

    def __init__(self, **kwargs):
        _BaseOutput.__init__(self, **kwargs)
        self.spec_ticks = None
        self.spec_labels = None
        self.spec_major = None

    def export(self):
        slist = _BaseOutput.export(self)
        if self.__getattribute__("spec_type") in ["ticks", "both"]:
            slist.append("{:s} spec {:d}".format(self._marker, len(self.spec_ticks)))
            for i, (loc, m) in enumerate(zip(self.spec_ticks, self.spec_major)):
                slist.append("{:s} {:s} {:d}, {:.3f}".format(self._marker, m, i, loc))
        if self.__getattribute__("spec_type") == "both":
            for i, (label, m) in enumerate(zip(self.spec_labels, self.spec_major)):
                if m == "major":
                    slist.append("ticklabel {:d} \"{:s}\"".format(i, label))
        return slist


class Tick(_Tick):
    """User interface of tick"""
    def __init__(self, major=None, mjc=None, mjs=None, mjlw=None, mjls=None, mjg=None,
                 minor=None, mic=None, mis=None, mit=None,
                 milw=None, mils=None, mig=None, **kwargs):
        # TODO consistency check
        _Tick.__init__(self, major=major, major_color=mjc, major_size=mjs,
                       major_grid_switch=mjg, major_linewidth=mjlw, major_linestyle=mjls,
                       minor=minor, minor_color=mic, minor_size=mis, minor_ticks=mit,
                       minor_grid_switch=mig, minor_linewidth=milw, minor_linestyle=mils)
        _raise_unknown_attr(self, *kwargs)

    def set_major(self, major=None, color=None, size=None,
                  lw=None, ls=None, grid=None, **kwargs):
        self._set(major=major, major_color=color, major_size=size,
                  major_grid_switch=grid,
                  major_linewidth=lw, major_linestyle=ls)
        _raise_unknown_attr(self, *kwargs)

    def set_minor(self, minor=None, color=None,
                  size=None, ticks=None, grid=None,
                  lw=None, ls=None, **kwargs):
        self._set(minor=minor, minor_color=color, minor_size=size,
                  minor_ticks=ticks, minor_grid_switch=grid,
                  minor_linewidth=lw, minor_linestyle=ls)
        _raise_unknown_attr(self, *kwargs)

    def set_place(self, rounded=None, place=None, **kwargs):
        self._set(place_rounded=rounded, place_position=place)
        _raise_unknown_attr(self, *kwargs)

    def set_spec(self, locs, labels=None, use_minor=None):
        """set custom ticks on axis.

        Note that locs should have same length as labels

        Args:
            locs (Iterable) : locations of custom ticks on the axis
            labels (Iterable) : labels of custom ticks
            use_minor (Iterable) : index of labels to use minor tick
        """
        if not isinstance(locs, Iterable):
            raise TypeError("locs should be Iterable, but got ", type(locs))
        self.__setattr__("spec_type", "ticks")
        self.spec_ticks = locs
        if labels:
            if len(labels) != len(locs):
                raise ValueError("labels should have the same length as locs")
            self.__setattr__("spec_type", "both")
            self.spec_labels = labels
        self.spec_major = ["major" for _ in self.spec_labels]
        if use_minor:
            for i in use_minor:
                self.spec_major[i] = "minor"


class _Bar(_BaseOutput):
    """_Axis bar"""
    _marker = 'bar'
    _attrs = {
        'bar_switch': (bool, Switch.ON, '{:s}'),
        'color': (int, Color.BLACK, '{:d}'),
        'linestyle': (int, LineStyle.SOLID, '{:d}'),
        'linewidth': (float, 2., '{:3.1f}'),
        }


class Bar(_Bar):
    """User interface of axis bar"""
    def __init__(self, switch=None, color=None, ls=None, lw=None, **kwargs):
        _Bar.__init__(self, bar_switch=switch, color=color, linestyle=ls, linewidth=lw)
        _raise_unknown_attr(self, *kwargs)

    def set(self, switch=None, color=None, ls=None, lw=None, **kwargs):
        self._set(bar_switch=switch, color=color, linestyle=ls, linewidth=lw)
        _raise_unknown_attr(self, *kwargs)


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
        self.label = label
        if label is None:
            self.label = ""
        self.label = str(self.label)
        if color:
            color = Color.get(color)
        _Label.__init__(self, layout=layout, place_position=position, char_size=charsize,
                        font=font, color=color, place=place)
        _raise_unknown_attr(self, *kwargs)

    def set(self, s=None, layout=None, position=None, charsize=None, font=None,
            color=None, place=None, **kwargs):
        """set the label to s

        Args:
            s (str or string-convertable) : the label of the axis
        """
        if s:
            self.label = str(s)
        self._set(layout=layout, color=color, place_position=position, char_size=charsize,
                  font=font, place=place)
        _raise_unknown_attr(self, *kwargs)

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
        switch (bool)
        tlf (str) : ticklabel format
    """
    def __init__(self, switch=None, tlf=None, formula=None, append=None, prepend=None, prec=None,
                 angle=None, font=None, color=None, skip=None, stagger=None,
                 place=None, offset=None, offset_switch=None, charsize=None,
                 start=None, stop=None, start_switch=None, stop_switch=None,
                 **kwargs):
        _TickLabel.__init__(self, ticklabel_switch=switch, format=tlf, formula=formula,
                            append=append, prepend=prepend, prec=prec, angle=angle, font=font,
                            color=color, skip=skip, stagger=stagger, place=place,
                            offset_switch=offset_switch, offset=offset,
                            start=start, start_type_switch=start_switch,
                            stop=stop, stop_type_switch=stop_switch, char_size=charsize)
        _raise_unknown_attr(self, *kwargs)

    def set(self, switch=None, tlf=None, formula=None, append=None, prepend=None, prec=None,
            angle=None, font=None, color=None, skip=None, stagger=None,
            place=None, offset=None, offset_switch=None, charsize=None,
            start=None, stop=None, start_switch=None, stop_switch=None,
            **kwargs):
        self._set(ticklabel_switch=switch, format=tlf, formula=formula, append=append,
                  prepend=prepend, prec=prec, angle=angle, font=font, color=color, skip=skip,
                  stagger=stagger, place=place, offset_switch=offset_switch, offset=offset,
                  start=start, start_type_switch=start_switch,
                  stop=stop, stop_type_switch=stop_switch, char_size=charsize)
        _raise_unknown_attr(self, *kwargs)


class _Errorbar(_BaseOutput):
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

class Errorbar(_Errorbar):
    """User interface of dataset errorbar appearance"""
    def __init__(self, switch=None, position=None, color=None, pattern=None, size=None,
                 lw=None, ls=None, rlw=None, rls=None, rc=None, rcl=None, **kwargs):
        _Errorbar.__init__(self, errorbar_switch=switch, place_position=position, color=color,
                           pattern=pattern, size=size, linewidth=lw, linestyle=ls,
                           riser_linewidth=rlw, riser_linestyle=rls,
                           riser_clip_switch=rc, riser_clip_length=rcl)
        _raise_unknown_attr(self, *kwargs)

    def set(self, switch=None, position=None, color=None, pattern=None, size=None,
            lw=None, ls=None, rlw=None, rls=None, rc=None, rcl=None, **kwargs):
        self._set(errorbar_switch=switch, place_position=position, color=color,
                  pattern=pattern, size=size, linewidth=lw, linestyle=ls,
                  riser_linewidth=rlw, riser_linestyle=rls,
                  riser_clip_switch=rc, riser_clip_length=rcl)
        _raise_unknown_attr(self, *kwargs)


class _Axis(_BaseOutput, _Affix):
    """Axis of graph
    """
    _marker = 'axis'
    _attrs = {
        'axis_switch': (bool, Switch.ON, '{:s}'),
        'type': (list, ["zero", "false"], '{:s} {:s}'),
        'offset': (list, [0.0, 0.0], '{:8f} , {:8f}'),
        }
    def __init__(self, axis='x', **kwargs):
        assert axis in ['x', 'y', 'altx', 'alty']
        _BaseOutput.__init__(self, **kwargs)
        _Affix.__init__(self, affix=axis, is_prefix=True)

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
    def __init__(self, axis='x', switch=None, at=None, offset=None,
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
        _Axis.__init__(self, axis=axis, axis_switch=switch, type=at, offset=offset)
        self._bar = Bar(switch=bar, color=bc, ls=bls, lw=blw)
        self._tick = Tick(major=major, mjc=mjc, mjs=mjs, mjlw=mjlw, mjls=mjls, mjg=mjg,
                          minor=minor, mic=mic, mis=mis, mit=mit, milw=milw, mils=mils, mig=mig)
        self._label = Label(label=label, layout=layout, position=position, charsize=lsize,
                            font=lfont, color=lc, place=lplace)
        self._ticklabel = TickLabel(switch=ticklabel, tlf=tlf, formula=formula, append=append,
                                    prepend=prepend, angle=angle, font=tlfont, color=tlc,
                                    skip=skip, stagger=stagger, offset=tloffset, charsize=tlsize,
                                    offset_switch=tlo_switch, start=start, stop=stop, place=tlplace,
                                    start_switch=start_switch, stop_switch=stop_switch)
        _raise_unknown_attr(self, *kwargs)

    def set(self, switch=None, at=None, offset=None, **kwargs):
        self._set(axis_switch=switch, type=at, offset=offset)
        _raise_unknown_attr(self, *kwargs)

    def export(self):
        if self.axis_switch is Switch.OFF:
            return [self._affix + self._marker + "  " + Switch.get_str(Switch.OFF),]
        slist = _BaseOutput.export(self) 
        header = [self._bar, self._label, self._tick, self._ticklabel]
        for x in header:
            slist += [self._affix + self._marker + " " + i for i in x.export()]
        return slist

    def set_major(self, **kwargs):
        self._tick.set_major(**kwargs)

    def set_minor(self, **kwargs):
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

class Axes(_Axes):
    """User interface of axes"""
    def __init__(self, axes, scale=None, invert=None, **kwargs):
        _Axes.__init__(self, axes, scale=scale, invert_switch=invert)
        _raise_unknown_attr(self, *kwargs)

    def set(self, scale=None, invert=None, **kwargs):
        self._set(scale=scale, invert_switch=invert)
        _raise_unknown_attr(self, *kwargs)

# TODO implement internal object _Dataset
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
        _Affix.__init__(self, affix=index, is_prefix=False)


class Dataset(_Dataset):
    """User interface of dataset object
    
    Args:
        index
        xyz (arraylike)
        datatype (str)
        label (str)
        comment (str)
        color (str) : global color control
        size (number) : symbol size
        lt (str) : line type
        lw (number) : linewidth
        ls (str/int) : line style
        lp (str/int) : line pattern
        lc (str/int) : line color
        keyword arguments (arraylike): error data
    """
    def __init__(self, index, *xyz, label=None, color=None, datatype=None, comment=None,
                 st=None, ssize=None, sc=None, sp=None, sfc=None, sfp=None,
                 slw=None, sls=None, char=None, charfont=None, skip=None,
                 lt=None, lw=None, lc=None, ls=None, lp=None,
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
        self._symbol = Symbol(st=st, color=sc, size=ssize, pattern=sp, fc=sfc, fp=sfp, lw=slw,
                              ls=sls, char=char, charfont=charfont, skip=skip)
        if lc is None:
            lc = color
        self._line = Line(lt=lt, color=lc, width=lw, style=ls, pattern=lp)
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
    """
    def __init__(self, index, xmin=None, ymin=None, xmax=None, ymax=None,
                 hidden=None, gt=None, stacked=None, barhgap=None,
                 fp=None, fpt=None, fpxy=None, fpform=None, fpprec=None,
                 title=None, subtitle=None,
                 **kwargs):
        # TODO user arguments
        _Graph.__init__(self, index, hidden=hidden, type=gt, stacked=stacked, bar_hgap=barhgap,
                        fixedpoint_switch=fp, fixedpoint_type=fpt, fixedpoint_xy=fpxy,
                        fixedpoint_format=fpform, fixedpoint_prec=fpprec)
        #_raise_unknown_attr(self, *kwargs)
        self._world = World()
        self.set_lim(xmin, ymin, xmax, ymax)
        self._stackworld = StackWorld()
        self._view = View()
        self._znorm = Znorm()
        self._title = Title(title=title)
        self._subtitle = SubTitle(subtitle=subtitle)
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
        self._set(hidden=hidden, type=gt, stacked=stacked, bar_hgap=barhgap,
                  fixedpoint_switch=fp, fixedpoint_type=fpt, fixedpoint_xy=fpxy,
                  fixedpoint_format=fpform, fixedpoint_prec=fpprec)
        _raise_unknown_attr(self, *kwargs)

    def __getitem__(self, i):
        return self._datasets[i]

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

    def _set_axis(self, axis, **kwargs):
        """set axis"""
        d = {'x': self._xaxis, 'y': self._yaxis, 'altx': self._altxaxis, 'alty': self._altyaxis}
        try:
            ax = d.get(axis)
        except KeyError:
            raise ValueError("axis name %s is not supported. %s" % (axis, d.keys()))
        ax.set(**kwargs)

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

    def set_view(self, xmin=None, ymin=None, xmax=None, ymax=None):
        """set the view (apperance in the plot) of graph on the plot"""
        pre = self._view.get_view()
        _logger.debug("view before %8f %8f %8f %8f", *pre)
        for i, v in enumerate([xmin, ymin, xmax, ymax]):
            if v is not None:
                pre[i] = v
        self._view.set_view(pre)
        _logger.debug("view after %8f %8f %8f %8f", *self._view.get_view())

    def set_xaxis(self, **kwargs):
        """set x axis"""
        self._set_axis('x', **kwargs)

    def set_yaxis(self, **kwargs):
        """set x axis"""
        self._set_axis('y', **kwargs)

    def set_altxaxis(self, **kwargs):
        """set x axis"""
        self._set_axis('altx', **kwargs)

    def set_altyaxis(self, **kwargs):
        """set x axis"""
        self._set_axis('alty', **kwargs)

    def plot(self, *xyz, **kwargs):
        """plot a dataset"""
        # check if a band structure like `y` data is parsed
        if len(xyz) == 2 and len(shape(xyz[1])) == 2:
            n = self.ndata
            ds = [Dataset(n, xyz[0], xyz[1][0], **kwargs),]
            for i, y in enumerate(xyz[1][1:]):
                ds.append(Dataset(n+i+1, xyz[0], y, **kwargs))
            self._datasets.extend(ds)
        else: 
            ds = Dataset(self.ndata, *xyz, **kwargs)
            self._datasets.append(ds)

    def set_xlabel(self, s, **kwargs):
        """set x label of graph to s"""
        self._xaxis.set_label(s, **kwargs)

    def set_ylabel(self, s, **kwargs):
        """set y label of graph to s"""
        self._yaxis.set_label(s, **kwargs)

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


# pylint: disable=too-many-locals
def _set_graph_alignment(rows, cols, hgap=0.02, vgap=0.02, **kwargs):
    """Set the graph alignment

    TODO:
        intricate handling of graph view with kwargs
    """
    # global min and max
    gxmin, gymin, gxmax, gymax = View._attrs['view_location'][1]
    width = (gxmax - gxmin - hgap * (cols-1)) / cols
    heigh = (gymax - gymin - vgap * (rows-1)) / rows
    _logger.debug("average graph width and height : %f %f", width, heigh)
    graphs = [] 
    # from left to right, upper to lower
    for row in range(rows):
        for col in range(cols):
            i = row * cols + col
            g = Graph(index=i)
            g.set_view(gxmin + (hgap+width) * col,
                       gymax - (vgap+heigh) * row - heigh,
                       gxmin + (hgap+width) * col + width,
                       gymax - (vgap+heigh) * row
                       )
            _logger.debug("graph view %8f %8f %8f %8f", *g._view.view_location)
            graphs.append(g)
            _logger.debug("graph view %8f %8f %8f %8f", *graphs[-1]._view.view_location)
    for i, g in enumerate(graphs):
        _logger.debug("initializting graphs %d done, view %8f %8f %8f %8f",
                      i, *g._view.view_location)
    if kwargs:
        raise NotImplementedError
    return graphs


class Plot:
    """the general control object for the grace plot

    Args:
        rows, cols (int)
        hgap, vgap (float)
        lw (number)
        ls (str/int)
        color (str/int)
        qtgrace (bool) : if true, QtGrace comments will be added 
    Public attributes:

    Public methods:

    Private attributes:
        _head (str)
        _graphs (list)
        _font (Font)
        _use_qtgrace (bool)

    Private methods:
    """
    def __init__(self, rows=1, cols=1, hgap=0.02, vgap=0.02,
                 lw=None, ls=None, color=None, pattern=None, font=None,
                 charsize=None, symbolsize=None, sformat=None,
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

    def get(self, i):
        """Get the Graph object of index i"""
        return self._get_graph(i)

    def _get_graph(self, i):
        """Get the Graph object of index i"""
        try:
            return self._graphs[i]
        except IndexError:
            raise IndexError(f"G.{i} does not exist")

    def plot(self, *xyz, igraph=0, **kwargs):
        """plot a data set to graph `igraph`

        Args:
            positional *xyz (arraylike)
            igraph (int)
            keyword arguments will parsed to Graph object
        """
        self._graphs[igraph].plot(*xyz, **kwargs)

    def add_object(self, objtype, **kwargs):
        """add object to the plot"""
        raise NotImplementedError

    def axhline(self):
        """add a horizontal line"""

    def axvline(self):
        """add a vertical line"""

    def title(self, title=None, igraph=0, **kwargs):
        """set the title of graph `igraph`"""
        self._graphs[igraph].set_title(title=title, **kwargs)

    def subtitle(self, subtitle=None, igraph=0, **kwargs):
        """set the subtitle of graph `igraph`"""
        self._graphs[igraph].set_subtitle(subtitle=subtitle, **kwargs)

    def xticks(self, igraph=0, **kwargs):
        """setup ticks of x axis of graph `igraph`"""
        self._graphs[igraph].xticks(**kwargs)

    def yticks(self, igraph=0, **kwargs):
        """setup ticks of y axis of graph `igraph`"""
        self._graphs[igraph].yticks(**kwargs)

    def xlabel(self, s, igraph=0, **kwargs):
        """set xlabel. emulate pylab.xlabel"""
        self._graphs[igraph].set_xlabel(s, **kwargs)

    def ylabel(self, s, igraph=0, **kwargs):
        """set ylabel. emulate pylab.ylabel"""
        self._graphs[igraph].set_ylabel(s, **kwargs)

    def set_xaxis(self, igraph=0, **kwargs):
        """set up x-axis of graph"""
        self._graphs[igraph].set_xaxis(**kwargs)

    def set_yaxis(self, igraph=0, **kwargs):
        """set up y-axis of graph"""
        self._graphs[igraph].set_yaxis(**kwargs)

    def set_xlim(self, xmin=None, xmax=None, igraph=0):
        """set xlimit of a graph

        Args:
            graph (int)
            xmin (float)
            xmax (float)
        """
        self._graphs[igraph].set_xlim(xmin=xmin, xmax=xmax)

    def set_ylim(self, ymin=None, ymax=None, igraph=0):
        """set ylimit of a graph

        Args:
            graph (int)
            ymin (float)
            ymax (float)
        """
        self._graphs[igraph].set_ylim(ymin=ymin, ymax=ymax)

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

