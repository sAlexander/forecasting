---
layout: post
title: Raspberry Pi + Forecasting
category: tutorials
description: A few quick notes on installing forecasting.py on a Raspberry Pi
---

Forecasting.py works perfectly on the Raspberry Pi. 

<h2 id="basic-setup">Basic Setup</h2>

Forecasting.py was tested on a Raspberry Pi, Model B with 512MB of RAM. 

A bare-bones installation of Raspbian 7.2 was installed on the 'Pi, and the 'Pi was connected directly to the router via ethernet.

Forecasting.py version 0.5.0 was tested, using the [quick start guide](/documentation/quick-start/).

<h2 id="download-performance">Download Performance</h2>

Considering the processor in the 'Pi, performance was quite good. However, it was _substantially_ slower than a mid-price desktop.

Here are a few timings:

-  **i7 3770k**: ~2 minutes to download entire nam temperature forecast (8,600,820 entries)
-  **Raspberry Pi**: ~25 minutes to download entire nam temperature forecast (8,600,820 entries)

However, the two results above were representative of the speed in other areas: inserting the grid for the nam model matched the performance above, and required no network connection.

<h2 id="query-performance">Query Performance</h2>

Query performance is quite nice. With the ~8 million records in the database, selecting one for a given time and point took 2.004 ms... speedy!

