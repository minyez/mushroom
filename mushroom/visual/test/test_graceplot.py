# -*- coding: utf-8 -*-
"""Test graceplot"""
import unittest as ut
import tempfile
import pathlib
from itertools import product

from numpy import array_equal
from mushroom.visual.graceplot import (_ColorMap, Color, Font, Symbol,
                                       Graph, View, World, Label, Axis,
                                       Plot, Dataset,
                                       encode_string, extract_data_from_agr)

class test_string_encoder(ut.TestCase):
    """test encoder to get grace-favored text string"""
    def test_greek(self):
        """encoding greek"""
        self.assertEqual(encode_string(r"\Gamma \beta"), r"\xG\f{} \xb\f{}")

    def test_special(self):
        """encoding special characters"""
        self.assertEqual(encode_string(r"\AA \BB"), r"\cE\C \BB")

    def test_italic(self):
        """encoding special characters"""
        self.assertEqual(encode_string(r"/this is italic/, this not"), 
                         r"\f{Times-Italic}this is italic\f{}, this not")
        self.assertEqual(encode_string(r"/italic here/, /also here/"), 
                         r"\f{Times-Italic}italic here\f{}, \f{Times-Italic}also here\f{}")

class test_ColorMap(ut.TestCase):
    """test colormap utilites"""

    def test_output(self):
        """test if the grace output of default colormap is as expected"""
        c = _ColorMap(load_custom=False)
        self.maxDiff = None
        s = """map color 0 to (255, 255, 255), "white"
map color 1 to (0, 0, 0), "black"
map color 2 to (255, 0, 0), "red"
map color 3 to (0, 255, 0), "green"
map color 4 to (0, 0, 255), "blue"
map color 5 to (255, 255, 0), "yellow"
map color 6 to (188, 143, 143), "brown"
map color 7 to (220, 220, 220), "grey"
map color 8 to (148, 0, 211), "violet"
map color 9 to (0, 255, 255), "cyan"
map color 10 to (255, 0, 255), "magenta"
map color 11 to (255, 165, 0), "orange"
map color 12 to (114, 33, 188), "indigo"
map color 13 to (103, 7, 72), "maroon"
map color 14 to (64, 224, 208), "turquoise"
map color 15 to (0, 139, 0), "green4"
"""
        self.assertEqual(str(c) + '\n', s)

    def test_add_color(self):
        """add new color to color map"""
        c = _ColorMap(load_custom=False)
        n = c.n
        c.add(10, 10, 10, None)
        self.assertEqual(n + 1, c.n)
        self.assertTrue(c.has_color("color" + str(n)))
        self.assertEqual(c[n], "color" + str(n))

    def test_get_color(self):
        """get an existing color"""
        c = _ColorMap(load_custom=False)
        n = c.n
        self.assertRaises(IndexError, c.get, n+1)
        self.assertRaises(ValueError, c.get, "colorcode not registered")
        self.assertRaises(TypeError, c.get, [])

class test_Font(ut.TestCase):
    """test font utilites"""

    f = Font()

    def test_output_without_at(self):
        """test if the grace output of default colormap is as expected"""
        s = """map font 0 to "Times-Roman", "Times-Roman"
map font 1 to "Times-Italic", "Times-Italic"
map font 2 to "Times-Bold", "Times-Bold"
map font 3 to "Times-BoldItalic", "Times-BoldItalic"
map font 4 to "Helvetica", "Helvetica"
map font 5 to "Helvetica-Oblique", "Helvetica-Oblique"
map font 6 to "Helvetica-Bold", "Helvetica-Bold"
map font 7 to "Helvetica-BoldOblique", "Helvetica-BoldOblique"
map font 8 to "Courier", "Courier"
map font 9 to "Courier-Oblique", "Courier-Oblique"
map font 10 to "Courier-Bold", "Courier-Bold"
map font 11 to "Courier-BoldOblique", "Courier-BoldOblique"
map font 12 to "Symbol", "Symbol"
map font 13 to "ZapfDingbats", \"ZapfDingbats\"
"""
        self.assertEqual(str(self.f) + "\n", s)

