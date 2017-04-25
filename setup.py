##############################################################################
#
# Copyright (c) 2011 Agendaless Consulting and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the BSD-like license at
# http://www.repoze.org/LICENSE.txt.  A copy of the license should accompany
# this distribution.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL
# EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND
# FITNESS FOR A PARTICULAR PURPOSE
#
##############################################################################

import os

from setuptools import setup
from setuptools import find_packages

here = os.path.abspath(os.path.dirname(__file__))

def read(fname):
    with open(fname) as fp:
        return fp.read()

try:
    README = read(os.path.join(here, 'README.rst'))
    CHANGES = read(os.path.join(here, 'CHANGES.rst'))
except:
    README = ''
    CHANGES = ''

requires = ['translationstring', 'iso8601']

testing_extras = ['nose', 'coverage']
docs_extras = [
    'Sphinx >= 1.3.1',
    'docutils',
    'pylons-sphinx-themes',
]

setup(name='colander',
      version='1.3.3',
      description=('A simple schema-based serialization and deserialization '
                   'library'),
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
          "Intended Audience :: Developers",
          "Programming Language :: Python",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.3",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: Implementation :: CPython",
          "Programming Language :: Python :: Implementation :: PyPy",
          ],
      keywords='serialize deserialize validate schema validation',
      author="Agendaless Consulting",
      author_email="pylons-discuss@googlegroups.com",
      url="http://docs.pylonsproject.org/projects/colander/en/latest/",
      license="BSD-derived (http://www.repoze.org/LICENSE.txt)",
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      test_suite="colander",
      extras_require={
          'testing': testing_extras,
          'docs': docs_extras,
          },
      )
