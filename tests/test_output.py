#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
from __future__ import division, print_function
from tests import typed, TTypeError
import random
import pytest

@typed()
def foo(x):
    raise RuntimeError


def do(st):
    argname = "".join(chr(random.randint(ord('a'), ord('z'))) for _ in range(6))
    exec("@typed({arg}={type})\n"
         "def foo({arg}=None):\n"
         "    return True\n".format(arg=argname, type=st),
         locals(), globals())
    for x in [None, random.randint(0, 10000), "zooka", (1, 3),
              [1, 5, 6], {"a"}, [3, 4, "b"],
              [999, .5, "`parampampam`", (1, 7), range(100), b"varrava"]]:
        try:
            foo(x)
        except TTypeError as e:
            e._handle_()

def assert_error(fn, arg, err):
    with pytest.raises(TTypeError) as e:
        fn(arg)
        assert False, "Error %r was expected" % err
    assert err in str(e.value)

def test_output():
    print()
    do("int")
    do("str")
    do("[int, str]")


def test_list_errors():
    @typed(x=[int])
    def foo1(x):
        return True

    assert foo1([])
    assert foo1([0])
    assert foo1(list(range(100)))
    assert_error(foo1, {"bar"}, "Parameter `x` of type `List[int]` received "
                                "value {'bar'} of type set")
    assert_error(foo1, ["bar"], "Parameter `x` of type `List[int]` received a "
                                "list where 1st element is 'bar' of type str")
    assert_error(foo1, [1, None, -1, 0], "2nd element is None")
    assert_error(foo1, [1, 7, 'why', 0], "3rd element is 'why' of type str")
    assert_error(foo1, [1, 7, 14, [15]], "4th element is [15] of type list")
    assert_error(foo1, [0] * 10 + [False], "11th element is False")
    assert_error(foo1, [0] * 11 + [True], "12th element is True")
    assert_error(foo1, [0] * 12 + [None] + [0] * 100, "13th element is None")
