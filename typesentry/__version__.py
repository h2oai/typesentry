#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
"""
"Single source of truth" project version.

This module exports a single variable `version`, which contains the project's
version number. All other modules or scripts that need to know the project's
version MUST import (or otherwise parse) this module.

On each release, version number in this file is updated manually.

Version numbers are governed by PEP-440. We use the 3-part format::

    major.minor.micro

"""

version = "0.1.4"
