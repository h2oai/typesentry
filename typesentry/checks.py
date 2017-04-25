#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
from __future__ import division, print_function

import sys


PY2 = sys.version_info[0] == 2

if PY2:
    _str_type = (str, unicode)  # noqa
    _int_type = (int, long)     # noqa
    _num_type = (int, long, float)  # noqa
    _primitive_type = (str, int, float, bool, unicode, long)  # noqa
else:
    _str_type = (str, bytes)
    _int_type = int
    _num_type = (int, float)
    _primitive_type = (str, int, float, bool, bytes)

try:
    import typing
except ImportError:
    typing = None



def checker_for_type(t):
    try:
        if t is True: return true_checker
        if t is False: return false_checker
        checker = memoized_type_checkers.get(t)
        if checker is not None:
            return checker
        hashable = True
    except Exception:
        # Exception may be raised if `t` is not hashable
        hashable = False

    # The type checker needs to be created
    checker = _create_checker_for_type(t)
    if hashable:
        memoized_type_checkers[t] = checker
    return checker


def _create_checker_for_type(t):
    if isinstance(t, _primitive_type):
        return LiteralChecker(t)
    if isinstance(t, MagicType):
        return t
    if isinstance(t, type):
        if issubclass(t, MagicType):
            return t()
        if typing:
            if issubclass(t, typing.List) and t is not list:
                itemtype = t.__args__ and t.__args__[0]
                if itemtype:
                    return ListChecker(itemtype)
                else:
                    return ClassChecker(list, name="List")
            if issubclass(t, typing.Dict) and t is not dict:
                if t.__args__:
                    key, value = t.__args__
                    return checker_for_type({key: value})
                else:
                    return ClassChecker(dict)
            if issubclass(t, typing.Tuple) and t is not tuple:
                tlen = len(t.__tuple_params__)
                if t.__tuple_use_ellipsis__:
                    assert tlen == 1
                    return TupleChecker(t.__tuple_params__[0], Ellipsis)
                else:
                    return TupleChecker(*t.__tuple_params__)
        # `t` is a name of the class, or a built-in type such as
        # `list, `tuple`, etc
        return ClassChecker(t)
    if typing:
        if t is typing.Any:
            return Any()
        if type(t) is type(typing.Union):  # flake8: disable=E721
            try:
                return U(*t.__union_params__)
            except AttributeError:
                return U(*t.__args__)
    if isinstance(t, list):
        # `t` is a list literal
        return ListChecker(U(*t))
    if isinstance(t, set):
        return SetChecker(U(*t))
    if isinstance(t, tuple):
        return TupleChecker(*t)
    if isinstance(t, dict):
        return DictChecker(t)
    raise RuntimeError("Unknown type %r for type-checker" % t)



#-------------------------------------------------------------------------------
# Basic types
#-------------------------------------------------------------------------------

class MagicType(object):
    """Base class for all "special" types."""

    def check(self, var):
        """
        Return True if the variable matches this type, and False otherwise.

        :param var: value that needs to be tested
        :returns: True iff `var` matches this type
        """
        return False

    def name(self):
        """Return string representing the name of this type."""
        return "?"

    def fuzzycheck(self, var):
        """
        Return a number from 0 to 1 indicating how closely ``var`` matches
        this type.

        This is similar to :meth:`check`, except that it may potentially be
        more computationally intensive. The return value of 0 indicates that
        ``var`` doesn't match this type at all, whereas 1 indicates a match.
        Values less than 1 may indicate "partial" match, for example a
        ``List[int]`` type may return the proportion of elements in the given
        list ``var`` that are integers.

        The default implementation of this function returns only 0 or 1.
        """
        return 1 if self.check(var) else 0


class Any(MagicType):
    def check(self, v):
        return True

    def name(self):
        return "Any"


class ClassChecker(MagicType):
    def __init__(self, cls, name=None):
        self.cls = cls
        self._name = name

    def check(self, v):
        return isinstance(v, self.cls)

    def name(self):
        return self._name or self.cls.__name__



#-------------------------------------------------------------------------------
# Checkers for primitive types
#-------------------------------------------------------------------------------

class NoneChecker(MagicType):
    def check(self, v):
        return v is None

    def name(self):
        return "None"


class BoolChecker(MagicType):
    def check(self, v):
        return isinstance(v, bool)

    def name(self):
        return "boolean"


class IntChecker(MagicType):
    def check(self, v):
        return isinstance(v, _int_type) and not isinstance(v, bool)

    def name(self):
        return "integer"


class FloatChecker(MagicType):
    """
    Float type has the semantic of "numeric", i.e. it maches both floats and
    integers (see PEP-0484).
    """
    def check(self, v):
        return isinstance(v, _num_type) and not isinstance(v, bool)

    def name(self):
        return "numeric"


class StrChecker(MagicType):
    """
    On Python2 we treat both `str` and `unicode` as matching this type; on
    Python3 both `str` and `bytes` match this type.
    """
    def check(self, v):
        return isinstance(v, _str_type)

    def name(self):
        return "string"


