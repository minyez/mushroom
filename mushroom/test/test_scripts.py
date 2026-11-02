"""check the module entry point and legacy command forwarders"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest as ut

from mushroom import __version__


class test_entrypoints(ut.TestCase):
    def test_legacy_help(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            for script in sorted((root / 'scripts').glob('m_*')):
                with self.subTest(script=script.name):
                    result = subprocess.run([sys.executable, str(script), '-h'], cwd=tmp,
                                            env=dict(os.environ, PYTHONPATH=str(root)), capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_module_version(self):
        result = subprocess.run([sys.executable, '-m', 'mushroom', '--version'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(__version__, result.stdout)
