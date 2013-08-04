---
layout: post
title: Compiling PostGIS 2.x.x
category: tutorials
description: PostGIS 2.x.x has a few big advantages over the 1.x.x version. Let's walk through the installation process for the latest and greatest PostGIS.
---

Compiling PostGIS 2.x.x has a few big advantages over the 1.x.x version. For one, the creation of a spacially aware database is much easier now, with the `create extension postgis;` command now available in psql. And secondly, and perhaps more importantly, improved access to spatial indicies is available in PostGIS 2.x.x; for finding the nearest neighbor to a point (a frequent task in using weather data), the index aware `<->` operator can be used, as detailed on [OpenGeo's Introduction to PostGIS](http://workshops.opengeo.org/postgis-intro/knn.html).

Much of this installation guide has been taken from the [OpenGeo's docs for compiling on Ubuntu 12.10](http://trac.osgeo.org/postgis/wiki/UsersWikiPostGIS20Ubuntu1210src). As you work your way through, reading a bit more from the original post may be helpful.

## Install Prerequisites

If you're running Ubuntu, you'll need to install the following packages by running:

```bash
sudo apt-get install build-essential postgresql-9.1 postgresql-server-dev-9.1 libgeos-c1 libxml2-dev libproj-dev libjson0-dev xsltproc docbook-xsl docbook-mathml libgdal1-dev checkinstall
```

I've gone ahead and included libgdal, as you'll likely want raster support.

## Installing Geos

For Ubuntu 12.04, the repositories don't have a sufficiently recent version of Geos for the PostGIS installation. Thankfully, getting Geos compiled is as easy as:

```bash
cd ~/source
wget http://download.osgeo.org/geos/geos-3.3.8.tar.bz2
tar xvf geos-3.3.8.tar.bz2
cd geos-3.3.8
./configure
make
sudo checkinstall
```

We've used `checkinstall` to install the package... it makes managing the packages much easier. You could also replace `sudo checkinstall` with `sudo make install`.



### install PostGIS

To build PostGIS, the following commands will get you setup:

```bash
cd ~/source
wget http://download.osgeo.org/postgis/source/postgis-2.0.3.tar.gz
tar xfvz postgis-2.0.3.tar.gz
cd postgis-2.0.3
./configure
make
sudo checkinstall
sudo ldconfig
```

## Using the new installation

Now that you're setup with PostGIS 2.0.3, you can enable PostGIS for a given database. After opening the postgres client with `psql DBNAME`, enable the PostGIS extension:

```postgres
create extension postgis;
create extension postgis_topology;
```

You're set!
