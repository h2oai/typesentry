#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
from tests import is_type, py3only, U


def test_literals():
    assert is_type(1, 1)
    assert is_type(1.0, 1)
    assert is_type(True, True, False)
    assert is_type(3, *range(5))
    assert is_type("foo", "foo", "bar")
    assert is_type(u"foo", "foo", "bar")
    assert is_type("foo", u"foo", u"bar")
    assert is_type("I", *list("ABCDEFGHIJKL"))
    assert is_type(None, None)
    assert is_type(None, int, str, None)
    assert not is_type(1, 2)
    assert not is_type(False, None)


def test_primitives():
    assert is_type(False, bool)
    assert is_type(True, bool)
    assert is_type(1, int)
    assert is_type(123456789101112123456789, int)
    assert is_type(1, float)
    assert is_type(1.1, float)
    assert is_type(float("nan"), float)
    assert is_type(float("inf"), float)
    assert is_type("hello", str)
    assert is_type(u"hello", str)
    assert is_type(b"hello", str)
    assert not is_type(1, bool)
    assert not is_type(1, str)
    assert not is_type(1.1, int)
    assert not is_type(False, int)
    assert not is_type(False, float)
    assert not is_type(True, int)
    assert not is_type(True, float)


def test_lists():
    assert is_type([], [int])
    assert is_type([], [[[list]]])
    assert is_type([1, 2], list)
    assert is_type([1, 2, 3], [int])
    assert is_type([1, 2, 3], [float])
    assert is_type([1, 2, "hello"], [int, str])
    assert is_type([1, 2, "hello", None], [int, str, None])
    assert is_type([[1]], [list])
    assert is_type([[1], [2, 3], [0]], [[int]])
    assert is_type([[2.0, 3.1, 0], [2, 4.4, 1.1], [-1, 0]], [[int, float]])
    assert not is_type([1, 2, "hello", None], [str, None])
    assert not is_type([[1]], [int])


def test_sets():
    assert is_type({1}, set)
    assert is_type(set(), set)  # literal {} is a dict!
    assert is_type(set(), {int})
    assert is_type({1, 2, 1, 1, 3}, {int})
    assert is_type({1, 2, 3}, {float})
    assert is_type({1, 2, 3}, {float, str, None})
    assert is_type({1, 2, 3.5, None, "Aye"}, {float, str, None})
    assert not is_type({1, 2, 3.5, None, False}, {float, str, None})


def test_dicts():
    assert is_type({"foo": 1, "bar": 2}, {str: int})
    assert is_type({"foo": 3, "bar": [5], "baz": None},
                   {str: U(None, int, [int])})
    assert is_type({"foo": 1, "bar": 2},
                   {"foo": int, "bar": U(int, float, None), "baz": bool})
    assert is_type({}, {"spam": int, "egg": int})
    assert is_type({"spam": 10}, {"spam": int, "egg": int})
    assert is_type({"egg": 1}, {"spam": int, "egg": int})
    assert is_type({"egg": 1, "spam": 10}, {"spam": int, "egg": int})
    # assert is_type({"egg": 1, "spam": 10}, Dict(egg=int, spam=int))
    # assert is_type({"egg": 1, "spam": 10},
    #                Dict(egg=int, spam=int, ham=U(int, None)))
    assert not is_type({"foo": 1}, {str: str})
    assert not is_type({"foo": 1, "bar": 2}, {"foo": int})
    assert not is_type({"foo": 1, "bar": 2}, {"foo": int, str: str})


@py3only
def test_Any():
    from typing import Any
    assert is_type(0, Any)
    assert is_type(None, Any)
    assert is_type(False, Any)
    assert is_type("", Any)
    assert is_type(lambda x: x + 1, Any)
    assert is_type([1, 3, 5], Any)


@py3only
def test_Union():
    from typing import Union, List
    assert is_type(1, Union[str, int])
    assert is_type("1", Union[str, int])
    assert is_type([1, 0, "hi"], List[Union[str, int]])
    assert not is_type(Union, Union[str, int])

    # In Python, bool is a subclass of int, and thus Union[bool, int] = int.
    # However we make a distinction between booleans and integers, hence
    # is_type(True, int) is False.
    assert not is_type(True, Union[bool, int])


@py3only
def test_List():
    from typing import List, Any
    assert is_type([], List)
    assert is_type([], List[int])
    assert is_type([], List[str])
    assert is_type([1, 4, -1], List[int])
    assert is_type([1, 4, -1], List[float])
    assert is_type(["sam", "ham", "hum", "bum"], List[str])
    assert is_type([1, False, "monkey"], List)
    assert is_type([1, False, "monkey"], List[Any])


# @py3only
# def test_Dict():
#     from typing import Dict
