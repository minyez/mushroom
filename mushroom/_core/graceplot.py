# -*- coding: utf-8 -*-
# pylint: disable=too-few-public-methods,missing-function-docstring
r"""A high-level Python interface to the Grace plotting package

Lastest adapted from `jscatter` graceplot
see https://gitlab.com/biehl/jscatter/-/blob/master/src/jscatter/graceplot.py ,
commit d482bf214b8ef43fa853491d57b3ccbee02e5728

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

from numpy import shape
from mushroom._core.data import Data
from mushroom._core.logger import create_logger

__NAME__ = "graceplot"
_logger = create_logger(__NAME__)
del create_logger

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
    # check if predefined rgb are valid
    for i in range(_N_COLOR_MAP):
        assert i in _COLOR_MAP.keys()
        _valid_rgb(*_COLOR_MAP[i])

    def __init__(self):
        self._cm = _COLOR_MAP
        self._cn = _PREDEF_COLOR_NAMES
        self._n = _N_COLOR_MAP
        # add user defined color_map
        try:
            from mushroom.__config__ import color_map
            for r, g, b, name in color_map:
                self.add(r, g, b, name)
        except (ImportError, TypeError, ValueError):
            _logger.warning("load user color_map failed")

    def __getitem__(self, i):
        return self._cm[i][3]

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
        if name is None:
            name = 'color' + str(self.n)
        elif self._check_colorname_dup(name):
            raise ValueError(f"color {name} has been defined with code {self._cn[name]}")
        _valid_rgb(r, g, b, name=name)
        if self._cm is _COLOR_MAP:
            self._cm = deepcopy(_COLOR_MAP)
            self._cn = deepcopy(_PREDEF_COLOR_NAMES)
        n = self.n
        self._cm[n] = (r, g, b, name)
        self._cn[name] = n

    def _check_colorname_dup(self, name):
        """Check if the color name is already defined"""
        return name in self._cn.keys()

    def get_color_code(self, name):
        """get the map code of color `name`"""
        if isinstance(name, str) and self._check_colorname_dup(name):
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
        return self._check_colorname_dup(name)


class Color:
    """color
    Args:
        color (str or int)
    """
    _cm = ColorMap()

    def __init__(self, color):
        raise NotImplementedError


class Pattern:
    """Pattern"""
    NONE = 0
    SOLID = 1


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
        d = {cls.ON: "on", cls.AUTO: "auto", cls.OFF: "off"}
        return d.get(i)


class Position:
    """Class for position contorl"""
    IN = -1
    BOTH = 0
    OUT = 1
    @classmethod
    def get_str(cls, i):
        """get the correspond attribute string"""
        d = {cls.IN: "in", cls.BOTH: "both", cls.OUT: "out"}
        return d.get(i)

class Affix:
    """object to dataset (s0,s1...), graph (g0,g1...), axis (x,y,altx,alty), etc.

    Args:
        affix (str) : the content to add as the affix, 0,1,2 or x,y,altx,alty
        pre (bool) : if True, the content will be added as prefix. Otherwise as suffix
    """
    _marker = ""

    def __init__(self, affix, pre=False):
        if pre:
            self._marker = str(affix) + self._marker
        else:
            self._marker = self._marker + str(affix)
    

class BaseOutput:
    """abstract class for printing element object

    _attrs and _marker must be redefined,
    with _attrs as a tuple, each member a 4-member tuple, as
    name, type, default value, print format for each attribute

    When type is bool, it will be treated invidually as a special
    attribute.
    """
    _attrs = None
    _marker = None

    def __init__(self, **kwargs):
        assert isinstance(self._attrs, tuple)
        for i in self._attrs:
            assert len(i) == 4
        assert isinstance(self._marker, str)
        for attr, typ, default, _ in self._attrs:
            v = kwargs.get(attr, default)
            if typ is not bool:
                v = typ(v)
            self.__setattr__(attr, v)

    def export(self):
        """export all object attributes as a list of string

        Each member is a line in agr file"""
        slist = []
        for attr, typ, _, f in self._attrs:
            s = ""
            attrv = self.__getattribute__(attr)
            _logger.debug("parsed export: %s , %s, %r", type(self).__name__, attr, attrv)
            if typ in [list, tuple, set]:
                temps = attr.replace("_", " ") + " " + f.format(*attrv)
            # special property marked by the type as bool
            elif typ is bool:
                temps = ""
                # for Symbol
                if attr == "type":
                    temps = " "
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
            s = s + self._marker + " " + temps
            _logger.debug("exporting: %s", s)
            slist.append(s)
        return slist

    def __str__(self):
        return "\n".join(self.export())

    def __repr__(self):
        return self.__str__()

    def str_at(self):
        """print out the object as a string with an @ at the beginning"""
        return "\n".join(self.export())

    def str(self):
        """print out the object as a string without beginning @
        
        The same as __str__"""
        return self.__str__()

class TitleLike(BaseOutput):
    """title and subtitle of graph"""
    _attrs = (
        ('font', int, 0, "{:d}"),
        ('size', float, 1.5, "{:8f}"),
        ('color', int, 1, "{:d}"),
        )

class Title(TitleLike):
    """title of graph"""
    _marker = 'title'
    _attrs = ((_marker+'_comment', bool, "", "\"{:s}\""),) \
             + TitleLike._attrs

class SubTitle(TitleLike):
    """title of graph"""
    _marker = 'subtitle'
    _attrs = ((_marker+'_comment', bool, "", "\"{:s}\""),) \
             + TitleLike._attrs

def _set_loclike_attr(marker, form, *args):
    f = [form,] * len(args)
    return ((marker + '_location', bool, args, ', '.join(f)),)

class World(BaseOutput):
    """world of graph"""
    _marker = 'world'
    _attrs = _set_loclike_attr('world', '{:8f}', 0., 0.7, 9.0, 2.7)

class StackWorld(BaseOutput):
    """stack world of graph"""
    _marker = 'stack_world'
    _attrs = _set_loclike_attr('stack_world', '{:8f}', 0., 0.7, 9.0, 2.7)

class View(BaseOutput):
    """stack world of graph"""
    _marker = 'stack_world'
    _attrs = _set_loclike_attr('stack_world', '{:8f}', 0., 0.7, 9.0, 2.7)

class Znorm(BaseOutput):
    """stack world of graph"""
    _marker = 'znorm'
    _attrs = _set_loclike_attr('znorm', '{:d}', 1)

class Line(BaseOutput):
    """Line object of dataset"""
    _marker = 'line'
    _attrs = (
        ('type', int, 1, "{:d}"),
        ('linestyle', int, LineStyle.SOLID, "{:d}"),
        ('linewidth', float, 4.0, "{:3f}"),
        ('color', int, 1, "{:d}"),
        ('pattern', int, 1, "{:d}"),
        )


class Legend(BaseOutput):
    """object to control the appearance of graph legend"""
    _marker = 'legend'
    _attrs = (
        #@    legend 0.75, 0.451567486
        ('legend_switch', bool, Switch.ON, '{:d}'),
        ('legend_location', bool, (0.75, 0.50), '{:6f} , {:6f}'),
        ('loctype', str, 'view', '{:s}'),
        ('font', int, 0, '{:d}'),
        ('color', int, 1, '{:d}'),
        ('length', int, 4, '{:d}'),
        ('vgap', int, 1, '{:d}'),
        ('hgap', int, 1, '{:d}'),
        ('invert', str, False, '{:s}'),
        ('char_size', float, 1.2, '{:8f}'),
        )

    def __init__(self, **kwargs):
        self.box = Box()
        BaseOutput.__init__(self, **kwargs)

    def export(self):
        slist = BaseOutput.export(self) + \
                [self._marker + " " + i for i in self.box.export()]


class Box(BaseOutput):
    """Box of legend"""
    _marker = 'box'
    _attrs = (
        ('color', int, 1, '{:d}'),
        ('pattern', int, Pattern.SOLID, '{:d}'),
        ('linewidth', float, 1.0, '{:3f}'),
        ('linestyle', int, LineStyle.SOLID, '{:d}'),
        ('fill_color', int, 1, '{:d}'),
        ('fill_pattern', int, Pattern.SOLID, '{:d}'),
        )

class Frame(BaseOutput):
    """frame"""
    CLOSED = 0
    HALFOPEN = 1
    BREAKTOP = 2
    BREAKBOT = 3
    BREAKLEFT = 4
    BREAKRIGHT = 5

    _marker = "frame"
    _attrs = (
        ('type', int, 0, "{:d}"),
        ('linestyle', int, LineStyle.SOLID, "{:d}"),
        ('linewidth', float, 1.0, "{:3f}"),
        ('color', int, 1, "{:d}"),
        ('pattern', int, 1, "{:d}"),
        ('background_color', int, 0, "{:d}"),
        ('background_pattern', int, 0, "{:d}"),
        )


class BaseLine(BaseOutput):
    """baseline of dataset"""
    _marker = 'baseline'
    _attrs = (
        ('type', int, 0, '{:d}'),
        ('baseline_switch', bool, Switch.OFF, '{:s}'),
        )


class DropLine(BaseOutput):
    """baseline of dataset"""
    _marker = 'dropline'
    _attrs = (
        ('dropline_switch', bool, Switch.OFF, '{:s}'),
        )


class Fill(BaseOutput):
    """Fill of dataset"""
    NONE = 0
    SOLID = 1
    OPAQUE = 2

    _marker = 'fill'
    _attrs = (
        ('type', int, NONE, '{:d}'),
        ('rule', int, 0, '{:d}'),
        ('color', int, 1, '{:d}'),
        ('pattern', int, 1, '{:d}'),
        )


class Default(BaseOutput):
    """Default options at head"""
    _marker = "default"
    _attrs = (
        ("linewidth", float, 1., "{:3f}"),
        ("linestyle", int, LineStyle.SOLID, "{:d}"),
        ("color", int, 1, "{:d}"),
        ("pattern", int, 1, "{:d}"),
        ("font", int, 0, "{:d}"),
        ("char_size", float, 1., "{:8f}"),
        ("symbol_size", float, 1., "{:8f}"),
        ("sformat", str, "%.8g", "\"{:s}\""),
        )
    def __init__(self, **kwargs):
        BaseOutput.__init__(self, **kwargs)


class Annotation(BaseOutput):
    """dataset annotation"""
    _marker = "avalue"
    _attrs = (
        ("avalue_switch", bool, Switch.OFF, "{:s}"),
        ("type", int, 2, "{:d}"),
        ("char_size", float, 1., "{:8f}"),
        ("font", int, 0, "{:d}"),
        ("color", int, 1, "{:d}"),
        ("rot", int, 0, "{:d}"),
        ("format", str, "general", "{:s}"),
        ("prec", int, 3, "{:d}"),
        ("append", str, "\"\"", "{:s}"),
        ("prepend", str, "\"\"", "{:s}"),
        ("offset", list, [0.0, 0.0], "{:8f} , {:8f}"),
        )
    def __init__(self, **kwargs):
        BaseOutput.__init__(self, **kwargs)


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

    _marker = "symbol"
    _attrs = (
        ("type", bool, CIRCLE, "{:d}"),
        ("size", float, 1., "{:8f}"),
        ("color", int, 1, "{:d}"),
        ("pattern", int, 1, "{:d}"),
        ("fill_color", int, 1, "{:d}"),
        ("fill_pattern", int, 1, "{:d}"),
        ("linewidth", float, 1, "{:3f}"),
        ("linestyle", int, LineStyle.SOLID, "{:d}"),
        ("char", int, 1, "{:d}"),
        ("char_font", int, 0, "{:d}"),
        ("skip", int, 0, "{:d}"),
        )


class Page(BaseOutput):
    """Page"""
    _marker = "page"
    _attrs = (
        ("size", list, (792, 612), "{:d}, {:d}"),
        ("scroll", float, 0.05, "{:.0%}"),
        ("inout", float, 0.05, "{:.0%}"),
        ("background_fill", bool, Switch.ON, "{:s}"),
        )
    def __init__(self, **kwargs):
        BaseOutput.__init__(self, **kwargs)


class TimeStamp(BaseOutput):
    """Timestamp"""
    _marker = "timestamp"
    _attrs = (
        ('timestamp_switch', bool, Switch.OFF, "{:s}"),
        ('color', int, 1, "{:d}"),
        ('rot', int, 0, "{:d}"),
        ('font', int, 0, "{:d}"),
        ('char_size', float, 1.0, "{:8f}"),
        ('def', str, time.strftime("%a %b %d %H:%M:%S %Y"), "\"{:s}\""),
        )
    def __init__(self, **kwargs):
        BaseOutput.__init__(self, **kwargs)


class Tick(BaseOutput):
    """Tick of axis

    Args:
        major (float) : value between major ticks
        minor (float) : value between minor ticks
    """
    _marker = 'tick'
    _attrs = (
        ('tick_switch', bool, Switch.ON, "{:s}"),
        ('tick_position', bool, Position.IN, "{:s}"),
        ('place_rounded', str, True, "{:s}"),
        ('place_position', bool, Position.BOTH, "{:s}"),
        ('spec_type', str, None, "{:s}"),
        ('default', int, 6, "{:d}"),
        ('major', float, 1., "{:3f}"),
        ('major_size', float, 0.5, "{:8f}"),
        ('major_color', float, 1., "{:3f}"),
        ('major_linewidth', float, 2.0, "{:3f}"),
        ('major_linestyle', int, LineStyle.SOLID, "{:d}"),
        ('major_grid_switch', bool, Switch.OFF, "{:s}"),
        ('minor', float, 1., "{:3f}"),
        ('minor_color', float, 1., "{:3f}"),
        ('minor_size', float, 1., "{:8f}"),
        ('minor_ticks', int, 1, "{:d}"),
        ('minor_grid_switch', bool, Switch.OFF, "{:s}"),
        ('minor_linewidth', float, 2.0, "{:3f}"),
        ('minor_linestyle', int, LineStyle.SOLID, "{:d}"),
        )

    def __init__(self, **kwargs):
        BaseOutput.__init__(self, **kwargs)

class Bar(BaseOutput):
    """Axis bar"""
    _markder = 'bar'
    _attrs = (
        ('bar_switch', bool, Switch.ON, '{:s}'),
        ('color', int, 1, '{:d}'),
        ('linestyle', int, LineStyle.SOLID, '{:d}'),
        ('linewidth', float, 4., '{:3f}'),
        )

class Label(BaseOutput):
    """Axis label"""
    _marker = 'label'
    _attrs = (
        ('layout', str, 'para', '{:s}'),
        ('place_position', bool, Switch.AUTO, '{:s}'),
        ('char_size', float, 1.5, "{:8f}"),
        ('font', int, 0, "{:d}"),
        ('color', int, 0, "{:d}"),
        ('place', str, "normal", "{:s}"),
        )

    def __init__(self, label=None, **kwargs):
        if label is None:
            self.label = ""
        self.label = str(self.label)
        BaseOutput.__init__(self, *kwargs)

    def export(self):
        slist = self._markder + " \"{:s}\"".format(self.label)
        slist += BaseOutput.export(self)
        return slist

class TickLabel(BaseOutput):
    """Label of axis tick"""
    _marker = 'ticklabel'
    _attrs = (
        ('ticklabel_switch', bool, Switch.AUTO, "{:s}"),
        ('format', str, "general", "{:s}"),
        ('formula', str, "", "\"{:s}\""),
        ('append', str, "", "\"{:s}\""),
        ('prepend', str, "", "\"{:s}\""),
        ("prec", int, 5, "{:d}"),
        ('angle', int, 0, "{:d}"),
        ('font', int, 0, "{:d}"),
        ('color', int, 1, "{:d}"),
        ('skip', int, 0, "{:d}"),
        ('stagger', int, 0, "{:d}"),
        ('place', str, "normal", "{:s}"),
        ('offset_switch', bool, Switch.AUTO, "{:s}"),
        ('offset', list, [0.00, 0.01], "{:8f} , {:8f}"),
        ('start_type_switch', bool, Switch.AUTO, "{:s}"),
        ('start', float, 0.0, "{:8f}"),
        ('stop_type_switch', bool, Switch.AUTO, "{:s}"),
        ('stop', float, 0.0, "{:8f}"),
        ('char_size', float, 1.5, "{:8f}"),
        )
    def __init__(self, **kwargs):
        BaseOutput.__init__(self, **kwargs)

class Errorbar(BaseOutput):
    """Errorbar of dataset"""
    _marker = 'errorbar'
    _attrs = (
        ('errorbar_switch', bool, Switch.ON, '{:s}'),
        ('place_position', bool, Position.BOTH, '{:s}'),
        ('color', int, 1, '{:d}'),
        ('pattern', int, 1, '{:d}'),
        ('size', float, 1.0, '{:8f}'),
        ('linewidth', float, 1.0, '{:3f}'),
        ('linestyle', int, LineStyle.SOLID, '{:d}'),
        ('riser_linewidth', float, 1.0, '{:3f}'),
        ('riser_linestyle', int, LineStyle.SOLID, '{:d}'),
        ('riser_clip_switch', bool, Switch.OFF, '{:s}'),
        ('riser_clip_length', float, 0.1, '{:8f}'),
        )


class Axis(BaseOutput, Affix):
    """Axis

    Args:
        axis (str) : in ['x', 'y', 'altx', 'alty']
    """
    _marker = 'axis'
    _attrs = (
        ('axis_switch', bool, Switch.ON, '{:s}'),
        ('type', list, ("zero", "false"), '{:s} {:s}'),
        ('offset', list, (0.0, 0.0), '{:8f} {:8f}'),
        )
    def __init__(self, axis='x', **kwargs):
        assert axis in ['x', 'y', 'altx', 'alty']
        self.bar = Bar()
        self.tick = Tick()
        self.ticklabel = TickLabel()
        BaseOutput.__init__(self, **kwargs)
        Affix.__init__(self, affix=axis, pre=True)

    def export(self):
        if self.axis_switch is Switch.OFF:
            return [self._marker + "  " + Switch.get_str(Switch.OFF),]
        raise NotImplementedError

    def set_major_tick(self):
        raise NotImplementedError

    def set_minor_tick(self):
        raise NotImplementedError

    def set_ticklabel(self):
        raise NotImplementedError

# TODO axes object for graph

# Classes for users

class Dataset(BaseOutput, Affix):
    """Object of grace dataset

    Args:
        index (int) : index of the dataset
    """
    _marker = 's'
    _attrs = (
        ('hidden', str, False, '{:s}'),
        ('type', str, 'xy', '{:s}'),
        )
    def __init__(self, index, legend=None, comment="", **kwargs):
        self.legend = {None: ""}.get(legend, legend)
        self.comment = {None: ""}.get(comment, comment)
        self._attrs += (
            ('legend_comment', bool, self.legend, "\"{:s}\""),
            ('comment_comment', bool, self.comment, "\"{:s}\""),
            )
        self.symbol = Symbol()
        self.line = Line()
        self.baseline = BaseLine()
        self.dropline = DropLine()
        self.fill = Fill()
        self.avalue = Annotation()
        self.errorbar = Errorbar()
        BaseOutput.__init__(self, **kwargs)
        Affix.__init__(self, index, pre=False)

    def export(self):
        """Export the header part of dataset"""
        slists = BaseOutput.export(self)
        to_exports = [self.symbol,
                      self.line,
                      self.baseline,
                      self.dropline,
                      self.fill,
                      self.avalue,
                      self.errorbar,]
        for ex in to_exports:
            slists += [self._marker + " " + i for i in ex.export()]
        return slists

    def export_data(self):
        """Export the data part"""
        raise NotImplementedError


class Graph(BaseOutput):
    """Graph object

    Args:
        index (int)"""
    _marker = 'g'
    def __init__(self, **kwargs):
        self.world = World()
        self.stackworld = StackWorld()
        self.view = View()
        self.znorm = Znorm()
        self.xaxis = Axis('x')
        self.yaxis = Axis('y')
        self.legend = Legend()
        self.frame = Frame()
        self.datasets = []
        BaseOutput.__init__(self, **kwargs)

    def __getitem__(self, i):
        return self.datasets[i]

    def set_xaxis(self):
        """adjust xaxis"""

    def add(self, x, y, datatype='xy', dataset=None):
        """Add dataset"""

    def set_yaxis(self):
        """adjust yaxis"""

    def export(self):
        raise NotImplementedError

    def _print_header(self):
        """export header part"""

    def _print_data(self):
        """export data part"""


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
        # TODO @background color 0
        # TODO r0, r1, link, etc
        self._timestamp = TimeStamp()
        self._default = Default()
        self._graphs = [Graph(),]
        self._font = Font()
        self._use_qtgrace = qtgrace

    def __str__(self):
        """TODO print the whole agr file"""
        header = [self._page, self._font, self._default, self._timestamp]
        slist = []
        for h in header:
            slist += h.export()
        s = "\n".join(slist)
        # add @ to each header line
        #s = self._comment_head + "@" + "\n@".join(s.split("\n"))
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
    print(Dataset(index=0))
    #print(Plot())
    #print(TickLabel().str())
    #print(Tick().str())

