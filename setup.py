from setuptools import setup, find_packages
from codecs import open  # To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


def is_pkg(line):
    return line and not line.startswith(('--', 'git', '#'))

VERSION = (1, 0, 1)


setup(
    name='addok-csv',
    version='.'.join(map(str, VERSION)),
    description='Add CSV support to your Addok instance.',
    long_description=long_description,
    url='https://github.com/etalab/addok-csv',
    author='Yohan Boniface',
    author_email='yohan.boniface@data.gouv.fr',
    license='WTFPL',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',

        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: GIS',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    keywords='addok geocoding csv plugin',
    packages=find_packages(exclude=['tests']),
    extras_require={'test': ['pytest']},
    include_package_data=True,
    entry_points={'addok.ext': ['csv=addok_csv']},
)
