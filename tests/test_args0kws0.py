#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
import pytest
from tests import typed


def test_foo():
    @typed()
    def foo():
        return True

    assert foo()

    with pytest.raises(TypeError) as e:
        foo(1)
    assert str(e.value) == "`foo()` doesn't take any arguments"

    with pytest.raises(TypeError) as e:
        foo(w=1)
    assert str(e.value) == "`foo()` got an unexpected keyword argument `w`"



def test_method():
    class Foo(object):
        @typed()
        def bar(self):
            return True

    foo = Foo()
    assert foo.bar()

    with pytest.raises(TypeError) as e:
        foo.bar(1)
    assert str(e.value) == "`bar()` doesn't take any arguments"



def test_bad():
    with pytest.raises(AssertionError):
        @typed(z=int)
        def foo1():
            pass

    with pytest.raises(AssertionError):
        @typed(_kwless=1)
        def foo2():
            pass
