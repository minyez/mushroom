#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""copy the desired workflow script from workflows directory

If platform is specified, job scheduler head will be added following the sheban
of workflow script.
"""
from pathlib import Path
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from mushroom.core.logger import create_logger
from mushroom.core.hpc import get_scheduler_head
from mushroom.core.db import DBWorkflow

_logger = create_logger("workflows")
del create_logger

def add_scheduler_header(wf: str, dirpath: str, platform: str, use_pbs=False):
    """add platform scheduler header to workflow control script.
    """
    head = get_scheduler_head(platform, use_pbs)
    wf_script = Path(dirpath) / "run_{}.sh".format(wf)
    with open(wf_script, "r") as h:
        lines = h.readlines()
    # avoid duplicate insertion
    prefix = {True: "#PBS"}.get(use_pbs, "#SBATCH")
    if len(lines) > 1:
        if not lines[1].startswith(prefix):
            lines[0] += head
            with open(wf_script, "w") as h:
                print(*lines, sep="", file=h)


def _parser():
    """the argument parser"""
    p = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group()
    g.add_argument("-f", dest="wf", type=str, default=None,
                   help="the name/index of workflow to add")
    g.add_argument("--filter", dest='search', type=str, default=None,
                   help="search available workflows with regex")
    g.add_argument("--init-links", dest='init_links', action="store_true",
                   help="initialize all links of dependency scripts")
    p.add_argument("--dst", type=str, default=".", help="destination to copy the workflow files")
    p.add_argument("--hpc", dest='platform', type=str, default=None, help="name of HPC platform")
    g.add_argument("-p", dest='print', action="store_true", help="print available workflows")
    p.add_argument("--pbs", dest='use_pbs', action="store_true",
                   help="use PBS instead of SLURM (sbatch)")
    p.add_argument("--readme", dest='copy_readme', action="store_true",
                   help="copy README when available")
    p.add_argument("--force", dest='overwrite', action="store_true", help="force overwrite")
    p.add_argument("-D", dest='debug', action="store_true", help="debug mode")
    return p


def workflows():
    """main stream"""
    args = _parser().parse_args()
    dbwf = DBWorkflow()

    if args.debug:
        _logger.setLevel("DEBUG")
    if args.search or args.print:
        for i, wf in dbwf.filter(args.search):
            print("{:3d} : {}".format(i, wf))
        return
    if args.init_links:
        for wf in dbwf.get_avail_workflows():
            dbwf.init_workflow_libs_symlink(wf)
        return

    if args.wf:
        wf = dbwf.get_workflow(args.wf)
        dbwf.init_workflow_libs_symlink(wf)
        dbwf.copy_workflow_to_dst(wf, args.dst, args.overwrite, args.copy_readme)
        if args.platform:
            add_scheduler_header(wf, args.dst, args.platform, args.use_pbs)


if __name__ == "__main__":
    workflows()

