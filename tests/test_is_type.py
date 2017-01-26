#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
from tests import is_type


def test0():
    assert is_type(1, int)
    assert is_type(1234567891011122345, int)
    assert is_type(1, float)
    assert not is_type(1, bool)
    assert not is_type(1, str)
    assert is_type(1.1, float)
    assert not is_type(1.1, int)
    assert is_type("hello", str)
    assert is_type(u"hello", str)
    assert is_type(b"hello", str)

def test1():
    assert is_type([1, 2, 3], [int])
    assert is_type([1, 2, 3], [float])
    assert is_type([1, 2, "hello"], [int, str])
    assert is_type([1, 2, "hello", None], [int, str, None])
    assert not is_type([1, 2, "hello", None], [str, None])
