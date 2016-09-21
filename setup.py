# coding:utf-8

import sys
from setuptools import setup, find_packages


setup(name='addresslib',
      version='0.4.27',
      description='Email Validation forked from Flanker',
      long_description=open('README.rst').read(),
      classifiers=[],
      keywords='',
      author='Mailgun Inc., Encircle Inc.',
      author_email='dev@encircleapp.com',
      url='http://mailgun.ne://github.com/EncircleInc/addresslib',
      license='Apache 2',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      tests_require=[
          'nose',
          'mock'
      ],
      install_requires=[
          'dnspython',
          'redis',
          'regex',
      ],
      )
