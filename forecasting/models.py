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

class model:
  """Initialize a forecasting model with a given model name (nam, gfs, etc)

  To use,
  m = forecasting.model(modelabbr)

  Options at the moment are:
  nam,gfs,rap,rtma,gfs_hd

  Just about everything here:
  http://nomads.ncep.noaa.gov:9090/dods/
  """

  # model
  modelname = ''
  urlbase   = ''
  url = ''

  # modelconn
  modelconn = None
  gridpointids = []

  # geo
  lats = []
  lons  = []
  timerange = []

  # database
  conn = None
  cur  = None
  dbversion = None
  dbmodelid = None

  # misc
  fpath = os.path.dirname(os.path.abspath(__file__))

  #
  VERSION = '0.5.0'

  # settings
  verbose = True



  def __init__(self, modelname):
    """Initilize the model with a modelname and set the url for the datafeed"""
    self.modelname = modelname
    self.baseurl = 'http://nomads.ncep.noaa.gov:9090/dods/{model}/{model}{date}/{model}_{hour}z'.format(model=modelname,date='{date}',hour='{hour}')

  def connect(self, **connargs):
    """Connect to postgis database and ensure the database has been properly setup

    Sample usage:
    m = forecasting.model(modelabbr)
    m.connect(database="weather",user="ubuntu",password="magic",hostname="localhost")

    If you're getting a 'Error connecting to database' exception, try connecting with psycgp2:

    import psycpg2 as pg
    pg.connect(PUT_ARGUMENTS_HERE)
    """
    try:
      self.conn = pg.connect(**connargs)
      self.curs = self.conn.cursor()
    except:
      raise Exception('Error connecting to database. Can you connect with the same parameters using psycpg2?')
    print 'Successfully connected to database'

    print 'Checking database version'
    try:
      self.curs.execute('select forecastingversion()')
      self.dbversion = self.curs.fetchone()[0]
    except:
      self.conn.rollback()
      self._migrate(self.VERSION)

  def transfer(self, fields, datatime=None, geo=None):
    """Transfer a set of fields for a given timestamp into the connected postgis database

    Usage:
    m = models('nam')
    m.connect(database="weather")
    fields = ['acpcpsfc','tmp2m'] # gfs
    datatime = datetime.strptime('Aug 02 2013 12:00PM', '%b %d %Y %I:%M%p')
    nam.transfer(datatime, fields)

    Eventually, there will also be a geo dictionary that can be used to specify a prefered
    lat/lon boundary (ie only grab a subset of available data), but at the moment, it's all or nothing.

    """

    # check for proper grid, set up if not present, and cache gridids
    self._setup()

    if datatime == None:
      datatime = datetime.strptime('Feb 02 2014 12:00PM', '%b %d %Y %I:%M%p')

    # create appropriate url
    date = datetime.strftime(datatime, '%Y%m%d')
    hour = datetime.strftime(datatime, '%H')
    self.url = self.baseurl.format(date=date,hour=hour)

    # Connect using pydap to the opendap server
    self.modelconn = open_url(self.url)

    # Process each field
    for field in fields:
      self._processfield(field,datatime) 

  def _migrate(self,version):
    """ Migrate the database to the correct version. This should be moved into a new class"""
    for files in os.listdir(os.path.join(self.fpath,"db/{version}/up".format(version=version))):
      if files.endswith('.sql'):
        filename = os.path.join(self.fpath,"db/{version}/up".format(version=version),files)
        print 'Running migration: %s' % filename
        cmd = open(filename,'r').read()
        print cmd
        self.curs.execute(cmd)
    self.conn.commit()


  def _setup(self):
    """Setup the grid and cache the gridpoints"""

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
    self.lats = data.lat[:]
    self.lons = data.lon[:]

    # grab number of gridpoints
    self.curs.execute("select count(1) from gridpoints where modelid = %d" % self.dbmodelid)
    numgridpoints = self.curs.fetchone()[0]

    if numgridpoints == nlat*nlon:
      print 'Correct grid initialized'
    else:
      print 'Initializing grid'
      lat = self.lats
      lon = self.lons
      for i in range(0,nlat):
        print 'Loading lat ',i
        for j in range(0,nlon):
          order = i*nlon+j
          self.curs.execute("insert into public.gridpoints (modelid,geom,ord) values(%d, ST_SetSRID(ST_MakePoint(%f, %f), 4326),%d);" % (self.dbmodelid, lat[i], lon[j], order))
      self.conn.commit()
      print 'Finished initializing grid'


    # cache the gridpoints
    self.gridpointids = self._retrievegridids()



  def _processfield(self, field, datatime):

    print '------------------------'
    print '-- Processing %s' % field
    print '------------------------'

    # Grab information
    fieldconn = self.modelconn[field]

    # Select the fieldid
    self.curs.execute("select insertfield(%d,'%s');" % (self.dbmodelid,field))
    fieldid = self.curs.fetchone()[0]

    # prepare the data for database entry
    dtype = ([('forecastid','i4'), ('gridpointid','i4'), ('value','f4')])

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
      self._copybinary(data, 'data')


  def _parsegeos(self,geo):
    # parse the goes list or dictionary

    results = []

    ###############
    ## if it's a single geo item already in dict form, parse it!
    if isinstance(geo,dict):
      # if it's a single point definition
      if all (k in geo for k in ('lat','lon')):
        if 'k' not in geo:
          geo['k'] = 1
        # run query to find the k closest points
        "select gridpointid, ST_AsText(geom) from gridpoints gp order by gp.geom <-> ST_SetSRID(ST_MakePoint(40,-105),4326) limit 5;"

        # what if it's quicker to do a single bound? Check for this?

      # if it's a bounded point
      elif all (k in geo for k in ('n','s','e','w')):
        if 'i' not in geo:
          geo['i'] = 1
        sbound = np.argmax(self.lat >= geo['s']) 
        nbound = np.argmax(self.lat >= geo['n']) - 1
        wbound = np.argmax(self.lon >= geo['w']) 
        ebound = np.argmax(self.lon >= geo['e']) - 1

        # find bounds that include n,s,e,w

      # we don't know what it is
      else:
        print('Geos does not match expected form. See geos doc')
        raise Exception('Unknown geos form')

    ###############
    ## if it's a list of geos, recursively call this function
    elif isinstance(geo,list) or isinstance(geo,tuple):
      for g in geo:
        results.extend(self._parsegeos(self,g))

    ###############
    ## we don't know what it is!?!?
    else:
      print 'Unknown geos type... it should be a dictionary or a list'
      raise Exception('Unknown geos type')
    
    # return the list of geos
    return results



  def _retrievegridids(self):
    selectgridids = "select gridpointid from gridpoints where gridpoints.modelid = %d order by ord;" % self.dbmodelid
    self.conn.commit()
    self.curs.execute(selectgridids)
    rows = self.curs.fetchall()
    gridids = np.array(rows)
    gridids = np.reshape(gridids,np.size(gridids))
    return gridids



  def _preparebinary(self,dat):
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

  def _copybinary(self,dat, table,columns=''):
    cpy = self._preparebinary(dat)
    cpy.seek(0)
    self.curs.copy_expert('COPY ' + table + ' FROM STDIN WITH BINARY', cpy)
    self.conn.commit()



if __name__ == '__main__':
  #fields = ['apcpsfc','hgtsfc','shtflsfc','soill0_10cm','soill10_40cm','soill40_100cm','soill100_200cm','soilm0_200cm','sotypsfc','pressfc','lhtflsfc','tcdcclm','tmpsfc','tmp2m','tkeprs']

  nam = model('nam')
  nam.connect(database="nam", user="ubuntu")
  fields = ['acpcpsfc','tmp2m'] # gfs
  datatime = datetime.strptime('Aug 02 2013 12:00PM', '%b %d %Y %I:%M%p')
  nam.transfer(datatime, fields)
