# !/usr/bin/env python
# encoding: utf-8

from setuptools import find_packages, setup

NAME = 'linnaeus'
DESCRIPTION = 'Recreate reference images using tiny images as pixels.'
URL = 'https://github.com/NaturalHistoryMuseum/linnaeus'
EMAIL = 'data@nhm.ac.uk'
AUTHOR = 'Alice Butcher'
REQUIRES_PYTHON = '>=3.6.0'
VERSION = '1.7'

with open('requirements.txt', 'r') as req_file:
    REQUIRED = [r.strip() for r in req_file.readlines()]

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=DESCRIPTION,
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(exclude=('tests',)),
    install_requires=REQUIRED,
    include_package_data=True,
    entry_points='''
        [console_scripts]
        linnaeus=linnaeus.cli:cli
    ''',
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython'
        ]
    )
