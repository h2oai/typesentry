#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
from __future__ import division, print_function

import sys
import re


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
    need_to_fix_typing = hasattr(typing.Union[int], "__union_params__")
except ImportError:  # pragma: no cover
    typing = None
    need_to_fix_typing = False



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
        if t is True:
            return true_checker
        if t is False:
            return false_checker
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
    if need_to_fix_typing:  # pragma: no cover
        if hasattr(t, "__union_params__"):
            t.__args__ = t.__union_params__
        if hasattr(t, "__tuple_params__"):
            t.__args__ = t.__tuple_params__
            if t.__tuple_use_ellipsis__:
                t.__args__ += (Ellipsis, )
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
                    if key is not typing.Any and value is not typing.Any:
                        return MtDict0(key, value)
                return MtClass(dict, name="Dict")
            if issubclass(t, typing.Tuple) and t is not tuple:
                if t.__args__:
                    if len(t.__args__) == 2 and t.__args__[1] is Ellipsis:
                        return MtTuple0(t.__args__[0])
                    else:
                        return MtTuple1(*t.__args__)
                else:
                    return MtClass(tuple, name="Tuple")
            if issubclass(t, typing.Set) and t is not set:
                itemtype = t.__args__ and t.__args__[0]
                if itemtype and itemtype is not typing.Any:
                    return MtSet(itemtype)
                else:
                    return MtClass(set, name="Set")
            if issubclass(t, typing.Callable) and \
                    str(t).startswith("typing.Callable"):
                return MtCallable(t.__args__)
            # This is somewhat ugly, but I do not know a better way to check
            # that something is constructed from Type.
            if str(t) == "typing.Type" or str(t).startswith("typing.Type["):
                cls = t.__args__ and t.__args__[0]
                if cls and cls is not typing.Any:
                    return MtType(cls)
                else:
                    return MtClass(type, name="Type")

        # `t` is a name of the class, or a built-in type such as
        # `list, `tuple`, etc
        return MtClass(t)
    if typing:
        if t is typing.Any:
            return MtAny()
        if type(t) is type(typing.Union):  # flake8: disable=E721
            return MtUnion(*t.__args__)
    if isinstance(t, list):
        # `t` is a list literal, such as [int, str]
        assert len(t)
        return MtList(MtUnion(*t) if len(t) > 1 else t[0])
    if isinstance(t, set):
        assert len(t) > 0
        return MtSet(MtUnion(*t) if len(t) > 1 else list(t)[0])
    if isinstance(t, tuple):
        if len(t) == 2 and t[1] is Ellipsis:
            return MtTuple0(t[0])
        else:
            return MtTuple1(*t)
    if isinstance(t, dict):
        if len(t.keys()) == 1:
            key, val = list(t.items())[0]
            if not isinstance(key, str):
                return MtDict0(key, val)
        return MtDict1(t)
    raise RuntimeError("Unknown type %r for type-checker" % t)


# ------------------------------------------------------------------------------
#
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


# ------------------------------------------------------------------------------
#
# Checkers for primitive types
# ------------------------------------------------------------------------------

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
            if s[0] == "u":
                # Python2 stringifies unicode strings as "u'something'", so
                # we want to remove that prefix
                s = s[1:]
            s = s[1:-1].replace('"', '\\"')
            return '"%s"' % s
        else:
            return str(self.literal)


# ------------------------------------------------------------------------------
#
# Checkers for collection types
# ------------------------------------------------------------------------------

class MtList(MagicType):
    """
    MagicType corresponding to `List[T]`.

    This type constructs special error message in the case it is matched against
    a list where some of the elements are `T` while others are not `T`.
    """

    def __init__(self, elem_type):
        self._elem = checker_for_type(elem_type)

    def check(self, v):
        c = self._elem
        return isinstance(v, list) and all(c.check(x) for x in v)

    def name(self):
        return "List[%s]" % self._elem.name()

    def fuzzycheck(self, value):
        if not isinstance(value, list):
            return 0
        chk = self._elem.fuzzycheck
        return sum(chk(x) for x in value) / len(value)

    def get_error_msg(self, paramname, value):
        if isinstance(value, list):
            elemchecker = self._elem.check
            for i, x in enumerate(value):
                if not elemchecker(x):
                    nth = _nth_str(i + 1)
                    sval = _prepare_value(x)
                    return ("%s of type `%s` received a list where %s element "
                            "is %s" % (paramname, self.name(), nth, sval))
        return MagicType.get_error_msg(self, paramname, value)



