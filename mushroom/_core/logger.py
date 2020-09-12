# -*- coding: utf-8 -*-
"""Logging facilities for mushroom"""

import logging

LOGLEVEL = logging.INFO
LOGFILE = "mushroom.log"
STREAM_LEVEL = logging.WARNING

ROOT_HAND = logging.FileHandler(LOGFILE, mode='w')
STREAM_HAND = logging.StreamHandler()
ROOT_FORM = logging.Formatter(fmt='%(asctime)s - %(name)s:%(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
STREAM_FORM = logging.Formatter(fmt='%(name)s:%(levelname)s - %(message)s')

ROOT_HAND.setFormatter(ROOT_FORM)
ROOT_HAND.setLevel(LOGLEVEL)
STREAM_HAND.setFormatter(STREAM_FORM)
STREAM_HAND.setLevel(STREAM_LEVEL)

def create_logger(name, level=None, handler=None, stream=False):
    """create a logger object for recording log
    
    Args:
      name (str) : the name of logger. 
      handler (logging handler object) : the handler.
          If set None, ROOT_HAND will be used.
      stream (bool) : if this logger will also print to stream"""
    logger = logging.getLogger(name)
    if level:
        logger.setLevel(level)
    else:
        logger.setLevel(LOGLEVEL)
    if handler:
        logger.addHandler(handler)
    else:
        logger.addHandler(ROOT_HAND)
    if stream:
        logger.addHandler(STREAM_HAND)
    return logger

