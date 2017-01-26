#!/usr/bin/env python
# Copyright 2017 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
from __future__ import division, print_function
import builtins
import functools
import re
import sys

import colorama

from typesentry.signature import Signature

__all__ = ("Config", )


class TypeError(builtins.TypeError): pass
class ValueError(builtins.ValueError): pass


class Config(object):
    """
    Usage::

        import typesentry
        typed = typesentry.Config().typed

        @typed(x=int)
        def foo(x):
            print(x)

    """

    def __init__(self, type_error=TypeError, value_error=ValueError,
                 disabled=False):
        """
        Create new type-checking configuration.

        :param type_error: exception class that should be used when a type
            error occurs. It is recommended that this class derives from the
            standard ``TypeError``.
        :param value_error: exception class that should be used when a value
            error occurs. It is recommended that this class derives from the
            standard ``ValueError``.
        :param bool disabled: if True, then all type-checking will be disabled.
        """
        self.TypeError = type_error
        self.ValueError = value_error
        self.typed = self._make_typed(disabled)
        self._install_exception_hooks()


    #---------------------------------------------------------------------------
    # Private
    #---------------------------------------------------------------------------

    def _install_exception_hooks(self):
        previous_except_hook = sys.excepthook

        def except_hook(exc_type, exc_value, exc_tb):
            if isinstance(exc_value, (self.TypeError, self.ValueError)):
                self._handle_tc_error(exc_type, exc_value, exc_tb)
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
                @functools.wraps(f)
                def fdecorated(*args, **kws):
                    fdecorated._args_checker(*args, **kws)
                    return f(*args, **kws)

                fdecorated._args_checker = self._make_args_checker(f, types)
                return fdecorated

            return prepared_decorator

        return typed


    def _make_args_checker(self, func, types):
        """
        Create a function that checks signature of ``func`` according to
        type-spec ``types``.

        :param func: function whose signature will be checked.
        :param types: dictionary of type specifications.
        """
        sig = Signature(func, types)

        def _checker(*args, **kws):
            # Check if too many arguments are provided
            num_args = len(args)
            if num_args > sig.max_positional_args:
                raise self._too_many_args_error(num_args, sig)

            # Check if there are too few arguments (without defaults)
            if num_args < sig.min_args:
                missing = [arg
                           for arg in sig.argnames[num_args:sig.min_args]
                           if arg not in kws]
                if missing:
                    raise self._too_few_args_error(missing, sig)

            # Check types of positional arguments
            for i, argvalue in enumerate(args):
                self._check_positional_arg(sig, i, argvalue)

            # Check types of keyword arguments
            for argname, argvalue in kws.items():
                argindex = sig.argindices.get(argname)
                if argindex is not None and argindex < num_args:
                    raise self._repeating_arg_error(argname, sig)
                self._check_keyword_arg(sig, argname, argvalue)

        return _checker


    def _too_many_args_error(self, num_args, sig):
        assert num_args > sig.max_positional_args
        s = sig.name_bt + " "
        if sig.has_no_args:
            s += "doesn't take any arguments"
        elif sig.has_only_kwargs:
            s += "accepts only keyword arguments"
        else:
            num_args -= sig.num_self_args
            plu1 = "argument" if sig.max_positional_args == 1 else "arguments"
            plu2 = "was" if num_args == 1 else "were"
            s += "takes %d positional %s but %d %s given" % \
                 (sig.max_positional_args, plu1, num_args, plu2)
        return self.TypeError(s)


    def _too_few_args_error(self, missing_args, sig):
        num_missing = len(missing_args)
        assert num_missing > 0
        plural = "argument" if num_missing == 1 else "arguments"
        s = "%s missing %d required positional %s" % \
            (sig.name_bt, num_missing, plural)
        if num_missing == 1:
            s += " `%s`" % missing_args[0]
        else:
            s += ": " + ", ".join("`%s`" % a for a in missing_args[:-1]) + \
                 " and `%s`" % missing_args[-1]
        return self.TypeError(s)


    def _repeating_arg_error(self, arg, sig):
        s = sig.name_bt + " got multiple values for argument `%s`" % arg
        return self.TypeError(s)


    def _check_positional_arg(self, sig, index, value):
        if index < len(sig.argnames):
            checker = sig.checkers.get(sig.argnames[index])
        else:
            assert sig.vararg
            checker = sig.checkers.get("*")
        if checker:
            if not checker.check(value):
                raise self.TypeError(
                    "Incorrect type for argument `%s`: expected %s got %r" %
                    (sig.argnames[index], checker.name(), type(value))
                )


    def _check_keyword_arg(self, sig, name, value):
        checker = (sig.checkers.get(name) or
                   sig.varkws and sig.checkers.get("**"))
        if checker:
            if not checker.check(value):
                raise self.TypeError(
                    "Incorrect type for argument `%s`: expected %s got %r" %
                    (name, checker.name(), type(value))
                )
        elif not sig.varkws:
            s = "%s got an unexpected keyword argument `%s`" % \
                (sig.name_bt, name)
            raise self.TypeError(s)


    def _handle_tc_error(self, exc_type, exc_value, exc_tb):
        white = colorama.Fore.WHITE + colorama.Style.BRIGHT
        darkred = colorama.Fore.RED
        red = colorama.Fore.LIGHTRED_EX + colorama.Style.NORMAL
        reset = colorama.Style.RESET_ALL

        msg = darkred + exc_type.__name__ + ": " + red + \
            re.sub(r"`([^`]*)`", white + "\\1" + red, str(exc_value)) + \
            "\n" + reset
        print(msg, file=sys.stderr)
