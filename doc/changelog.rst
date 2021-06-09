Changelog
=========
2021-06-09
----------
improve quick grace plot to parse NXY data

minor improve in beamer template and grace object

2021-05-18
----------
add equation of states

2021-05-12
----------
Improve beamer doctemp

2021-05-08
----------
Improve toc and appendix part in tex doctemp

* Refactor the logger.

2021-05-05
----------
Machine file generation in w2k.

More option in pkgs.tex of TeX document template.

2021-04-19
----------
Improvement for STEM reading template.

[fix]
^^^^^
* (bs) add unit option for displaying band/te
* (scripts) print head of dielectric matrix for q!=0

2021-04-07
----------
Special function Gamma(1/2-n) and tests.

New template for STEM book reading,
improved report template.

2021-03-26
----------
Quick grace plotter, color cycler in graceplot

2021-03-25
----------
Fix error in solid angles

Fix symops for spglib fallback in ``Cell``

2021-03-24
----------
skip missing package exception unless called

* Refresh beamer template

[improve]
^^^^^^^^^
* (scripts) also export total DOS with ``m_vasp_dos``
* (scripts) ``apb`` and ``ap`` options are now lists
* (workflow) VASP shell module, add AEXX tag in variables for hf

2021-03-02
----------
transition energy for aims, logger in w2k dos

[improve]
^^^^^^^^^
* (workflow) VASP shell module
* (workflow) support LDA+U tags in dft banddos script of VASP

2021-02-10
----------
Kickoff argcomplete for scripts

Improve latex project template

2021-02-02
----------
Band specification in gap degw

2021-01-30
----------
Fix line segments searching when ``klist_band`` like kpoints are parsed.

In order to do this, mechanisms in ``find_k_segments`` and ``compute_x``
of KPath object have changed.

2021-01-29
----------
fix banddos script when parchg is required

2021-01-28
----------
option to draw projected band with prop. area

2021-01-26
----------
self-energy correction extractor

Other change:

* default axis bar linewidth to 3.0
* addition of BandStructure by a real number
* more cell entries in database

2021-01-24
----------
w2k/gap band/dos plotting scripts

* (w2k) dos reader
* (graceplot) change page background default to fill
* (bs) transition energy between any bands and kpoints

2021-01-18
----------
qtl reader and pwav plot for w2k

* allow computing occupation by efermi in bs if occ is absent

2021-01-09
----------
``DBCell`` supports cell conversion now.

* Keyword argument ``filter_k_after`` changed to ``filter_k_behind``
* ``m_aims_gap`` supports kpoint filtering.
* optimize beamer document template

2021-01-08
----------
aims cell reader and exporter, band output reader

2020-12-27
----------
Minor change in document template

2020-12-22
----------
Beamer slides document template

2020-12-18
----------
debug vmat, allow eps data print and compare

2020-12-15
----------
adopt vmat reader for Intel executable

[fix]
^^^^^
* abscissa rescale in band plot

[improve]
^^^^^^^^^
* nbyte_recl parameter of Vmat object (``gap``)

[doc]
^^^^^
* change log rST layout

[new]
^^^^^
* tex project report template (``doctemp``)
* ``display`` module to adapat object curating.

2020-12-14
----------
special functions, etc

[new]
^^^^^
* Gpq in some cutoff (``cell``)
* k-points sort in MPGrid (``kpoints``)
* new functions in (``math_func``)

   * Hypergeometric function 2F2
   * rising factor
   * general combination number

[test]
^^^^^^

* ``test_math_func`` added

[improve]
^^^^^^^^^
* draw eps matrix (``m_gap_eps``)

2020-12-12
----------
New cells, math functions, typo fix

[new]
^^^^^
* more FeS2 structures from ICSD
* math functions for structure constant calculation (``math_func``)
* retrive lattice vectors within some cutoff (``cell``)

2020-12-05
----------
improvements and typo fix

[improve]
^^^^^^^^^
* explicit ENCUTGW and NBANDS setup in ``vasp_gw_conv`` workflow

[fix]
^^^^^
* typo in ``vasp_gw_conv``
* imports in examples

2020-12-03
----------
GAP eps reader script

[improve]
^^^^^^^^^
* gracify appearance
* vmat plot

2020-12-01
----------
Extract commit message from change log

2020-09-21
----------
``_set`` backend method for graceplot objects

2020-09-18
----------
First complete version of ``graceplot.py``

It can generate a file with default parameter that xmgrace can read

