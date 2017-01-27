# -*- encoding: utf-8 -*-
from __future__ import division, print_function

import inspect

from .checks import checker_for_type


class Signature(object):
    """
    Function signature record
    """

    def __init__(self, f, types, config):
        self.tc_config = config
        fspec = inspect.getargspec(f)
        self.function = f
        self.vararg = fspec.varargs
        self.varkws = fspec.keywords
        self.argnames = tuple(fspec.args)
        self.argindices = {name: i for i, name in enumerate(fspec.args)}
        self.num_self_args = 1 if fspec.args and fspec.args[0] == "self" else 0
        self.retchecker = None
        self.checkers = {}
        self.argsset = set(fspec.args)

        # Minimum number of arguments that must be supplied -- all the other
        # have defaults and can be omitted.
        self.min_args = len(fspec.args) - len(fspec.defaults or [])

        # Maximum number of args that can be supplied positionally (i.e. without
        # a name).
        self.max_positional_args = 65536 if self.vararg else len(fspec.args)

        if "_kwless" in types:
            kwless = types.pop("_kwless")
            assert not self.vararg, "_kwless cannot be used with varargs"
            assert isinstance(kwless, int), "_kwless should be an int"
            kwless += self.num_self_args
            assert kwless < len(self.argnames), \
                "_kwless cannot exceed the number of arguments"
            self.max_positional_args = kwless

        if "_return" in types:
            rettype = types.pop("_return")
            self._retval_checker = checker_for_type(rettype)
        else:
            self._retval_checker = None

        self._create_checkers(types)
        self.retval_checker = self.make_retval_checker()


    @property
    def name(self):
        return self.function.__name__


    @property
    def name_bt(self):
        return "`%s()`" % self.name


    @property
    def has_no_args(self):
        return (self.vararg is None and self.varkws is None and
                len(self.argnames) == self.num_self_args)

    @property
    def has_only_kwargs(self):
        return self.max_positional_args == self.num_self_args


    def make_args_checker(self):
        """
        Create a function that checks signature of the function.
        """
        def _checker(*args, **kws):
            # Check if too many arguments are provided
            num_args = len(args)
            if num_args > self.max_positional_args:
                raise self._too_many_args_error(num_args)

            # Check if there are too few arguments (without defaults)
            if num_args < self.min_args:
                missing = [arg
                           for arg in self.argnames[num_args:self.min_args]
                           if arg not in kws]
                if missing:
                    raise self._too_few_args_error(missing)

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
                    raise self.tc_config.TypeError(
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
            if argname == self.vararg:
                self.checkers["*"] = checker
            elif argname == self.varkws:
                self.checkers["**"] = checker
            else:
                assert argname in self.argnames, \
                    "`%s` is not a valid function argument" % argname
                self.checkers[argname] = checker


    def _too_many_args_error(self, num_args):
        assert num_args > self.max_positional_args
        s = self.name_bt + " "
        if self.has_no_args:
            s += "doesn't take any arguments"
        elif self.has_only_kwargs:
            s += "accepts only keyword arguments"
        else:
            num_args -= self.num_self_args
            plu1 = "argument" if self.max_positional_args == 1 else "arguments"
            s += "takes %d positional %s but %d were given" % \
                 (self.max_positional_args, plu1, num_args)
        return self.tc_config.TypeError(s)


    def _too_few_args_error(self, missing_args):
        num_missing = len(missing_args)
        assert num_missing > 0
        plural = "argument" if num_missing == 1 else "arguments"
        s = "%s missing %d required positional %s" % \
            (self.name_bt, num_missing, plural)
        if num_missing == 1:
            s += " `%s`" % missing_args[0]
        else:
            s += ": " + ", ".join("`%s`" % a for a in missing_args[:-1]) + \
                 " and `%s`" % missing_args[-1]
        return self.tc_config.TypeError(s)


    def _repeating_arg_error(self, arg):
        s = self.name_bt + " got multiple values for argument `%s`" % arg
        return self.tc_config.TypeError(s)


    def _check_positional_arg(self, index, value):
        if index < len(self.argnames):
            argname = self.argnames[index]
            checker = self.checkers.get(argname)
        else:
            assert self.vararg
            argname = "*" + self.vararg
            checker = self.checkers.get("*")
        if checker:
            if not checker.check(value):
                tval = checker_for_type(type(value)).name()
                raise self.tc_config.TypeError(
                    "Incorrect type for argument `%s`: expected %s got %s" %
                    (argname, checker.name(), tval)
                )


    def _check_keyword_arg(self, name, value):
        checker = (self.checkers.get(name) or
                   self.varkws and self.checkers.get("**"))
        if checker:
            if not checker.check(value):
                tval = checker_for_type(type(value)).name()
                raise self.tc_config.TypeError(
                    "Incorrect type for argument `%s`: expected %s got %s" %
                    (name, checker.name(), tval)
                )
        else:
            if not self.varkws and name not in self.argsset:
                s = "%s got an unexpected keyword argument `%s`" % \
                    (self.name_bt, name)
                raise self.tc_config.TypeError(s)
