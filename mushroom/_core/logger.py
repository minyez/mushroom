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
    STREAM_LEVEL = get_logging_level(stream_level)
except ImportError:
    STREAM_LEVEL = logging.WARNING

LOGFILE = "mushroom.log"

ROOT_HAND = logging.FileHandler(LOGFILE, mode='w')
STREAM_HAND = logging.StreamHandler()
ROOT_FORM = logging.Formatter(fmt='%(asctime)s - %(name)s:%(levelname)s - %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')
STREAM_FORM = logging.Formatter(fmt='%(name)s:%(levelname)s - %(message)s')

ROOT_HAND.setFormatter(ROOT_FORM)
ROOT_HAND.setLevel(LOG_LEVEL)
STREAM_HAND.setFormatter(STREAM_FORM)
STREAM_HAND.setLevel(STREAM_LEVEL)


def create_logger(name, level=None, f_handler=True, s_handler=False):
    """create a logger object for recording log
    
    Args:
        name (str) : the name of logger. 
        f_handler (bool) : if write to the file handler (file "mushroom.log").
        s_handler (bool) : if write to the stream handler (stdout)
    """
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(get_logging_level(level))
    else:
        logger.setLevel(LOG_LEVEL)
    if f_handler:
        logger.addHandler(ROOT_HAND)
    if s_handler:
        logger.addHandler(STREAM_HAND)
    return logger

