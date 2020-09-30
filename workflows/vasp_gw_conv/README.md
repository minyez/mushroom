# `vasp_gw_conv`

## Description

Script to run GW convergence tests on ENCUT, ENCUTGW and NBANDS simulaneously in VASP.

## Files

- `run_vasp_gw_conv.sh` : flow control file
- `vasp.sh` : VASP infrastructure functions
- `INCAR.scf`
- `KPOINTS.scf`
- `INCAR.diag`
- `INCAR.gw`
- `KPOINTS.gw`

## TODO

Maximum number of plane-wave can be estimated from crystal structure,
Instead of extrapolating from known number at some cut-off,
the convergence of bands should guess from the structure.

## References

See

- [[ShishkinM06]]
- [[KlimesJ14]]
- [[GruneisA14]]
