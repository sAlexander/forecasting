import numpy as np
from pydap.client import open_url
import psycopg2 as pg

conn = pg.connect("dbname=nam user=salexander")
cur = conn.cursor()

url = 'http://nomads.ncep.noaa.gov:9090/dods/nam/nam20130725/nam_18z'
field = 'apcpsfc'
nam = open_url(url)

dat = nam[field]
dat = dat[0,:,:]
shp = dat.shape
for i in range(0,shp[1]):
  for j in range(0,shp[2]):
    cur.execute("insert into public.grid (geom) values(ST_SetSRID(ST_MakePoint(%f, %f), 4326))" % (dat.lat[i], dat.lon[j]))

conn.commit()
cur.close()
conn.close()



