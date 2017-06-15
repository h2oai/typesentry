#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
from __future__ import division, print_function
import functools
import re
import sys

import colorama

from typesentry.checks import checker_for_type, U
from typesentry.signature import Signature

__all__ = ("Config", )


# Derive from the builtin TypeError
class TsTypeError(TypeError):
    def _handle_(self):
        _handle_tc_error(self)


# Derive from the builtin ValueError
class TsValueError(ValueError):
    def _handle_(self):
        _handle_tc_error(self)


TsTypeError.__name__ = "TypeError"
TsValueError.__name__ = "ValueError"



class Config(object):
    """
    Usage::

        import typesentry
        typed = typesentry.Config().typed

        @typed(x=int)
        def foo(x):
            print(x)

    """

    def __init__(self, type_error=TsTypeError, value_error=TsValueError,
                 disabled=False, soft_exceptions=True):
        """
        Create new type-checking configuration.

        :param type_error: exception class that should be used when a type
            error occurs. It is recommended that this class derives from the
            standard ``TypeError``.
        :param value_error: exception class that should be used when a value
            error occurs. It is recommended that this class derives from the
            standard ``ValueError``.
        :param disabled: if True, then all type-checking will be disabled.
        :param soft_exceptions: if True, then a custom exceptions handler will
            be installed at the console level, which will catch any exception
            with method ``._handle_()`` and use that method to report the
            error.
        """
        self.TypeError = type_error
        self.ValueError = value_error
        self.typed = self._make_typed(disabled)
        if soft_exceptions:
            assert callable(getattr(type_error, "_handle_")), \
                "Class %s missing method ._handle_()" % type_error.__name__
            assert callable(getattr(value_error, "_handle_")), \
                "Class %s missing method ._handle_()" % value_error.__name__
            self._install_exception_hooks()


    @staticmethod
    def is_type(value, *types):
        if len(types) == 1:
            checker = checker_for_type(types[0])
        else:
            checker = checker_for_type(U(*types))
        return checker.check(value)


    @staticmethod
    def name_type(*types):
        if len(types) == 1:
            checker = checker_for_type(types[0])
        else:
            checker = checker_for_type(U(*types))
        return checker.name()


    #---------------------------------------------------------------------------
    # Private
    #---------------------------------------------------------------------------

    def _install_exception_hooks(self):
        previous_except_hook = sys.excepthook

        def except_hook(exc_type, exc_value, exc_tb):  # pragma: no cover
            # This function cannot be tested, becauses it can only be executed
            # by the Python's console
            if hasattr(exc_value, "_handle_"):
                exc_value._handle_()
            else:
                previous_except_hook(exc_type, exc_value, exc_tb)

        sys.excepthook = except_hook


    def _make_typed(self, disabled):
        if disabled:
            # Return a factory producing noop decorators
            return lambda **types: lambda f: f

        def typed(**types):
            """
            Decorator that can be used to declare a function's type signature.

            Example::

                @typed(x=int, msg=Optional[str])
                def foo(x, msg=None):
                    pass
            """
            # `typed(...)` is called as a decorator factory, and therefore must
            # return a decorator object.
            def prepared_decorator(f):
                sig = Signature(f, types, self)
                check_params = sig.params_checker
                check_retval = sig.return_checker

                @functools.wraps(f)
                def fdecorated(*args, **kws):
                    check_params(*args, **kws)
                    ret = f(*args, **kws)
                    check_retval(ret)
                    return ret

                fdecorated._signature_ = sig
                return fdecorated

            return prepared_decorator

        return typed



def _handle_tc_error(exc):
    white = colorama.Fore.WHITE + colorama.Style.BRIGHT
    darkred = colorama.Fore.RED
    red = colorama.Fore.LIGHTRED_EX + colorama.Style.NORMAL
    reset = colorama.Style.RESET_ALL

    msg = darkred + exc.__class__.__name__ + ": " + red + \
        re.sub(r"`([^`]*)`", white + "\\1" + red, str(exc)) + \
        "\n" + reset
    print(msg, file=sys.stderr)
