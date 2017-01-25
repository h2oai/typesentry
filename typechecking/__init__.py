#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License v2.0;  -*- encoding: utf-8 -*-
from __future__ import absolute_import

from .checks import MagicType, checker_for_type
from .config import Config
from .__version__ import version as __version__

__all__ = ("checker_for_type", "Config", "MagicType", "__version__")
