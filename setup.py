from setuptools import setup

install_requires =[]
with open('requirements.txt') as fh:
    for r in fh:
        r = r.strip()
        if r:
            install_requires.append(r)
            
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
