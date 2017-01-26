#!/usr/bin/env python
# Copyright 2016 H2O.ai; Apache License Version 2.0;  -*- encoding: utf-8 -*-
"""
Build script for the `typesentry` module.

    $ python setup.py bdist_wheel
    $ twine upload dist/*

"""
from setuptools import find_packages, setup
from typesentry.__version__ import version

packages = find_packages(exclude=["tests*", "docs*"])

setup(
    name="typesentry",
    version=version,

    description="Run-time type checking of arguments passed to functions",

    # The homepage
    url="https://github.com/h2oai/typesentry.git",

    # Author details
    author="Pasha Stetsenko",
    author_email="pasha@h2o.ai",

    license="Apache v2.0",

    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Topic :: Utilities"
    ],
    keywords=["types", "typing", "typecheck"],

    packages=packages,

    # Runtime dependencies
    install_requires=[
        "colorama>=0.3",
    ],
    tests_require=[
        "pytest>=3.0",
        "pytest-cov",
    ],

    # This module doesn't expect to introspect its own source code.
    # (change this flag when this assumption no longer holds)
    zip_safe=True,
)
