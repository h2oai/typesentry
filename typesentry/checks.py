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
    _str_type = str
    _int_type = int
    _num_type = (int, float)
    _primitive_type = (str, int, float, bool, bytes)

try:
    import typing
except ImportError:
    typing = None



def checker_for_type(t):
    """
    Return "checker" function for the given type `t`.

    This checker function will accept a single argument (of any type), and
    return True if the argument matches type `t`, or False otherwise. For
    example:

        chkr = checker_for_type(int)
        assert chkr.check(123) is True
        assert chkr.check("5") is False
    """
    try:
        if t is True: return true_checker
        if t is False: return false_checker
        checker = memoized_type_checkers.get(t)
        if checker is not None:
            return checker
        hashable = True
    except TypeError:
        # Exception may be raised if `t` is not hashable (e.g. a dict)
        hashable = False

    # The type checker needs to be created
    checker = _create_checker_for_type(t)
    if hashable:
        memoized_type_checkers[t] = checker
    return checker


def _create_checker_for_type(t):
    if isinstance(t, _primitive_type):
        return MtLiteral(t)
    if isinstance(t, MagicType):
        return t
    if isinstance(t, type):
        if issubclass(t, MagicType):
            return t()
        if typing:
            if issubclass(t, typing.List) and t is not list:
                itemtype = t.__args__ and t.__args__[0]
                if itemtype and itemtype is not typing.Any:
                    return MtList(itemtype)
                else:
                    return MtClass(list, name="List")
            if issubclass(t, typing.Dict) and t is not dict:
                if t.__args__:
                    key, value = t.__args__
                    return checker_for_type({key: value})
                else:
                    return MtClass(dict)
            if issubclass(t, typing.Tuple) and t is not tuple:
                tlen = len(t.__tuple_params__)
                if t.__tuple_use_ellipsis__:
                    assert tlen == 1
                    return MtTuple(t.__tuple_params__[0], Ellipsis)
                else:
                    return MtTuple(*t.__tuple_params__)
            if issubclass(t, typing.Set) and t is not set:
                itemtype = t.__args__ and t.__args__[0]
                if itemtype and itemtype is not typing.Any:
                    return MtSet(itemtype)
                else:
                    return MtClass(set, name="Set")

        # `t` is a name of the class, or a built-in type such as
        # `list, `tuple`, etc
        return MtClass(t)
    if typing:
        if t is typing.Any:
            return MtAny()
        if type(t) is type(typing.Union):  # flake8: disable=E721
            try:
                return U(*t.__union_params__)
            except AttributeError:
                return U(*t.__args__)
    if isinstance(t, list):
        # `t` is a list literal, such as [int, str]
        return MtList(U(*t))
    if isinstance(t, set):
        return MtSet(U(*t))
    if isinstance(t, tuple):
        return MtTuple(*t)
    if isinstance(t, dict):
        return MtDict(t)
    raise RuntimeError("Unknown type %r for type-checker" % t)



# ------------------------------------------------------------------------------
# Basic types
# ------------------------------------------------------------------------------

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
        return int(self.check(var))

    def get_error_msg(self, paramname, value):
        """
        Return message for the type error that should be emitted when the
        `value` fails typecheck for this type.

        The base class has reasonably good implementation of this method, so
        subclasses are not required to override it. However sometimes a class
        may implement this method in order to show custom error messages
        (especially related to fuzzy checking).

        :param paramname: "full" name of the parameter that holds the value;
            this will look either like "Parameter `foo`", or "Vararg parameter"
        :param value: the value that failed typecheck. The class may assume
            that this value is such that `self.check(value) is False`.
        :returns: a string containing error message for a TypeError exception.
        """
        return ("%s of type `%s` received value %s"
                % (paramname, self.name(), _prepare_value(value)))



class MtAny(MagicType):
    def check(self, v):
        return True

    def name(self):
        return "Any"


class MtClass(MagicType):
    def __init__(self, cls, name=None):
        self._cls = cls
        self._name = name or cls.__name__

    def check(self, v):
        return isinstance(v, self._cls)

    def name(self):
        return self._name



#-------------------------------------------------------------------------------
# Checkers for primitive types
#-------------------------------------------------------------------------------

class MtNone(MagicType):
    def check(self, v):
        return v is None

    def name(self):
        return "None"


class MtBool(MagicType):
    def check(self, v):
        return v is True or v is False

    def name(self):
        return "bool"


class MtInt(MagicType):
    def check(self, v):
        return isinstance(v, _int_type) and v is not True and v is not False

    def name(self):
        return "int"


class MtFloat(MagicType):
    """
    Float type has the semantic of "numeric", i.e. it maches both floats and
    integers (see PEP-0484).
    """
    def check(self, v):
        return isinstance(v, _num_type) and not isinstance(v, bool)

    def name(self):
        return "float"


class MtStr(MagicType):
    """
    On Python2 we treat both `str` and `unicode` as matching this type; on
    Python3 only `str` (not `bytes`) match this type.
    """
    def check(self, v):
        return isinstance(v, _str_type)

    def name(self):
        return "str"


class MtLiteral(MagicType):
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

class MtList(MagicType):
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

    def get_error_msg(self, paramname, value):
        if isinstance(value, list):
            elemchecker = self._elem.check
            ibad = -1
            for i, x in enumerate(value):
                if not elemchecker(x):
                    ibad = i + 1
                    break
            nth = ("%dst" if (ibad % 10 == 1 and ibad % 100 != 11) else
                   "%dnd" if (ibad % 10 == 2 and ibad % 100 != 12) else
                   "%drd" if (ibad % 10 == 3 and ibad % 100 != 13) else
                   "%dth") % ibad
            sval = _prepare_value(value[ibad - 1])
            return ("%s of type `%s` received a list where %s element is %s"
                    % (paramname, self.name(), nth, sval))
        else:
            return super(MtList, self).get_error_msg(paramname, value)



class MtSet(MagicType):
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



class MtTuple(MagicType):
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


class MtDict(MagicType):
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
    None: MtNone(),
    type(None): MtNone(),
    bool: MtBool(),
    int: MtInt(),
    float: MtFloat(),
    str: MtStr(),
}

true_checker = MtLiteral(True)
false_checker = MtLiteral(False)


def _prepare_value(val, maxlen=50):
    """
    Stringify value `val`, ensuring that it is not too long.
    """
    if val is None or val is True or val is False:
        return str(val)
    sval = repr(val)
    sval = sval.replace("\n", " ").replace("\t", " ").replace("`", "'")
    if len(sval) > maxlen:
        sval = sval[:maxlen - 4] + "..." + sval[-1]
    tval = checker_for_type(type(val)).name()
    return "%s of type %s" % (sval, tval)
