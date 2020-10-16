# `vasp_hf_conv`

## Description

Script to run convergence test for hybrid functional (HF) calculations in VASP.

The convergence is tested against `ENCUT` and k-point mesh.

Note: you have to prepare POSCAR and POTCAR before running the script.

## Files

Things you may need to adapt
- `variables.sh` : variables to set by user
- `INCAR.pbe` : input for PBE preconverge SCF
- `INCAR.hf` : input for HF SCF loop

Thins usually not necessary to change
- `run_vasp_hf_conv.sh` : flow control script 
- `common.sh` : infrastructure functions for common use
- `vasp.sh` : VASP infrastructure functions

## TODO

## References

See:

