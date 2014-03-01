#! python
from mpl_toolkits.basemap import Basemap  # import Basemap matplotlib toolkit
import numpy as np
import matplotlib.pyplot as plt
import psycopg2 as pg
import json

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
m.name = 'rap'
and fld.name = 'snodsfc'
and fcst.datatime = (select max(datatime) from forecasts where forecasts.fieldid = fld.fieldid)
and fcst.datatime = fcst.datatimeforecast
order by gp.ord;
"""

curs.execute(q)
rows = curs.fetchall()

lats = np.array([i[0] for i in rows])
lons = np.array([i[1] for i in rows])
temp = np.array([i[2] for i in rows])


m = Basemap(projection='lcc',lon_0=-100, lat_0=40,width=5.e6,height=5.e6)

x,y = m(lons,lats)

m.drawcoastlines()
m.drawcountries()
m.drawstates()
parallels = np.arange(0.,80,20.)
m.drawparallels(parallels,labels=[1,0,0,1])
meridians = np.arange(10.,360.,30.)
m.drawmeridians(meridians,labels=[1,0,0,1])

maxval = [0.25,8]
cs = m.contourf(lons,lats,temp,maxval,extend='neither', tri=True)

geos = []
print len(cs.collections)
for collection in cs.collections:
    print len(collection.get_paths())
    for path in collection.get_paths():
        for polygon in path.to_polygons():
            if len(polygon)>3:
                poly = {
                        'type': 'Polygon',
                        'coordinates': [polygon.tolist()]}
                geos.append(poly)

geometries = {
        'type': 'GeometryCollection',
        'geometries': geos }


snow = open('snow.json','w')
snow.write(json.dumps(geometries))
snow.close()
