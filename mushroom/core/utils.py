# -*- coding: utf-8 -*-
"""some general utilities that I do not know where to put"""
from datetime import datetime


def get_current_timestamp(with_weekday: bool = False, datetime_str: str = None):
    """return the current timestamp

    Args:
        with_weekday (bool): If True, the format 'YYYY-MM-DD WKD HH:MM:SS'.
            Otherwise it is 'YYYY-MM-DD HH:MM:SS'.
        datetime_str (str): If not None, it will be used as the stamp instead of current time.
            Only recoginize a few formats.
    """
    # Get current date and time by guessing the format
    if datetime_str is not None:
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %a",
            "%Y-%m-%d %H",
            "%Y-%m-%d %a %H",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %a %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %a %H:%M:%S",
            "%d %b %Y %H:%M",
            "%B %d, %Y, %I %p",
            "%Y-%m-%dT%H:%M:%S",
            "%Y%m%dT%H%M%S",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(datetime_str, fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError("cannot recognize input datetime format")
    else:
        dt = datetime.now()

    # Format as string
    if with_weekday:
        timestamp = dt.strftime("%Y-%m-%d %a %H:%M:%S")
    else:
        timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
    return timestamp


def raise_no_module(mod, modname: str, msg: str = None):
    """
    Raise when a module is not found (set to None) when it is required
    """
    if mod is None:
        if msg is None:
            raise ModuleNotFoundError("require {}".format(modname))
        raise ModuleNotFoundError("require {}: {}".format(modname, msg))
