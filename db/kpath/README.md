# K-path database

all kpaths are stored in a JSON file. 

## Naming

The file should be named as "spacegroup number" + `shorthand of k-point symbols`.

## keys and values

- `ksymbols`: use for drawing plots, e.g. parsed to `--sym` option of `m_vasp_band`
- `labels`: labels of special points on the path.
- `coeffs`: coefficients or coordinates of special point on the path.

Note `labels` and `coeffs` should have the same number of members, which must be even
to include all start and end points of path segments.

