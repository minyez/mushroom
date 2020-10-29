# `vasp_hf_scf`

## Description

Workflow script and inputs to run hybrid functional (HF) SCF calculations in VASP.

Note:
- you have to prepare POSCAR and POTCAR before running the script.
- check the `variables.sh` file.
- check the `KPOINTS.scf` and adapt to your need and resources

## Files

Things you may need to adapt
- `variables.sh` : variables to set by user
- `INCAR.pbe` : input for PBE SCF for preconvergence
- `INCAR.coarse` : input for preconverging HF with a coarse parameter
- `INCAR.hf` : input for HF SCF loop
- `KPOINTS.scf` : kmesh for the whole calculation

Things usually not necessary to change
- `run_vasp_hf_scf.sh` : flow control file
- `vasp.sh` : VASP infrastructure functions
- `common.sh` : infrastructure functions for general usage

## TODO

- [ ] data collection

## References

