#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
from __future__ import division, print_function
from tests import typed, TTypeError, U, py3only
import random
import pytest


def assert_error(fn_or_type, argvalue, errormsg):
    if isinstance(fn_or_type, type(assert_error)):
        fn = fn_or_type
    else:
        @typed(xyz=fn_or_type)
        def fn(xyz):
            return True

    with pytest.raises(TTypeError) as e:
        fn(argvalue)
    assert errormsg in str(e.value)




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
    do({str: int}, [{"koo": 1}, {"moo": "foo"}, {1: 5},
                    {"a": 1, "b": 2, "c": 3}])
    do({str: int}, ["test"])



def test_lists():
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


def test_unions():
    @typed(x=U([int], [str]))
    def foo2(x):
        return True

    assert foo2([])
    assert foo2([1, 17, 55])
    assert foo2(["ham", "spam", "egg2"])
    assert_error(foo2, [1, 5, "ham"],
                 "Parameter `x` expects type `List[int]` but received a list "
                 "where 3rd element is 'ham' of type str")
    assert_error(foo2, ["spam", "bom", "bim", 2],
                 "Parameter `x` expects type `List[str]` but received a list "
                 "where 4th element is 2 of type int")
    assert_error(foo2, {"q": 0},
                 "Parameter `x` of type `List[int] | List[str]` received "
                 "value {'q': 0} of type dict")


@py3only
def test_dicts0():
    from typing import Dict, List, Any, Union
    assert_error(Dict, "what", "Parameter `xyz` of type `Dict` received value "
                               "'what' of type str")
    assert_error(Dict[Any, Any], "what", "Parameter `xyz` of type `Dict` "
                                         "received value 'what' of type str")
    assert_error(Dict[str, int], "hello",
                 "Parameter `xyz` of type `Dict[str, int]` received value "
                 "'hello' of type str")
    assert_error(Dict[str, List[int]], {"a": [1, 5, 'q']},
                 "Parameter `xyz` of type `Dict[str, List[int]]` received a "
                 "dict with a key-value pair {'a': [1, 5, 'q']}")
    assert_error(Union[Dict[str, int], Dict[str, str]],
                 {"a": 1, "b": 1, "d": "boo"},
                 "Parameter `xyz` expects type `Dict[str, int]` but received "
                 "a dict with a key-value pair {'d': 'boo'}")
    assert_error(Union[Dict[str, int], Dict[str, str]], None,
                 "Parameter `xyz` of type `Dict[str, int] | "
                 "Dict[str, str]` received value None")


def test_dict1():
    assert_error({"a": int}, 777,
                 "Parameter `xyz` of type `{'a': int}` received value 777 of "
                 "type int")
    assert_error(U({"a": int}, {"A": int}), 777,
                 "Parameter `xyz` of type `{'a': int} | {'A': int}` received "
                 "value 777 of type int")
    assert_error({"a": int}, {"a": "zero"},
                 "Parameter `xyz` of type `{'a': int}` received a dict where "
                 "key 'a' had value 'zero' of type str")
    assert_error({"a": int}, {"a": 0, "b": 1},
                 "Parameter `xyz` of type `{'a': int}` received a dict with "
                 "an unknown key 'b'")
    assert_error({"f": int, Ellipsis: str}, {"f": 0, "g": 5},
                 "Parameter `xyz` of type `{'f': int, ...: str}` received a "
                 "dict where key 'g' had value 5 of type int")
    assert_error(U({"a": int, "b": int, "c": int}, {"a": int},
                   {"a": int, "b": str, "c": int}),
                 {"a": 1, "b": "f", "c": "f"},
                 "received a dict where key 'c' had value 'f' of type str")
