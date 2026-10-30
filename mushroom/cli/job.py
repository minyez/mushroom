# -*- coding: utf-8 -*-
"""HPC job commands

Modules heavier than click are imported inside the commands to keep the entry fast.
"""
import os
import pathlib
import subprocess as sp

import click

from mushroom.cli._utils import Group, multi_option

SUBMITTED_STAMP = ".submitted"


@click.group(cls=Group)
def job():
    """HPC job utilities"""


@job.command("add-header")
@click.argument("script_path")
@click.option("-J", "jobname", default=None, help="job name")
@click.option("-N", "nnodes", type=int, default=1, help="number of nodes")
@click.option("-n", "ntasks", type=int, default=None, help="number of tasks")
@click.option("-p", "platform", default=None, help="manually specify platform")
@click.option("--use-pbs", is_flag=True, help="use PBS headers")
def add_header(script_path, jobname, nnodes, ntasks, platform, use_pbs):
    """add job control headers to script for running on an HPC"""
    from mushroom.hpc import add_scheduler_header, current_platform, current_use_pbs

    pscript = pathlib.Path(script_path)
    if not pscript.is_file():
        raise FileNotFoundError("script {} is not found".format(pscript))
    if platform is None:
        platform = current_platform
        use_pbs = current_use_pbs
    try:
        add_scheduler_header(pscript, platform, use_pbs=use_pbs)
    except ValueError as err:
        raise ValueError from err


def _create_sbatch_script_object(script_path, opts_extra):
    """create the script object from template and extra sbatch options in the form of k:v"""
    from mushroom.hpc import SbatchScript

    ss = SbatchScript(template=script_path)
    sbatch_opts_extra = {}
    if opts_extra:
        for option in opts_extra:
            k, v = option.split(":", maxsplit=1)
            sbatch_opts_extra[k] = v
        print("Extra sbatch options: {}".format(sbatch_opts_extra))
    ss.set_sbatch(**sbatch_opts_extra)
    return ss


def _generate_sbatch_args(script_name: str, dep: str = None, dep_job_id: int = None,
                          sbatch_cmd: str = "sbatch"):
    """generate the arguments of submission command"""
    args = [sbatch_cmd,]
    if dep is not None and dep_job_id is not None:
        args.append("--dependency=after" + dep + f":{dep_job_id:d}")
    args.append(script_name)
    return args


def _generate_dir_list(pat, only_list):
    """get the directories to submit"""
    if pat is None:
        pat = "*/"
    if not only_list:
        return list(d for d in pathlib.Path(".").glob(pat) if d.is_dir())
    return [d for d in map(pathlib.Path, only_list) if d.is_dir()]


# pylint: disable=R0914
@job.command()
@click.argument("sbatch_script")
@click.option("--dry", is_flag=True, help="Generate run script but do not submit")
@click.option("--max", "max_jobs", type=int, default=100, help="max jobs to submit")
@click.option("--dep", default=None, type=click.Choice(["any", "ok"]),
              help="job dependency (after), the submitted jobs will depend on previous one")
@click.option("--dep-jobid", type=int, default=None,
              help="ID of initial dependent job, only works when --dep is set")
@multi_option("--only", metavar="DIR...", help="only submit in these directories")
@click.option("--prefix", default=None, help="prefix to job name")
@click.option("--pat", default=None, help="Pattern for glob.glob")
@click.option("--cmd", default="sbatch", help="sbatch command, default: sbatch")
@multi_option("-s", "--sbatch-opts-extra", metavar="K:V...", help="extra sbatch options, k:v")
def submit(sbatch_script, dry, max_jobs, dep, dep_jobid, only, prefix, pat, cmd, sbatch_opts_extra):
    """Copy calculation script and submit"""
    from mushroom.aims.analyse import is_finished_aimsdir
    from mushroom.core.ioutils import conv_integers_to_series
    from mushroom.hpc import _logger, is_slurm_enabled

    # exit when it is not on an HPC and is not a dry run
    if not is_slurm_enabled() and not dry:
        raise OSError("sacct is not enabled, probably we are not on an HPC")

    finished = 0
    submitted = 0
    failed = 0
    skipped = 0
    script_path = pathlib.Path(sbatch_script)
    ss = _create_sbatch_script_object(script_path, sbatch_opts_extra)

    script_name = script_path.name
    cwd = pathlib.Path(".").absolute()
    all_dirs = _generate_dir_list(pat, only)

    jobids_submitted = []

    for d in all_dirs:
        # TODO: adapt calculations other than FHI-aims
        is_finished = is_finished_aimsdir(d)
        submitted_stampfile = d / SUBMITTED_STAMP
        if is_finished is not None:
            print("Directory {} finished".format(d.name))
            finished += 1
            continue
        if submitted_stampfile.exists():
            print("Directory {} already submitted, skip".format(d))
            skipped += 1
            continue
        if submitted >= max_jobs:
            continue

        # set job name
        if prefix is None:
            ss.set_sbatch(J=d)
        else:
            ss.set_sbatch(J="{}_{}".format(prefix, d))
        ss.write(d / script_name)
        os.chmod(d / script_name, 0o775)

        os.chdir(d.absolute())
        if not dry:
            sbatch_args = _generate_sbatch_args(script_name, dep, dep_jobid, sbatch_cmd=cmd)
            _logger.debug("Running subprocess: %s", " ".join(sbatch_args))
            p = sp.Popen(sbatch_args, stdout=sp.PIPE, stderr=sp.PIPE)
            out, _ = p.communicate()
            out = str(out, encoding='utf-8')
            ret = p.returncode
            if ret == 0:
                jobid = int(out.split()[-1])
                dep_jobid = jobid
                jobids_submitted.append(jobid)
                print("Submitted copied {} at directory {}, jobid {}".format(script_name, d, jobid))
                submitted += 1
                # create an empty stamp to mark already submitted
                pathlib.Path(SUBMITTED_STAMP).touch()
            else:
                print("Failed to submit {} at directory {}".format(script_name, d))
                failed += 1
        else:
            print("Entered {}, exiting as dry-run".format(d))
            skipped += 1
        os.chdir(cwd)

    if submitted >= max_jobs:
        print("Submitted {} jobs, maxmimal at single run, now take a break".format(submitted))

    print("Already completed tasks: {}".format(finished))
    print("  Skipped submitted dir: {}".format(skipped))
    print("  Newly submitted tasks: {}".format(submitted))
    print("       Failed submision: {}".format(failed))

    if len(jobids_submitted) > 0:
        print("Submitted jobs: {}".format(",".join(conv_integers_to_series(jobids_submitted))))
