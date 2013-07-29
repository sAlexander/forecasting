# built-in libraries
from struct import pack
from io import BytesIO
from datetime import date, datetime, timedelta
import glob
import os

# third party libraries
import numpy as np
from pydap.client import open_url
import psycopg2 as pg

# local libraries
# NONE

class Model:

  # model
  modelname = ''
  urlbase   = ''
  url = ''

  # modelconn
  modelconn = None
  gridpointids = []

  # geo
  latrange  = []
  lonrange  = []
  timerange = []

  # database
  conn = None
  cur  = None
  dbversion = None
  dbmodelid = None

  #
  VERSION = '0.5.0'

  # settings
  verbose = True



  def __init__(self, modelname):
    self.modelname = modelname
    self.baseurl = 'http://nomads.ncep.noaa.gov:9090/dods/{model}/{model}{date}/{model}_{hour}z'.format(model='nam',date='{date}',hour='{hour}')

  def connect(self, **connargs):
    # TODO error checking and cursor creation
    self.conn = pg.connect(**connargs)
    self.curs = self.conn.cursor()

    try:
      self.curs.execute('select forecastingversion()')
      self.dbversion = self.curs.fetchone()[0]
    except:
      self.conn.rollback()
      self.migrate(self.VERSION)

  def migrate(self,version):
    for files in os.listdir("../db/{version}/up".format(version=version)):
      if files.endswith('.sql'):
        filename = os.path.join("../db/{version}/up".format(version=version),files)
        print 'Running migration: %s' % filename
        cmd = open(filename,'r').read()
        print cmd
        self.curs.execute(cmd)
    self.conn.commit()


  def setup(self):
    # TODO check database is at proper version

    # Get modelid
    self.curs.execute("select insertmodel('%s');" % self.modelname)
    self.dbmodelid = self.curs.fetchone()[0]

    ## Check to see if grid has correct number of entries, and cache gridids locally
    # grab the shape of the lat lon points
    field = 'apcpsfc'
    yesterday = (date.today() - timedelta(1)).strftime('%Y%m%d')
    morning = '00'
    self.modelconn = open_url(self.baseurl.format(date=yesterday, hour=morning))
    dat = self.modelconn[field]
    shp = dat.shape
    nlat = shp[1]
    nlon = shp[2]

    # grab number of gridpoints
    self.curs.execute("select count(1) from gridpoints where modelid = %d" % self.dbmodelid)
    numgridpoints = self.curs.fetchone()[0]

    if numgridpoints == nlat*nlon:
      print 'Correct grid initialized'
    else:
      print 'Initializing grid'
      lat = dat.lat[:]
      lon = dat.lon[:]
      print 'fetched grid'
      for i in range(0,nlat):
        for j in range(0,nlon):
          print i,j
          self.curs.execute("insert into public.gridpoints (modelid,geom) values(%d, ST_SetSRID(ST_MakePoint(%f, %f), 4326));" % (self.dbmodelid, lat[i], lon[j]))
      print 'finished uploading'
      self.conn.commit()
      print 'finished committing'

    lat = np.repeat(dat.lat,nlon)
    lon = np.tile(dat.lon,nlat)
    self.gridpointids = self.retrievegridids(lat,lon)

  def transfer(self, datatime, fields, geo=None):
    self.setup()
    date = datetime.strftime(datatime, '%Y%m%d')
    hour = datetime.strftime(datatime, '%H')
    self.url = self.baseurl.format(date=date,hour=hour)
    self.modelconn = open_url(self.url)
    for field in fields:
      self.processfield(field) 


  def processfield(self, field):

    print '------------------------'
    print '-- Processing %s' % field
    print '------------------------'

    # Grab information
    fieldconn = self.modelconn[field]

    # Select the fieldid
    self.curs.execute("select insertfield(%d,'%s');" % (self.dbmodelid,field))
    fieldid = self.curs.fetchone()[0]

    # prepare the data for database entry
    dtype = ([('forecastid','i4'), ('gridpointid','i4'), ('value','f8')])

    # fetch the data from the server
    fullshape = fieldconn.shape
    dim = fieldconn.dimensions

    # cases for datatypes
    TIMEONLY = 1
    TIMEANDLEV = 2
    if len(fullshape) == 3 and dim[0] == 'time':
      print 'field has three components: time, lat, lon'
      dat = fieldconn[:,:,:]
      shp = dat.shape
      ntime = shp[0]
      nlat = shp[1]
      nlon = shp[2]
      iterates = np.empty([ntime,2])
      iterates[:,0] = np.arange(0,ntime)
      iterates[:,1] = None
      itercase = TIMEONLY
    elif len(fullshape) == 4 and dim[0] == 'time' and dim[1] == 'lev':
      print 'field has four components: time, lev, lat, lon'
      dat = fieldconn[:,0:fullshape[1]:4,:,:]
      shp = dat.shape
      ntime = shp[0]
      nlev = shp[1]
      nlat = shp[2]
      nlon = shp[3]
      iterates = np.empty([ntime*nlev,2])
      iterates[:,0] = np.repeat(np.arange(0,ntime),nlev)
      iterates[:,1] = np.tile(np.arange(0,nlev),ntime)
      itercase = TIMEANDLEV
    else:
      print 'unkown shape! quitting!'
      print dim
      raise Exception('Unknown Data Shape')

    
    # loop over each timestemp and level
    for it,ilev in iterates:
      print 'IT: %d' % it

      # calculate the forecast datatime
      datatimeforecast = datetime.fromordinal(int(dat.time[it])) + timedelta(hours=24*(dat.time[it]%1), days=-1)

      # Select (or create) the forecastid
      if np.isnan(ilev):
        self.curs.execute("select insertforecast(%d,null,'%s','%s');" % (fieldid, datatime, datatimeforecast))
      else:
        lev = dat.lev[ilev]
        self.curs.execute("select insertforecast(%d,%f,'%s','%s');" % (fieldid, lev, datatime, datatimeforecast))
      forecastid = self.curs.fetchone()[0]

      # Setup the data
      data = np.empty(nlat*nlon,dtype)
      if itercase == TIMEONLY:
        data['value'] = np.reshape(dat.array[it,:,:],nlat*nlon)
      elif itercase == TIMEANDLEV:
        data['value'] = np.reshape(dat.array[it,ilev,:,:],nlat*nlon)
      data['gridpointid'] = self.gridpointids[:]
      data['forecastid'] = np.ones(nlat*nlon)*forecastid

      # Remove bad data
      data = data[data['value'] < 1e10,:]

      # Clear our entries associated with this forecastid
      self.curs.execute('delete from data where forecastid = %d' % forecastid)
      self.conn.commit()

      # Send to database
      copy_binary(data, 'data', binary=True)

  def retrievegridids(self,lat,lon):
    n = np.size(lat)
    dtype = ([('ord','i4'),('lat','f4'),('lon','f4')])
    data =np.empty(n,dtype)
    data['ord'] = np.arange(n)
    data['lat'] = lat
    data['lon'] = lon
    createtemptable = 'drop table if exists temp; create table temp (ord int primary key, lat real, lon real);'
    self.curs.execute(createtemptable)
    self.copy_binary(data,'temp',binary=True)
    selectgridids = "select gridpointid from temp inner join gridpoints as g on St_DWithin(g.geom,st_geomfromtext('POINT(' || temp.lat || ' ' || temp.lon || ')',4326),.005) order by ord;"
    self.conn.commit()
    self.curs.execute(selectgridids)
    rows = self.curs.fetchall()
    gridids = np.array(rows)
    gridids = np.reshape(gridids,np.size(gridids))
    return gridids



  def prepare_binary(self,dat):
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

  def copy_binary(self,dat, table, binary):
    cpy = self.prepare_binary(dat)
    cpy.seek(0)
    self.curs.copy_expert('COPY ' + table + ' FROM STDIN WITH BINARY', cpy)
    self.conn.commit()



if __name__ == '__main__':
  #fields = ['apcpsfc','hgtsfc','shtflsfc','soill0_10cm','soill10_40cm','soill40_100cm','soill100_200cm','soilm0_200cm','sotypsfc','pressfc','lhtflsfc','tcdcclm','tmpsfc','tmp2m','tkeprs']

  nam = Model('nam')
  nam.connect(database="nam", user="salexander")
  fields = ['apcpsfc','hgtsfc']
  datatime = datetime.strptime('Jul 21 2013  12:00PM', '%b %d %Y %I:%M%p')
  nam.transfer(datatime, fields)