class test_View(ut.TestCase):
    """test the view object"""

    def test_set_get(self):
        """test set view functionality"""
        v = View()
        new = [0.1, 0.1, 1.0, 1.0]
        v.set_view(new)
        self.assertListEqual(new, v.get_view())

        v1 = View()
        new1 = [0.2, 0.2, 2.0, 2.0]
        v1.set_view(new1)
        self.assertListEqual(new1, v1.get_view())
        self.assertListEqual(new, v.get_view())

class test_World(ut.TestCase):
    """test the world object"""

    def test_set_get(self):
        """test set view functionality"""
        w = World()
        new = [1., 2., 3.0, 4.0]
        w.set_world(new)
        self.assertListEqual(new, w.get_world())

        w1 = World()
        new1 = [2., 2., 5., 8.0]
        w1.set_world(new1)
        self.assertListEqual(new1, w1.get_world())
        self.assertListEqual(new, w.get_world())

class test_Axis(ut.TestCase):
    """test Axix functionality"""

    def test_label(self):
        """test the axis label setup"""
        a = Axis('x')
        l = a._label
        # raise for unknown attribute
        self.assertRaises(ValueError, l.set, not_an_attribute="label")
        l.set(s=r"\Gamma")
        self.assertEqual(r"\Gamma", l.label)

    def test_ticklabel(self):
        """raise for unknown attribute"""
        a = Axis('x')
        tl = a._ticklabel
        self.assertRaises(ValueError, tl.set, not_an_attribute="ticklabel")
        tl.set(switch="off")

class test_Graph(ut.TestCase):
    """test graph operations"""
    def test_set(self):
        """set graph attributes"""
        g = Graph(index=0)
        g.set(hidden=False)

    def test_graph_properties(self):
        """test graph properties"""
        g = Graph(index=0)
        g.set_title(title="Hello world!")
        self.assertEqual(g.title, "Hello world!")
        g.title = "Hello again"
        self.assertEqual(g.title, "Hello again")
        g.set_subtitle(subtitle="Hello world!")
        self.assertEqual(g.subtitle, "Hello world!")
        g.subtitle = "Hello again"
        self.assertEqual(g.subtitle, "Hello again")

    def test_change_view(self):
        """test if view changing is working"""
        g = Graph(index=1)
        g.set_view(0.0, 0.0, 1.0, 0.5)
        self.assertListEqual(g._view.view_location, [0.0, 0.0, 1.0, 0.5])

    def test_set_legend(self):
        """test legend setup"""
        g = Graph(index=0)
        g.plot([0,], [0,], label="origin")
        g.set_legend(switch="off", color="red")
        horis = ["left", "center", "right"]
        verts = ["upper", "middle", "lower", "bottom"]
        for hori, vert in product(horis, verts):
            g.set_legend(loc="{} {}".format(vert, hori))

    def test_plot(self):
        """test plotting data"""
        g = Graph(index=1)
        x = [0.0, 1.0, 2.0]
        y = [1.0, 2.0, 3.0]
        g.plot(x, y, label="y=x+1", symbol="o", color="red")
        self.assertEqual(g[0]._symbol.type, Symbol.get("o"))
        # both symbol and line are colored
        self.assertEqual(g[0]._symbol.color, Color.get("red"))
        self.assertEqual(g[0]._line.color, Color.get("red"))
        
    def test_multiple_plot(self):
        """test plotting xy data"""
        g = Graph(index=1)
        x = [0.0, 1.0, 2.0]
        y = [[1.0, 2.0, 3.0], [2.0, 3.0, 4.0], [3.0, 4.0, 5.0]]
        g.plot(x, y, symbol="o", color="red")
        self.assertEqual(len(y), len(g))

    def test_extremes(self):
        """test x/ymin/max of graphs"""
        g = Graph(index=1)
        g.plot([1,], [2,])
        g.plot([-1,], [3,])
        g.plot([2.3,], [-1.2,])
        self.assertEqual(g.xmin(), -1)
        self.assertEqual(g.xmax(), 2.3)
        self.assertEqual(g.min(), -1.2)
        self.assertEqual(g.max(), 3)
        g.tight_graph()

    def test_drawing(self):
        """test draing objects"""
        g = Graph(index=1)
        g.axvline(0.0)
        # percentage
        g.axvline(0.5, loctype="view", ymin="10", ymax="80")
        g.axhline(0.0)
        # percentage
        g.axhline(0.5, loctype="view", xmin="10", xmax="80")
        g.text("some annotation", [0.5, 0.5], loctype="view")
        self.assertListEqual(g._objects[-1].string_location, [0.5, 0.5])
        g.circle([0.5, 0.5], 0.1, 0.1)
        g.export()


