# -*- coding: utf-8 -*-
"""functions related to operations on high-performance computing platform
"""
try:
    from mushroom.__config__ import sbatch_headers
except ImportError:
    sbatch_headers = {}
try:
    from mushroom.__config__ import pbs_headers
except ImportError:
    pbs_headers = {}

def get_scheduler_head(platform: str, use_pbs: bool = False) -> str:
    """get platform-specific sbatch/pbs head string to workflow script"""
    avail_platforms = {True: pbs_headers}.get(use_pbs, sbatch_headers)
    prefix = {True: "PBS"}.get(use_pbs, "SBATCH")
    try:
        head = avail_platforms.get(platform)
        return f"#{prefix} " + f"\n#{prefix} ".join(head) + "\n"
    except KeyError:
        raise ValueError("{} headers are not set for platform {}".format(prefix, platform))

