"""Tests of reusable plotting styles."""
import unittest as ut

try:
    import matplotlib as mpl
    mpl.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    mpl = plt = None

from mushroom.visual import pyplot

PLT_INSTALLED = plt is not None


@ut.skipUnless(PLT_INSTALLED, "requires matplotlib")
class test_pyplot(ut.TestCase):

    def test_idempotent(self):
        with mpl.rc_context():
            pyplot.rc_gracify()
            pyplot.rc_gracify()
            self.assertEqual(plt.rcParams["xtick.major.size"],
                             mpl.rcParamsDefault["xtick.major.size"] * 1.5)
            self.assertEqual(plt.rcParams["font.serif"].count("Times New Roman"), 1)

    def test_context(self):
        before = dict(mpl.rcParams)
        style = pyplot.gracify_style()
        self.assertEqual(dict(mpl.rcParams), before)
        with mpl.rc_context(style):
            self.assertEqual(mpl.rcParams["font.size"], 16)
        self.assertEqual(dict(mpl.rcParams), before)

    def test_figsize(self):
        self.assertEqual(pyplot.figsize("aps-double", aspect=0.5), (7., 3.5))
        self.assertEqual(pyplot.figsize(nrows=2), (3.375, 5.0625))
        with self.assertRaisesRegex(ValueError, "aps-single"):
            pyplot.figsize("unknown")
