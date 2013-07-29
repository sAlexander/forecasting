from struct import pack
from io import BytesIO
from datetime import datetime, timedelta
import numpy as np
from pydap.client import open_url
import psycopg2 as pg


def processfield(nam, field):

  print '------------------------'
  print '-- Processing %s' % field
  print '------------------------'

  # Grab information
  datbase = nam[field]

  # Select the fieldid
  curs.execute("select insertfield('%s');" % field)
  fieldid = curs.fetchone()[0]

  # prepare the data for database entry
  dtype = ([('dataentryid','i4'), ('gridid','i4'), ('value','f8')])

  # fetch the data from the server
  fullshape = datbase.shape
  dim = datbase.dimensions

  # cases for datatypes
  TIMEONLY = 1
  TIMEANDLEV = 2
  if len(fullshape) == 3 and dim[0] == 'time':
    print 'field has three components: time, lat, lon'
    dat = datbase[:,:,:]
    shp = dat.shape
    ltime = shp[0]
    llat = shp[1]
    llong = shp[2]
    iterates = np.empty([ltime,2])
    iterates[:,0] = np.arange(0,ltime)
    iterates[:,1] = None
    itercase = TIMEONLY
  elif len(fullshape) == 4 and dim[0] == 'time' and dim[1] == 'lev':
    print 'field has four components: time, lev, lat, lon'
    dat = datbase[:,0:fullshape[1]:4,:,:]
    shp = dat.shape
    ltime = shp[0]
    llev = shp[1]
    llat = shp[2]
    llong = shp[3]
    iterates = np.empty([ltime*llev,2])
    iterates[:,0] = np.repeat(np.arange(0,ltime),llev)
    iterates[:,1] = np.tile(np.arange(0,llev),ltime)
    itercase = TIMEANDLEV
  else:
    print 'unkown shape! quitting!'
    print dim
    raise Exception('Unknown Data Shape')

  
  print shp

  # Grab the gridids from the server
  lat = np.repeat(dat.lat,llong)
  lon = np.tile(dat.lon,llat)
  gridids = retrievegridids(lat,lon)

  
  # dimensions to loop over

  # loop over each timestemp
  for it,ilev in iterates:
    print ''
    print 'IT: %d' % it
    print ''

    # calculate the forecast datatime
    datatimeforecast = datetime.fromordinal(int(dat.time[it])) + timedelta(hours=24*(dat.time[it]%1), days=-1)

    # Select (or create) the dataentryid
    if np.isnan(ilev):
      curs.execute("select insertdataentry(%d,null,'%s','%s');" % (fieldid, datatime, datatimeforecast))
    else:
      lev = dat.lev[ilev]
      curs.execute("select insertdataentry(%d,%f,'%s','%s');" % (fieldid, lev, datatime, datatimeforecast))
    dataentryid = curs.fetchone()[0]

    # Setup the data
    data = np.empty(llat*llong,dtype)
    if itercase == TIMEONLY:
      data['value'] = np.reshape(dat.array[it,:,:],llat*llong)
    elif itercase == TIMEANDLEV:
      data['value'] = np.reshape(dat.array[it,ilev,:,:],llat*llong)
    data['gridid'] = gridids[:]
    data['dataentryid'] = np.ones(llat*llong)*dataentryid

    # Remove bad data
    data = data[data['value'] < 1e10,:]

    print data

    # Clear our entries associated with this dataentryid
    curs.execute('delete from data where dataentryid = %d' % dataentryid)
    conn.commit()

    # Send to database
    copy_binary(data, 'data', binary=True)

def retrievegridids(lat,lon):
  n = np.size(lat)
  dtype = ([('ord','i4'),('lat','f4'),('lon','f4')])
  data =np.empty(n,dtype)
  data['ord'] = np.arange(n)
  data['lat'] = lat
  data['lon'] = lon
  createtemptable = 'drop table if exists temp; create table temp (ord int primary key, lat real, lon real);'
  curs.execute(createtemptable)
  copy_binary(data,'temp',binary=True)
  selectgridids = "select gridid from temp inner join grid on St_DWithin(grid.geom,st_geomfromtext('POINT(' || temp.lat || ' ' || temp.lon || ')',4326),.005) order by ord;"
  conn.commit()
  curs.execute(selectgridids)
  rows = curs.fetchall()
  gridids = np.array(rows)
  gridids = np.reshape(gridids,np.size(gridids))
  return gridids



def prepare_binary(dat):
  # found here: http://stackoverflow.com/questions/8144002/use-binary-copy-table-from-with-psycopg2
  pgcopy_dtype = [('num_fields','>i2')]
  for field, dtype in dat.dtype.descr:
    pgcopy_dtype += [(field + '_length', '>i4'),
                        (field, dtype.replace('<', '>'))]
  pgcopy = np.empty(dat.shape, pgcopy_dtype)
  pgcopy['num_fields'] = len(dat.dtype)
  for i in range(len(dat.dtype)):
    field = dat.dtype.names[i]
    pgcopy[field + '_length'] = dat.dtype[i].alignment
    pgcopy[field] = dat[field]
  cpy = BytesIO()
  cpy.write(pack('!11sii', b'PGCOPY\n\377\r\n\0', 0, 0))
  cpy.write(pgcopy.tostring())  # all rows
  cpy.write(pack('!h', -1))  # file trailer
  return(cpy)

def copy_binary(dat, table, binary):
  cpy = prepare_binary(dat)
  cpy.seek(0)
  curs.copy_expert('COPY ' + table + ' FROM STDIN WITH BINARY', cpy)
  conn.commit()
  tend = datetime.now()



if __name__ == '__main__':
  fields = ['apcpsfc','hgtsfc','shtflsfc','soill0_10cm','soill10_40cm','soill40_100cm','soill100_200cm','soilm0_200cm','sotypsfc','pressfc','lhtflsfc','tcdcclm','tmpsfc','tmp2m','tkeprs']

  conn = pg.connect("dbname=nam user=salexander")
  curs = conn.cursor()

  datatime = '2013-07-25 18:00'
  url = 'http://nomads.ncep.noaa.gov:9090/dods/nam/nam20130725/nam_18z'
  nam = open_url(url)
  for field in fields:
    processfield(nam,field)
