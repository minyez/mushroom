# -*- coding: utf-8 -*-
"""workflow objects for FHI-aims"""
import pathlib
from typing import List, Union

from mushroom.aims.analyse import get_atoms_from_geometry
from mushroom.aims.species import readlines_species_defaults
from mushroom.aims.stdout import StdOut
from mushroom.core.typehint import Path
from mushroom.workflow import run_command, with_hard_stack_limit

__all__ = [
    "AimsWorkdir",
    "get_species_text",
    "link_files",
    "run_aims",
]


class AimsWorkdir:
    """Class to handle a FHI-aims calculation working folder"""

    def __init__(self, dirpath: str, aimsout: str = "aims.out", aimserr: str = None):
        dirpath = pathlib.Path(dirpath).absolute()
        self.dirpath = dirpath
        self.path_control = dirpath / "control.in"
        self.path_geometry = dirpath / "geometry.in"
        self.path_aimsout = dirpath / aimsout
        self.path_aimserr = None
        if aimserr is not None:
            self.path_aimserr = dirpath / aimserr

        self.band_output_glob = "band[0-9][0-9][0-9][0-9].out"

        self.efermi = None
        self.nspin = None
        self.nelect = None

        # Objects to handle inputs and outputs
        self._control = None
        self._geometry = None
        self._aimsout = None

    def load_output(self):
        self._aimsout = StdOut(self.path_aimsout, lazy_load=False)

    def is_finished(self):
        return self._aimsout.is_finished(False)

    def is_converged(self):
        return self._aimsout.is_finished(True)


def get_species_text(path_geometry: Path, directory: str, species_defaults: str = None) -> str:
    """get the species defaults of all elements in a geometry file

    The blocks are copied without change, to keep the comments and commented basis tiers.

    Args:
        path_geometry (Path) : path of geometry.in
        directory (str) : directory of species category or its alias,
            e.g. "defaults_2020/intermediate_gw"
        species_defaults (str) : path of species_defaults. Default to use the configuration

    Returns:
        str, with blocks in the alphabetic order of elements
    """
    elements = sorted(set(get_atoms_from_geometry(str(path_geometry))))
    return readlines_species_defaults(directory, *elements, species_defaults=species_defaults)


def link_files(source: Path, target: Path, pattern: str) -> List[pathlib.Path]:
    """link files from a directory to another one, e.g. restart files

    Args:
        source (Path) : directory of the files
        target (Path) : directory of the links
        pattern (str) : glob pattern of file names

    Returns:
        list of the links

    Raises:
        FileNotFoundError : when no file matches
    """
    source, target = pathlib.Path(source).resolve(), pathlib.Path(target)
    paths = sorted(source.glob(pattern))
    if not paths:
        raise FileNotFoundError("No {} in {}".format(pattern, source))
    links = []
    for path in paths:
        link = target / path.name
        link.unlink(missing_ok=True)
        link.symlink_to(path)
        links.append(link)
    return links


def run_aims(command: Union[str, List[str]], cwd: Path = ".", output: str = "aims.out",
             error: str = "aims.err", require_converge: bool = True):
    """run FHI-aims and check that it ends normally

    The stack limit is raised to the hard limit, since FHI-aims needs a large stack.
    FHI-aims reports the value in its output.

    Args:
        command (str or list) : the FHI-aims command, e.g. "mpirun -np 4 aims.x"
        cwd (Path) : the working directory
        output (str) : file of standard output, relative to ``cwd``
        error (str) : file of standard error, relative to ``cwd``
        require_converge (bool) : also require a converged SCF cycle.
            Switch it off for runs without SCF, e.g. with ``sc_iter_limit 0``

    Raises:
        RuntimeError : when FHI-aims does not end normally
    """
    run_command(with_hard_stack_limit(command), output, cwd=cwd, error=error)
    path = pathlib.Path(cwd) / output
    if not StdOut(path, lazy_load=True).is_finished(require_converge):
        raise RuntimeError("FHI-aims does not end normally, check {}".format(path))
