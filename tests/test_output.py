#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
from __future__ import division, print_function
from tests import typed, TTypeError
import random
import pytest


def assert_error(fn, arg, err):
    with pytest.raises(TTypeError) as e:
        fn(arg)
        assert False, "Error %r was expected" % err
    assert err in str(e.value)



def test_output():
    def do(st, args):
        @typed(monty=st)
        def foo(monty):
            return True

        for x in args:
            try:
                assert foo(x)
            except TTypeError as e:
                e._handle_()

    print()
    list0 = [None, random.randint(0, 10000), "zooka", (1, 3),
             [1, 5, 6], {"a"}, [3, 4, "b"],
             [999, .5, "`parampampam`", (1, 7), range(100), b"varrava"]]
    do(int, list0)
    do(str, list0)
    do([int, str], list0)
    do(bytes, ["hi", b"there"])



def test_list_errors():
    @typed(x=[int])
    def foo1(x):
        return True

    assert foo1([])
    assert foo1([0])
    assert foo1(list(range(100)))
    assert_error(foo1, {"bar"}, "Parameter `x` of type `List[int]` received "
                                "value %r of type set" % {"bar"})
    assert_error(foo1, ["bar"], "Parameter `x` of type `List[int]` received a "
                                "list where 1st element is 'bar' of type str")
    assert_error(foo1, [1, None, -1, 0], "2nd element is None")
    assert_error(foo1, [1, 7, 'why', 0], "3rd element is 'why' of type str")
    assert_error(foo1, [1, 7, 14, [15]], "4th element is [15] of type list")
    assert_error(foo1, [0] * 10 + [False], "11th element is False")
    assert_error(foo1, [0] * 11 + [True], "12th element is True")
    assert_error(foo1, [0] * 12 + [None] + [0] * 100, "13th element is None")
