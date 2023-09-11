# -*- coding: utf-8 -*-

from mushroom.core.logger import create_logger

_logger = create_logger("aims")
del create_logger


class AimsNotFinishedError(Exception):
    """Exception that FHI-aims calculation is not finished"""
    pass

