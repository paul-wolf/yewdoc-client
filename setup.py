# -*- coding: utf-8 -*-
from setuptools import setup

install_requires =[]
with open('requirements.txt') as fh:
    for r in fh:
        r = r.strip()
        if r:
            install_requires.append(r)
            
setup(
<<<<<<< HEAD
    name="yd",
    version="0.2.0",
    # py_modules=["yewdoc"],
    packages=find_packages(),
    include_package_data=True,
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
=======
    name='yd',
    version='0.1.0',
    py_modules=['yewdoc'],
    install_requires=install_requires,
    entry_points='''
>>>>>>> Change setup.py to read requirements from requirements.txt rather then a redundant array that must be kept in-sync with requirements.txt.
        [console_scripts]
        yd = yd:cli
    """,
)
