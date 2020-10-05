#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""copy the desired workflow script from workflows directory
"""
import os
from shutil import copyfile
from pathlib import Path
from argparse import ArgumentParser

from mushroom._core.logger import create_logger

DIR_WORKFLOWS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'workflows'))
PATH_WORKFLOWS = Path(DIR_WORKFLOWS)
_logger = create_logger("workflows")
del create_logger

def add_sbatch_header(wf, platform):
    """add platform-specific sbatch header to workflow script"""
    raise NotImplementedError

def copy_wf_to_dst(wf, dst="."):
    """copy the workflow files to directory dst

    Args:
        wf (str) : name of workflow
        dst (str) : copying destination. Default to pwd
    """
    p = PATH_WORKFLOWS / wf
    dst = Path(dst)
    _logger.info("Copying %s files to %s", p, dst)
    for x in p.glob("*"):
        if not x.name.startswith("."):
            copyfile(x, dst / x.name)
            _logger.info(">> %s", x.name)

def get_avail_workflows(prog=None):
    """get all available workflows in the directory

    Args:
        prog (str) : name of program.
            If set, only the workflows for this program will be shown.
    """
    if prog:
        awfs = [x.name for x in PATH_WORKFLOWS.glob(prog.lower() + "_*")
                if x.is_dir() and x.name != "libs"]
    else:
        awfs = [x.name for x in PATH_WORKFLOWS.iterdir()
                if x.is_dir() and x.name != "libs"]
    return awfs

def init_workflow_symlink(wf):
    """create symlinks to common libraries in all workflow directories

    If file `.depends` is found in the directory, it will read each line as
    file name of the library script to source in `lib`

    Args:
        wf (str) : name of workflow
    """
    p = Path(PATH_WORKFLOWS / wf / ".depends")
    if p.is_file():
        _logger.debug(p)
        with p.open() as f:
            for x in f.readlines():
                dep = x.strip()
                pnew = PATH_WORKFLOWS / wf / dep
                if not pnew.is_symlink():
                    pnew.symlink_to(PATH_WORKFLOWS / 'libs' / dep)
    else:
        prog = wf.split("_")[0] + ".sh"
        p = Path(PATH_WORKFLOWS / wf / prog)
        _logger.debug(p)
        if not p.is_symlink():
            p.symlink_to(PATH_WORKFLOWS / 'libs' / prog)

def complete_workflow_name(wf):
    """complete the workflow name

    Args:
        wf (str) : name of workflow
    """
    choices = get_avail_workflows()
    if wf in choices:
        _logger.info("Found workflow: %s", wf)
        return wf
    for x in choices:
        if x.startswith(wf):
            _logger.info("Detected workflow: %s for %s", x, wf)
            return x
    raise ValueError("no workflow is found for ", wf)

def _parser():
    """the argument parser"""
    p = ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group()
    g.add_argument("-f", dest="wf", type=str, default=None,
                   help="the name of workflow to add")
    g.add_argument("-s", dest='search', type=str, default=None,
                   help="search available workflows for program")
    g.add_argument("-p", dest='print', action="store_true",
                   help="print available workflows")
    g.add_argument("--hpc", dest='platform', type=str, default=None,
                   help="name of HPC platform")
    g.add_argument("--init-links", dest='init_links', action="store_true",
                   help="initialize all links of dependency scripts")
    p.add_argument("--dst", type=str, default=".",
                   help="destination to copy the workflow files")
    p.add_argument("-D", dest='debug', action="store_true",
                   help="debug mode")
    return p.parse_args()

def workflows():
    """main stream"""
    args = _parser()

    if args.debug:
        _logger.setLevel("DEBUG")
    if args.search or args.print:
        for wf in get_avail_workflows(prog=args.search):
            print(wf)
        return
    if args.init_links:
        for wf in get_avail_workflows():
            init_workflow_symlink(wf)
        return

    if args.wf:
        wf = complete_workflow_name(args.wf)
        init_workflow_symlink(wf)
        copy_wf_to_dst(wf, args.dst)


if __name__ == "__main__":
    workflows()
