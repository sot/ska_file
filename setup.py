from setuptools import setup

from Ska.File import __version__

setup(name='Ska.File',
      author = 'Tom Aldcroft',
      description='Various file utilities',
      author_email = 'taldcroft@cfa.harvard.edu',
      py_modules = ['Ska.File'],
      version=__version__,
      zip_safe=False,
      packages=['Ska'],
      package_dir={'Ska' : 'Ska'},
      package_data={}
      )
