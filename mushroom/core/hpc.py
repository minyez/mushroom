# -*- coding: utf-8 -*-
"""functions related to operations on high-performance computing platform

Register your platforms in the .mushroomrc file, in the form

    {uid}@{host}

where `uid` is the output of `whoami`, and `host` the output of `uname -n`
"""
import pathlib
from typing import Union
from os import geteuid, PathLike
from pwd import getpwuid
from socket import gethostname
from mushroom.core.logger import create_logger
_logger = create_logger("hpc")
del create_logger

__all__ = ["get_scheduler_header", "add_scheduler_header"]
try:
    from mushroom.__config__ import uname_platforms
except ImportError:
    uname_platforms = {}

# obtain the effective uid and hostname
_user = getpwuid(geteuid()).pw_name
_host = gethostname()
_user_at_host = "{}@{}".format(_user, _host)
del _user, _host, geteuid, getpwuid, gethostname
current_platform, current_use_pbs = uname_platforms.get(_user_at_host, (None, False))
_logger.debug("current user@host: %s", _user_at_host)
del _user_at_host

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
    avail_platforms = {True: pbs_headers}.get(use_pbs, sbatch_headers)
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
    prefix = {True: "#PBS"}.get(use_pbs, "#SBATCH")
    if len(lines) > 1:
        if not lines[1].startswith(prefix):
            lines[0] += head
            with pscript.open("w") as h:
                print(*lines, sep="", file=h)

