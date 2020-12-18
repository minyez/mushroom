Changelog
=========

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
^^^^^
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

