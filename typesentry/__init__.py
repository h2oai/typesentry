#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License v2.0;  -*- encoding: utf-8 -*-

from .checks import MagicType, checker_for_type
from .checks import MtNot as Not
from .checks import MtUnion as U
from .checks import MtIntersection as I
from .config import Config
from .__version__ import version as __version__

__all__ = ("checker_for_type", "Config", "MagicType", "U", "I", "Not",
           "__version__")
