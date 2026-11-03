"""Small plotting interface shared by matplotlib and Grace."""
import numpy as np
try:
    from matplotlib.axes import Axes
except ImportError:
    Axes = None
from mushroom.visual.graceplot import Graph, plot_colormap, prefer_gracecolors
from mushroom.core.logger import loggers

_logger = loggers['grace']
_COLOR_TO_GRACE = {'lime': 'green', 'green': 'green4', 'gray': 'grey',
                   'k': 'black', 'r': 'red', 'b': 'blue', 'g': 'green4'}
_COLOR_TO_PLT = {'green4': '#008b00', 'grey': '#dcdcdc'}
# Retain the palette names here; translate their RGB values only at the backend.
DEFAULT_COLORS = list(prefer_gracecolors)


class AxesAdapter:
    """Common operations on a plotting axes, with backend-specific primitives."""

    def __init__(self, ax):
        self._raw = ax

    @property
    def raw(self):
        """Return the original axes for further customization."""
        return self._raw

    def xgrid(self, positions, color='gray', ls='dashed', lw=None):
        """Draw vertical guides at the supplied coordinates."""
        for x in positions:
            self.axvline(x, color=color, ls=ls, lw=lw)


class PltAxes(AxesAdapter):
    """Translate shared styles to matplotlib."""

    engine = 'plt'

    def line(self, x, ys, color='black', ls='solid', lw=None, marker='none', ms=None, label=None):
        """Plot columns of ys, assigning a label to only the first line."""
        lines = self.raw.plot(x, ys, color=_COLOR_TO_PLT.get(color, color), ls=ls,
                              lw=lw, marker=marker, ms=ms)
        if lines and label is not None:
            lines[0].set_label(label)
        return lines

    def scatter(self, x, y, sizes, color='black', label=None):
        """Plot markers with sizes expressed as squared point diameters."""
        return self.raw.scatter(x, y, s=sizes, color=_COLOR_TO_PLT.get(color, color), label=label)

    def axhline(self, y, color='black', ls='solid', lw=None):
        """Draw a horizontal reference line."""
        return self.raw.axhline(y, color=color, ls=ls, **({} if lw is None else {"lw": lw}))

    def axvline(self, x, color='black', ls='solid', lw=None):
        """Draw a vertical reference line."""
        return self.raw.axvline(x, color=color, ls=ls, **({} if lw is None else {"lw": lw}))

    def set_xlim(self, xmin=None, xmax=None):
        """Set the horizontal limits."""
        self.raw.set_xlim(xmin, xmax)

    def set_ylim(self, ymin=None, ymax=None):
        """Set the vertical limits."""
        self.raw.set_ylim(ymin, ymax)

    def set_xlabel(self, label):
        """Set the horizontal axis label."""
        self.raw.set_xlabel(label)

    def set_ylabel(self, label):
        """Set the vertical axis label."""
        self.raw.set_ylabel(label)

    def set_xticks(self, positions, labels):
        """Set special point ticks and optional labels."""
        self.raw.set_xticks(positions, labels=labels)

    def legend(self, loc='best'):
        """Show the dataset legend."""
        self.raw.legend(loc=loc)

    def fill_between(self, x, y, color, alpha=0.3):
        """Fill the region between y and zero."""
        self.raw.fill_between(x, y, color=_COLOR_TO_PLT.get(color, color), alpha=alpha)

    def fill_betweenx(self, y, x, color, alpha=0.3):
        """Fill a vertical DOS region using the shared color vocabulary."""
        self.raw.fill_betweenx(y, x, color=_COLOR_TO_PLT.get(color, color), alpha=alpha)


class GraceAxes(AxesAdapter):
    """Translate shared styles to Grace graphs."""

    engine = 'grace'

    @staticmethod
    def _style(color, ls='solid', lw=None):
        color = _COLOR_TO_GRACE.get(color, color)
        if color not in plot_colormap.names:
            raise ValueError('Unknown Grace color: {}'.format(color))
        return dict(color=color, ls='dotdashed' if ls == 'dashdot' else ls, lw=lw)

    def line(self, x, ys, color='black', ls='solid', lw=None, marker='none', ms=None, label=None):
        """Plot columns of ys with one legend entry."""
        kwargs = self._style(color, ls, lw)
        kwargs.update(symbol={'s': 'square'}.get(marker, marker), ssize=None if ms is None else ms / 6., label=label)
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        # Grace expects (nlines, npoints), unlike matplotlib.
        return self.raw.plot(x, np.asarray(ys).T, **kwargs)

    def scatter(self, x, y, sizes, color='black', label=None):
        """Plot point diameters in Grace's size unit (one unit is six points)."""
        return self.raw.plot(x, y, datatype='xysize', size=np.sqrt(sizes) / 6.,
                             symbol='o', label=label, **self._style(color, 'none'))

    def axhline(self, y, color='black', ls='solid', lw=None):
        """Draw a horizontal reference line."""
        self.raw.axhline(y, **self._style(color, ls, lw))

    def axvline(self, x, color='black', ls='solid', lw=None):
        """Draw a vertical reference line."""
        self.raw.axvline(x, **self._style(color, ls, lw))

    def set_xlim(self, xmin=None, xmax=None):
        """Set the horizontal limits."""
        self.raw.set_xlim(xmin, xmax)

    def set_ylim(self, ymin=None, ymax=None):
        """Set the vertical limits."""
        self.raw.set_ylim(ymin, ymax)

    def set_xlabel(self, label):
        """Set the horizontal axis label."""
        self.raw.x.set_label(label)

    def set_ylabel(self, label):
        """Set the vertical axis label."""
        self.raw.y.set_label(label)

    def set_xticks(self, positions, labels):
        """Set special point ticks and optional labels."""
        self.raw.x.set_spec(positions, labels=labels)

    def legend(self, loc='best'):
        """Show the legend, using upper right for automatic placement."""
        self.raw.set_legend(loc='upper right' if loc == 'best' else loc)

    def fill_between(self, x, y, color, alpha=0.3):
        """Warn and ignore fills, which this Grace adapter does not support."""
        _logger.warning('Grace fill_between is not supported; ignoring fill')


def wrap_axes(ax):
    """Wrap a matplotlib Axes or Grace Graph; preserve existing adapters."""
    if isinstance(ax, AxesAdapter):
        return ax
    if isinstance(ax, Graph):
        return GraceAxes(ax)
    if Axes is not None and isinstance(ax, Axes):
        return PltAxes(ax)
    raise TypeError('Expected matplotlib Axes or Grace Graph, got {}'.format(type(ax)))
