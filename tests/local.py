#!/usr/bin/env python

import re
import subprocess

with open('.travis.yml', 'rt') as f:
    for line in f.readlines():
        match = re.match(r'(.*?)(nosetest.*)', line)
        if match:
            command = match.groups()[-1].split()
            print(command)
            subprocess.check_call(command)
