"""Regression check for the optional band overlay in both plot engines."""
import contextlib
import io
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

import matplotlib.pyplot as plt
import numpy as np


class TestBandOverlay(unittest.TestCase):
    def test_compare(self):
        script = Path(__file__).resolve().parents[3] / "scripts" / "m_aims_band"
        source = Path(__file__).parent / "data" / "Si_GW_band1001.out"
        data = np.loadtxt(source)
        data[:, 5::2] += 2.0
        nbands = (data.shape[1] - 4) // 2
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bands"
            comparison = Path(directory) / "shifted.out"
            comparison2 = Path(directory) / "shifted2.out"
            np.savetxt(comparison, data[:2])
            np.savetxt(comparison2, data[2:])
            for engine in ("plt", "grace"):
                for compare in (False, True):
                    argv = [str(script), str(source), "--engine", engine,
                            "--geo", str(Path(directory) / "geometry.in"),
                            "--vbmz", "-o", str(output)]
                    if compare:
                        argv += ["--compare", str(comparison), str(comparison2)]
                    with patch("sys.argv", argv), patch.object(plt, "show"), \
                            contextlib.redirect_stdout(io.StringIO()):
                        runpy.run_path(str(script), run_name="__main__")
                    if engine == "plt":
                        lines = plt.gca().lines
                        self.assertEqual(len(lines), nbands * (1 + compare) + 1)
                        if compare:
                            for first, second in zip(lines[:nbands], lines[nbands:-1]):
                                self.assertEqual(second.get_color(), "red")
                                self.assertEqual(second.get_linestyle(), "--")
                                np.testing.assert_allclose(first.get_ydata(), second.get_ydata())
                        plt.close("all")
                    else:
                        agr = output.with_suffix(".agr").read_text()
                        self.assertEqual(agr.count("line color 2"), nbands if compare else 0)
                        if compare:
                            self.assertIn(f"s{nbands} line linestyle 3", agr)


if __name__ == "__main__":
    unittest.main()
