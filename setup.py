from setuptools import setup

install_requires =[]
with open('requirements.txt') as fh:
    [install_requires.append(r.strip()) for r in fh if len(r.strip()) >0]
    
setup(
    name='yd',
    version='0.1.0',
    py_modules=['yewdoc'],
    install_requires=install_requires,
    entry_points='''
        [console_scripts]
        yd = yewdoc:cli
    ''',
)
