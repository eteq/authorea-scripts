#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

import pypandoc

pypandoc.convert_file('README.md', 'rst', outputfile='README.rst')
setup(
    name='authorea-scripts',
    version='0.0.5',
    py_modules=['build-authorea'],
    description='Tools for working locally with Authorea projects',
    url='https://github.com/mpjuers/authorea-scripts',
    author='Mark Juers',
    author_email='mpjuers@indiana.edu',
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'pypandoc',
        'panflute'
        ],
    entry_points='''
        [console_scripts]
        build-authorea-latex=authorea_scripts.local_build:main
        stripreftags=authorea_scripts.stripreftags:main
    ''',
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        ]
    )
