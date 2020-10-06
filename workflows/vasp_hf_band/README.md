# `vasp_hf_band`

## Description

Script to run hybrid functional (HF) band structure calculation in VASP.

The following 5-step procedure is adopted:

1. Non-self-consistent PBE calculation (NELM=1) with k-path `KPOINTS.path` to get `IBZKPT.band`
2. Non-self-consistent PBE calculation (NELM=1) with homogenous grid `KPOINTS.scf` to get `IBZKPT.scf`
3. PBE SCF with the KPOINTS.band which combines `IBZKPT.band` and `IBZKPT.band`,
    with all points in the second weighing zero.
4. Fixed-charge coarse HF calculation with above KPOINTS.
5. Fixed-charge accurate HF calculation with above KPOINTS.

Note that:
- give a further look to every INCAR
- prepare your own `POSCAR` and `POTCAR`
- check and adapt `variables.sh`. `KPOINTS.path`
- `KPOINTS.scf` should be consistent with previous HF SCF calculation
- For now, `CHGCAR` preconverged under a HF SCF calculation with the same SCF kmesh,
   ENCUT and PREC is required (could be done with `vasp_hf_scf` workflow).
   Copy it here and name it as `CHGCAR.hf`.

## Files

Things you may need to adapt
- `variables.sh` : variables to set by user
- `INCAR.pbe` : input for PBE preconverge SCF
- `INCAR.hf` : input for HF band calculation
- `KPOINTS.scf` : kmesh for PBE and HF SCF
- `KPOINTS.path` : k-path file for band structure

Things usually not necessary to change
- `run_vasp_hf_band.sh` : flow control file
- `common.sh` : infrastructure functions for common use
- `vasp.sh` : VASP infrastructure functions

## TODO

- [ ] optimize for metal

## References

See:

