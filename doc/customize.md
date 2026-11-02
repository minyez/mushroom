# Customization

Several variables can be customized in `.mushroomrc`.

- `log_level` : verbose level of file logger
- `stream_level` : verbose level of stream (stdout) logger
- `sbatch_headers` : SBATCH headers to include after the sheban of workflow control script.
- `pbs_headers` : PBS headers to include after the sheban of workflow control script.
- `symprec` : spglib symmetry tolerance


The `.mushroomrc` file is Python code executed during import, including a file in the current directory. Only run mushroom in directories whose `.mushroomrc` you trust, especially in shared HPC scratch directories.
