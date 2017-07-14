#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
from __future__ import division, print_function
from tests import typed, TTypeError, U, py3only, nth_str, PY3
import random
import sys
import pytest

if PY3:
    from io import StringIO
else:
    from cStringIO import StringIO

class CaptureIO(str):
    """
    Context manager for capturing output from stdout/stderr
    """
    def __enter__(self):
        self._result = (None, None)
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        self._iostdout = StringIO()
        self._iostderr = StringIO()
        sys.stdout = self._iostdout
        sys.stderr = self._iostderr
        return self

    def __exit__(self, *args):
        self._result = (self._iostdout.getvalue(),
                        self._iostderr.getvalue())
        del self._iostdout
        del self._iostderr
        sys.stdout = self._stdout
        sys.stderr = self._stderr

    def result(self):
        return self._result


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

        def oof(z):
            return foo(z)

        for x in args:
            try:
                assert oof(x)
            except TTypeError as e:
                e._handle_(*sys.exc_info())

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
                 "Parameter `x` of type `Union[List[int], List[str]]` received "
                 "value {'q': 0} of type dict")
    assert_error(U([int, str], int, str), [1, "boo", False],
                 "Parameter `xyz` expects type `List[Union[int, str]]` but "
                 "received a list where 3rd element is False")


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
                 "Parameter `xyz` of type `Union[Dict[str, int], "
                 "Dict[str, str]]` received value None")


def test_dict1():
    assert_error({"a": int}, 777,
                 "Parameter `xyz` of type `{'a': int}` received value 777 of "
                 "type int")
    assert_error(U({"a": int}, {"A": int}), 777,
                 "Parameter `xyz` of type `Union[{'a': int}, {'A': int}]` "
                 "received value 777 of type int")
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


@py3only
def test_type():
    from typing import Type

    class A: pass

    class B(A): pass

    assert_error(Type[A], [1, 5, 2],
                 "type `Type[A]` received value [1, 5, 2] of type list")
    assert_error(Type[A], int,
                 "Parameter `xyz` of type `Type[A]` received class int "
                 "which is not a subclass of A")
    assert_error(Type[B], A,
                 "Parameter `xyz` of type `Type[B]` received class A "
                 "which is not a subclass of B")


def test_tuple():
    assert_error((str, Ellipsis), "With Her =>",
                 "Parameter `xyz` of type `Tuple[str, ...]` received value "
                 "'With Her =>' of type str")
    assert_error((int, Ellipsis), (1, 7, 0, "foo", 5),
                 "Parameter `xyz` of type `Tuple[int, ...]` received a tuple "
                 "where 4th element is 'foo' of type str")
    assert_error(U((int, Ellipsis), (str, Ellipsis), (list, Ellipsis)),
                 ("foo", 1, 7, 0, 5),
                 "Parameter `xyz` expects type `Tuple[int, ...]` but received "
                 "a tuple where 1st element is 'foo' of type str")
    assert_error(U((int, Ellipsis), (str, Ellipsis), (float, Ellipsis)), "huh?",
                 "Parameter `xyz` of type `Union[Tuple[int, ...], Tuple[str, "
                 "...], Tuple[float, ...]]` received value 'huh?' of type str")
    assert_error((int, str), (1, 5),
                 "Parameter `xyz` of type `Tuple[int, str]` received a tuple "
                 "where 2nd element is 5 of type int")
    assert_error((int, str), (1, "foo", "bar"),
                 "Parameter `xyz` of type `Tuple[int, str]` received a tuple "
                 "of length 3, whereas length 2 was expected")
    assert_error((int, str), (1,),
                 "Parameter `xyz` of type `Tuple[int, str]` received a tuple "
                 "of length 1, whereas length 2 was expected")
    assert_error((int, str), '(1, "foo")',
                 "Parameter `xyz` of type `Tuple[int, str]` received value "
                 "'(1, \"foo\")' of type str")
    assert_error(U((int, str), (int, int)), (2, 5, 3),
                 "Parameter `xyz` expects type `Tuple[int, int]` but received "
                 "a tuple of length 3, whereas length 2 was expected")
    assert_error(U((int, str), (int, int)), "(2, 5)",
                 "Parameter `xyz` of type `Union[Tuple[int, str], Tuple[int, "
                 "int]]` received value '(2, 5)' of type str")


def test_set():
    assert_error({int}, None,
                 "Parameter `xyz` of type `Set[int]` received value None")
    assert_error({int}, {1, 5, "pawn"},
                 "Parameter `xyz` of type `Set[int]` received set containing "
                 "an element 'pawn' of type str")
    assert_error(U({int}, {str}), None,
                 "Parameter `xyz` of type `Union[Set[int], Set[str]]` received "
                 "value None")
    assert_error(U({int}, {str}), {1, 5, "pawn"},
                 "Parameter `xyz` expects type `Set[int]` but received a "
                 "set containing an element 'pawn' of type str")


def test_nth_str():
    assert nth_str(0) == "0th"
    assert nth_str(1) == "1st"
    assert nth_str(2) == "2nd"
    assert nth_str(3) == "3rd"
    assert nth_str(4) == "4th"
    for i in range(5, 21):
        assert nth_str(i) == str(i) + "th"
    assert nth_str(21) == "21st"
    assert nth_str(22) == "22nd"
    assert nth_str(23) == "23rd"
    assert nth_str(24) == "24th"
    assert nth_str(100) == "100th"
    assert nth_str(101) == "101st"
    assert nth_str(111) == "111th"
    assert nth_str(112) == "112th"
    assert nth_str(113) == "113th"
    assert nth_str(121) == "121st"
    assert nth_str(122) == "122nd"
    assert nth_str(123) == "123rd"
    assert nth_str(1000) == "1000th"


def test_tb1():
    @typed(x=int, y=U([int], [str]))
    def important(x, y, *others):
        return True

    try:
        important(8, "bar", "not", "me")
    except TTypeError as e:
        with CaptureIO() as output:
            e._handle_(*sys.exc_info())
        out, err = output.result()
        assert not out
        assert "important(x, y, *others)" in err


def test_tb2():
    @typed(x=int, y=U([int], [str]))
    def otherwise(x=0, y=None, *otherargs, **kws):
        return True

    try:
        otherwise(8, "bar", "not", "me")
    except TTypeError as e:
        with CaptureIO() as output:
            e._handle_(*sys.exc_info())
        out, err = output.result()
        assert not out
        assert "otherwise(x=0, y=None, *otherargs, **kws)" in err


def test_tb3():
    class A(object):
        @typed(once=bool, twice=str, thrice=U(str, [str]))
        def attempt(self, once, twice="Yes", thrice="Nay"):
            return True

    try:
        A().attempt(True, "1", .5)
        assert False
    except TTypeError as e:
        with CaptureIO() as output:
            e._handle_(*sys.exc_info())
        out, err = output.result()
        assert not out
        assert "attempt(self, once, twice='Yes', thrice='Nay')" in err
