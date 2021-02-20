from setuptools import setup, find_packages

install_requires = list()
with open('requirements.txt') as fh:
    for r in fh:
        r = r.strip()
        if r:
            install_requires.append(r)
            
setup(
    name="yd",
    version="0.2.0",
    packages=find_packages(),
    include_package_data=True,
    py_modules=['yewdoc'],
    install_requires=install_requires,
    entry_points = {
        "console_scripts": [
            "yd = yd:cli",
        ]
    }
)
