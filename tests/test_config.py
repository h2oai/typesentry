#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
from __future__ import division, print_function
import sys
from tests import typesentry
import pytest


def test_reporting():
    conf = typesentry.Config(soft_exceptions=True)
    TE = conf.TypeError
    VE = conf.ValueError
    typed = conf.typed

    @typed(x=int)
    def foo(x):
        pass

    try:
        foo("just a flesh wound!")
        assert False, "Expected a failure above"
    except TE as e:
        assert str(type(e)) == "<class 'typesentry.config.TypeError'>"
        e._handle_(*sys.exc_info())

    try:
        raise VE("bad value")
        assert False, "Expected a failure above"
    except VE as e:
        assert str(type(e)) == "<class 'typesentry.config.ValueError'>"
        e._handle_(*sys.exc_info())


def test_custom_exceptions():
    class CustomError(TypeError):
        def _handle_(self, *args):
            pass

    conf = typesentry.Config(type_error=CustomError, value_error=CustomError,
                             soft_exceptions=False)

    @conf.typed(x=int)
    def foo(x):
        pass

    try:
        foo("bazinga!")
        assert False, "Expected a failure"
    except CustomError as e:
        e._handle_()

    with pytest.raises(RuntimeError) as e:
        typesentry.Config(type_error=CustomError)
    assert (str(e.value) == "Class CustomError must take parameter `src` when "
                            "soft exceptions are used")


def test_disabled():
    conf = typesentry.Config(disabled=True)

    @conf.typed(x=int)
    def foo(x):
        pass

    foo("You should be ok")
