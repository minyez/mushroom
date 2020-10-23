# -*- coding: utf-8 -*-
"""Logging facilities for mushroom"""
import logging

def get_logging_level(ll):
    """get the logging level if ll is a str"""
    if isinstance(ll, str):
        ll = logging._nameToLevel.get(ll.upper(), None)
    return ll

try:
    from mushroom.__config__ import log_level
    LOG_LEVEL = get_logging_level(log_level)
except ImportError:
    LOG_LEVEL = logging.INFO

try:
    from mushroom.__config__ import stream_level
    _STREAM_LEVEL = get_logging_level(stream_level)
except ImportError:
    _STREAM_LEVEL = logging.INFO

LOGFILE = "mushroom.log"

_ROOT_HAND = logging.FileHandler(LOGFILE, mode='a')
_STREAM_HAND = logging.StreamHandler()
_ROOT_FORM = logging.Formatter(fmt='%(asctime)s - %(name)7s:%(levelname)8s - %(message)s',
                               datefmt='%Y-%m-%d %H:%M:%S')
_STREAM_FORM = logging.Formatter(fmt='%(name)7s:%(levelname)8s - %(message)s')

_ROOT_HAND.setFormatter(_ROOT_FORM)
_ROOT_HAND.setLevel(LOG_LEVEL)
_STREAM_HAND.setFormatter(_STREAM_FORM)
_STREAM_HAND.setLevel(_STREAM_LEVEL)


def create_logger(name: str, level: str = None,
                  f_handler: bool = True, s_handler: bool = True) -> logging.Logger:
    """create a logger object for recording log
    
    Args:
        name (str) : the name of logger. 
        level (str or int) : level of logger
        f_handler (bool) : if write to the file handler (file "mushroom.log").
        s_handler (bool) : if write to the stream handler (stdout)
    """
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(get_logging_level(level))
    else:
        logger.setLevel(LOG_LEVEL)
    if f_handler:
        logger.addHandler(_ROOT_HAND)
    if s_handler:
        logger.addHandler(_STREAM_HAND)
    return logger

