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
    log_level = get_logging_level(log_level)
except ImportError:
    log_level = logging.INFO
try:
    from mushroom.__config__ import stream_level
    stream_level = get_logging_level(stream_level)
except ImportError:
    stream_level = logging.INFO
try:
    from mushroom.__config__ import log_to_file
except ImportError:
    log_to_file = True
try:
    from mushroom.__config__ import log_to_stream
except ImportError:
    log_to_stream = False

logfile = "mushroom.log"

_root_hand = logging.FileHandler(logfile, mode='a')
_stream_hand = logging.StreamHandler()
_root_form = logging.Formatter(fmt='%(asctime)s - %(name)7s:%(levelname)8s - %(message)s',
                               datefmt='%Y-%m-%d %H:%M:%S')
_stream_form = logging.Formatter(fmt='%(name)7s:%(levelname)8s - %(message)s')

_root_hand.setFormatter(_root_form)
_root_hand.setLevel(log_level)
_stream_hand.setFormatter(_stream_form)
_stream_hand.setLevel(stream_level)


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
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(get_logging_level(level))
    else:
        logger.setLevel(log_level)
    if f_handler is None:
        f_handler = log_to_file
    if f_handler:
        logger.addHandler(_root_hand)
    if s_handler is None:
        s_handler = log_to_stream
    if s_handler:
        logger.addHandler(_stream_hand)
    return logger

