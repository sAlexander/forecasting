#! python
from mpl_toolkits.basemap import Basemap  # import Basemap matplotlib toolkit
import numpy as np
import matplotlib.pyplot as plt
import psycopg2 as pg

conn = pg.connect(database='weather',user='salexander')
curs = conn.cursor()

q = """
select
ST_X(geom),
ST_Y(geom),
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

lons = np.array([i[0] for i in rows])
lats = np.array([i[1] for i in rows])
temp = np.array([i[2] for i in rows])

dpi = 200.0
a = 0.562264326368
w = 1800.0
h = w*a



fig = plt.figure(frameon = False)
fig.set_size_inches(w/dpi,h/dpi)
ax = plt.axes([0,0,1,1])
m = Basemap(projection='merc',llcrnrlat=24,urcrnrlat=50,llcrnrlon=-125,urcrnrlon=-66)
print m.aspect

x,y = m(lons,lats)

maxtemp = np.max(temp)
print maxtemp

cs = m.contourf(x,y,temp,np.linspace(3,15,10),cmap=plt.cm.Reds,extend='both', tri=True)
plt.savefig('nowhite.png', dpi=dpi)