class test_Plot(ut.TestCase):
    """test Plot functionality"""

    def test_init_properties(self):
        """default properties"""
        p = Plot(1, 1, description="Hello World")
        self.assertEqual("Hello World", p.description)

    def test_set_default(self):
        """default properties"""
        p = Plot(1, 1)
        p.set_default(font=2)
        self.assertEqual(2, p._default.font)

    def test_change_limits(self):
        """test limits manipulation of all graphs"""
        p = Plot(2, 2)
        p.set_xlim(xmin=1.0, xmax=2.0)
        p.set_ylim(ymin=3.0, ymax=4.0)
        for g in p.get():
            self.assertListEqual(g._world.world_location,
                                 [1.0, 3.0, 2.0, 4.0])
        p.tight_graph()

    def test_add_graph(self):
        """graph addition"""
        p = Plot(2, 2)
        p.add_graph()
        self.assertEqual(len(p), 2*2+1)

    def test_regular_graphs(self):
        """generate regular graph alignment"""
        p = Plot(1, 1)
        self.assertEqual(len(p._graphs), 1*1)
        p = Plot(3, 4, hgap=[0.01, 0.0, 0.02], vgap=[0.02, 0.0],
                 width_ratios="3:2:1:4", heigh_ratios="1:3:2")
        self.assertEqual(len(p._graphs), 3*4)

    def test_subplots(self):
        """test subplots generation"""
        p, _ = Plot.subplots()
        self.assertEqual(len(p), 1)
        p, _ = Plot.subplots(3)
        self.assertEqual(len(p), 3)
        p, _ = Plot.subplots(32)
        self.assertEqual(len(p), 6)

    def test_write(self):
        """writing to agr"""
        p = Plot(1, 1)
        p.plot([0, 1, 2], [3, 2, 1])
        self.assertEqual(len(p), 1)
        tf = tempfile.NamedTemporaryFile()
        with open(tf.name, 'w') as h:
            p.write(file=h)
        p.write(file=tf.name)
        p.write(file=pathlib.Path(tf.name))
        self.assertRaises(TypeError, p.write, file=[1,])
        tf.close()


class test_Dataset(ut.TestCase):
    """test for Dataset"""
    def test_line(self):
        """the line setup"""
        d = Dataset(0, [0,], [0,])
        d.set_line(width=1.0)
        self.assertEqual(d._line.linewidth, 1.0)

    def test_errobar(self):
        """the errorbar setup"""
        d = Dataset(0, [0,], [0,])
        d.set_errorbar(color="red")
        self.assertEqual(d._errorbar.color, Color.RED)

class test_classmethod(ut.TestCase):
    """test classmethod for quick plot"""
    def test_banddos(self):
        """band dos graph"""
        p = Plot.band_dos()
        self.assertEqual(len(p), 2)

    def test_bandstructure(self):
        """band graph"""
        p = Plot.bandstructure()
        self.assertEqual(len(p), 1)

    def test_dos(self):
        """dos graph"""
        p = Plot.dos()
        self.assertEqual(len(p), 1)

    def test_double_y(self):
        """dos graph"""
        p = Plot.double_yaxis()
        self.assertEqual(len(p), 2)

class test_read_agr(ut.TestCase):
    """test agr reading methods"""
    def text_extract_data_from_agr(self):
        """extract data"""
        tf = tempfile.NamedTemporaryFile(suffix=".agr")
        types, data, legends = extract_data_from_agr(tf.name)
        # empty
        self.assertListEqual([], types)
        self.assertListEqual([], data)
        self.assertListEqual([], legends)
        with open(tf.name, 'w') as h:
            print("@ s0 legend \"test\"\n@target G0.S0\n@type xy\n1 2\n3 4\n5 6\n&\n", file=h)

        types, data, legends = extract_data_from_agr(tf.name)
        self.assertListEqual(['xy'], types)
        self.assertListEqual(['test'], legends)
        self.assertEqual(1, len(data))
        self.assertTrue(array_equal(data[0], [[1, 3, 5], [2, 4, 6]]))
        tf.close()


if __name__ == "__main__":
    ut.main()
