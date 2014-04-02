#! python
from mpl_toolkits.basemap import Basemap  # import Basemap matplotlib toolkit
import numpy as np
import matplotlib.pyplot as plt
import psycopg2 as pg

from forecasting.model import Model
nam = Model('rap')
nam.connect(database='weather',user='salexander')
nam.info()

lat = nam.lat
lon = nam.lon

nlat = nam.nlat
nlon = nam.nlon

conn = pg.connect(database='weather',user='salexander')
curs = conn.cursor()

q = """
select
ord,
value
from data
inner join gridpoints gp on data.gridpointid = gp.gridpointid
inner join forecasts fcst on data.forecastid = fcst.forecastid
inner join fields fld on fcst.fieldid = fld.fieldid
inner join models m on fld.modelid = m.modelid
where 
m.name = 'rap'
and fld.name = 'wnd80m'
and fcst.datatime = (select max(datatime) from forecasts where forecasts.fieldid = fld.fieldid)
and fcst.datatime = fcst.datatimeforecast
order by gp.ord;
"""

curs.execute(q)
rows = curs.fetchall()

temp = np.empty((nlat,nlon))
lats,lons = np.meshgrid(lat,lon)
lats = np.transpose(lats)
lons = np.transpose(lons)

for row in rows:
  order = row[0]
  value = row[1]
  i = int(order/nlon)
  j = order - i*nlon
  temp[i,j] = value


plt.imshow(temp)
plt.show()

plt.col
print lon.shape
print lat.shape
print temp.shape

m = Basemap(projection='lcc',lon_0=-100, lat_0=40,width=4.e6,height=4.e6)
# m = Basemap(projection='ortho',lat_0=45,lon_0=-100,resolution='l')
x,y = m(lons,lats)
print 'minx: %f' % np.min(x)
print 'maxx: %f' % np.max(x)
print 'miny: %f' % np.min(y)
print 'miny: %f' % np.max(y)
plt.imshow(x,y,temp)
plt.show()
m.drawcoastlines()
cs = m.contourf(x,y,temp,40,cmap=plt.cm.jet,extend='both')
cbar = m.colorbar(cs,location='bottom',pad="5%")
cbar.set_label('deg C')

plt.show()

