"""Small plotting interface shared by matplotlib and Grace."""

import numpy as np

try:
    from matplotlib.axes import Axes
except ImportError:
    Axes = None

from mushroom.visual.graceplot import Graph, plot_colormap, prefer_gracecolors
from mushroom.core.logger import loggers

_logger = loggers["grace"]
_COLOR_TO_GRACE = {"lime": "green", "green": "green4", "gray": "grey",
                   "k": "black", "r": "red", "b": "blue", "g": "green4"}
_COLOR_TO_PLT = {"green4": "#008b00", "grey": "#dcdcdc"}
# Retain the palette names here; translate their RGB values only at the backend.
DEFAULT_COLORS = list(prefer_gracecolors)


class AxesAdapter:
    """Common plotting operations with backend-specific primitives.

    Args:
        ax: Underlying Matplotlib Axes or Grace Graph.
    """

    def __init__(self, ax):
        self._raw = ax

    @property
    def raw(self):
        """Return the original plotting axes.

        Returns:
            Axes or Graph: Original object for backend-specific customization.
        """
        return self._raw

    def xgrid(self, positions, color="gray", ls="dashed", lw=None):
        """Draw vertical guides at supplied coordinates.

        Args:
            positions: Guide abscissae, shape (npositions,), in x-axis units.
            color: Shared color name.
            ls: Line style.
            lw: Line width in backend units, or None for its default.

        Returns:
            None: Guides are added to the axes.
        """
        for x in positions:
            self.axvline(x, color=color, ls=ls, lw=lw)


class PltAxes(AxesAdapter):
    """Translate shared styles to matplotlib.

    Args:
        ax: Underlying Matplotlib Axes.
    """

    engine = "plt"

    def line(self, x, ys, color="black", ls="solid", lw=None, marker="none", ms=None, label=None):
        """Plot curves with one legend entry.

        Args:
            x: Abscissae, shape (npoints,), in x-axis units.
            ys: Ordinates, shape (npoints,) or (npoints, nlines), in y-axis units.
            color: Shared color name.
            ls: Line style.
            lw: Line width in backend units, or None for its default.
            marker: Marker symbol.
            ms: Marker diameter in points, or None for its default.
            label: Legend label for the first curve, or None.

        Returns:
            list or None: Matplotlib Line2D objects, or None for Grace.
        """
        lines = self.raw.plot(x, ys, color=_COLOR_TO_PLT.get(color, color), ls=ls,
                              lw=lw, marker=marker, ms=ms)
        if lines and label is not None:
            lines[0].set_label(label)
        return lines

    def scatter(self, x, y, sizes, color="black", label=None):
        """Plot markers with sizes expressed as squared point diameters.

        Args:
            x: Abscissae, shape (npoints,), in x-axis units.
            y: Ordinates, shape (npoints,), in y-axis units.
            sizes: Squared marker diameters in points squared, shape (npoints,).
            color: Shared color name.
            label: Legend label, or None.

        Returns:
            PathCollection or None: Matplotlib collection, or None for Grace.
        """
        return self.raw.scatter(x, y, s=sizes, color=_COLOR_TO_PLT.get(color, color), label=label)

    def axhline(self, y, color="black", ls="solid", lw=None):
        """Draw a horizontal reference line.

        Args:
            y: Ordinate in y-axis units.
            color: Shared color name, translated for the backend.
            ls: Line style.
            lw: Line width in backend units, or None for its default.

        Returns:
            Line2D or None: Matplotlib line, or None for Grace.
        """
        return self.raw.axhline(y, color=_COLOR_TO_PLT.get(color, color), ls=ls, **({} if lw is None else {"lw": lw}))

    def axvline(self, x, color="black", ls="solid", lw=None):
        """Draw a vertical reference line.

        Args:
            x: Abscissa in x-axis units.
            color: Shared color name, translated for the backend.
            ls: Line style.
            lw: Line width in backend units, or None for its default.

        Returns:
            Line2D or None: Matplotlib line, or None for Grace.
        """
        return self.raw.axvline(x, color=_COLOR_TO_PLT.get(color, color), ls=ls, **({} if lw is None else {"lw": lw}))

    def set_xlim(self, xmin=None, xmax=None):
        """Set horizontal limits.

        Args:
            xmin: Lower bound in x-axis units, or None to retain it.
            xmax: Upper bound in x-axis units, or None to retain it.

        Returns:
            None: The limits are updated.
        """
        self.raw.set_xlim(xmin, xmax)

    def set_ylim(self, ymin=None, ymax=None):
        """Set vertical limits.

        Args:
            ymin: Lower bound in y-axis units, or None to retain it.
            ymax: Upper bound in y-axis units, or None to retain it.

        Returns:
            None: The limits are updated.
        """
        self.raw.set_ylim(ymin, ymax)

    def set_xlabel(self, label):
        """Set the horizontal axis label.

        Args:
            label: Label string in backend notation.

        Returns:
            None: The label is updated.
        """
        self.raw.set_xlabel(label)

    def set_ylabel(self, label):
        """Set the vertical axis label.

        Args:
            label: Label string in backend notation.

        Returns:
            None: The label is updated.
        """
        self.raw.set_ylabel(label)

    def set_xticks(self, positions, labels):
        """Set special-point ticks and labels.

        Args:
            positions: Tick abscissae, shape (nticks,), in x-axis units.
            labels: Corresponding backend-formatted strings, or None for backend defaults.

        Returns:
            None: Ticks are updated.
        """
        self.raw.set_xticks(positions, labels=labels)

    def legend(self, loc="best"):
        """Show the dataset legend.

        Args:
            loc: Legend location; best maps to upper right for Grace.

        Returns:
            None: The legend is updated.
        """
        self.raw.legend(loc=loc)

    def fill_between(self, x, y, color, alpha=0.3):
        """Fill between a curve and zero, or log unsupported Grace filling.

        Args:
            x: Abscissae, shape (npoints,), in x-axis units.
            y: Ordinates, shape (npoints,), in y-axis units.
            color: Shared color name.
            alpha: Opacity from zero to one; ignored by Grace.

        Returns:
            None: Matplotlib adds a fill; Grace logs a warning.
        """
        self.raw.fill_between(x, y, color=_COLOR_TO_PLT.get(color, color), alpha=alpha)

    def fill_betweenx(self, y, x, color, alpha=0.3):
        """Fill between a vertical curve and zero.

        Args:
            y: Ordinates, shape (npoints,), in y-axis units.
            x: Abscissae, shape (npoints,), in x-axis units.
            color: Shared color name.
            alpha: Opacity from zero to one.

        Returns:
            None: The fill is added.
        """
        self.raw.fill_betweenx(y, x, color=_COLOR_TO_PLT.get(color, color), alpha=alpha)


