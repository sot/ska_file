# Licensed under a 3-clause BSD style license - see LICENSE.rst
from setuptools import setup

setup(name='Ska.File',
      author = 'Tom Aldcroft',
      description='Various file utilities',
      author_email = 'taldcroft@cfa.harvard.edu',
      py_modules = ['Ska.File'],
      use_scm_version=True,
      setup_requires=['setuptools_scm', 'setuptools_scm_git_archive'],
      zip_safe=False,
      packages=['Ska'],
      package_dir={'Ska' : 'Ska'},
      package_data={}
      )
