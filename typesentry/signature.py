# -*- encoding: utf-8 -*-
from __future__ import division, print_function

import inspect

from .checks import checker_for_type


class Signature(object):
    """
    Function signature record.
    """

    def __init__(self, func, types, typesentry_config):
        # The Config object
        self._tc = typesentry_config

        # The original function that was inspected
        self.function = func

        # List of all parameters (Parameter objects), positional and keyword
        self.params = []

        # Parameter object for the return value
        self.retval = Parameter("_return", kind="RETURN")

        # Index of the vararg parameter in self.params
        self._ivararg = None

        # Index of the varkws parameter in self.params
        self._ivarkws = None

        self._iargs = dict()

        # Maximum number of positional parameters (without varargs)
        self._max_positional_args = 0

        # Minimum number of arguments that must be supplied -- all the other
        # have defaults and can be omitted.
        self._min_positional_args = 0

        # Names of keyword-only arguments that have no defaults
        self._required_kwonly_args = set()

        # 0 or 1 depending on whether the function has 'self' argument. This
        # flag allows us to correctly report the number of arguments for a
        # method (1 less than what the signature suggests).
        self._num_self_args = 0

        #--------------------------------------------------------
        # This will initialize all of the arguments defined above
        self._fill_from_inspection_spec(types)

        # Function that can be invoked to check the type of the return value
        self.return_checker = self._make_retval_checker()

        # Function that can be invoked to check the arguments passed to the
        # inspected function.
        self.params_checker = self._make_args_checker()



    def _fill_from_inspection_spec(self, types):
        if hasattr(inspect, "getfullargspec"):
            fspec = inspect.getfullargspec(self.function)
        else:
            fspec = inspect.getargspec(self.function)

        if fspec.args:
            self._max_positional_args = len(fspec.args)
            self._min_positional_args = len(fspec.args)
            for arg in fspec.args:
                p = Parameter(arg)
                if arg == "self" and len(self.params) == 0:
                    self._num_self_args = 1
                    p = Parameter("self", kind="POSITIONAL_ONLY")
                    if "self" in types:
                        raise RuntimeError("`self` parameter must not be typed")
                if arg in types:
                    p.type = types.pop(arg)
                self.params.append(p)

        if fspec.defaults:
            self._min_positional_args -= len(fspec.defaults)
            for i in range(1, len(fspec.defaults) + 1):
                self.params[-i].default = fspec.defaults[-i]

        if fspec.varargs:
            p = Parameter(name=fspec.varargs, kind="VAR_POSITIONAL")
            if fspec.varargs in types:
                p.type = types.pop(fspec.varargs)
            self._ivararg = len(self.params)
            self.params.append(p)

        if getattr(fspec, "kwonlyargs", None):
            self._required_kwonly_args = set(fspec.kwonlyargs)
            for arg in fspec.kwonlyargs:
                p = Parameter(arg, kind="KEYWORD_ONLY")
                if arg in types:
                    p.type = types.pop(arg)
                self.params.append(p)

        if getattr(fspec, "kwonlydefaults", None):
            fkw = fspec.kwonlydefaults
            for i in range(1, len(fkw) + 1):
                p = self.params[-i]
                p.default = fkw[p.name]
                self._required_kwonly_args.remove(p.name)

        if getattr(fspec, "varkw", None) or getattr(fspec, "keywords", None):
            vkw = getattr(fspec, "varkw", None) or getattr(fspec, "keywords")
            p = Parameter(name=vkw, kind="VAR_KEYWORD")
            if vkw in types:
                p.type = types.pop(vkw)
            self._ivarkws = len(self.params)
            self.params.append(p)

        if "_return" in types:
            self.retval.type = types.pop("_return")

        if "_kwonly" in types:
            kwonly = types.pop("_kwonly")
            if not isinstance(kwonly, int):
                raise RuntimeError("_kwonly parameter should be an integer")
            if self._required_kwonly_args:
                raise RuntimeError("_kwonly parameter cannot be used with '*' "
                                   "argument in Python3")
            j = 0
            for i in range(len(self.params) - 1, -1, -1):
                p = self.params[i]
                if p.kind.startswith("VAR_"):
                    continue
                if p.kind == "POSITIONAL_OR_KEYWORD":
                    p.kind = "KEYWORD_ONLY"
                    if p.is_required:
                        self._required_kwonly_args.add(p.name)
                else:
                    raise RuntimeError(
                        "%s parameter %s cannot be made KEYWORD_ONLY" %
                        (p.kind, p.name)
                    )
                j += 1
                if j == kwonly:
                    break
            if j != kwonly:
                raise RuntimeError("Too many keyword-only parameters requested")
            self._max_positional_args -= kwonly
            self._min_positional_args = min(self._min_positional_args,
                                            self._max_positional_args)

        if types:
            raise RuntimeError("Invalid function argument(s): %s" %
                               ", ".join(types.keys()))

        self._iargs = {param.name: i for i, param in enumerate(self.params)}



    def _make_retval_checker(self):
        """Create a function that checks the return value of the function."""
        rvchk = self.retval.checker
        if rvchk:
            def _checker(value):
                if not rvchk.check(value):
                    raise self._tc.TypeError(
                        "Incorrect return type in %s: expected %s got %s" %
                        (self.name_bt, rvchk.name(),
                         checker_for_type(type(value)).name())
                    )
        else:
            def _checker(value):
                pass
        return _checker


    def _make_args_checker(self):
        """
        Create a function that checks signature of the source function.
        """
        def _checker(*args, **kws):
            # Check if too many arguments are provided
            nargs = len(args)
            if nargs > self._max_positional_args and self._ivararg is None:
                raise self._too_many_args_error(nargs)

            # Check if there are too few positional arguments (without defaults)
            if nargs < self._min_positional_args:
                missing = [p.name
                           for p in self.params[nargs:self._min_positional_args]
                           if p.name not in kws]
                # The "missing" arguments may still be provided as keywords, in
                # which case it's not an error at all.
                if missing:
                    raise self._too_few_args_error(missing, "positional")

            # Check if there are too few required keyword arguments
            if self._required_kwonly_args:
                missing = [kw
                           for kw in self._required_kwonly_args
                           if kw not in kws]
                if missing:
                    raise self._too_few_args_error(missing, "keyword")

            # Check types of positional arguments
            for i, argvalue in enumerate(args):
                self._check_positional_arg(i, argvalue)

            # Check types of keyword arguments
            for argname, argvalue in kws.items():
                argindex = self._iargs.get(argname)
                if argindex is not None and argindex < nargs:
                    raise self._repeating_arg_error(argname)
                self._check_keyword_arg(argname, argvalue)

        return _checker


    def _check_positional_arg(self, index, value):
        if index < self._max_positional_args:
            param = self.params[index]
            argname = param.name
        else:
            assert self._ivararg is not None
            param = self.params[self._ivararg]
            argname = "*" + param.name
        self._check_arg(param, argname, value)


    def _check_keyword_arg(self, name, value):
        index = self._iargs.get(name)
        if index is None:
            index = self._ivarkws
        if index is None:
            s = "%s got an unexpected keyword argument `%s`" % \
                (self.name_bt, name)
            raise self._tc.TypeError(s)
        self._check_arg(self.params[index], name, value)


    def _check_arg(self, param, name, value):
        checker = param.checker
        if not checker:
            return
        if checker.check(value):
            return
        if param.has_default:
            dflt = param.default
            if value is dflt or value == dflt:
                return
        tval = checker_for_type(type(value)).name()
        raise self._tc.TypeError(
            "Incorrect type for argument `%s`: expected %s got %s" %
            (name, checker.name(), tval)
        )


    @property
    def name_bt(self):
        return "`%s()`" % self.function.__name__



    def _too_many_args_error(self, num_args):
        num_all_args = len(self.params) - self._num_self_args
        num_pos_args = self._max_positional_args - self._num_self_args
        s = self.name_bt + " "
        if num_all_args == 0:
            s += "doesn't take any arguments"
        elif num_pos_args == 0:
            s += "accepts only keyword arguments"
        else:
            num_args -= self._num_self_args
            plu1 = "argument" if num_pos_args == 1 else "arguments"
            s += "takes %d positional %s but %d were given" % \
                 (num_pos_args, plu1, num_args)
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


    def __repr__(self):
        return ("<typesentry.Signature(%s) minpos=%d maxpos=%d ivararg=%r "
                "ivarkws=%r self=%d reqkwonly={%s} params=[%s]>" %
                (self.function.__name__,
                 self._min_positional_args,
                 self._max_positional_args,
                 self._ivararg, self._ivarkws,
                 self._num_self_args,
                 ", ".join(self._required_kwonly_args),
                 ", ".join(repr(p) for p in self.params)))




