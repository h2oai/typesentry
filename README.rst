.. -*- mode: rst -*-

.. image:: https://codecov.io/gh/h2oai/typesentry/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/h2oai/typesentry
   :alt: Code coverage
.. image:: https://img.shields.io/pypi/v/typesentry.svg
   :target: https://pypi.python.org/pypi/typesentry
.. image:: https://img.shields.io/pypi/pyversions/typesentry.svg
   :target: https://pypi.python.org/pypi/typesentry


typesentry
==========

Python library for run-time type checking for type-annotated functions. It
supports both Python-3 annotations (as defined in
`PEP 484 <https://www.python.org/dev/peps/pep-0484/>`_), and legacy Python-2
annotations via decorators. The library also provides function ``is_type``
analogous to builtin ``isinstance`` to allow type checking in other scenarios.

The goal of this library is to provide performat, convenient, configurable
module that can be used in a variety of different contexts.



Rationale
---------

Python is a dynamically typed language; it is the source of its strength and
of its appeal. Still, every object in the language does have its own type, and
every function has an implied signature — the types of arguments that it can
operate on. Passing arguments of incorrect types leads either to unexpected
results, or more likely to an exception.

Thus, PEP-484 was introduced, which mentions in its introduction that

    This PEP aims to provide a standard syntax for type annotations, opening up
    Python code to easier static analysis and refactoring, **potential runtime
    type checking** ...

Of course, it is each developer's choice whether or not to use runtime type
checking. Obviously, there is a certain amount of overhead to check the type of
each argument (especially when it's a container type). However we have found
that *not* doing so itself causes problems:

- Exceptions that are raised are either only tangentially related to the actual
  problem, or outright cryptic. You may see errors about unsupported operations
  on a type, unavailable attributes, and worse. But very rarely you see a clear
  message such as "Argument ``x`` expected to be an integer, but instead
  received ``None``".
- A function may not do anything to its argument other than storing it for
  later use. If the argument had invalid type, it will manifest itself some time
  later in the program, at which point it would already be impossible to know
  how this bad argument came out to be.

In short, runtime type checks slow down the program, whereas their absence slow
down the programmer. We also recognize that Python code may be executed in
different environments, which would lead to a different choice in this tradeoff:

- *Production environment*, where the code runs against a set of predefined and
  carefully vetted inputs. Perhaps in this case runtime checks can be forfeited.
- *Testing environment*, where speed is much less of an importance but ability
  to quickly identify errors is more crucial. Runtime checks should be always
  on.
- *Interactive programming*, via a console or Jupyter Notebook, where the
  software engineer writes the code in a trial-and-error loop. Again, runtime
  checks are extremely useful here, since speed of debugging the problems
  dominates the speed of code execution.



Usage
-----

The ``typesentry`` library is intended to be used from other packages. The
minimal example of how to do it looks like this::

    import typesentry
    tc1 = typesentry.Config()
    typed = tc1.typed        # decorator to check function arguments at runtime
    is_typed = tc1.is_typed  # equivalent of isinstance()

Typically you would put this into a separate file in your project, and then
import symbols ``typed`` and ``is_typed`` (or however you want to name them)
from that file.

The ``Config`` object here allows you to specify how exactly the type checking
should behave. In particular you can enable/disable type checking, pass custom
exception class that will be used when a type error is detected, etc. More
settings are expected to be added in the future.

You can create more than one ``Config`` object, with different settings,
allowing you to have typecheck-decorators with different degrees of persistence.

Once you this file (let's assume it's ``utils/types.py`` for concreteness),
then the annotation ``@typed`` and function ``is_typed()`` can be used as
follows (in both Python 2 and 3):

.. code-block:: python

    from .utils.types import typed
    from typing import List, Union

    @typed(x=Union[List[int], List[str]])
    def together(x):
        if not x:
            return None
        elif isinstance(x[0], int):
            return sum(x)
        else:
            return "".join(x)

or using Python 3 type annotations:

.. code-block:: python

    from .utils.types import typed, is_type
    from typing import List, Union

    @typed()
    def together(x: Union[List[int], List[str]]):
        if not x:
            return None
        elif isinstance(x[0], int):
            return sum(x)
        else:
            return "".join(x)

Now let's try calling this function with various arguments:

>>> together([])
>>> together([1, 5, -2])
4
>>> together(["hello", ",", " ", "world", "!"])
'hello, world!'
>>> # Notice how in 2 examples below the error message is different depending
>>> # on whether the argument looks more like List[int] or List[str]
>>> together(["hello", ",", " ", "world", 1])
TypeError: Parameter x expects type List[str] but received a list where 5th element is 1 of type int
           File <stdin>, line 1, in
                together(x)
           File <stdin>, line 1, in <module>()
>>> together(["hello", 2, 9, 11, 1])
TypeError: Parameter x expects type List[int] but received a list where 1st element is 'hello' of type str
           File <stdin>, line 1, in
                together(x)
           File <stdin>, line 1, in <module>()
>>> # If it doesn't look like either, then a more generic message is displayed
>>> together([False, True])
TypeError: Parameter x of type Union[List[int], List[str]] received value [False, True] of type list
           File <stdin>, line 1, in
                together(x)
           File <stdin>, line 1, in <module>()
>>> # Also note that we treat booleans as types distinct from int:
>>> isinstance(True, int), isinstance(True, bool)
(True, True)
>>> is_type(True, int), is_type(True, bool)
(False, True)



Soft exceptions
---------------
In addition to trying to generate helpful messages to the user upon seeing a
type mismatch, this module also advocates for the use of "kind" (or "soft")
exceptions. It applies in the context of interactive programming from within a
console or a Jupyter notebook.

The idea is that when a user makes a small innocent mistake, such as a typo in
a parameter's name, or providing wrong parameter value — then throwing back at
them exceptions with long intimidating stack traces is rather rude. The error
message should not attempt to overwhelm the user, but rather help them correct
the problem.

Hence, the notion of "soft exceptions". They can be turned on/off using
``Config``s parameter ``soft_exceptions`` (which is ``True`` by default).
In this mode ``typesentry`` installs an exception hook (via ``sys.excepthook``)
such that whenever an exception exposing a ``_handle_()`` method propagates
to the outer level, then instead of printing the default stack trace, this
``_handle_()`` method would be invoked. Thus, "soft exceptions" are just
regular exceptions for all intents and purposes, except with respect to how
they appear in the console.

The default exception class used by ``typesentry`` implements custom
``_handle_()`` method which prints the error message at the top, then the
signature of the function where type mismatch has occurred, and finally the
compactified stack trace. It also uses colors to accentuate the most important
parts of the error message.

The user may override this behavior by either specifying turning off soft
exceptions in the ``Config``, providing their own exception class which may or
may not implement ``_handle_()``, or submitting a Pull Request ;)

