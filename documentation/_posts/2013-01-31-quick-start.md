---
layout: post
title: Quick Start Guide
category: tutorials
description: A quick start guide to get you up and running with forecasting and Ubuntu.
---

This guide will walk you through using forecasting as a python module to cache weather data into a postgis database. If you're instead looking to get started on the API, head over to [the API documentation](/documentation/Api).

<h2 id="forecasting">Quick start for forecasting module</h2>

This guide assumes you're using Linux, and has been tested with Ubuntu 12.04 to 13.04. If you've played around with the code on other operating systems with success (or without success), let us know!

First, let's install all of the components required for PostGIS and the python dependencies. Most of these are likely already installed on your system, but I've included them below in case you're starting from a bare-bones setup.

{% highlight bash %}
sudo apt-get install build-essential git postgresql-9.1 python-numpy python-pip python-psycopg2 python-dev python-genshi python-paste python-pastedeploy python-httplib2 python-pastescript
sudo pip install pydap
{% endhighlight %}

<h2 id="postgis">Install PostGIS</h2>

If you're looking for the easiest way to setup your database, installing PostGIS through the repository is certainly an option. However, at the time of this writing, it will set you up with an older version (1.5.3) which doesn't contain the best feature yet: an efficient way to search for the nearest points. This has real performance impacts: on my [Raspberry Pi](/documentation/Raspberry-Pi/), a search for the 8 nearest neighbors in a 1,000,000 row dataset took 53 seconds with version 1.5.3 and 8.2 milliseconds with version 2.0.4.

Considering this missing feature, I highly recommend you compile the latest PostGIS... don't worry, it'll be easy! I've listed both options below. Choose your own adventure.

<h3 id="repository">Install PostGIS from the repository (not recommended)</h3>

Simply install from the repository:

{% highlight bash %}
sudo apt-get install postgresql-9.1-postgis
{% endhighlight %}

You're done!

<h3 id="compile">Compile the latest PostGIS version (2.0.4)</h3>

These compile instructions were based upon the [great guide on the osgeo wiki](https://trac.osgeo.org/postgis/wiki/UsersWikiPostGIS20Ubuntu1210src). First, let's install the dependencies for PostGIS:

{% highlight bash %}
sudo apt-get install libgeos-c1 libxml2-dev libproj-dev libjson0-dev xsltproc docbook-xsl docbook-mathml libgdal1-dev
{% endhighlight %}

Second, let's download the source code. I'm partial to having a `~/source` directory to temporarily store all of these source files before they're installed.

{% highlight bash %}
wget http://download.osgeo.org/postgis/source/postgis-2.0.4.tar.gz
tar xfz postgis-2.0.4.tar.gz
cd postgis-2.0.4
{% endhighlight %}

Finally, let's configure and install the module:

{% highlight bash %}
./configure
make
sudo make install
{% endhighlight %}

And you're done! Not too bad, 'eh?

## Configure PostGRES

Let's now log into postgres, create our `chef` user, and setup PostGIS. You'll want to replace `chef` with your own username, or jump through some hoops to correct permissions (as [discussed on stack overflow](http://stackoverflow.com/questions/18664074/getting-error-peer-authentication-failed-for-user-postgres-when-trying-to-ge)).

First, let's connect into psql

{% highlight bash %}
sudo -u postgres psql
{% endhighlight %}

Now, we create a database, setup permissions, and leave the psql client:

{% highlight postgres %}
create database weather;
create user chef with superuser;
grant all privileges on database weather to chef;
grant all privileges on database postgres to chef;
\q
{% endhighlight %}

Finally, let's setup postGIS in the weather database. Hop into the postgres database using the command `psql -U chef weather`, and run the two following commands:

{% highlight postgres %}
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
{% endhighlight %}

## Using the forecasting module

You're ready now! After [installing the forecasting module]({% post_url 2013-01-30-installation %}), you'll be ready to grab the weather data with a command like:

{% highlight python %}
from forecasting import model

nam = model('nam')
nam.connect(database='weather', user='chef')
fields = ['tmp2m']
nam.transfer(fields)
{% endhighlight %}

The query above will set up your database table, load in the mesoscale grid, and grab the latest temperature data. Woot!