class Parameter(object):
    """
    Single parameter / return value in a function's signature.

    The interface closely resembles that of ``inspect.Parameter``.
    """
    SHORT_POSITIONAL_NAME = {
        "POSITIONAL_ONLY": "P",
        "POSITIONAL_OR_KEYWORD": "PK",
        "KEYWORD_ONLY": "K",
        "VAR_KEYWORD": "VK",
        "VAR_POSITIONAL": "VP",
    }

    def __init__(self, name, kind="POSITIONAL_OR_KEYWORD"):
        self.name = name
        self.kind = kind
        self._checker = None
        self._default = None
        self._has_default = False


    @property
    def type(self):  # pragma: no cover
        return self._type

    @type.setter
    def type(self, t):
        self._type = t
        self._checker = checker_for_type(t)

    @property
    def checker(self):
        return self._checker

    @property
    def is_required(self):
        return not self._has_default

    @property
    def has_default(self):
        return self._has_default

    @property
    def default(self):
        return self._default

    @default.setter
    def default(self, val):
        self._default = val
        self._has_default = True

    def __repr__(self):
        return ("<Param '%s' %s%s>" %
                (self.name,
                 Parameter.SHORT_POSITIONAL_NAME[self.kind],
                 " " + self._checker.name() if self._checker else ""))
