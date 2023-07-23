# -*- coding: utf-8 -*-
"""Logging facilities for mushroom"""
import os
import logging


def get_logging_level(ll):
    """get the logging level if ll is a str"""
    if isinstance(ll, str):
        ll = logging._nameToLevel.get(ll.upper(), None)
    return ll


# try to get logger level from environment variabl
log_level = "notset"
try:
    log_level = os.environ["MUSHROOM_LOG"]
except KeyError:
    try:
        from mushroom.__config__ import log_level
    except ImportError:
        pass
log_level = get_logging_level(log_level)

stream_level = "notset"
try:
    stream_level = os.environ["MUSHROOM_STREAM"]
except KeyError:
    try:
        from mushroom.__config__ import stream_level
    except ImportError:
        pass
stream_level = get_logging_level(stream_level)


def _set_handler(flevel, slevel):
    """set the mode and log level of handler and stream logger

    Args:
        fmode (str): io mode of file logger
        """
    try:
        from mushroom.__config__ import logfile_mode
    except ImportError:
        logfile_mode = 'w'
    file_hand = None
    stream_hand = None
    fform = logging.Formatter(fmt='%(asctime)s - %(name)7s:%(levelname)8s - %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')
    sform = logging.Formatter(fmt='%(name)7s:%(levelname)8s - %(message)s')
    if flevel != logging.NOTSET:
        file_hand = logging.FileHandler("mushroom.log", mode=logfile_mode)
        file_hand.setFormatter(fform)
        file_hand.setLevel(flevel)
    if slevel != logging.NOTSET:
        stream_hand = logging.StreamHandler()
        stream_hand.setFormatter(sform)
        stream_hand.setLevel(slevel)

    return file_hand, stream_hand


# global handler
_fhand, _shand = _set_handler(log_level, stream_level)


def create_logger(name: str, level: str = None,
                  f_handler: bool = None, s_handler: bool = None) -> logging.Logger:
    """create a logger object for recording log

    Args:
        name (str) : the name of logger.
        level (str or int) : level of logger
        f_handler (bool) : if write to the file handler (file "mushroom.log").
            None to use custom variable ``log_to_file``
        s_handler (bool) : if write to the stream handler (stdout)
            None to use custom variable ``log_to_stream``
    """
    try:
        from mushroom.__config__ import log_to_file
    except ImportError:
        log_to_file = True
    try:
        from mushroom.__config__ import log_to_stream
    except ImportError:
        log_to_stream = False

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

