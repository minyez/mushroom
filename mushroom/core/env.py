# -*- coding: utf-8 -*-
"""environment"""
from os import geteuid
from pwd import getpwuid
from socket import gethostname

username = getpwuid(geteuid()).pw_name
"""user name"""

hostname = gethostname()
"""host name"""

del geteuid, getpwuid, gethostname
