#! python
from mpl_toolkits.basemap import Basemap  # import Basemap matplotlib toolkit
import numpy as np
import matplotlib.pyplot as plt
import psycopg2 as pg

conn = pg.connect(database='weather',user='salexander',port=5433)
curs = conn.cursor()

q = """
select
ST_X(geom),
ST_Y(geom),
value
from data
inner join gridpoints gp on data.gridid = gp.gridpointid
inner join forecasts fcst on data.forecastid = fcst.forecastid
inner join fields fld on fcst.fieldid = fld.fieldid
inner join models m on fld.modelid = m.modelid
where 
m.name = 'nam'
and fld.name = 'tmp2m'
and fcst.datatime = (select max(datatime) from forecasts where forecasts.fieldid = fld.fieldid)
and fcst.datatime = fcst.datatimeforecast
order by gp.ord;
"""

curs.execute(q)
rows = curs.fetchall()

lats = np.array([i[0] for i in rows])
lons = np.array([i[1] for i in rows])
temp = np.array([i[2] for i in rows])


m = Basemap(projection='lcc',lon_0=-100, lat_0=40,width=4.e6,height=4.e6)

x,y = m(lons,lats)

m.drawcoastlines()
m.drawcountries()
m.drawstates()
parallels = np.arange(0.,80,20.)
m.drawparallels(parallels,labels=[1,0,0,1])
meridians = np.arange(10.,360.,30.)
m.drawmeridians(meridians,labels=[1,0,0,1])

cs = m.contourf(x,y,temp,np.linspace(250,300,40),cmap=plt.cm.jet,extend='both', tri=True)
cbar = m.colorbar(cs,location='bottom',pad="5%")
cbar.set_label('deg C')

plt.show()

