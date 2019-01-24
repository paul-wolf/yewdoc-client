from setuptools import setup

setup(
    name='yd',
    version='0.1.0',
    py_modules=['yewdoc'],
    install_requires=[
        "click==6.6",
        "Jinja2==2.7.3",
        "Markdown==2.6.2",
        "MarkupSafe==0.23",
        "pypandoc",
        "python-dateutil==2.4.2",
        "pytz==2015.4",
        "requests==2.7.0",
        "six>=1.9.0",
        "StringGenerator",
        "tzlocal==1.2",
        "wheel",
        "humanize==0.5.1",
   ],
    entry_points='''
        [console_scripts]
        yd = yewdoc:cli
    ''',
)