class MtSet(MagicType):
    def __init__(self, elem_type):
        self._elem = checker_for_type(elem_type)

    def check(self, v):
        chk = self._elem.check
        return isinstance(v, set) and all(chk(x) for x in v)

    def name(self):
        return "Set[%s]" % self._elem.name()

    def fuzzycheck(self, value):
        if not isinstance(value, set):
            return 0
        chk = self._elem.fuzzycheck
        return sum(chk(x) for x in value) / len(value)

    def get_error_msg(self, paramname, value):
        if isinstance(value, set):
            elemchecker = self._elem.check
            for x in value:
                if not elemchecker(x):
                    sval = _prepare_value(x)
                    return ("%s of type `%s` received set containing an "
                            "element %s" % (paramname, self.name(), sval))
        return MagicType.get_error_msg(self, paramname, value)



class MtTuple1(MagicType):
    """
    MagicType corresponding to `Tuple[T1, ..., Tn]` (tuple with fixed
    number of entries). For a tuple with variable number of entries, see
    :class:`MtTuple0`.
    """

    def __init__(self, *items):
        self._checks = [checker_for_type(t) for t in items]

    def check(self, v):
        return (isinstance(v, tuple) and
                len(v) == len(self._checks) and
                all(c.check(v[i]) for i, c in enumerate(self._checks)))

    def fuzzycheck(self, value):
        if not isinstance(value, tuple):
            return 0
        maxlen = max(len(value), len(self._checks))
        minlen = min(len(value), len(self._checks))
        return sum(self._checks[i].fuzzycheck(value[i])
                   for i in range(minlen)) / maxlen

    def name(self):
        return "Tuple[%s]" % ", ".join(ch.name() for ch in self._checks)

    def get_error_msg(self, paramname, value):
        if isinstance(value, tuple):
            if len(value) != len(self._checks):
                return ("%s of type `%s` received a tuple of length %d, "
                        "whereas length %d was expected"
                        % (paramname, self.name(), len(value),
                           len(self._checks)))
            for i, chk in enumerate(self._checks):
                if not chk.check(value[i]):
                    sval = _prepare_value(value[i])
                    return ("%s of type `%s` received a tuple where %s element "
                            "is %s"
                            % (paramname, self.name(), _nth_str(i + 1), sval))
        return MagicType.get_error_msg(self, paramname, value)



class MtTuple0(MagicType):
    """
    MagicType corresponding to `Tuple[T, ...]`.

    This type constructs special error message in the case it is matched against
    a tuple where some of the elements are `T` while others are not `T`.
    """

    def __init__(self, elem_type):
        self._elem = checker_for_type(elem_type)

    def check(self, v):
        c = self._elem
        return isinstance(v, tuple) and all(c.check(x) for x in v)

    def name(self):
        return "Tuple[%s, ...]" % self._elem.name()

    def fuzzycheck(self, value):
        if not isinstance(value, tuple):
            return 0
        chk = self._elem.fuzzycheck
        return sum(chk(x) for x in value) / len(value)

    def get_error_msg(self, paramname, value):
        if isinstance(value, tuple):
            elemchecker = self._elem.check
            ibad = -1
            for i, x in enumerate(value):
                if not elemchecker(x):
                    ibad = i + 1
                    break
            nth = _nth_str(ibad)
            sval = _prepare_value(value[ibad - 1])
            return ("%s of type `%s` received a tuple where %s element is %s"
                    % (paramname, self.name(), nth, sval))
        else:
            return MagicType.get_error_msg(self, paramname, value)



