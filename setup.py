#!/usr/bin/env python
# Copyright 2016 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
"""
Build script for the `typechecking` module.
"""
from setuptools import find_packages, setup
from typechecking.__version__ import version

packages = find_packages(exclude=["tests*", "docs*"])

setup(
    name="typechecking",
    version=version,

    description="Run-time type checking of arguments passed to functions",

    # The homepage
    url="https://github.com/st-pasha/typechecking.git",

    # Author details
    author="Pasha Stetsenko",
    author_email="pasha@h2o.ai",

    license="Apache v2.0",

    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: Apache Software License",
    ],

    packages=packages,

    # Runtime dependencies
    install_requires=[],
    tests_require=["pytest"],

    # This module doesn't expect to introspect its own source code.
    # (change this flag if this assumption no longer holds)
    zip_safe=True,
)
