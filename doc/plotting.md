# Band data, DOS and convergence plots

Read a calculation once and use the same data with either backend. The library
works without Click. Matplotlib is required only for the `plt` backend; install
it with `pip install 'mushroom[plot]'`. Grace files can be written with NumPy
alone, without `xmgrace` or `gracebat` installed. Image conversion from Grace
requires `gracebat`.

## Python

```python
import matplotlib as mpl
import matplotlib.pyplot as plt
from mushroom.io import read_band, read_dos
from mushroom.visual.pyplot import gracify_style, figsize
from mushroom.visual.bandplot import plot_band, plot_band_dos

bands = read_band("calculation", code="vasp")
with mpl.rc_context(gracify_style(fontsize=10)):
    fig, ax = plt.subplots(figsize=figsize("aps-single"))
    plot_band(ax, bands.bs, bands.kpath(), ksymbols=bands.ksymbols)
    ax.set_ylim(-6, 6)
    fig.savefig("bands.pdf")

    dos = read_dos("calculation", code="vasp")
    fig, (band_ax, dos_ax) = plot_band_dos(
        bands.bs, bands.kpath(), dos, ksymbols=bands.ksymbols)
    fig.savefig("band-dos.pdf")
```

`gracify_style()` returns a dictionary and does not change global settings.
`rc_gracify()` applies the same settings globally; repeated calls do not enlarge
ticks. Figure column presets are `aps-single`, `aps-double`, `acs-single`,
`acs-double`, `nature-single`, and `nature-double`. `aspect` and `nrows` control
height relative to the column width.

```python
from mushroom.io import read_band
from mushroom.visual.graceplot import Plot
from mushroom.visual.bandplot import plot_band

bands = read_band("calculation", code="aims", kind="gw")
fig, ax = Plot.subplots()
plot_band(ax, bands.bs, bands.kpath(), ref="vbm", ksymbols=bands.ksymbols)
ax.set_ylim(-6, 6)
fig.write(file="bands.agr")
```

`plot_band` returns its original axes. It accepts matplotlib Axes, Grace Graph,
or a wrapper from `mushroom.visual.axes`. Up/down bands use blue solid/red dashed
lines by default; `spin=0` or `spin=1` selects one channel. The deprecated
`bandplot()` wrapper remains available.

Energy references are `None`, `"none"`, a number in the object's energy unit,
`"vbm"`, `"cbm"`, `"ef"`/`"efermi"`/`"fermi"`, `"vbm_0"`, or a state such as
`"0:2:cbm+1"`. Both spins use one reference. Comparison plots align each data set
independently. Plain labels such as `Gamma`, `X`, and `K|U` are formatted for the
selected backend. Labels must match the number of special path positions.

In `plot_band_dos`, the default DOS shift is the band reference in the shared
absolute energy scale. Use `dos_ref="efermi"` if the DOS has its own Fermi zero.
DOS is converted to the band energy unit on a copy. Spin-down DOS is plotted
negative by default. `plot_fatband(scale=...)` scales marker diameters in Grace
units (six points); diameter follows weight, or area follows weight with
`prop_area=True`. Grace ignores filled DOS regions with a warning.

## Command line

New plotting commands default to `--engine plt`. With `-o`, the extension
chooses the image format. Without `-o`, interactive matplotlib backends show the
figure; noninteractive backends save `plotband.pdf`, `plotdos.pdf`,
`plot_qpcorr.pdf`, or `collect.pdf`. `--savefig` applies only to Grace conversion.
Existing program-specific commands retain their backend and filename defaults.
`vasp band` and `w2k band` now draw both spins when present; the existing WIEN2k
`--spin` still selects the fatband channel.

```sh
mushroom band calculation -o bands.pdf --ref vbm
mushroom band run-a run-b --labels PBE HSE --align vbm -o comparison.svg
mushroom band calculation --apb 'Si:s:0,1' --area -o fatband.png
mushroom band calculation --dos calculation --aps 'Si:p' -o combined.png
mushroom dos calculation --aps 'Si:s' 'Si:p' -e m8~5 -o dos.pdf
mushroom qp-corr librpa.out --fit --ref vbm -o corrections.pdf
mushroom collect --pat 'k*' --param 'k=k(\d+)' --sort k --delta energy --csv convergence.csv
mushroom collect --pat 'k*' --param 'k=k(\d+)' --plot k:energy -o convergence.pdf
mushroom emass calculation --band vbm cbm --k 20 -n 5
```

Band paths can be directories, native files or `.npz`. Directory detection
rejects ties; use `--code` to select the program. Supported native bands are
VASP, FHI-aims, WIEN2k and LibRPA. QP pairs additionally support GAP eqpeV files.
KS/QP arrays from `read_qp_pair` share the same printed band window. For other
objects, `qp_correction` honors optional zero-based `band_start` attributes;
without these, both arrays must start at the same band.

Collection records individual failures in the `error` field and continues.
Energy deltas use the last row as reference and are reported in meV. Energies
and gaps use eV, and wall time uses seconds. WIEN2k SCF parsing is provisional:
real `case.scf` and `case.dayfile` fixtures are still needed. Completion requires
the final dayfile convergence flags and normal stop, because WIEN2k 19.2
`run_lapw` writes convergence there rather than in `case.scf`.

Effective masses use a quadratic fit on each side of the chosen point, never
across a special point. At least three distinct points on a side are needed.
Reciprocal vectors must be in inverse Angstrom and include 2pi, as supplied by
`BandPathData.kpath()`. A normalized plotting axis does not change the physical
fit. Masses are signed: valence maxima give negative values. Without `--k`, the
maximum occupied or minimum empty state of each selected band is used.

## Portable archives and HPC workflow

```sh
# HPC: parse once, analyze and transfer the small archive
mushroom band calculation --data --save bands.npz
# Local computer
mushroom band bands.npz -o bands.pdf
mushroom band bands.npz --engine grace -o bands.agr
mushroom dos calculation --data --save dos.npz
```

`BandStructure`, `DensityOfStates` and `BandPathData` provide `save`/`load`.
BandStructure and DensityOfStates also provide `to_dict`/`from_dict`.
An archive is written with `numpy.savez_compressed` and can be read with
`numpy.load(path, allow_pickle=False)`. No object arrays or pickle are used.
`__meta__` is a scalar JSON string containing `format="mushroom"`,
`format_version=1`, `kind`, units, Fermi energy and projector labels.

| Kind | Array keys | Additional metadata |
| --- | --- | --- |
| BandStructure | `eigen`, `occ`, `weight`, `pwav` | `unit`, `efermi`, `atms`, `prjs`, `use_occ_only` |
| DensityOfStates | `egrid`, `tdos`, `pdos` | `unit`, `efermi`, `atms`, `prjs` |
| BandPathData | band arrays plus `kpts`, `recp_latt` | band metadata plus `ksymbols`, `code`, `source` |

Missing occupations/projections/reciprocal vectors are omitted. Occupations
inferred from a Fermi level are stored explicitly to retain band-edge decisions.
Loaders reject the wrong kind and unsupported versions. Fractional `kpts` have
shape `(nkpts, 3)`; `recp_latt` rows use the `Cell.b` convention in inverse
Angstrom including 2pi. Archives are data containers, not executable code.
