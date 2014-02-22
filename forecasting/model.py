# built-in libraries
from struct import pack
from io import BytesIO
from datetime import date, datetime, timedelta
import glob
import os
import re
import urllib2

# third party libraries
import numpy as np
from pydap.client import open_url
import psycopg2 as pg

# local libraries
# NONE

class Model:
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
    baseurl   = ''
    timeurl  = ''
    url = ''

    # modelconn
    modelconn = None
    gridpointids = []

    # geo
    lat = []
    lon  = []
    nlat = None
    nlon = None
    daterange = []

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
        self.timeurl = 'http://nomads.ncep.noaa.gov:9090/dods/{model}'.format(model=modelname)

    def info(self):
        """Describe the current model. This includes things like the model name, url, number of lat/lon, etc"""

        self._setup()

        print '----------------------'
        print '-- Model Name: %s' % self.modelname
        print '----------------------'
        print ''
        print 'URL: %s' % self.baseurl
        print ''
        print 'LATITUDE'
        print 'num: %d' % self.nlat
        print 'min: %f' % np.min(self.lat)
        print 'max: %f' % np.max(self.lat)
        print ''
        print 'LONGITUDE'
        print 'num: %d' % self.nlon
        print 'min: %f' % np.min(self.lon)
        print 'max: %f' % np.max(self.lon)
        print ''
        print 'TIME'
        print 'min: %s' % datetime.strftime(datetime.strptime(str(self.daterange[0]), '%Y%m%d'),'%Y-%m-%d')
        print 'max: %s' % datetime.strftime(datetime.strptime(str(self.daterange[1]), '%Y%m%d'),'%Y-%m-%d')



    def getdaterange(self):
        """Get the date range for the current model"""

        regex = re.compile("%s(\d{8})" % self.modelname)
        f = urllib2.urlopen(self.timeurl)

        results = regex.findall(f.read())
        numdates = [int(i) for i in results]
        return [np.min(numdates), np.max(numdates)]

    def getlatesttime(self):
        """Get the datatime for the latest time available"""

        # refresh the daterange
        self.daterange = self.getdaterange()
        lastday = self.daterange[1]

        result = None
        for hour in range(0,24):
            datatime = datetime.strptime('%s%02d' % (lastday, hour), '%Y%m%d%H')
            url = self._createurl(datatime)
            res = self._checkurl(url)
            if res == True:
                result = datatime
        return result


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

    def transfer(self, fields, datatime=None, geos=None):
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

        if geos == None:
            bounds=[[[0,self.nlat,1],[0,self.nlon,1]]]
        else:
            print '-----------------------------'
            print '-- parsing geos information:'
            print '-----------------------------'
            bounds = self._parsegeos(geos)


        # create the url for the datatime
        url = self._createurl(datatime)

        # check the url
        check = self._checkurl(url)
        if check == True:
            print 'Datatime is available on the remote server'
            self.url = url
        else:
            print 'Datatime is not available on the remote server'
            raise Exception('Datatime is not available on the remote server')

        # Connect using pydap to the opendap server
        self.modelconn = open_url(self.url)

        # Process each field
        for field in fields:
            for bound in bounds:
                self._processfield(field,datatime,bound)

    def _createurl(self,datatime):
        # create appropriate url
        date = datetime.strftime(datatime, '%Y%m%d')
        hour = datetime.strftime(datatime, '%H')
        return self.baseurl.format(date=date,hour=hour)

    def _checkurl(self,url):
        # We have to check the das file for an error
        f = urllib2.urlopen(url+'.das')
        response = f.read()
        if response[0:5] == 'Error':
            return False
        else:
            return True

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

        # Get the time range
        self.daterange = self.getdaterange()

        ## Check to see if grid has correct number of entries, and cache gridids locally
        # grab the shape of the lat lon points
        field = 'tmp2m'
        datatime = self.getlatesttime()
        url = self._createurl(datatime)
        self.modelconn = open_url(url)
        dat = self.modelconn[field]
        shp = dat.shape
        nlat = shp[1]
        nlon = shp[2]
        self.nlat = nlat
        self.nlon = nlon
        self.lat = dat.lat[:]
        self.lon = dat.lon[:]

        # grab number of gridpoints
        self.curs.execute("select count(1) from gridpoints where modelid = %d" % self.dbmodelid)
        numgridpoints = self.curs.fetchone()[0]

        if numgridpoints == nlat*nlon:
            print 'Correct grid initialized'
        else:
            print 'Initializing grid'
            lat = self.lat
            lon = self.lon
            for i in range(0,nlat):
                print 'Loading lat ',i
                for j in range(0,nlon):
                    order = i*nlon+j
                    self.curs.execute("insert into public.gridpoints (modelid,geom,ord) values(%d, ST_SetSRID(ST_MakePoint(%f, %f), 4326),%d);" % (self.dbmodelid, lat[i], lon[j], order))
            self.conn.commit()
            print 'Finished initializing grid'


        # cache the gridpoints
        self.gridpointids = self._retrievegridids()



    def _processfield(self, field, datatime, bound):

        print '------------------------'
        print '-- Processing %s' % field
        print '------------------------'

        # Tell pydap which field we're interested in
        fieldconn = self.modelconn[field]

        # Select the fieldid from the database
        self.curs.execute("select insertfield(%d,'%s');" % (self.dbmodelid,field))
        fieldid = self.curs.fetchone()[0]

        # prepare a data structure for database entry
        dtype = ([('forecastid','i4'), ('gridpointid','i4'), ('value','f4')])

        # fetch shape information about the data
        fullshape = fieldconn.shape
        dim = fieldconn.dimensions

        # cases for datatypes
        TIMEONLY = 1
        TIMEANDLEV = 2

        # set the bounds
        ilats = bound[0][0]
        ilate = bound[0][1]
        ilati = bound[0][2]
        ilons = bound[1][0]
        ilone = bound[1][1]
        iloni = bound[1][2]
        latrange = np.arange(ilats,ilate,ilati)
        lonrange = np.arange(ilons,ilone,iloni)



        if len(fullshape) == 3 and dim[0] == 'time':
            print 'field has three components: time, lat, lon'

            # grab the data container
            dat = fieldconn[:,ilats:ilate:ilati,ilons:ilone:iloni]

            # grab information about the container shape
            shp = dat.shape
            ntime = shp[0]
            nlat = shp[1]
            nlon = shp[2]

            # create iterates to loop over
            iterates = np.empty([ntime,2])
            iterates[:,0] = np.arange(0,ntime)
            iterates[:,1] = None
            itercase = TIMEONLY
        elif len(fullshape) == 4 and dim[0] == 'time' and dim[1] == 'lev':
            print 'field has four components: time, lev, lat, lon'

            # grab the data container
            dat = fieldconn[:,0:fullshape[1]:4, ilats:ilate:ilati,ilons:ilone:iloni]

            # grab information about the container shape
            shp = dat.shape
            ntime = shp[0]
            nlev = shp[1]
            nlat = shp[2]
            nlon = shp[3]

            # create iterates to loop over
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

            # set up the grid point holder
            tord = []
            for i in latrange:
                for j in lonrange:
                    tord.append(i*self.nlon + j)

            # fill up the data structure from the data container
            data = np.empty(nlat*nlon,dtype)
            if itercase == TIMEONLY:
                data['value'] = np.reshape(dat.array[it,:,:],nlat*nlon)
            elif itercase == TIMEANDLEV:
                data['value'] = np.reshape(dat.array[it,ilev,:,:],nlat*nlon)
            data['gridpointid'] = self.gridpointids[tord]
            data['forecastid'] = np.ones(nlat*nlon)*forecastid

            # Remove bad data
            data = data[data['value'] < 1e10,:]

            # Send to database
            try:
                # this will fail if there are duplicates, but it's way faster
                self.conn.commit()
                self._copybinary(data, 'data')
            except:
                # try to insert more safely
                self.conn.rollback()
                self._copybinary(data, 'stagingdata')
                self.curs.execute('select applystagingdata();')
                self.conn.commit()


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
                q = "select ord, ST_AsText(geom) from gridpoints gp where gp.modelid = %d order by gp.geom <-> ST_SetSRID(ST_MakePoint(%f,%f),4326) limit %d;" % (self.dbmodelid, geo['lat'],geo['lon'],geo['k'])
                self.curs.execute(q)
                rows = self.curs.fetchall()
                for order in rows:
                    order = order[0]
                    ilat = int(order/self.nlon)
                    ilon = order % self.nlon
                    results.append([[ilat,ilat+1,1],[ilon,ilon+1,1]])
                    print 'latitude = %f' % self.lat[ilat]
                    print 'longitude = %f' % self.lon[ilon]
                    print ''


                # what if it's quicker to do a single bound? Check for this?

            # if it's a bounded point
            elif all (k in geo for k in ('n','s','e','w')):
                if 'i' not in geo:
                    geo['i'] = 1
                sbound = np.argmax(self.lat >= geo['s'])
                nbound = np.argmax(self.lat >= geo['n'])
                wbound = np.argmax(self.lon >= geo['w'])
                ebound = np.argmax(self.lon >= geo['e'])

                results.append([[sbound,nbound,geo['i']],[wbound,ebound,geo['i']]])
                # find bounds that include n,s,e,w

            # we don't know what it is
            else:
                print('Geos does not match expected form. See geos doc')
                raise Exception('Unknown geos form')

        ###############
        ## if it's a list of geos, recursively call this function
        elif isinstance(geo,list) or isinstance(geo,tuple):
            for g in geo:
                results.extend(self._parsegeos(g))

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

    nam = Model('nam')
    nam.connect(database="weather", user="salexander")
    datatime =  nam.getlatesttime()
    geos = {'lat': 39.97316, 'lon': -105.145, 'k':8}
    fields = ['tmp2m'] # nam
    nam.transfer(fields, datatime,geos=geos)
