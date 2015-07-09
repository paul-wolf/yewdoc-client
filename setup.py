from setuptools import setup

setup(
    name='yd',
    version='0.1.0',
    py_modules=['yewdoc'],
    install_requires=[
        'click==4.0',
        'flake8==2.4.1',
        'mccabe==0.3.1',
        'pep8==1.5.7',
        'pyflakes==0.8.1',
        'python-dateutil==2.4.2',
        'pytz==2015.4',
        'requests==2.7.0',
        'six==1.9.0',
        'tzlocal==1.2',
        'wsgiref==0.1.2',
        'StringGenerator',
        'markdown',
    ],
    entry_points='''
        [console_scripts]
        yd = yewdoc:cli
    ''',
)
