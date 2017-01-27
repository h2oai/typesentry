#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
from tests import name_type, py3only, MagicType, U, I, NOT


def test_simple():
    class ABCD(object):
        pass

    class EFGH(MagicType):
        pass

    class IJKL(MagicType):
        def name(self):
            return "i-j-k-l"

    assert name_type(int) == "integer"
    assert name_type(str) == "string"
    assert name_type(None) == "None"
    assert name_type(bool) == "boolean"
    assert name_type(float) == "numeric"
    assert name_type(0) == "0"
    assert name_type(1) == "1"
    assert name_type(123) == "123"
    assert name_type(False) == "False"
    assert name_type(True) == "True"
    assert name_type("foo") == '"foo"'
    assert name_type(ABCD) == "ABCD"
    assert name_type(EFGH) == "?"  # name() is not overridden
    assert name_type(IJKL) == "i-j-k-l"
    assert name_type(MagicType) == "?"


def test_composites():
    assert name_type(int, str) == "integer | string"
    assert name_type(U(int, str)) == "integer | string"
    assert name_type(U(1, 2, 3)) == "1 | 2 | 3"
    assert name_type(U(False, 0, "")) == 'False | 0 | ""'
    assert name_type(U(int, None)) == "?integer"
    assert name_type(U(None, float)) == "?numeric"
    assert name_type(I(int, str)) == "integer & string"
    assert name_type(I(int)) == "integer"
    assert name_type(I(int, NOT(0))) == "integer & !0"
    assert name_type(I(int, NOT(0, 1, -1))) == "integer & !(0 | 1 | -1)"


def test_collections():
    assert name_type(dict) == "dict"
    assert name_type(list) == "list"
    assert name_type(set) == "set"
    assert name_type([int]) == "List[integer]"
    assert name_type([int, str]) == "List[integer | string]"


@py3only
def test1():
    from typing import Any, Union, List, Set, Dict
    assert name_type(Any) == "Any"
    assert name_type(List) == "List"
    assert name_type(List[str]) == "List[string]"
    assert name_type(List[int]) == "List[integer]"
    assert name_type(Set) == "Set"
    assert name_type(Set[Any]) == "Set"
    # assert name_type(Set[List]) == "Set[List]"