class MtDict1(MagicType):
    """
    MagicType corresponding to type declaration `{k1: v1, ..., kn: vn}`. Here
    keys must be string literals (additionally, key `...` is also accepted,
    which matches any key other than those given explicitly).
    """

    def __init__(self, kvs):
        self._checks = {}
        self._anycheck = None
        for k, v in kvs.items():
            if k is Ellipsis:
                self._anycheck = checker_for_type(v)
                continue
            if not isinstance(k, str):
                raise RuntimeError("Keys in the dict literal must be string "
                                   "constants: %r" % kvs)
            self._checks[k] = checker_for_type(v)

    def check(self, value):
        return (isinstance(value, dict) and
                all(k in self._checks and self._checks[k].check(v) or
                    self._anycheck and self._anycheck.check(v)
                    for k, v in value.items()))

    def fuzzycheck(self, value):
        if not isinstance(value, dict):
            return 0
        total = 0
        for k, v in value.items():
            checker = self._checks.get(k, self._anycheck)
            if checker:
                total += checker.fuzzycheck(v)
        return total / len(value)

    def name(self):
        fields0 = ", ".join("%r: %s" % (k, v.name())
                            for k, v in self._checks.items())
        if self._anycheck:
            fields0 += ", ...: %s" % self._anycheck.name()
        return "{%s}" % fields0

    def get_error_msg(self, paramname, value):
        if isinstance(value, dict):
            for k, v in value.items():
                checker = self._checks.get(k, self._anycheck)
                if checker:
                    if not checker.check(v):
                        vval = _prepare_value(v)
                        return ("%s of type `%s` received a dict where key %r "
                                "had value %s"
                                % (paramname, self.name(), k, vval))
                else:
                    return ("%s of type `%s` received a dict with an unknown "
                            "key %r" % (paramname, self.name(), k))
            raise RuntimeError("Value %r satisfies %r" %  # pragma: no cover
                               (value, self.name()))
        else:
            return super(MtDict1, self).get_error_msg(paramname, value)



class MtDict0(MagicType):
    """
    MagicType for `Dict[Tk, Tv]` from the typing module. Alternatively, this
    type can also be declared using a dict literal: `{Tk: Tv}`. The primary
    difference from :class:`MtDict1` is that this class allows typed keys and
    values, but does not allow different types for values depending on the type
    of the key.
    """

    def __init__(self, key, val):
        self._key = checker_for_type(key)
        self._val = checker_for_type(val)

    def check(self, value):
        kchk = self._key.check
        vchk = self._val.check
        return (isinstance(value, dict) and
                all(kchk(k) and vchk(v) for k, v in value.items()))

    def fuzzycheck(self, value):
        if not isinstance(value, dict):
            return 0
        kchk = self._key.fuzzycheck
        vchk = self._val.fuzzycheck
        return sum(kchk(k) * vchk(v) for k, v in value.items()) / len(value)

    def name(self):
        return "Dict[%s, %s]" % (self._key.name(), self._val.name())

    def get_error_msg(self, paramname, value):
        if isinstance(value, dict):
            kchk = self._key.check
            vchk = self._val.check
            for k, v in value.items():
                if not kchk(k) or not vchk(v):
                    kval = _prepare_value(k, notype=True)
                    vval = _prepare_value(v, notype=True)
                    return ("%s of type `%s` received a dict with a key-value "
                            "pair {%s: %s}"
                            % (paramname, self.name(), kval, vval))
            raise RuntimeError("Value %r satisfies %r" %  # pragma: no cover
                               (value, self.name()))
        else:
            return super(MtDict0, self).get_error_msg(paramname, value)


class MtType(MagicType):

    def __init__(self, cls):
        assert isinstance(cls, type)
        self._cls = cls

    def check(self, val):
        return isinstance(val, type) and issubclass(val, self._cls)

    def name(self):
        return "Type[%s]" % self._cls.__name__

    def get_error_msg(self, paramname, value):
        if isinstance(value, type):
            return ("%s of type `%s` received class %s which is not a subclass "
                    "of %s"
                    % (paramname, self.name(), value.__name__,
                       self._cls.__name__))
        else:
            return super(MtType, self).get_error_msg(paramname, value)


