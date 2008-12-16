from setuptools import setup
setup(name='Ska.File',
      author = 'Tom Aldcroft',
      description='Various file utilities',
      author_email = 'taldcroft@cfa.harvard.edu',
      py_modules = ['Ska.File'],
      version='1.0',
      zip_safe=False,
      namespace_packages=['Ska'],
      packages=['Ska'],
      package_dir={'Ska' : 'Ska'},
      package_data={}
      )
