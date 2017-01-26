#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import print_function

import sys
sys.path.insert(0, "..")

import typesentry  # noqa

_tc = typesentry.Config()
typed = _tc.typed
TypeError = _tc.TypeError
ValueError = _tc.ValueError

__all__ = ("typed", "TypeError", "ValueError")
