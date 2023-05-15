# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from setuptools import setup, find_packages

setup(
    name='putils',
    version='1.0.0',
    description='Utility functions for protein analysis',
    author='Brian Loyal',
    author_email='bloyal@amazon.com',
    license='Apache License, Version 2.0',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    python_requires='>=3',
    install_requires=[
        'pandas',
        'numpy',
        'biopython'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        "Programming Language :: Python :: 3",
    ],
)