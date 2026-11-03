"""verify optional dependencies do not leak into library imports"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest as ut


class test_library_imports(ut.TestCase):
    def test_without_optional_dependencies(self):
        source = '''
import importlib
import pkgutil
import sys
sys.modules[sys.argv[1]] = None
import mushroom
excluded = {"mushroom.__main__", "mushroom.abacus", "mushroom.core.atoms", "mushroom.core.bz"}
def walk(package):
    for info in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if info.name in excluded or ".test" in info.name or info.name.startswith("mushroom.cli"):
            continue
        module = importlib.import_module(info.name)
        if info.ispkg:
            walk(module)
walk(mushroom)
for name in ('mushroom.io', 'mushroom.collect', 'mushroom.visual.bandplot', 'mushroom.visual.dosplot'):
    importlib.import_module(name)
if sys.argv[1] == 'matplotlib':
    from mushroom.core.bs import BandStructure
    from mushroom.core.kpoints import KPathLinearizer
    from mushroom.visual.graceplot import Plot
    from mushroom.visual.bandplot import plot_band
    bs = BandStructure([[[-1., 2.], [-2., 3.]]], efermi=0.)
    plot_band(Plot.subplots()[1], bs, KPathLinearizer([[0, 0, 0], [.5, 0, 0]]))
'''
        root = Path(__file__).resolve().parents[2]
        for missing in ['click', 'matplotlib', 'spglib', 'scipy']:
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as tmp:
                result = subprocess.run([sys.executable, '-c', source, missing], cwd=tmp,
                                        env=dict(os.environ, PYTHONPATH=str(root)), capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
