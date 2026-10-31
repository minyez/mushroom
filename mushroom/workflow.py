# -*- coding: utf-8 -*-
"""utilities shared by the workflow scripts

Program-specific steps are put in the module of the program, e.g. ``mushroom.vasp``.
"""
import math
import os
import pathlib
import shlex
import shutil
import subprocess as sp
from typing import List, Union

from mushroom.core.logger import loggers
from mushroom.core.typehint import Path

_logger = loggers["workflow"]

__all__ = [
    "get_ntasks",
    "require_executable",
    "require_files",
    "largest_div_below_sqrt",
    "run_command",
]


def get_ntasks(default: int) -> int:
    """get the number of tasks from the scheduler, otherwise use ``default``"""
    return int(os.environ.get("SLURM_NTASKS", default))


def require_executable(executable: str):
    """raise when the command or path is not an executable"""
    if shutil.which(executable) is None:
        raise FileNotFoundError("Valid executable {} not found".format(executable))


def require_files(*paths: Path):
    """raise when any of the files is missing"""
    for path in paths:
        if not pathlib.Path(path).is_file():
            raise FileNotFoundError("Missing required file {}".format(path))


def largest_div_below_sqrt(num: int) -> int:
    """get the largest divider of integer ``num`` not above its square root"""
    for i in range(math.isqrt(num), 0, -1):
        if num % i == 0:
            return i
    raise ValueError("expect a positive integer, got {}".format(num))


def run_command(command: Union[str, List[str]], output: Path, cwd: Path = "."):
    """run a command and redirect both stdout and stderr to a file

    Args:
        command (str or list) : the command to run
        output (Path) : the path of output file, relative to ``cwd``
        cwd (Path) : the working directory

    Raises:
        subprocess.CalledProcessError : when the command fails
    """
    if isinstance(command, str):
        command = shlex.split(command)
    _logger.info("running %r in %s", command, cwd)
    with (pathlib.Path(cwd) / output).open("w") as h:
        sp.run(command, cwd=cwd, stdout=h, stderr=sp.STDOUT, check=True)
