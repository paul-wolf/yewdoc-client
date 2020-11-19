# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name="yd",
    version="0.2.0",
    py_modules=["yewdoc"],
    install_requires=[
        "click",
        "Jinja2",
        "Markdown",
        "pypandoc",
        "python-dateutil",
        "pytz",
        "requests",
        "StringGenerator",
        "tzlocal",
        "humanize",
        "python-gnupg",
        "glom",
    ],
    entry_points="""
        [console_scripts]
        yd = yd:cli
    """,
)
