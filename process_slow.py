from datetime import datetime, timedelta
import numpy as np
from pydap.client import open_url
import psycopg2 as pg

fields = ['apcpsfc','tmp2m']

conn = pg.connect("dbname=nam user=salexander")
cur = conn.cursor()

datatime = '2013-07-25 18:00'
url = 'http://nomads.ncep.noaa.gov:9090/dods/nam/nam20130725/nam_18z'
field = 'apcpsfc'
nam = open_url(url)

for field in fields:
  cur.execute("select insertfield('%s');" % field)
  fieldid = cur.fetchone()[0]
  datbase = nam[field]
  shp = datbase.shape
  print '------------------------'
  print '-- Processing %s, ID: %s' % (field,fieldid)
  print '------------------------'

  for it in range(0,shp[0]):
    print ''
    print 'IT: %d' % it
    print ''
    dat = datbase[it,:,:]
    t = datetime.fromordinal(int(dat.time[0])) + timedelta(hours=24*(dat.time[0]%1), days=-1)
    cur.execute("select insertdataentry(%d,'%s','%s');" % (fieldid,datatime,t))
    dataentryid = cur.fetchone()[0]
    for i in range(0,shp[1]):
      print 'Lat: %03d' % i
      for j in range(0,shp[2]):
        val = dat.array[0,i,j]
        if val < 1e15:
          cur.execute('select insertdata(%f,%f,%d,%f);' % (dat.lat[i], dat.lon[j], dataentryid, val))
      conn.commit()