class LiteralChecker(MagicType):
    def __init__(self, literal):
        self.literal = literal

    def check(self, v):
        return v == self.literal

    def name(self):
        if isinstance(self.literal, _str_type):
            s = repr(self.literal)
            if s[0] == "u": s = s[1:]
            s = s[1:-1].replace('"', '\\"')
            return '"%s"' % s
        else:
            return str(self.literal)



#-------------------------------------------------------------------------------
# Checkers for collection types
#-------------------------------------------------------------------------------

class ListChecker(MagicType):
    def __init__(self, elem_type):
        self._elem = checker_for_type(elem_type)

    def check(self, v):
        c = self._elem
        return isinstance(v, list) and all(c.check(x) for x in v)

    def name(self):
        return "List[%s]" % self._elem.name()

    def fuzzycheck(self, v):
        if not isinstance(v, list): return 0
        if len(v) == 0: return 1
        c = self._elem
        return sum(c.fuzzycheck(x) for x in v) / len(v)



class SetChecker(MagicType):
    def __init__(self, elem_type):
        self._elem = checker_for_type(elem_type)

    def check(self, v):
        c = self._elem
        return isinstance(v, set) and all(c.check(x) for x in v)

    def name(self):
        return "Set[%s]" % self._elem.name()

    def fuzzycheck(self, v):
        if not isinstance(v, set): return 0
        if len(v) == 0: return 1
        c = self._elem
        return sum(c.fuzzycheck(x) for x in v) / len(v)



class TupleChecker(MagicType):
    def __init__(self, *items):
        if len(items) >= 2 and items[-1] is Ellipsis:
            # Variable-length tuple whose last element has type `_last`
            self._checks = [checker_for_type(t) for t in items[:-2]]
            self._last = checker_for_type(items[-2])
        else:
            # Fixed-length tuple
            self._checks = [checker_for_type(t) for t in items]
            self._last = None

    def check(self, v):
        n = len(self._checks)
        if self._last:
            return (isinstance(v, tuple) and
                    len(v) >= n and
                    all(c.check(v[i]) for i, c in enumerate(self._checks)) and
                    all(self._last.check(elem) for elem in v[n:]))
        else:
            return (isinstance(v, tuple) and
                    len(v) == n and
                    all(c.check(v[i]) for i, c in enumerate(self._checks)))

    def name(self):
        if self._last:
            first = ", ".join(ch.name() for ch in self._checks)
            return "Tuple[" + ", ".join([first, self._last.name(), "..."]) + "]"
        else:
            return "Tuple[" + ", ".join(ch.name() for ch in self._checks) + "]"


class DictChecker(MagicType):
    def __init__(self, kvs):
        self._checks = [(checker_for_type(k), checker_for_type(v))
                        for k, v in kvs.items()]

    def check(self, value):
        return (isinstance(value, dict) and
                all(any(chk.check(k) and chv.check(v)
                        for chk, chv in self._checks)
                    for k, v in value.items()))

    def name(self):
        return "{%s}" % ", ".join("%s: %s" % (chk.name(), chv.name())
                                  for chk, chv in self._checks)



#-------------------------------------------------------------------------------
# Set operations with checkers
#-------------------------------------------------------------------------------

class U(MagicType):
    """
    Union of types.

    We say that ``x`` is of type ``U(type1, ..., typeN)`` if type of ``x`` is
    one of ``type1``, ..., or ``typeN``.
    """

    def __init__(self, *types):
        assert len(types) >= 1
        self._checkers = [checker_for_type(t) for t in types]

    def check(self, var):
        return any(c.check(var) for c in self._checkers)

    def name(self):
        res = [c.name() for c in self._checkers]
        if len(res) == 2 and "None" in res:
            res.remove("None")
            return "?" + res[0]
        else:
            return " | ".join(res)


class I(MagicType):
    """
    Intersection of types.

    We say that ``x`` is of type ``I(type1, ..., typeN)`` if type of ``x`` is
    all of ``type1``, ..., ``typeN``.
    """

    def __init__(self, *types):
        assert len(types) >= 1
        self._checkers = [checker_for_type(t) for t in types]

    def check(self, var):
        return all(c.check(var) for c in self._checkers)

    def name(self):
        return " & ".join(c.name() for c in self._checkers)


class NOT(MagicType):
    """
    Negation of a type.

    This type matches if and only if the variable is *not* of any of the
    provided types.
    """

    def __init__(self, *types):
        assert len(types) >= 1
        self._checkers = [checker_for_type(t) for t in types]

    def check(self, var):
        return not any(c.check(var) for c in self._checkers)

    def name(self):
        if len(self._checkers) > 1:
            return "!(%s)" % " | ".join(ch.name() for ch in self._checkers)
        else:
            return "!" + self._checkers[0].name()


#-------------------------------------------------------------------------------
# Other
#-------------------------------------------------------------------------------

memoized_type_checkers = {
    None: NoneChecker(),
    type(None): NoneChecker(),
    bool: BoolChecker(),
    int: IntChecker(),
    float: FloatChecker(),
    str: StrChecker(),
    Any: Any(),
}

true_checker = LiteralChecker(True)
false_checker = LiteralChecker(False)
