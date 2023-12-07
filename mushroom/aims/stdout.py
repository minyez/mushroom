# -*- coding: utf-8 -*-
"""utilities for parsing standard output of FHI-aims"""
import re
from io import StringIO

from mushroom.core.bs import BandStructure
from mushroom.core.typehint import Path
from mushroom.core.ioutils import conv_string
from mushroom.core.logger import loggers


_logger = loggers["aims"]


class AimsNotFinishedError(Exception):
    """Exception for aims calculation is not finished"""
    pass


def split_aimsout_region(lines):
    """split the aimsout region for processing"""


class StdOut:
    """a general-purpose object to handle aims standard output

    Currently only support handling SCF and post-SCF.

    Args:
        pstdout (Path): path to the aims standard output file
    """

    aims_version = "230214-9c10ff0ac"

    def __init__(self, pstdout: Path, lazy_load: bool = False):
        self._path = pstdout

        with open(pstdout, 'r', encoding='utf-8') as h:
            lines = h.readlines()
        _logger.info("Reading standard output from: %s", pstdout)
        self._not_converged = lines[-2].strip() == '*** scf_solver: SCF cycle not converged.'
        self._finished = self._not_converged or lines[-2].strip() == 'Have a nice day.'

        self._aims_version = None

        self._finished_system = False
        self._finished_control = False
        self._finished_geometry = False
        self._finished_prep = False
        self._finished_pbc_lists_init = False
        self._finished_scf_init = False

        self._system_lines = None
        self._control_lines = None
        self._geometry_lines = None
        self._prep_lines = None
        self._pbc_lists_init_lines = None
        self._scf_init_lines = None
        self._scf_lines = None
        self._postscf_lines = None
        self._timestat_lines = None

        self._ntasks = None
        self._nnodes = None
        self._node_names = None
        self._node_names_unique = None
        self._omp_threads = None
        self._control = None
        self._geometry = None
        self._timestat = None

        self._n_cells = None
        self._n_cells_pm = None
        self._n_cells_H = None
        self._n_matrix_size_H = None

        # real space integration information
        self._n_full_points = None
        self._n_full_points_nz = None

        self._nspins = None
        self._nkpts = None
        self._nbands = None
        self._nbasis_H = None
        self._nelect = None
        self._nbasis_uc = None
        self._nbasis = None
        self._nrad = None

        # scf
        self._nscf_ite = None

        # postscf stuff
        self._nbasbas = None
        self._gw_kgrid_result = None
        self._gw_kgrid_kpts = None

        # determine the version before dividing regions
        for l in lines:
            if l.startswith("  FHI-aims version") or l.startswith("          Version "):
                self._aims_version = l.split()[-1]
                break
        if self._aims_version is None:
            raise ValueError("cannot extract aims version, incomplete calculation")

        self._divide_output_lines(lines)
        if not lazy_load:
            self._handle()

    def _divide_output_lines(self, lines):
        """coarsely devide the lines into sections"""
        for i, l in enumerate(lines):
            if l.startswith("  Obtaining array dimensions for all initial allocations:"):
                self._finished_system = True
                self._system_lines = lines[:i]
            if l.startswith("  Parsing control.in "):
                self._control_lines = lines[i:]
            if l.startswith("  Completed first pass over input file control.in"):
                self._finished_control = True
                self._control_lines = self._control_lines[:self._control_lines.index(l)]
            if l.startswith("  Parsing geometry.in (first pass over file, find array dimensions only)."):
                self._geometry_lines = lines[i:]
            if l.startswith("  Completed first pass over input file geometry.in"):
                self._finished_geometry = True
                self._geometry_lines = self._geometry_lines[:self._geometry_lines.index(l)]
                self._prep_lines = lines[i:]
            if l.startswith("  Preparations completed."):
                self._finished_prep = True
                self._prep_lines = self._prep_lines[:self._prep_lines.index(l)]
            if l.startswith("  Initializing index lists of integration centers"):
                self._pbc_lists_init_lines = lines[i:]
            if l.startswith("          Begin self-consistency loop: Initialization."):
                self._finished_pbc_lists_init = True
                if self._pbc_lists_init_lines is not None:
                    self._pbc_lists_init_lines = self._pbc_lists_init_lines[:self._pbc_lists_init_lines.index(l)]
                self._scf_init_lines = lines[i:]
            if l.startswith("          Begin self-consistency iteration #    1"):
                self._finished_scf_init = True
                self._scf_init_lines = self._scf_init_lines[:self._scf_init_lines.index(l)]
                self._scf_lines = lines[i:]
            # if l.startswith("  Post-SCF correlation calculation starts"):
            if l.startswith("  End decomposition of the XC Energy"):
                self._scf_lines = self._scf_lines[:self._scf_lines.index(l) + 1]
                self._postscf_lines = lines[i:]
            if l.startswith("          Leaving FHI-aims.") and not self._not_converged:
                # in case that SCF is not converged, it will leave aims without starting postscf
                if self._postscf_lines is not None:
                    self._postscf_lines = self._postscf_lines[:self._postscf_lines.index(l)]
            if l.startswith("          Detailed time accounting"):
                self._timestat_lines = lines[i + 1:]
            if l.startswith("          Partial memory accounting:"):
                self._timestat_lines = self._timestat_lines[:self._timestat_lines.index(l)]

    def _handle(self):
        """handle the data processing"""
        self._handle_system()
        self._handle_prep()
        self._handle_pbc_lists_init()
        self._handle_scf_init()
        self._handle_scf()
        self._handle_postscf()
        self._handle_timing_statistics()

    def _handle_system(self):
        """process the system environment information"""
        if not self._finished_system:
            _logger.warning("System info is not complete, some data might be missing")
        taskl_pat = re.compile(r"^  Task\s*(\d+) on host (.*) reporting.")
        for i, l in enumerate(self._system_lines):
            if l.startswith("  Task"):
                m = taskl_pat.match(l)
                if m is not None:
                    if self._node_names is None:
                        self._node_names = []
                    self._node_names.append(m.group(2).strip())
                continue
            if l.startswith("  *** Environment variable OMP_NUM_THREADS"):
                try:
                    self._omp_threads = int(self._system_lines[i + 1].strip())
                # when unset
                except (IndexError, ValueError):
                    pass
                continue
            if l.startswith("  | Environment variable OMP_NUM_THREADS correctly set to"):
                self._omp_threads = int(l[:-2].split()[-1])

        if self._node_names is not None:
            self._node_names_unique = set(self._node_names)
            self._ntasks = len(self._node_names)
            self._nnodes = len(self._node_names_unique)

    def get_nnodes(self):
        """get number of nodes used"""
        return self._nnodes

    def get_ntasks(self):
        """get number of tasks used"""
        return self._ntasks

    def get_node_names(self):
        """get names of nodes for each task"""
        return self._node_names

    def get_omp_threads(self):
        """get the omp threads used in the run"""
        return self._omp_threads

    def _handle_prep(self):
        """process the information in the header part, i.e. data before the self-consistency loop"""
        # the control information
        if not self._finished_prep:
            _logger.warning("preparation is not finished, skip")
            return
        for i, l in enumerate(self._prep_lines):
            if l.startswith("  | Number of spin channels           :"):
                self._nspins = int(l.split()[-1])
            if l.startswith("  | Total number of radial functions:"):
                self._nrad = int(l.split()[-1])
            if l.startswith("  | Total number of basis functions :"):
                self._nbasis = int(l.split()[-1])
            if l.startswith("  | Number of Kohn-Sham states (occupied + empty)"):
                self._nbands = int(l.split()[-1])
            if l.startswith("*** Environment variable OMP_NUM_THREADS is set to"):
                try:
                    self._omp_threads = int(self._prep_lines[i + 1].strip())
                except (IndexError, ValueError):
                    pass
            if l.startswith("  | Environment variable OMP_NUM_THREADS correctly set to"):
                self._omp_threads = int(l[:-2].split()[-1])

    def _handle_pbc_lists_init(self):
        """process the data in initializing pbc list by the subroutine initialize_bc_dependent_lists"""
        if not self._finished_pbc_lists_init:
            _logger.warning("PBC lists initialization is not finished")
        if self._pbc_lists_init_lines is None:
            return
        for i, l in enumerate(self._pbc_lists_init_lines):
            # if l.startswith("  Initializing the k-points"):
            #     try:
            #         self._nkpts = int(self._pbc_lists_init_lines[i + 1].split()[-1])
            #     except (IndexError, ValueError):
            #         pass
            if l.startswith("  | Number of k-points"):
                self._nkpts = conv_string(l, int, -1)
            if l.startswith("  | Number of basis functions in the Hamiltonian integrals"):
                self._nbasis_H = conv_string(l, int, -1)
            if l.startswith("  | Number of basis functions in a single unit cell"):
                self._nbasis_uc = conv_string(l, int, -1)
            if l.startswith("  | Number of super-cells (origin)"):
                self._n_cells = conv_string(l, int, -1)
            if l.startswith("  | Number of super-cells (after PM_index)"):
                self._n_cells_pm = conv_string(l, int, -1)
            if l.startswith("  | Number of super-cells in hamiltonian"):
                self._n_cells_H = conv_string(l, int, -1)
            if l.startswith("  | Size of matrix packed + index"):
                self._n_matrix_size_H = conv_string(l, int, -1)
        # For molecular systems, there is no k-point session
        # Set to 1 for consistent handling of solids and molecules
        if self._nkpts is None:
            self._nkpts = 1

    def _handle_scf_init(self):
        """process the data in the self-consistency loop initialization"""
        if not self._finished_scf_init:
            _logger.warning("self-consistent loop initialization is not finished")
        if self._scf_init_lines is None:
            return
        for i, l in enumerate(self._scf_init_lines):
            if l.startswith("  | Initial density: Formal number of electrons"):
                self._nelect = float(l.split()[-1])
            if l.startswith("  | Net number of integration points"):
                self._n_full_points = int(l.split()[-1])
            if l.startswith("  | of which are non-zero points"):
                self._n_full_points_nz = int(l.split()[-1])

    def _handle_postscf(self):
        if not self._finished:
            _logger.warning("Calculation is not finished, postscf processing could fail")
        if self._postscf_lines is None:
            return
        for i, l in enumerate(self._postscf_lines):
            if l.startswith("  | Shrink_full_auxil_basis : there are totally"):
                self._nbasbas = int(l.split()[-5])

    def _handle_timing_statistics(self):
        """process the timing statistics at the end of calculation"""
        if not self._finished:
            _logger.warning("Calculation is not finished, stop processing timing statistics")
            return
        if self._timestat_lines is None:
            return
        # tline = re.compile(r'^\s+\|(.*):' + r'\s*(?[\d\.]+\s+s)?' * 2 + r'\\n$')
        # tline = re.compile(r'^\s+\|(.*):' + r'\s*([\d\.]+)\s+s' * 2 + r'\\n$')
        tline = re.compile(r"\s+\|\s*(\S.*\S)\s*:" + r"\s*\(?\s*([\d\.]+)\s+s\)?" * 2 + r"\n$")
        timestat = {}
        self._timestat = {}
        for l in self._timestat_lines:
            m = tline.match(l)
            if m is not None:
                timestat[m.group(1)] = (float(m.group(2)), float(m.group(3)))
        # print(timestat)
        # name a subset of recorded timing
        items = (("Total time", "total"),
                 ("Initialization for periodic correlated calc", "post_scf_pbc_init"),
                 ("The exact-exchange part of GW calc.", "exx_xc_k"),
                 ("Total time for polarizability calc.", "polar"),
                 ("Total time for polarizability of k space", "polar_k"),
                 ("Total time for GW self-energy (regular k) c", "gwse_k"),
                 ("Total time for GW band self-energy calc.", "gwse_b"),
                 ("Total time for EXX&XC calc. for GW band", "exx_xc_b")
                 )
        for item, key in items:
            try:
                self._timestat[key] = timestat.pop(item)
            except KeyError:
                pass

    def is_finished(self):
        """check if the calculation is finished successfully"""
        return self._finished

    @property
    def nelect(self):
        """the integer number of electrons"""
        from numpy import rint
        return int(rint(self._nelect))

    def _handle_scf(self):
        """process the data in the self-consistency iterations"""
        for i, l in enumerate(self._scf_lines):
            if l.startswith("  End self-consistency iteration #    "):
                self._nscf_ite = conv_string(l, int, 4)

    def get_control(self):
        """return a Control object"""
        from mushroom.aims.input import Control
        if self._control is None:
            if not self._finished_control:
                raise ValueError("control.in in the output is not complete")
            # the content of control.in are between two banner lines
            banner_locs = []
            for i, l in enumerate(self._control_lines):
                if l.startswith("  -------------------------"):
                    banner_locs.append(i)
            if len(banner_locs) != 2:
                raise ValueError("Internal error: should be exactly 2 banner lines in control session")
            self._control = Control.read(
                StringIO("".join(self._control_lines[banner_locs[0] + 1:
                                                     banner_locs[1]])))
        return self._control

    def get_geometry(self):
        """return a Cell object representing the geometry"""
        raise NotImplementedError

    def get_n_spin_kpt_band_basis(self):
        """get the most requested dimensions of the system

        Return:
            4 int, number of spins, kpoints, bands/states and basis functions"""
        return self._nspins, self._nkpts, self._nbands, self._nbasis

    def get_QP_result(self):
        """get the aims QP result from the standard output

        The dict includes 6 items, with their key corresponding to each data column
        in the output file:
        - ``occ`` : occupation number (occ_num),
        - ``eps`` : starting-point eigenvalues (e_gs)
        - ``exx`` : exact exchange contribution (e_x^ex),
        - ``vxc`` : xc contribution to starting-point (e_xc^gs)
        - ``sigc``: non-local correlation from self-energy (e_c^nloc)
        - ``eqp`` : QP energy (e_qp).

        Note the names of keys differ from the column names, since they are adapted
        according to their meaning so that the keys are consistent across different
        programs. The value is a (nspins, nkpoints, nbands) array.

        Returns:
            a dict
        """
        import numpy as np

        errmsg = "QP calculations is not {} from the standard output"
        if self._gw_kgrid_result is not None and self._gw_kgrid_kpts is not None:
            return self._gw_kgrid_result, self._gw_kgrid_kpts

        if self._postscf_lines is None:
            raise ValueError(errmsg.format("found"))
        st = None
        ed = None
        # looking for the header of the GW result part
        for i, l in enumerate(self._postscf_lines):
            if l.strip().startswith("GW quasi-particle energy levels"):
                st = i
            if l.strip().startswith("DFT/Hartree-Fock") \
                    or l.strip().startswith("Valence band maximum (VBM) from the GW") \
                    or l.strip().startswith("Spin-up valence band maximum"):
                ed = i
        if st is None or ed is None:
            raise ValueError(errmsg.format('finished'))
        eqpline = re.compile(r'^\s*(\d+)' + r'\s+(-?[\d\.]+)' * 6 + r'(\\n)?$')
        # search the data
        array = []
        istates = []
        for l in self._postscf_lines[st:ed]:
            m = eqpline.match(l)
            if m:
                istates.append(int(m.group(1)))
                array.append([*map(float, (m.group(i) for i in range(2, 8)))])
        array = np.array(array)
        kpts = []
        kptline = re.compile(r'^  K_point\s+(\d+)\s+:' + r'\s+(-?[\d\.]+)' * 3 + r'(\\n)?$')
        for l in self._postscf_lines[st:ed]:
            m = kptline.match(l)
            if m:
                kpts.append([*map(float, (m.group(i) for i in range(2, 5)))])
        # molecule cases
        if len(kpts) == 0:
            kpts = [[0, 0, 0]]
        kpts = np.array(kpts)
        # reshape all arrays. Generally, the first state is a fully occupied core state
        # thus the number of spins can be decided from its occupation number
        # this is usually not used, as the channel should be printed at the preparation stage
        if self._nspins is None:
            nspins = 1
            if array[0, 0] == 1:
                nspins = 2
            self._nspins = nspins
        # the number of kpoints to print, not necessary that used in SCF
        nkpts = istates.count(istates[0]) // self._nspins
        assert (nkpts == len(kpts))

        # TODO: verify that kmesh goes faster than spin
        #       otherwise one may swap the first two axis
        keys = ["occ", "eps", "exx", "vxc", "sigc", "eqp"]
        d = {}
        for i, k in enumerate(keys):
            d[k] = array[:, i].reshape(self._nspins, nkpts, -1, order="C")
        # store the data
        self._gw_kgrid_result = d
        self._gw_kgrid_kpts = kpts

        return self._gw_kgrid_result, self._gw_kgrid_kpts

    def get_QP_sigc(self):
        """get the correlation self-energy to Koh-Sham state"""
        d, _ = self.get_QP_result()
        return d["sigc"]

    def get_QP_sigx(self):
        """get the exchange self-energy correction (i.e. exact-exchange) to Koh-Sham state"""
        d, _ = self.get_QP_result()
        return d["exx"]

    get_exx = get_QP_sigx

    def get_QP_bandstructure(self, kind="eqp"):
        """get the QP band structure

        Args:
            kind (str): the key of QP energies, default to "eqp".
                using "eps" can be viewed as a helper function to get the KS band structure

        Returns
            BandStructure object
        """
        d, kpts = self.get_QP_result()
        if kind not in ["eqp", "eps"]:
            raise ValueError("Use eqp/eps for QP/KS band structure")
        # TODO: which case does the occupation number refer to when
        #       there is a band reordering?
        return BandStructure(d[kind], d["occ"], unit='ev'), kpts

    def get_cpu_time(self):
        """get CPU time accounting (in seconds)"""
        if self._timestat is None:
            raise AimsNotFinishedError
        return {k: v[0] for k, v in self._timestat.items()}

    def get_wall_time(self):
        """get wall time accounting (in seconds)"""
        if self._timestat is None:
            raise AimsNotFinishedError
        return {k: v[1] for k, v in self._timestat.items()}

    def get_wall_time_total(self):
        """get total wall time (in seconds)"""
        if self._timestat is None:
            raise AimsNotFinishedError
        return self._timestat['total'][1]

