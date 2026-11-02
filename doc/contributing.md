# Contributing

Mushroom supports Python 3.9 and newer. Library modules outside `mushroom.cli` must not import Click or CLI modules. Import optional numerical and plotting packages only where needed, or handle their absence explicitly.

## Tests

Use `unittest as ut` and `class test_name(ut.TestCase)` in the relevant package's `test/` directory. Isolate generated files with `tempfile`. Every bug fix needs a regression test that fails before the fix. Derive expected values independently: use hand calculations, physical identities, real program output, or explicitly packed binary records. Check array shapes and units as well as values.

Run `python -m pytest` and `make lint` after each logical change. Run the full suite on Python 3.9 and 3.12 before release. Measure branch-aware coverage with `python -m pytest --cov=mushroom --cov-branch`. Test dependencies are listed in `requirements_test.txt`; docstring coverage is checked with `interrogate -v mushroom`.

## Docstrings

Use Google-style docstrings with triple double quotes. Keep the summary on one line, with a lowercase initial and no final period. Separate longer explanations from the summary with one blank line. Use a raw docstring when it contains backslashes.

Use `Args:`, `Returns:`, `Yields:`, `Raises:`, `Note:`, `Examples:`, and `Attributes:`. Write parameter entries as `name (type): description`, without a space before the colon. Document class constructor arguments in the class docstring. Simple getters need only a summary; readers, parsers and numerical operations need their units, array shapes, indexing conventions and relevant error conditions.

```python
from typing import Optional


def read_energies(path: str, nmax: Optional[int] = None):
    """read the energies from a text file

    Args:
        path (str): input file path
        nmax (int): maximum number of states; None reads all states

    Returns:
        ndarray: energies in eV, shape (nstates,)

    Raises:
        ValueError: if an energy cannot be parsed
    """
```

Run `ruff check mushroom`. The configuration preserves the established summary style and excludes tests from docstring checks. The author's three untracked work-in-progress modules are also excluded from lint and documentation coverage; do not edit or stage them as part of maintenance work.

## CI and packaging

Install from a checkout with `python -m pip install .`, or keep using the documented `PYTHONPATH` setup on HPC systems. The legacy scripts remain in `scripts/`. Build distributions with `python -m build`.

Codecov uploads use the CircleCI orb and its `CODECOV_TOKEN` environment variable. Rotate the previously committed upload token in Codecov, then set its replacement in CircleCI project settings. The token must not be stored in repository files. See the [Codecov token setup documentation](https://docs.codecov.com/docs/adding-the-codecov-token).
