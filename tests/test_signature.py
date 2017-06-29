#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
import pytest
import time
from tests import typed, py3only, TTypeError


def test_func_0args0kws():
    @typed()
    def foo():
        return True

    assert foo()

    with pytest.raises(TTypeError) as e:
        foo(1)
    assert str(e.value) == "`foo()` doesn't take any arguments"

    with pytest.raises(TTypeError) as e:
        foo(1, 2, 3)
    assert str(e.value) == "`foo()` doesn't take any arguments"

    with pytest.raises(TTypeError) as e:
        foo(w=1)
    assert str(e.value) == "`foo()` got an unexpected keyword argument `w`"

    with pytest.raises(TTypeError) as e:
        foo(1, q=2)
    assert str(e.value) == "`foo()` doesn't take any arguments"



def test_method_noargs():
    class Foo(object):
        @typed()
        def bar(self):
            return True

    foo = Foo()
    assert foo.bar()

    with pytest.raises(TTypeError) as e:
        foo.bar(1)
    assert str(e.value) == "`bar()` doesn't take any arguments"

    with pytest.raises(TTypeError) as e:
        foo.bar(ww=1)
    assert str(e.value) == "`bar()` got an unexpected keyword argument `ww`"




def test_func_1arg0kws():
    @typed(x=int)
    def foo(x):
        return True

    assert foo(1)
    assert foo(x=15)

    with pytest.raises(TTypeError) as e:
        foo()
    assert str(e.value) == "`foo()` missing 1 required positional argument `x`"

    with pytest.raises(TTypeError) as e:
        foo(1, 2, 3)
    assert str(e.value) == "`foo()` takes 1 positional argument but 3 were " \
                           "given"

    with pytest.raises(TTypeError) as e:
        foo("bar")
    assert str(e.value) == ("Parameter `x` of type `int` received value 'bar' "
                            "of type str")

    with pytest.raises(TTypeError) as e:
        foo(1, x=2)
    assert str(e.value) == "`foo()` got multiple values for argument `x`"



def test_func_3args0kws():
    @typed(x=int, y=float, z=str)
    def foo(x, y, z):
        return "%d %.3f %s" % (x, y, z)

    assert foo(1, 2, "bar")
    assert foo(z="reverse", x=7, y=0.001)

    with pytest.raises(TTypeError) as e:
        foo()
    assert str(e.value) == "`foo()` missing 3 required positional arguments: "\
                           "`x`, `y` and `z`"

    with pytest.raises(TTypeError) as e:
        foo(y=0)
    assert str(e.value) == "`foo()` missing 2 required positional arguments: "\
                           "`x` and `z`"

    with pytest.raises(TTypeError) as e:
        foo(x=[3], y=4, z="")
    assert str(e.value) == ("Parameter `x` of type `int` received value [3] "
                            "of type list")

def test_func_varargs():
    @typed(args=int)
    def foo(*args):
        return sum(args)

    assert foo() == 0
    assert foo(1) == 1
    assert foo(1, 2, 3, 4, 5) == 15

    with pytest.raises(TTypeError) as e:
        foo(1, 3, "bar")
    assert str(e.value) == ("Vararg parameter of type `int` received "
                            "value 'bar' of type str")



def test_func_varkws():
    @typed(kws=float)
    def foo(**kws):
        return sum(kws.values())

    assert foo() == 0
    assert foo(x=1) == 1
    assert foo(x=1, y=3.3, z=0.7) == 5

    with pytest.raises(TTypeError) as e:
        foo(x=1, xx=3, xxx="bar")
    assert str(e.value) == ("Parameter `xxx` of type `numeric` received value "
                            "'bar' of type str")

    with pytest.raises(TTypeError) as e:
        foo(1, 2, x=10)
    assert str(e.value) == "`foo()` accepts only keyword arguments"



def test_return_value():
    @typed(_return=float)
    def foo():
        return time.time()

    @typed(_return=int)
    def bar(x):
        return x

    assert foo() > 0
    assert bar(1) == 1

    with pytest.raises(TTypeError) as e:
        bar("test")
    assert str(e.value) == "Incorrect return type in `bar()`: " \
                           "expected int got str"



def test_bad_declaration():
    with pytest.raises(RuntimeError) as e:
        @typed(z=int)
        def foo1():
            pass
    assert str(e.value) == "Invalid function argument(s): z"

    with pytest.raises(RuntimeError) as e:
        class A(object):
            @typed(self=int)
            def __init__(self):
                pass
    assert str(e.value) == "`self` parameter must not be typed"


def test_wrapped_function():
    import functools

    def decorator(f):
        @functools.wraps(f)
        def decorated(*args):
            print("Running f(%r)" % args)
            return f(*args)
        if not hasattr(decorated, "__wrapped__"):
            decorated.__wrapped__ = f
        return decorated

    @typed(x=int)
    @decorator
    @decorator
    def foo(x):
        return True

    assert foo(5)
    with pytest.raises(TTypeError) as e:
        foo("bar")
    assert str(e.value) == ("Parameter `x` of type `int` received value 'bar' "
                            "of type str")


@py3only
def test_function_with_signature():
    # We have to use exec() here, otherwise it would be a syntax error on
    # Python-2
    exec("@typed()\n"
         "def foo(x: int = None) -> bool:\n"
         "    return True\n", locals(), globals())

    assert foo()  # noqa
    assert foo(1)  # noqa
    with pytest.raises(TTypeError) as e:
        foo("oo")
    assert str(e.value) == ("Parameter `x` of type `int` received value 'oo' "
                            "of type str")
    with pytest.raises(RuntimeError) as e:
        exec("@typed(x=str)\n"
             "def foo(x: int = None):\n"
             "    return True\n", locals(), globals())
    assert str(e.value) == ("Parameter `x` should not have its type specified "
                            "both in @typed() and in the annotations")


def test_defaults():
    @typed(x=int)
    def foo(x=None):
        return True

    assert foo()
    assert foo(5)
    assert foo(None)
    assert foo(x=10)
    assert foo(x=None)

    with pytest.raises(TTypeError) as e:
        foo(x="")
    assert str(e.value) == ("Parameter `x` of type `int` received value '' "
                            "of type str")