class GraceAxes(AxesAdapter):
    """Translate shared styles to Grace graphs.

    Args:
        ax: Underlying Grace Graph.
    """

    engine = "grace"

    @staticmethod
    def _style(color, ls="solid", lw=None):
        color = _COLOR_TO_GRACE.get(color, color)
        if color not in plot_colormap.names:
            raise ValueError("Unknown Grace color: {}".format(color))
        return dict(color=color, ls="dotdashed" if ls == "dashdot" else ls, lw=lw)

    def line(self, x, ys, color="black", ls="solid", lw=None, marker="none", ms=None, label=None):
        """Plot curves with one legend entry.

        Args:
            x: Abscissae, shape (npoints,), in x-axis units.
            ys: Ordinates, shape (npoints,) or (npoints, nlines), in y-axis units.
            color: Shared color name.
            ls: Line style.
            lw: Line width in backend units, or None for its default.
            marker: Marker symbol.
            ms: Marker diameter in points, or None for its default.
            label: Legend label for the first curve, or None.

        Returns:
            list or None: Matplotlib Line2D objects, or None for Grace.
        """
        kwargs = self._style(color, ls, lw)
        kwargs.update(symbol={"s": "square"}.get(marker, marker), ssize=None if ms is None else ms / 6., label=label)
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        # Grace expects (nlines, npoints), unlike matplotlib.
        return self.raw.plot(x, np.asarray(ys).T, **kwargs)

    def scatter(self, x, y, sizes, color="black", label=None):
        """Plot markers with sizes expressed as squared point diameters.

        Args:
            x: Abscissae, shape (npoints,), in x-axis units.
            y: Ordinates, shape (npoints,), in y-axis units.
            sizes: Squared marker diameters in points squared, shape (npoints,).
            color: Shared color name.
            label: Legend label, or None.

        Returns:
            PathCollection or None: Matplotlib collection, or None for Grace.
        """
        return self.raw.plot(x, y, datatype="xysize", size=np.sqrt(sizes) / 6.,
                             symbol="o", label=label, **self._style(color, "none"))

    def axhline(self, y, color="black", ls="solid", lw=None):
        """Draw a horizontal reference line.

        Args:
            y: Ordinate in y-axis units.
            color: Shared color name, translated for the backend.
            ls: Line style.
            lw: Line width in backend units, or None for its default.

        Returns:
            Line2D or None: Matplotlib line, or None for Grace.
        """
        self.raw.axhline(y, **self._style(color, ls, lw))

    def axvline(self, x, color="black", ls="solid", lw=None):
        """Draw a vertical reference line.

        Args:
            x: Abscissa in x-axis units.
            color: Shared color name, translated for the backend.
            ls: Line style.
            lw: Line width in backend units, or None for its default.

        Returns:
            Line2D or None: Matplotlib line, or None for Grace.
        """
        self.raw.axvline(x, **self._style(color, ls, lw))

    def set_xlim(self, xmin=None, xmax=None):
        """Set horizontal limits.

        Args:
            xmin: Lower bound in x-axis units, or None to retain it.
            xmax: Upper bound in x-axis units, or None to retain it.

        Returns:
            None: The limits are updated.
        """
        self.raw.set_xlim(xmin, xmax)

    def set_ylim(self, ymin=None, ymax=None):
        """Set vertical limits.

        Args:
            ymin: Lower bound in y-axis units, or None to retain it.
            ymax: Upper bound in y-axis units, or None to retain it.

        Returns:
            None: The limits are updated.
        """
        self.raw.set_ylim(ymin, ymax)

    def set_xlabel(self, label):
        """Set the horizontal axis label.

        Args:
            label: Label string in backend notation.

        Returns:
            None: The label is updated.
        """
        self.raw.x.set_label(label)

    def set_ylabel(self, label):
        """Set the vertical axis label.

        Args:
            label: Label string in backend notation.

        Returns:
            None: The label is updated.
        """
        self.raw.y.set_label(label)

    def set_xticks(self, positions, labels):
        """Set special-point ticks and labels.

        Args:
            positions: Tick abscissae, shape (nticks,), in x-axis units.
            labels: Corresponding backend-formatted strings, or None for backend defaults.

        Returns:
            None: Ticks are updated.
        """
        self.raw.x.set_spec(positions, labels=labels)

    def legend(self, loc="best"):
        """Show the dataset legend.

        Args:
            loc: Legend location; best maps to upper right for Grace.

        Returns:
            None: The legend is updated.
        """
        self.raw.set_legend(loc="upper right" if loc == "best" else loc)

    def fill_between(self, x, y, color, alpha=0.3):
        """Fill between a curve and zero, or log unsupported Grace filling.

        Args:
            x: Abscissae, shape (npoints,), in x-axis units.
            y: Ordinates, shape (npoints,), in y-axis units.
            color: Shared color name.
            alpha: Opacity from zero to one; ignored by Grace.

        Returns:
            None: Matplotlib adds a fill; Grace logs a warning.
        """
        _logger.warning("Grace fill_between is not supported; ignoring fill")


def wrap_axes(ax):
    """Wrap a matplotlib Axes or Grace Graph, preserving existing adapters.

    Args:
        ax: Matplotlib Axes, Grace Graph or AxesAdapter instance.

    Returns:
        AxesAdapter: Adapter exposing shared line, scatter, axis and legend methods.

    Raises:
        TypeError: If ax is not a supported axes or adapter.
    """
    if isinstance(ax, AxesAdapter):
        return ax
    if isinstance(ax, Graph):
        return GraceAxes(ax)
    if Axes is not None and isinstance(ax, Axes):
        return PltAxes(ax)
    raise TypeError("Expected matplotlib Axes or Grace Graph, got {}".format(type(ax)))
