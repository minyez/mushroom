# `vasp_hf_band`

## Description

Script to run hybrid functional (HF) band structure calculation in VASP.

## Files

Things you may need to adapt
- `variables.sh` : variables to set by user
- `INCAR.pbe` : input for PBE preconverge SCF
- `INCAR.hf` : input for HF SCF loop
- `INCAR.band` : input for HF band structure
- `KPOINTS.scf` : kmesh for PBE and HF SCF
- `KPOINTS.band` : kpath file for band structure

Thins usually not necessary to change
- `run_vasp_hf_band.sh` : flow control file
- `common.sh` : infrastructure functions for common use
- `vasp.sh` : VASP infrastructure functions

## TODO

## References

See:

