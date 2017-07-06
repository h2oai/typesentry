#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
from tests import name_type, py3only, MagicType, U, I, Not


def test_simple():
    class ABCD(object):
        pass

    class EFGH(MagicType):
        pass

    class IJKL(MagicType):
        def name(self):
            return "i-j-k-l"

    assert name_type(int) == "int"
    assert name_type(str) == "str"
    assert name_type(None) == "None"
    assert name_type(bool) == "bool"
    assert name_type(float) == "float"
    assert name_type(0) == "0"
    assert name_type(1) == "1"
    assert name_type(123) == "123"
    assert name_type(False) == "False"
    assert name_type(True) == "True"
    assert name_type("foo") == '"foo"'
    assert name_type(u"föö")  # pytest cannot handle unicode properly
    assert name_type(ABCD) == "ABCD"
    assert name_type(EFGH) == "?"  # name() is not overridden
    assert name_type(IJKL) == "i-j-k-l"
    assert name_type(MagicType) == "?"

@py3only
def test_unicode_literal():
    # In py2 this stringifies into '"f\\xf6\\xf6"'
    assert name_type(u"föö") == '"föö"'


def test_composites():
    assert name_type(int, str) == "Union[int, str]"
    assert name_type(U(int, str)) == "Union[int, str]"
    assert name_type(U(1, 2, 3)) == "Union[1, 2, 3]"
    assert name_type(U(False, 0, "")) == 'Union[False, 0, ""]'
    assert name_type(U(int, None)) == "Optional[int]"
    assert name_type(U(None, float)) == "Optional[float]"
    assert name_type(I(int, str)) == "Intersection[int, str]"
    assert name_type(I(int, bool, float)) == "Intersection[int, bool, float]"
    assert name_type(I(int, Not(0))) == "Intersection[int, Not[0]]"
    assert name_type(I(int, Not(1, -1))) == "Intersection[int, Not[1, -1]]"


def test_collections():
    assert name_type(dict) == "dict"
    assert name_type(list) == "list"
    assert name_type(set) == "set"
    assert name_type([int]) == "List[int]"
    assert name_type([int, str]) == "List[Union[int, str]]"


@py3only
def test_typing():
    from typing import Any, List, Set, Dict, Type, Tuple
    assert name_type(Any) == "Any"
    assert name_type(List) == "List"
    assert name_type(List[Any]) == "List"
    assert name_type(List[str]) == "List[str]"
    assert name_type(List[int]) == "List[int]"
    assert name_type(Set) == "Set"
    assert name_type(Set[Any]) == "Set"
    assert name_type(Set[List]) == "Set[List]"
    assert name_type(Dict) == "Dict"
    assert name_type(Dict[Any, Any]) == "Dict"
    assert name_type(Dict[str, int]) == "Dict[str, int]"
    assert name_type(Type) == "Type"
    assert name_type(Type[int]) == "Type[int]"
    assert name_type(Type[MagicType]) == "Type[MagicType]"
    assert name_type(Tuple) == "Tuple"
    assert name_type(Tuple[int]) == "Tuple[int]"
    assert name_type(Tuple[int, str, List]) == "Tuple[int, str, List]"
    assert name_type(Tuple[int, Ellipsis]) == "Tuple[int, ...]"
    assert name_type(Tuple[str, Ellipsis]) == "Tuple[str, ...]"


@py3only
def test_callable():
    from typing import Callable, Union
    assert name_type(Callable) == "Callable"
    assert name_type(Callable[Ellipsis, int]) == "Callable[..., int]"
    assert name_type(Callable[[str], int]) == "Callable[[str], int]"
    assert name_type(Callable[[int, bool, str], float]) \
        == "Callable[[int, bool, str], float]"
