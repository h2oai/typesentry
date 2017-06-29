#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
import pytest
from tests import typed, py3only, TTypeError

foo = 1
bar = 2
baz = 3


def test_kwonly1():
    @typed(_kwonly=2)
    def foo(x, y):
        return (x, y)

    assert foo(x=1, y=2)
    assert foo(y="spam", x="ham")

    with pytest.raises(TTypeError) as e:
        foo(1, 2)
    assert str(e.value) == "`foo()` accepts only keyword arguments"

    with pytest.raises(TTypeError) as e:
        foo(1, y=2)
    assert str(e.value) == "`foo()` accepts only keyword arguments"



def test_kwonly2():
    @typed(_kwonly=1)
    def bar(x, y):
        return (x, y)

    assert bar(x=3, y=4)
    assert bar(3, y=7)

    with pytest.raises(TTypeError) as e:
        assert bar._signature_._max_positional_args == 1
        assert bar._signature_._min_positional_args == 1
        bar(1, x=2)
    assert str(e.value) == "`bar()` missing 1 required keyword argument `y`"

    with pytest.raises(TTypeError) as e:
        bar(1)
    assert str(e.value) == "`bar()` missing 1 required keyword argument `y`"

    with pytest.raises(TTypeError) as e:
        bar(1, smth=2)
    assert str(e.value) == "`bar()` missing 1 required keyword argument `y`"

    with pytest.raises(TTypeError) as e:
        bar(1, 2)
    assert str(e.value) == "`bar()` takes 1 positional argument but 2 " \
                           "were given"



def test_kwonly3():
    @typed(_kwonly=2)
    def baz(a, b, c, d=4):
        return True

    assert baz(1, 2, c=3, d=44)
    assert baz(1, 2, c=3)

    with pytest.raises(TTypeError) as e:
        baz(1, 2, 3, 4)
    assert str(e.value) == "`baz()` takes 2 positional arguments but 4 " \
                           "were given"

    with pytest.raises(TTypeError) as e:
        baz(1, 2, d=5)
    assert str(e.value) == "`baz()` missing 1 required keyword argument `c`"

    with pytest.raises(TTypeError) as e:
        # assert baz._signature_._min_positional_args == 2
        baz(1, c=2, d=5)
    assert str(e.value) == "`baz()` missing 1 required positional argument `b`"



def test_kwonly4():
    @typed(_kwonly=2)
    def ooz(a, b=2, x=None):
        return True

    assert ooz(3)
    assert ooz(5, b=0)



@py3only
def test_py3_signatures():
    exec("@typed(x=int, y=int)\n"
         "def bar(x, *, y):\n"
         "    return x + y\n", locals(), globals())

    assert bar(1, y=2) == 3
    assert bar(x=5, y=7) == 12

    exec("@typed(x=int, y=int)\n"
         "def baz(x, *, y=5):\n"
         "    return x + y\n", locals(), globals())

    assert baz(5) == 10
    assert baz(x=1) == 6
    assert baz(x=1, y=2) == 3

    with pytest.raises(RuntimeError) as e:
        exec("@typed(_kwonly=1)\n"
             "def foo(x, *, y):\n"
             "    return True\n", locals(), globals())
    assert str(e.value) == "_kwonly parameter cannot be used with '*' " \
                           "argument in Python3"



def test_bad_declarations():
    with pytest.raises(RuntimeError) as e:
        @typed(_kwonly=None)
        def foo0():
            pass
    assert str(e.value) == "_kwonly parameter should be an integer"

    with pytest.raises(RuntimeError) as e:
        @typed(_kwonly=1)
        def foo2():
            pass
    assert str(e.value) == "Too many keyword-only parameters requested"

    with pytest.raises(RuntimeError) as e:
        @typed(_kwonly=1)
        def foo3(*args):
            pass
    assert str(e.value) == "Too many keyword-only parameters requested"

    with pytest.raises(RuntimeError) as e:
        @typed(_kwonly=1)
        def foo4(*args, **varargs):
            pass
    assert str(e.value) == "Too many keyword-only parameters requested"

    with pytest.raises(RuntimeError) as e:
        class A(object):
            @typed(_kwonly=1)
            def __init__(self):
                pass
    assert str(e.value) == "POSITIONAL_ONLY parameter self cannot be made " \
                           "KEYWORD_ONLY"
