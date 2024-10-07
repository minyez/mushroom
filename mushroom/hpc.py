# -*- coding: utf-8 -*-
"""functions related to operations on high-performance computing platform

Register your platforms in the .mushroomrc file, in the form

    {uid}@{host}

where `uid` is the output of `whoami`, and `host` the output of `uname -n`
"""
import pathlib
import subprocess as sp
from re import split as rsplit
from typing import Union, Iterable
from os import PathLike
from io import StringIO
from mushroom.core.ioutils import open_textio
from mushroom.core.env import username, hostname
from mushroom.core.logger import loggers

_logger = loggers["hpc"]

__all__ = ["SbatchOptions", "get_scheduler_header", "add_scheduler_header"]
try:
    from mushroom.__config__ import uname_platforms
except ImportError:
    uname_platforms = {}

# obtain the effective uid and hostname
_user_at_host = "{}@{}".format(username, hostname)
current_platform, current_use_pbs = uname_platforms.get(_user_at_host, (None, False))
_logger.debug("current user@host: %s", _user_at_host)
del _user_at_host


class SbatchOptions:
    """Object to handle sbatch options in command line tool or script

    Args:
        template: file to load as an template.

    Other keyword arguments are treated as sbatch options, and will
    overwrite those in the template
    """

    options = ["--account",
               "-c", "--cpus-per-task", "-x", "--exclude",
               "-J", "--job-name", "-N", "--nodes", "-n", "--ntasks",
               "--ntasks-per-node", "--ntasks-per-core",
               "--time", "-o", "--output", "-e", "--error",
               "--mem", "--mem-per-cpu",
               "-D", "--exclusive",
               "-p", "--partition", "--qos", "--mail-type", "--mail-user",
               "-F", "--nodefile", "-w", "--nodelist"]
    # protect for error input of options
    options = [x.strip("=") for x in options]

    keywords = {}
    for x in options:
        keywords[x.strip("-").replace("-", "_")] = x

    def __init__(self, template=None, **kwargs):
        self._keywords_values = {}
        if template is not None:
            with open_textio(template, 'r') as h:
                slines = [
                    x[8:].strip() for x in h.readlines() if x.strip().startswith("#SBATCH ")
                ]
            template_kwargs = {}
            for l in slines:
                try:
                    k, v = rsplit(r"[ =]", l, maxsplit=1)
                except ValueError:
                    k = rsplit(r"[ =]", l, maxsplit=1)[0]
                    v = True
                template_kwargs[k.strip("-").replace("-", "_")] = v
            self.set(**template_kwargs)
        self.set(**kwargs)

    def set(self, **kwargs):
        """set arguments"""
        for k, v in kwargs.items():
            if k in self.keywords.keys():
                self._keywords_values[k] = v
            else:
                _logger.warning("unknown sbatch keyword %s", k)

    def export_script(self):
        """export into bash script options

        Returns:
            list of str
        """
        return ["#SBATCH " + x for x in self.export_command()]

    def export_command(self):
        """export into options for command line"""
        slist = []
        for k, v in self._keywords_values.items():
            if v is True:
                slist.append("{}".format(self.keywords[k]))
            elif v is not None:
                slist.append("{} {}".format(self.keywords[k], v))
        return slist


