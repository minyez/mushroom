# -*- coding: utf-8 -*-
"""timing and profiling utilities"""
from time import time
from functools import wraps

class Timer:
    def __init__(self):
        self._tstart = None
        self._atime = 0.0
        self._counts = 0

    def enable(self):
        self._tstart = time()

    def disable(self):
        if self._tstart is not None:
            self._atime = time() - self._tstart
            self._counts += 1
        self._tstart = None

class Profiler:
    def __init__(self):
        self._timers = {}

    def register(self, name, *args, **kwargs):
        """register a timer with name"""
        if name not in self._timers:
            self._timers[name] = Timer()

    def enable(self, name):
        """start profiling under name"""
        self._timers[name].enable()

    def disable(self, name):
        """stop current profiling and add data"""
        self._timers[name].disable()

profiler = Profiler()

def timing_func(func):
    @wraps(func)
    def wrap(*args, **kw):
        ts = time()
        result = func(*args, **kw)
        te = time()
        return result
    return wrap

def timing_method(method):
    @wraps(method)
    def wrap(ref, *args, **kw):
        ts = time()
        result = method(ref, *args, **kw)
        te = time()
        return result
    return wrap

