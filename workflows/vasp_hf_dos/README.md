# `vasp_hf_dos`

## Description

Script to run hybrid functional (HF) DOS calculations in VASP.

Note:
- you have to prepare POSCAR and POTCAR before running the script.
- check the `variables.sh` file.
- If you have already preconverged CHGCAR file with the same `NGx(F)`,
  which usually means the same `ENCUT` and `PREC` is used, copy it
  here and name it as `CHGCAR.hf`.
- If you don't, then check the `KPOINTS.scf` file and make it suit your needs.

## Files

Things you may need to adapt
- `variables.sh` : variables to set by user
- `INCAR.pbe` : input for PBE SCF for preconvergence
- `INCAR.hf` : input for HF SCF loop
- `KPOINTS.dos` : kmesh for the DOS calculation

Optional file
- `KPOINTS.scf` : required when there is no `CHGCAR.hf`

Things usually not necessary to change
- `run_vasp_hf_dos.sh` : flow control file
- `vasp.sh` : VASP infrastructure functions
- `common.sh` : infrastructure functions for general usage

## TODO

- [ ] data collection

## References

