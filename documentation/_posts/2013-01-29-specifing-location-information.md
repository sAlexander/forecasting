---
layout: post
title: Specifying Location Information
category: tutorials
description: When downloading a small subset of a forecast (ie only the four closest points to my house), one would use the geos feature in Forecasting.
---

Downloading an entire forecast can not only be wasteful of bandwidth, but also wasteful of storage space. For example, a single forecast from the nam model results in over 8 million data points being stored in your database. Which begs the question: what if I don't care about what's happening on the other side of the US/world?

That's where Forecasting comes to the rescue. Forecasting allows you to specify locations in one of two ways: a point with k neighbors, or a lat/lon box. Below both options are described, and a couple of examples are given after. Once you have your location described, you pass it to the `transfer` function as either a dict or list of dicts.

### Describing a Point

Describing a point is simple:

{% highlight python %}
geos = {
        'lat': 40.00, # * required
        'lon': -100.00, # * required
        'k':8 # (optional) nearest neighbors defaults to 1 (ie only itself).
        }
{% endhighlight %}

### Describing a Bounded Box

Describing a bounded box is quite easy as well:

{% highlight python %}
geos = {
        'n': 41.00,   # * required
        's': 39.00,   # * required
        'e': -99.00,  # * required
        'w': -101.00, # * required
        'i':2         # (optional) download every ith datapoint, defaults to 1.
        }
{% endhighlight %}

### A simple example using geos

{% highlight python %}
from forecasting import Model

nam = Model('nam')
nam.connect(database='weather', user='chef')

fields = ['tmp2m']
geos = {'lat': 40.00, 'lon': -100.00, 'k':8}

nam.transfer(fields, geos=geos)
# this will now transfer only the 8 points described by the geos dict
{% endhighlight %}

### Using multiple geos definitions

Using multiple geos definitions is as easy as combining them as a list. For example:


{% highlight python %}
geos = [{ # Bounded Box
        'n': 41.00,   # * required
        's': 39.00,   # * required
        'e': -99.00,  # * required
        'w': -101.00, # * required
        'i':2         # (optional) download every ith datapoint, defaults to 1.
       },{ # Point with Neighbors
        'lat': 38.00, # * required
        'lon': -100.00, # * required
        'k':8 # (optional) nearest neighbors defaults to 1 (ie only itself).
       }]
{% endhighlight %}

The above will download both sets of data, one after the other. Easy as pie!

Performance Note: If you ever define overlapping geos, Forecasting will handle it gracefully and ignore duplicate datapoints. However, specify your largest geos first so that Forecasting can take advantage of the faster binary copy to the database.
