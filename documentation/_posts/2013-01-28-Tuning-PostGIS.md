---
layout: post
title: Tuning PostGIS
category: tutorials
description: The default PostGIS configuration on many systems is terribly underpowered. Here we discuss a few tuning options.
---

The default PostGIS configuration on many systems is terribly underpowered for our needs -- it makes sense for the average user that doesn't want Postgresql taking up half of the system memory, but for our data hungry needs, a bit more power will help.

## Moving the data directory

The default data directory for Postgresql in Ubuntu is on the main `/` drive. As the database grows, you'll likely want this to be hosted on a secondary drive that's dedicated to the task.

Moving the database (as detailed on [Stackoverflow](http://stackoverflow.com/a/11608918/490692)) is as easy as:

```bash
# Remove the current database location
sudo pg_dropcluster --stop 9.1 main

# Create the database in a new location -- make sure to adjust /path/to/db to your prefered location
# Beware, this will overwrite your current configuration file
sudo pg_createcluster -d /path/to/db 9.1 main

# Researt the server with the new location
sudo /etc/init.d/postgresql start
```

## Tune for Performance

The default memory for PostGIS is setup to the bare minimum. Samiux has a great description on [performance tuning for Postgresql on Ubuntu/Debian](http://samiux.wordpress.com/2009/07/26/howto-performance-tuning-for-postgresql-on-ubuntudebian/) -- head strait to his post if you want the full breakdown, but for a system with 8GB memory, a good set of defaults are:

```
max_connections = 140
shared_buffers = 2GB
temp_buffers = 8MB
work_mem = 16MB
maintenance_work_mem = 1GB
wal_buffers = 8MB
checkpoint_segments = 128
effective_cache_size = 6GB
cpu_tuple_cost = 0.0030
cpu_index_tuple_cost = 0.0010
cpu_operator_cost = 0.0005
fsync = off
checkpoint_timeout = 1h
```

One thing you're likely to need to do is increase the value of shmmax and shmall for your system. Google unit conversion lets us know that [2GB = 2147483648 Bytes](https://www.google.com/search?q=2gb+to+bytes) of data. Editing `/etc/sysctl.d/30-postgresql-shm.conf`, you'll want to set shmax to x Bytes, and shmall to x/4096 Bytes (actually do the division).

```bash
kernel.shmmax=2147483648
kernel.shmall=270744
```

or if you just want to enable the settings now:

```bash
sudo sysctl -w kernel.shmmax=2147483648
sudo sysctl -w kernel.shmall=270744
```
