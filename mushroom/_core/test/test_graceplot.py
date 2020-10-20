# -*- coding: utf-8 -*-
"""Test graceplot"""
import unittest as ut

from mushroom._core.graceplot import (_ColorMap, Color, Font, Symbol,
                                      Graph, View,
                                      Plot,
                                      encode_string)

class test_string_encoder(ut.TestCase):
    """test encoder to get grace-favored text string"""
    def test_greek(self):
        """encoding greek"""
        self.assertEqual(encode_string(r"\Gamma \beta"), r"\xG\f{} \xb\f{}")

class test_ColorMap(ut.TestCase):
    """test colormap utilites"""

    def test_output(self):
        """test if the grace output of default colormap is as expected"""
        c = _ColorMap()
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
        c = _ColorMap()
        n = c.n
        c.add(10, 10, 10, None)
        self.assertEqual(n + 1, c.n)
        self.assertTrue(c.has_color("color" + str(n)))
        self.assertEqual(c[n], "color" + str(n))


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

    def test_set_view(self):
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

class test_Graph(ut.TestCase):
    """test graph operations"""

    def test_change_view(self):
        """test if view changing is working"""
        g = Graph(index=1)
        g.set_view(0.0, 0.0, 1.0, 0.5)
        self.assertListEqual(g._view.view_location, [0.0, 0.0, 1.0, 0.5])

    def test_plot(self):
        """test plotting data"""
        g = Graph(index=1)
        x = [0.0, 1.0, 2.0]
        y = [1.0, 2.0, 3.0]
        g.plot(x, y, label="y=x+1", symbol="o", color="red")
        self.assertEqual(g[0]._symbol.type, Symbol.get("o"))
        self.assertEqual(g[0]._symbol.color, Color.get("red"))
        self.assertEqual(g[0]._line.color, Color.get("red"))
        

class test_Axis(ut.TestCase):
    """test Axix functionality"""


class test_Plot(ut.TestCase):
    """test Plot functionality"""

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

    def test_regular_graphs(self):
        """generate regular graph alignment"""
        p = Plot(1, 1)
        self.assertEqual(len(p._graphs), 1*1)
        p = Plot(3, 4, hgap=[0.01, 0.0, 0.02], vgap=[0.02, 0.0],
                 width_ratios="3:2:1:4", heigh_ratios="1:3:2")
        self.assertEqual(len(p._graphs), 3*4)


if __name__ == "__main__":
    ut.main()
