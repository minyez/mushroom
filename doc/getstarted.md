# Get started

## Dependencies

The following packages are required for normal use
- Python >= 3.7
- NumPy
- SciPy (for special functions)
- Spglib (for symmtery detection)

These dependencies can be installed by

```shell
pip install -r requirements.txt
```

or

```bash
# assume you already have virtual environment `myenv`
conda install -c conda-forge -n myenv --file requirements.txt
```

if you use conda.

There are also optional depedencies

- lxml and BeautifulSoup4 (for XML and HTML parser)
- argcomplete (for completing scripts arguments from command line)
- matplotlib (for some scripts and utilites under `visual/pyplot` module)

They are declared in `requirements_optional.txt` and can be installed like above.

## Installation

You need to adjust `PYTHONPATH` and `PATH` environment variables to use Mushroom python package and scripts in `scripts`
Assume that Mushroom is cloned to `path/to/mushroom`.

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

Then you can test this pacakge by running `pytest`
```bash
pytest
```
at the root path of mushroom.

Note that some tests will not run if you do not have all (basic and optional) dependencies included.
To enable a full test, please install all the runtime and test dependencies in `requirements_test.txt`.
This can be done in the same way as descibed in [Dependencies](#dependencies).
