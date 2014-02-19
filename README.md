forecasting.py
===========

Get weather data easily using python. Supports gfs, nam, and rap, with support for individual weather stations on the way. Full information with examples can be found at [getforecasting.com](http://getforecasting.com)

## Basic Usage

```from forecasting import models

nam = models('nam')
nam.connect(database='weather', user='chef')
fields = ['tmp2m']
nam.transfer(fields)
```

## Quick Start Guide

Check out the [quick start](http://getforecasting.com/documentation/quick-start/) guide at getforecasting.com

## Documentation

See the [full set of documentation](http://getforecasting.com/documentation/).

