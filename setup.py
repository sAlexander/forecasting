#!/usr/bin/env python

from distutils.core import setup

setup(name='Forecasting',
      version='0.5.0',
      description='Weather Forecasting Utilities',
      author='Spencer Alexander',
      author_email='contact@getforecasting.com',
      url='http://getforecasting.com',
      packages=['forecasting'],
      package_data={'forecasting': ['db/0.5.0/up/*.sql','db/0.5.0/down/*.sql']},
     )
