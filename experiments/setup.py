#!/usr/bin/env python3

"Setuptools params"
from setuptools import setup, find_packages

VERSION = '0.1'

modname = distname = 'fancy'


def readme():
    with open('README.md', 'r') as f:
        return f.read()


setup(
    name=distname,
    version=VERSION,
    description='Scripts for all the python experiments and plots of the FANcY project',
    author='Edgar Costa Molero',
    author_email='cedgar@ethz.ch',
    packages=find_packages(),
    long_description=readme(),
    include_package_data=True,
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python 3",
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Topic :: System :: Networking",
    ],
    keywords='networking p4',
    license='GPLv2',
    setup_requires=['matplotlib'],
    install_requires=[
        'tabulate==0.8.9',
        'ipdb',
        'numpy',
        'psutil',
        'termcolor==1.1.0',
        'deprecated',
        'scapy==2.4.3',
        'pandas',
        'seaborn==0.11.2',
        'beautifulsoup4==4.7.1',
        'psutil',
        'ipaddr',
        'SciencePlots==1.0.5',
    ],
    # scapy might be 2.4.3?
    extras_require={}
)
