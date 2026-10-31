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
import tarfile
import tempfile
from contextlib import contextmanager
from typing import Iterable, List, Tuple, Union

from mushroom.core.logger import loggers
from mushroom.core.typehint import Path

_logger = loggers["workflow"]

__all__ = [
    "get_ntasks",
    "require_executable",
    "require_files",
    "largest_div_below_sqrt",
    "get_npar_kpar",
    "with_hard_stack_limit",
    "run_command",
    "open_example",
    "diff_files",
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


def get_npar_kpar(ntasks: int) -> Tuple[int, int]:
    """get the band and k-point parallel groups from the number of tasks"""
    kpar = largest_div_below_sqrt(ntasks)
    return ntasks // kpar, kpar


def with_hard_stack_limit(command: Union[str, List[str]]) -> List[str]:
    """wrap a command to run it with the stack limit raised to the hard limit

    The limit is set in a new shell, not in Python. macOS can refuse to raise the
    limit of a running Python, while a new process can do it. The hard limit is
    about 64 MB on macOS, and other systems can have no limit.

    Args:
        command (str or list) : the command to run

    Returns:
        list, the wrapped command
    """
    if isinstance(command, str):
        command = shlex.split(command)
    return ["bash", "-c", 'ulimit -s hard && exec "$@"', "--", *command]


def run_command(command: Union[str, List[str]], output: Path, cwd: Path = ".",
                stdin: str = None, error: Path = None):
    """run a command and redirect its stdout and stderr to files

    Args:
        command (str or list) : the command to run
        output (Path) : the path of output file, relative to ``cwd``
        cwd (Path) : the working directory
        stdin (str) : the text to send to standard input
        error (Path) : the path of file for stderr, relative to ``cwd``.
            Default to write stderr to ``output``

    Raises:
        subprocess.CalledProcessError : when the command fails
    """
    if isinstance(command, str):
        command = shlex.split(command)
    _logger.info("running %r in %s", command, cwd)
    with (pathlib.Path(cwd) / output).open("w") as h:
        if error is None:
            sp.run(command, cwd=cwd, input=stdin, text=True, stdout=h, stderr=sp.STDOUT, check=True)
        else:
            with (pathlib.Path(cwd) / error).open("w") as h_err:
                sp.run(command, cwd=cwd, input=stdin, text=True, stdout=h, stderr=h_err,
                       check=True)


@contextmanager
def open_example(tarball: Path):
    """extract the example of a workflow and yield the path to the top directory ``example``"""
    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(tarball) as h:
            h.extractall(tmpdir, filter="data")
        yield pathlib.Path(tmpdir) / "example"


def diff_files(dir1: Path, dir2: Path, names: Iterable[str]) -> List[str]:
    """get the names of text files that are different in two directories"""
    dir1, dir2 = pathlib.Path(dir1), pathlib.Path(dir2)
    return [name for name in names if (dir1 / name).read_text() != (dir2 / name).read_text()]
