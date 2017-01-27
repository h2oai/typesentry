#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import print_function
import pytest

import sys
sys.path.insert(0, "..")

import typesentry  # noqa
from typesentry import U, I, NOT  # noqa

_tc = typesentry.Config()
typed = _tc.typed
is_type = _tc.is_type
TypeError = _tc.TypeError
ValueError = _tc.ValueError


#------ pytest fixtures --------------------------------------------------------

py3only = pytest.mark.skipif(sys.version_info < (3, 5),
                             reason="at least mymodule-1.1 required")


__all__ = ("is_type", "typed", "py3only", "TypeError", "ValueError",
           "U", "I", "NOT")
