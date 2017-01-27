#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License v2.0;  -*- encoding: utf-8 -*-

from .checks import MagicType, checker_for_type, U, I, NOT
from .config import Config
from .__version__ import version as __version__

__all__ = ("checker_for_type", "Config", "MagicType", "U", "I", "NOT",
           "__version__")
