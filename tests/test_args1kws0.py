#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
import pytest
from tests import typed, TypeError


@typed(x=int)
def foo(x):
    return True


def test_foo():
    assert foo(1)
    assert foo(x=15)

    with pytest.raises(TypeError) as e:
        foo()
    assert str(e.value) == "`foo()` missing 1 required positional argument `x`"

    with pytest.raises(TypeError) as e:
        foo(1, 2, 3)
    assert str(e.value) == "`foo()` takes 1 positional argument but 3 were " \
                           "given"

    with pytest.raises(TypeError) as e:
        foo("bar")
    assert str(e.value) == "Incorrect type for argument `x`: expected " \
                           "integer got <class 'str'>"

    with pytest.raises(TypeError) as e:
        foo(1, x=2)
    assert str(e.value) == "`foo()` got multiple values for argument `x`"
