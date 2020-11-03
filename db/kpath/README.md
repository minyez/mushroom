# K-path database

All special kpoints along a k-point path are stored in a JSON file.

## Naming of JSON

The file should be named in a short-hand form of the special k-point symbols, and
saved under the directory named after the number of space group of to the
crystal cell which has the Brillouin zone where the special kpoints are defined.

## keys and values

- `variation`: the variation type defined in Setyawan and Curtarolo, 2010
- `ksymbols`: use for drawing plots, e.g. parsed to `--sym` option of `m_vasp_band`
- `labels`: labels of special points on the path.
- `coeffs`: coefficients or coordinates of special point on the path.
- `source`: the source where the kpath is obtained (optional)

Note `labels` and `coeffs` should have the same number of members, which is usually even
to include all start and end points of path segments.

