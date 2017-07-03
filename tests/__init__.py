#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import print_function
import pytest

import sys
sys.path.insert(0, "..")

import typesentry  # noqa
from typesentry import U, I, Not, MagicType  # noqa
from typesentry.checks import _nth_str as nth_str  # noqa


_tc = typesentry.Config()
typed = _tc.typed
is_type = _tc.is_type
name_type = _tc.name_type
TTypeError = _tc.TypeError
TValueError = _tc.ValueError


#------ pytest fixtures --------------------------------------------------------

py3only = pytest.mark.skipif(sys.version_info < (3, 5),
                             reason="at least mymodule-1.1 required")
PY3 = sys.version_info > (3, )

__all__ = ("is_type", "name_type", "typed", "TTypeError", "TValueError",
           "py3only", "U", "I", "Not", "MagicType", "PY3", "nth_str")
