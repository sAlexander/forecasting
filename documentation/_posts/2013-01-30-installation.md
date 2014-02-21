---
layout: post
title: Installation
category: tutorials
description: Installation instructions to get forecasting running on your system of choice.
---

## Python and OS Support

The forecasting module is known to work with python 2.7 and Ubuntu 12.04-13.04 or Debian 7.2 (on a [Raspberry Pi](/documentation/Raspberry-Pi/)!).

More testing is underway with additional python versions as well as other linux distributions, Mac OSX, and Windows.

## Downloading the Source

Regardless of your installation method, you'll need to download the source. Download it where you like... I'm partial to a `~/source` directory.

```bash
git clone https://github.com/sAlexander/forecasting.git
```

## Install to Your System

The source code is distributed with a `setup.py` file. To install to your system, hop into the source code directory (`cd ~/source/forecasting`) and run:

```bash
sudo python setup.py install
```

That's it! To import, you can run something like

```python
from forecasting import Model
```

## Install to Your Project

If you prefer to keep the source code local rather than install it to your system, simply copy the `forecasting` folder from the main directory of the source code to your folder of interest.

You can now import the package in your particular project with:

```python
from forecasting import Model
```

