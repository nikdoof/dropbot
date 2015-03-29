#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from dropbot import __version__ as pkg_version

readme = open('README.md').read()

requirements = [
    'sleekxmpp==1.3.1',
    'eveapi==1.2.6',
    'redis==2.10.2',
    'requests==2.3.0',
    'humanize==0.5',
    'dnspython==1.11.1',
    'networkx==1.9',
]

test_requirements = [
    'mock==1.0.1',
]

setup(
    name='dropbot',
    version=pkg_version,
    description='A XMPP bot to provide simple services to NOG8S and Predditors in general',
    long_description=readme,
    author='Andrew Williams',
    author_email='andy@tensixtyone.com',
    url='https://github.com/nikdoof/dropbot/',
    packages=[
        'dropbot',
    ],
    include_package_data=True,
    install_requires=requirements,
    license="BSD",
    zip_safe=False,
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    entry_points = {
        'console_scripts': ['dropbot=dropbot.cli:main'],
    }
)
