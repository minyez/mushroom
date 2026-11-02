# -*- coding: utf-8 -*-
"""Logging facilities for mushroom"""
import os
import logging
import warnings

from mushroom import __config__
from typing import Optional


def _get_config(name, default):
    return getattr(__config__, name, default)


def get_logging_level(ll):
    """resolve a logging level, warning and returning NOTSET for invalid values"""
    value = logging.getLevelName(ll.upper()) if isinstance(ll, str) else ll
    if isinstance(value, int):
        return value
    warnings.warn(f"invalid logging level {ll!r}; using NOTSET", stacklevel=2)
    return logging.NOTSET


log_level = get_logging_level(os.environ.get("MUSHROOM_LOG", _get_config("log_level", "notset")))
stream_level = get_logging_level(os.environ.get("MUSHROOM_STREAM", _get_config("stream_level", "notset")))


def _set_handler(flevel, slevel):
    """set the mode and log level of handler and stream logger

    Args:
        flevel (int): threshold for the file handler
        slevel (int): threshold for the stream handler
    """
    logfile_mode = _get_config('logfile_mode', 'w')
    file_hand = None
    stream_hand = None
    fform = logging.Formatter(fmt='%(asctime)s - %(name)10s:%(levelname)8s - %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')
    sform = logging.Formatter(fmt='%(name)10s:%(levelname)8s - %(message)s')
    if flevel != logging.NOTSET:
        file_hand = logging.FileHandler("mushroom.log", mode=logfile_mode, delay=True)
        file_hand.setFormatter(fform)
        file_hand.setLevel(flevel)
    if slevel != logging.NOTSET:
        stream_hand = logging.StreamHandler()
        stream_hand.setFormatter(sform)
        stream_hand.setLevel(slevel)

    return file_hand, stream_hand


# global handler
_fhand, _shand = _set_handler(log_level, stream_level)


def create_logger(name: str, level: Optional[str] = None,
                  f_handler: Optional[bool] = None, s_handler: Optional[bool] = None) -> logging.Logger:
    """create a logger object for recording log

    Args:
        name (str): the name of logger.
        level (str or int): level of logger
        f_handler (bool): if write to the file handler (file "mushroom.log").
            None to use custom variable ``log_to_file``
        s_handler (bool): if write to the stream handler (stdout)
            None to use custom variable ``log_to_stream``
    """
    log_to_file = _get_config("log_to_file", True)
    log_to_stream = _get_config("log_to_stream", False)

    logger = logging.getLogger(name)

    if level is None:
        logger.setLevel(log_level)
    else:
        logger.setLevel(get_logging_level(level))
    if f_handler is None:
        f_handler = log_to_file
    if f_handler and _fhand is not None:
        logger.addHandler(_fhand)
    if s_handler is None:
        s_handler = log_to_stream
    if s_handler and _shand is not None:
        logger.addHandler(_shand)
    return logger


class LoggersManager:
    """Object to manage a set of loggers"""

    def __init__(self):
        self._loggers = {}

    def has_logger(self, name: str) -> bool:
        """check if the logger with name is available"""
        return self._loggers.get(name, None) is not None

    def register(self, name: str, level: Optional[str] = None,
                 f_handler: Optional[bool] = None, s_handler: Optional[bool] = None) -> None:
        """register a logger with name to the logger manager"""
        if not self.has_logger(name):
            logger = create_logger(name, level, f_handler, s_handler)
            self._loggers[name] = logger
            logger.debug("Logger registered")

    def get(self, name: str) -> logging.Logger:
        """get the logger corresponding to the name"""
        logger = self._loggers.get(name, None)
        if logger is None:
            raise KeyError("logger not registered: %s" % name)
        return self._loggers.get(name)

    def __getitem__(self, name: str) -> logging.Logger:
        logger = self._loggers.get(name, None)
        if logger is None:
            self.register(name)
        return self._loggers.get(name)


loggers = LoggersManager()
