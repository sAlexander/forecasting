---
layout: post
title: Quick Start Guide
category: tutorials
description: A quick start guide to get you up and running with forecasting and Ubuntu.
---

This guide will walk you through using forecasting as a python module to cache weather data into a postgis database. If you're instead looking to get started on the API, head over to [the API documentation](http://api.getforecasting.com).

<h2 id="forecasting">Quick start for forecasting module</h2>

This guide assumes you're using Linux, and has been tested with Ubuntu 12.04 to 13.04. If you've played around with the code on other operating systems with success (or without success), let us know!

First, let's install all of the components required for PostGIS and the python dependencies. Most of these are likely already installed on your system, but I've included them below in case you're starting from a bare-bones setup.

{% highlight bash %}
sudo apt-get install build-essential git postgresql-9.1 postgresql-9.1-postgis python-numpy python-pip python-psycopg2 python-dev python-genshi python-paste python-pastedeploy python-httplib2 python-pastescript
sudo pip install pydap
{% endhighlight %}

This will get you setup with an earlier version of PostGIS. If you're looking to have the latest and greatest PostGIS 2.x.x (which we think is a great idea), go ahead and compile PostGIS 2.x.x instead.

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

Finally, let's setup postGIS in the weather database

{% highlight bash %}
sudo -u postgres psql -d weather -f /usr/share/postgresql/9.1/contrib/postgis-1.5/postgis.sql
sudo -u postgres psql -d weather -f /usr/share/postgresql/9.1/contrib/postgis-1.5/spatial_ref_sys.sql 
sudo -u postgres psql -d weather -f /usr/share/postgresql/9.1/contrib/postgis_comments.sql
{% endhighlight %}

If you have problems with the above, it could be because the file described after `-f` is incorrect. Try `locate postgis.sql` to find the correct location.

You're ready now! After [installing the forecasting module]({% post_url 2013-01-30-installation %}), you'll be ready to grab the weather data with a command like:

{% highlight python %}
from forecasting import model

nam = model('nam')
nam.connect(database='weather', user='chef')
fields = ['tmp2m']
nam.transfer(fields)
{% endhighlight %}

The query above will set up your database table, load in the mesoscale grid, and grab the latest temperature data. Woot!

