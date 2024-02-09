# -*- coding: utf-8 -*-
"""workflow objects for FHI-aims"""
import os


class AimsInput:

    def __init__(self, control, geometry):
        self.geometry = geometry
        self.control = control