We intend to further improve and refine this functionality (for example,
currently support for Jupyter Notebooks is missing).



Extensions
----------
You can extend functionality of this module by declaring custom types as
classes deriving from ``typesentry.MagicType``. At a minimum, you would
override methods ``check(self, var)`` which should return ``True`` iff a
variable ``var`` matches the type; and method ``name(self)`` which returns
string description of your new type (to be used in error messages).

In addition there are also methods ``fuzzy_check(self, var)`` returning a
float value from 0 to 1 indicating how well ``var`` matches the type; and
``get_error_msg(self, param, var)`` which should return an error message
about parameter ``param = var`` not matching the type. These two methods are
advanced and need not be implemented. However they are useful if you want to
provide smarter-than-usual feedback to the user.

For example, suppose you have a set of functions that work with rectangular
matrices, i.e. objects of the type ``List[List[float]]``. At some point you
realize that this is insufficient: you need to guarantee that all internal
arrays have the same dimensions, otherwise it's not really a matrix. The code
to implement such type may look like this:

.. code-block:: python

    from typesentry import MagicType

    class MatrixT(MagicType):
        def check(self, var) -> bool:
            if not isinstance(var, list) or not var: return False
            for elem in var:
                if not isinstance(elem, list): return False
                if len(elem) != len(var[0]): return False
                if not all(isinstance(x, float) for x in elem): return False
            return True

        def name(self) -> str:
            return "Matrix"



Installation
------------

.. code-block:: bash

    pip install typesentry



See Also
--------
- `PEP 484 <https://www.python.org/dev/peps/pep-0484/>`_ — Python standard for
  declaring type annotations.
- `MyPy <http://mypy-lang.org/>`_ — static type analyzer (i.e. at compile time).
- `TypeGuard <https://github.com/agronholm/typeguard>`_ — alternative runtime
  type checker.
- `Enforce <https://github.com/RussBaz/enforce>`_ — another runtime type
  checker.
