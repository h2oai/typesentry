# -*- encoding: utf-8 -*-
from __future__ import division, print_function

import inspect

from .checks import checker_for_type


class Signature(object):
    """
    Function signature record
    """

    def __init__(self, func, types, typesentry_config):
        self._tc = typesentry_config
        self.function = func
        if hasattr(inspect, "getfullargspec"):
            fspec = inspect.getfullargspec(func)
            # List of positional arguments (both positional-only and
            # positional/keyword arguments)
            self.args = fspec.args
            # List of keyword-only arguments (may be empty, but not None)
            self.kwonlyargs = fspec.kwonlyargs
            # Name of the "*args" argument, or None if there isn't one
            self.varargs = fspec.varargs
            # Name of the "**kws" argument, or None if there isn't one
            self.varkw = fspec.varkw
            # Number of positional arguments without defatuls
            self.num_required_args = len(self.args) - len(fspec.defaults or [])
            # List of keyword-only arguments with no defaults
            self.required_kwonlyargs = list(set(self.kwonlyargs) -
                                            set(fspec.kwonlydefaults or []))
        else:
            fspec = inspect.getargspec(func)
            self.args = fspec.args
            self.kwonlyargs = []
            self.varargs = fspec.varargs
            self.varkw = fspec.keywords
            self.num_required_args = len(self.args) - len(fspec.defaults or [])
            self.required_kwonlyargs = []

        self.retchecker = None
        self.checkers = {}

        self.argindices = {name: i for i, name in enumerate(self.args)}
        self.argsset = set(self.args)
        self.num_self_args = 1 if self.args and self.args[0] == "self" else 0

        # Minimum number of arguments that must be supplied -- all the other
        # have defaults and can be omitted.
        self.min_args = len(self.args) - len(fspec.defaults or [])

        if "_kwless" in types:
            kwless = types.pop("_kwless")
            assert not self.varargs, "_kwless cannot be used with varargs"
            assert isinstance(kwless, int), "_kwless should be an int"
            kwless += self.num_self_args
            assert kwless < len(self.args), \
                "_kwless cannot exceed the number of arguments"
            self.kwonlyargs = self.args[kwless:]
            self.args = self.args[:kwless]
            if kwless < self.num_required_args:
                self.required_kwonlyargs = \
                    set(self.kwonlyargs[:self.num_required_args - kwless])
                self.num_required_args = kwless

        if "_return" in types:
            rettype = types.pop("_return")
            self._retval_checker = checker_for_type(rettype)
        else:
            self._retval_checker = None

        self._create_checkers(types)
        self.retval_checker = self.make_retval_checker()


    @property
    def name_bt(self):
        return "`%s()`" % self.function.__name__


    @property
    def has_no_args(self):
        return (self.varargs is None and self.varkw is None and
                len(self.kwonlyargs) == 0 and
                len(self.args) == self.num_self_args)

    @property
    def has_only_kwargs(self):
        return len(self.args) == self.num_self_args


    def make_args_checker(self):
        """
        Create a function that checks signature of the source function.
        """
        def _checker(*args, **kws):
            # Check if too many arguments are provided
            num_args = len(args)
            if num_args > len(self.args) and not self.varargs:
                raise self._too_many_args_error(num_args)

            # Check if there are too few arguments (without defaults)
            if num_args < self.num_required_args:
                missing = [arg
                           for arg in self.args[num_args:self.num_required_args]
                           if arg not in kws]
                if missing:
                    raise self._too_few_args_error(missing, "positional")

            if self.required_kwonlyargs:
                missing = [k for k in self.required_kwonlyargs if k not in kws]
                if missing:
                    raise self._too_few_args_error(missing, "keyword")

            # Check types of positional arguments
            for i, argvalue in enumerate(args):
                self._check_positional_arg(i, argvalue)

            # Check types of keyword arguments
            for argname, argvalue in kws.items():
                argindex = self.argindices.get(argname)
                if argindex is not None and argindex < num_args:
                    raise self._repeating_arg_error(argname)
                self._check_keyword_arg(argname, argvalue)

        return _checker


    def make_retval_checker(self):
        """Create a function that checks the return value of the function."""
        if self._retval_checker:
            def _checker(retval):
                if not self._retval_checker.check(retval):
                    raise self._tc.TypeError(
                        "Incorrect return type in %s: expected %s got %s" %
                        (self.name_bt, self._retval_checker.name(),
                         checker_for_type(type(retval)).name())
                    )
        else:
            def _checker(retval):
                pass
        return _checker


    def _create_checkers(self, types):
        # TODO: merge with ``make_args_checker()``
        for argname, argtype in types.items():
            checker = checker_for_type(argtype)
            if argname == self.varargs:
                self.checkers["*"] = checker
            elif argname == self.varkw:
                self.checkers["**"] = checker
            else:
                assert argname in self.args or argname in self.kwonlyargs, \
                    "`%s` is not a valid function argument" % argname
                self.checkers[argname] = checker


    def _too_many_args_error(self, num_args):
        s = self.name_bt + " "
        if self.has_no_args:
            s += "doesn't take any arguments"
        elif self.has_only_kwargs:
            s += "accepts only keyword arguments"
        else:
            num_args -= self.num_self_args
            plu1 = "argument" if len(self.args) == 1 else "arguments"
            s += "takes %d positional %s but %d were given" % \
                 (len(self.args), plu1, num_args)
        return self._tc.TypeError(s)


    def _too_few_args_error(self, missing_args, argtype):
        num_missing = len(missing_args)
        assert num_missing > 0
        plural = "argument" if num_missing == 1 else "arguments"
        s = "%s missing %d required %s %s" % \
            (self.name_bt, num_missing, argtype, plural)
        if num_missing == 1:
            s += " `%s`" % missing_args[0]
        else:
            s += ": " + ", ".join("`%s`" % a for a in missing_args[:-1]) + \
                 " and `%s`" % missing_args[-1]
        return self._tc.TypeError(s)


    def _repeating_arg_error(self, arg):
        s = self.name_bt + " got multiple values for argument `%s`" % arg
        return self._tc.TypeError(s)


    def _check_positional_arg(self, index, value):
        if index < len(self.args):
            argname = self.args[index]
            checker = self.checkers.get(argname)
        else:
            assert self.varargs
            argname = "*" + self.varargs
            checker = self.checkers.get("*")
        if checker:
            if not checker.check(value):
                tval = checker_for_type(type(value)).name()
                raise self._tc.TypeError(
                    "Incorrect type for argument `%s`: expected %s got %s" %
                    (argname, checker.name(), tval)
                )


    def _check_keyword_arg(self, name, value):
        checker = (self.checkers.get(name) or
                   self.varkw and self.checkers.get("**"))
        if checker:
            if not checker.check(value):
                tval = checker_for_type(type(value)).name()
                raise self._tc.TypeError(
                    "Incorrect type for argument `%s`: expected %s got %s" %
                    (name, checker.name(), tval)
                )
        else:
            if not self.varkw and name not in self.argsset:
                s = "%s got an unexpected keyword argument `%s`" % \
                    (self.name_bt, name)
                raise self._tc.TypeError(s)
