#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
from mushroom.graceplot import Plot

p = Plot()
# add multiple data at once
x = np.linspace(-np.pi, np.pi, 50)
y = [np.sin(x), 2*np.sin(x)]
p.plot(x, y)
p.write(file="band.agr")
