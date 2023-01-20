# Licensed under a 3-clause BSD style license - see LICENSE.rst
from setuptools import setup
from ska_helpers.setup_helper import duplicate_package_info

name = "ska_file"
namespace = "Ska.File"

packages = ["ska_file"]
package_dir = {name: name}

duplicate_package_info(packages, name, namespace)
duplicate_package_info(package_dir, name, namespace)

setup(name=name,
      author = 'Tom Aldcroft',
      description='Various file utilities',
      author_email = 'taldcroft@cfa.harvard.edu',
      py_modules = ['Ska.File'],
      use_scm_version=True,
      setup_requires=['setuptools_scm', 'setuptools_scm_git_archive'],
      zip_safe=False,
      packages=packages,
      package_dir=package_dir,
      package_data={}
      )
