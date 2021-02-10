# mushroom

[![CircleCI](https://circleci.com/gh/minyez/mushroom.svg?style=svg&circle-token=ffe7a030a0398a96231dfde5ab97f5e797256fd2)](https://app.circleci.com/pipelines/github/minyez/mushroom/)
[![codecov](https://codecov.io/gh/minyez/mushroom/branch/master/graph/badge.svg?token=SM7R1XB2VW)](https://codecov.io/gh/minyez/mushroom)

A **M**ulti-f**U**nctional, **S**imple and **H**elpful **R**esearch t**OO**lkit for **M**aterial science (build time)

This is just a contrived name for yet another analysis tool for scientific computations in material science.

*N.B.*: I have been searching for a better way to write efficient, readable and maintainable code,
and hopefully will do in the days to come.
Any suggestions concerning code style, feature, etc, are totally welcome.

## Dependencies

- Python >= 3.7
- NumPy
- SciPy (for special functions)
- Spglib (for symmtery detection)
- PyCIFRW (for reading cif)
- BeautifulSoup4 (for scrapper and XML parser)
- Bash >= 4.4 (for using workflow scripts)

Run `pip install -r requirements.txt` to install dependencies.
If you use `conda`, try

```bash
conda install -c conda-forge -n myenv --file requirements.txt
```

Note that in this case you may need to set your virtual environment `myenv` first.

There is also optional depedencies declared in `requirements_optional.txt`

- argcomplete (for completing scripts arguments from command line)

## Installation

Assume that mushroom is cloned to `path/to/mushroom`.
To use mushroom python package and scripts in `scripts`

```bash
export PYTHONPATH="path/to/mushroom:$PYTHONPATH"
export PATH="path/to/mushroom/scripts:$PATH"
```

You may test the Python pacakge by running `pytest`

```bash
pytest
```

or just

```bash
make pytest
```

## Usage

See documentaion in `doc` for usage.

## Examples

See `examples`.

