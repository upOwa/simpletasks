#!/usr/bin/env python
# -*- coding: utf-8 -*-

# flake8: noqa

import codecs
import os

from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding="utf-8").read()


setup(
    name="simpletasks",
    use_scm_version=True,
    author="Thomas Muguet",
    author_email="hi@tmuguet.me",
    maintainer="Thomas Muguet",
    maintainer_email="hi@tmuguet.me",
    license="LGPL",
    url="https://github.com/upOwa/simpletasks",
    description="A simple library to run one task, or multiples ones in sequence or parallel",
    long_description=read("README.rst"),
    py_modules=["simpletasks"],
    python_requires=">=3.6",
    setup_requires=["setuptools_scm"],
    install_requires=[],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Topic :: Utilities",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
    ],
)
