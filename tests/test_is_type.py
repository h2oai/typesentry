#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
from tests import is_type


def test_literals():
    assert is_type(1, 1)
    assert is_type(1.0, 1)
    assert is_type(True, True, False)
    assert is_type(3, *range(5))
    assert is_type("foo", "foo", "bar")
    assert is_type(u"foo", "foo", "bar")
    assert is_type("foo", u"foo", u"bar")
    assert is_type(None, None)
    assert not is_type(1, 2)
    assert not is_type(False, None)


def test_primitives():
    assert is_type(False, bool)
    assert is_type(True, bool)
    assert is_type(1, int)
    assert is_type(1234567891011122345, int)
    assert is_type(1, float)
    assert is_type(1.1, float)
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
    assert is_type([1, 2], list)
    assert is_type([1, 2, 3], [int])
    assert is_type([1, 2, 3], [float])
    assert is_type([1, 2, "hello"], [int, str])
    assert is_type([1, 2, "hello", None], [int, str, None])
    assert is_type([[1]], [list])
    assert is_type([[1], [2, 3], [0]], [[int]])
    assert not is_type([1, 2, "hello", None], [str, None])
    assert not is_type([[1]], [int])


def test_sets():
    assert is_type({1}, set)
    assert is_type(set(), set)  # literal {} is a dict!
    assert is_type(set(), {int})
    assert is_type({1, 2, 3}, {int})
    assert is_type({1, 2, 3}, {float})
    assert is_type({1, 2, 3}, {float, str, None})
    assert is_type({1, 2, 3.5, None, "Aye"}, {float, str, None})
    assert not is_type({1, 2, 3.5, None, False}, {float, str, None})
