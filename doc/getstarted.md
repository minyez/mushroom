# Get started

## Dependencies

- Python >= 3.7
- NumPy
- SciPy (for special functions)
- Spglib (for symmtery detection)
- lxml and BeautifulSoup4 (for XML parser)
- matplotlib

These dependencies can be installed by

```shell
pip install -r requirements.txt
```

or

```bash
conda install -c conda-forge -n myenv --file requirements.txt
```

if you use conda

## Installation

Assume that mushroom is cloned to `path/to/mushroom`.
To use mushroom python package and scripts in `scripts`

```bash
export PYTHONPATH="path/to/mushroom:$PYTHONPATH"
export PATH="path/to/mushroom/scripts:$PATH"
```

## Test

Extra dependencies have to be installed to test the code.
Among them, `pytest` is the fundamental one

```shell
pip install pytest
```

Then you may test this pacakge by running `pytest`
at the root path of mushroom.