class MtCallable(MagicType):
    def __init__(self, args):
        self._args = args

    def check(self, val):
        return callable(val) and (self._args is None or
                                  self._args[0] is Ellipsis or
                                  len(self._args) - 1 ==
                                  val.__code__.co_argcount)

    def name(self):
        if self._args is None:
            return "Callable"
        elif self._args[0] is Ellipsis:
            return "Callable[..., %s]" % checker_for_type(self._args[1]).name()
        else:
            return "Callable[[%s], %s]" % (
                ", ".join(checker_for_type(z).name() for z in self._args[:-1]),
                checker_for_type(self._args[-1]).name())



# ------------------------------------------------------------------------------
#
# Set operations with checkers
# ------------------------------------------------------------------------------

class MtUnion(MagicType):
    """
    Union of types.

    We say that ``x`` is of type ``U(type1, ..., typeN)`` if type of ``x`` is
    one of ``type1``, ..., or ``typeN``.

    Construction of error message for this type relies on the "fuzzy-checking"
    mechanism. In particular we find the best fuzzy-matched type among all
    constituent types of the union, and use that element's error message. For
    example, if type T is a union `Union[int, str, List[int], List[str]]` and
    the value `[0, 1, "a"]` is supplied, then the error message will be
    displayed as if T was `List[int]`.
    """

    def __init__(self, *types):
        if len(types) <= 1:
            raise RuntimeError("More than one type is expected for Union "
                               "constructor: %r" % types)
        self._checkers = [checker_for_type(t) for t in types]

    def check(self, var):
        return any(c.check(var) for c in self._checkers)

    def fuzzycheck(self, v):
        return max(c.fuzzycheck(v) for c in self._checkers)

    def name(self):
        res = [c.name() for c in self._checkers]
        if len(res) == 2 and "None" in res:
            return "Optional[%s]" % (res[0] if res[1] == "None" else res[1])
        else:
            return "Union[%s]" % ", ".join(res)

    def get_error_msg(self, paramname, value):
        best = max(self._checkers, key=lambda c: c.fuzzycheck(value))
        bestscore = best.fuzzycheck(value)
        if bestscore > 0:
            msg = best.get_error_msg(paramname, value)
            # Slightly modify the message, to hint that the provided type is not
            # THE type of the argument, but just one of its possible types
            mm = re.match(r"^(.*) of type (`[^`]+`) received ?a? ?(.*)$", msg)
            if mm:
                msg = "%s expects type %s but received a %s" % mm.groups()
            return msg
        else:
            return super(MtUnion, self).get_error_msg(paramname, value)



class MtIntersection(MagicType):
    """
    Intersection of types.

    We say that ``x`` is of type ``I(type1, ..., typeN)`` if type of ``x`` is
    all of ``type1``, ..., ``typeN``.
    """

    def __init__(self, *types):
        if len(types) <= 1:
            raise RuntimeError("More than one type is expected for Intersection"
                               " constructor: %r" % types)
        self._checkers = [checker_for_type(t) for t in types]

    def check(self, var):
        return all(c.check(var) for c in self._checkers)

    def name(self):
        return "Intersection[%s]" % ", ".join(c.name() for c in self._checkers)


class MtNot(MagicType):
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
        return "Not[%s]" % ", ".join(ch.name() for ch in self._checkers)


# ------------------------------------------------------------------------------
#
# Other
# ------------------------------------------------------------------------------

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


def _prepare_value(val, maxlen=50, notype=False):
    """
    Stringify value `val`, ensuring that it is not too long.
    """
    if val is None or val is True or val is False:
        return str(val)
    sval = repr(val)
    sval = sval.replace("\n", " ").replace("\t", " ").replace("`", "'")
    if len(sval) > maxlen:
        sval = sval[:maxlen - 4] + "..." + sval[-1]
    if notype:
        return sval
    else:
        tval = checker_for_type(type(val)).name()
        return "%s of type %s" % (sval, tval)

def _nth_str(n):
    """Return posessive form of numeral `n`: 1st, 2nd, 3rd, etc."""
    if n % 10 == 1 and n % 100 != 11:
        return "%dst" % n
    if n % 10 == 2 and n % 100 != 12:
        return "%dnd" % n
    if n % 10 == 3 and n % 100 != 13:
        return "%drd" % n
    return "%dth" % n