class SbatchScript:
    """object to set and write a sbatch script

    Args:
        commands (str or iterable of str): command to run
        commands_template: file including commands to write

    One cannot use both parameters at the same time.
    In this case, commands will be loaded and template is ignored.
    Other keywords argument will be treated as sbatch option and
    handled by the ``SbatchOptions`` class
    """

    def __init__(self,
                 commands: Union[str, Iterable[str]] = None,
                 sheban: str = "#!/usr/bin/env bash",
                 template: str = None,
                 commands_template: Union[str, PathLike, StringIO] = None,
                 sbatch_options_template: Union[str, PathLike, StringIO] = None,
                 **kwargs):
        if template is not None and commands_template is None:
            commands_template = template
        if template is not None and sbatch_options_template is None:
            sbatch_options_template = template
        self._sbatch_options = SbatchOptions(template=sbatch_options_template, **kwargs)
        self._commands = None
        self._sheban = sheban
        if commands is not None:
            if isinstance(commands, (list, tuple, set)):
                self._commands = "\n".join(commands)
            else:
                self._commands = commands
        elif commands_template is not None:
            with open_textio(commands_template, 'r') as h:
                # prune sheban and sbatch directives
                self._commands = "".join([
                    x for x in h.readlines()
                    if not x.startswith("#!") and not x.startswith("#SBATCH")
                ])

    @property
    def commands(self):
        return self._commands

    @commands.setter
    def commands(self, commands):
        self._commands = commands

    def set_sbatch(self, **kwargs):
        self._sbatch_options.set(**kwargs)

    def __str__(self):
        slist = []
        slist.append(self._sheban)
        slist.extend(self._sbatch_options.export_script())
        if self._commands is not None:
            slist.append(self._commands)
        return "\n".join(slist)

    def write(self, fn="run.sh"):
        if self._commands is None:
            _logger.warning("You are writing no commands to sbatch script!")
        with open(fn, 'w') as h:
            print(str(self), file=h)


def get_scheduler_header(platform: str, use_pbs: bool = False) -> str:
    """get platform-specific sbatch/pbs header lines.

    Args:
        platform (str) : identifier of platform. should be found in sbatch_headers or pbs_headers
        use_pbs (bool)

    Return:
        str
    """
    try:
        from mushroom.__config__ import sbatch_headers
    except ImportError:
        sbatch_headers = {}
    try:
        from mushroom.__config__ import pbs_headers
    except ImportError:
        pbs_headers = {}
    avail_platforms = sbatch_headers
    if use_pbs:
        avail_platforms = pbs_headers
    prefix = {True: "PBS"}.get(use_pbs, "SBATCH")
    head = avail_platforms.get(platform, None)
    if head is None:
        raise ValueError("{} headers are not set for platform {}".format(prefix, platform))
    _logger.debug("found %s headers for platform %s ", prefix, platform)
    return "".join("#{} {}\n".format(prefix, l) for l in head)


def add_scheduler_header(pscript: Union[str, PathLike],
                         platform: str, use_pbs: bool = False):
    """add platform scheduler header to script.

    The header is added after the first line, which is usually the sheban
    """
    if platform is None:
        return
    head = get_scheduler_header(platform, use_pbs)
    pscript = pathlib.Path(pscript)
    with open(pscript, "r") as h:
        lines = h.readlines()
    # avoid duplicate insertion by checking the second line of script
    prefix = "#SBATCH"
    if use_pbs:
        prefix = "#PBS"
    if len(lines) > 1:
        if not lines[1].startswith(prefix):
            lines[0] += head
            with pscript.open("w") as h:
                print(*lines, sep="", file=h)


def is_slurm_enabled() -> bool:
    """check if slurm is enabled and configured on the platform.

    This is achieved by calling sacct and reading its returncode"""
    import subprocess as sp
    try:
        p = sp.Popen(["sacct", "-h"], stderr=sp.PIPE, stdout=sp.PIPE)
        ret = p.wait()
        if ret == 0:
            return True
    except FileNotFoundError:
        # sacct not found
        pass
    return False


def sbatch_submit(script_name: str) -> int:
    """submit a script by sbatch and get the return code

    sbatch is assumed available.

    Args:
        script_name (str): the path of script file to submit

    Return
        return code, jobid
    """
    retcode = None
    p = sp.Popen(["sbatch", script_name], stdout=sp.PIPE, stderr=sp.PIPE)
    out, _ = p.communicate()
    out = str(out, encoding='utf-8')
    ret = p.returncode
    if ret == 0:
        out = int(out.split()[-1])
    return ret, out
