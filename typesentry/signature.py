# -*- encoding: utf-8 -*-
from __future__ import division, print_function

import inspect

from .checks import checker_for_type


class Signature(object):
    """
    Function signature record
    """

    def __init__(self, f, types):
        fspec = inspect.getargspec(f)
        self.function = f
        self.vararg = fspec.varargs
        self.varkws = fspec.keywords
        self.argnames = tuple(fspec.args)
        self.argindices = {name: i for i, name in enumerate(fspec.args)}
        self.num_self_args = 1 if fspec.args and fspec.args[0] == "self" else 0
        self.retchecker = None
        self.checkers = {}

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
            self.retchecker = checker_for_type(rettype)

        self._create_checkers(types)


    @property
    def name(self):
        return self.function.__name__


    @property
    def name_bt(self):
        return "`%s()`" % self.name


    @property
    def has_self_arg(self):
        return self.argnames and self.argnames[0] == "self"


    @property
    def has_no_args(self):
        return (self.vararg is None and self.varkws is None and
                len(self.argnames) == self.num_self_args)

    @property
    def has_only_kwargs(self):
        return self.max_positional_args == self.num_self_args


    def _create_checkers(self, types):
        for argname, argtype in types.items():
            if argname == "_kwless": continue
            checker = checker_for_type(argtype)
            if argname == self.vararg:
                self.checkers["*"] = checker
            elif argname == self.varkws:
                self.checkers["**"] = checker
            else:
                assert argname in self.argnames, \
                    "`%s` is not a valid function argument" % argname
                self.checkers[argname] = checker
