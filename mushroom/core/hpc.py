# -*- coding: utf-8 -*-
"""functions related to operations on high-performance computing platform

Register your platforms in the .mushroomrc file, in the form

    {uid}@{host}

where `uid` is the output of `whoami`, and `host` the output of `uname -n`
"""
from os import geteuid
from pwd import getpwuid
from socket import gethostname
from mushroom.core.logger import create_logger
_logger = create_logger("hpc")
del create_logger

__all__ = ["get_scheduler_head",]
try:
    from mushroom.__config__ import sbatch_headers
except ImportError:
    sbatch_headers = {}
try:
    from mushroom.__config__ import pbs_headers
except ImportError:
    pbs_headers = {}
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
del _user_at_host

def get_scheduler_head(platform: str, use_pbs: bool = False) -> str:
    """get platform-specific sbatch/pbs head string to workflow script"""
    avail_platforms = {True: pbs_headers}.get(use_pbs, sbatch_headers)
    prefix = {True: "PBS"}.get(use_pbs, "SBATCH")
    head = avail_platforms.get(platform)
    if head is None:
        raise ValueError("{} headers are not set for platform {}".format(prefix, platform))
    _logger.debug("platform %s registered", platform)
    return f"#{prefix} " + f"\n#{prefix} ".join(head) + "\n"

