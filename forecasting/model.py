# built-in libraries
from datetime import date, datetime, timedelta
import glob
import os
import re
import urllib2

# third party libraries
import numpy as np
from pydap.client import open_url
import pydap.lib
pydap.lib.CACHE = "/tmp/pydap-cache/"

# local libraries
from database import Database
import util

class Model:
    """
    Initialize a forecasting model with a given model name (nam, gfs, etc)

    Usage:
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
    lev = []
    nlat = None
    nlon = None
    nlev = None
    daterange = []

    # database
    database = None

    # calculated fields
    calcfields = []

    # misc
    fpath = os.path.dirname(os.path.abspath(__file__))

    # settings
    verbose = True



    def __init__(self, modelname):
        """
        Initilize the model with a modelname and set the url for the datafeed
        """
        self.modelname = modelname
        self.baseurl = 'http://nomads.ncep.noaa.gov:9090/dods/{model}/{model}{date}/{model}_{hour}z'.format(model=modelname,date='{date}',hour='{hour}')
        self.timeurl = 'http://nomads.ncep.noaa.gov:9090/dods/{model}'.format(model=modelname)

    def connect(self, **connargs):
        """
        Connect to postgis database and ensure the database has been properly setup

        Sample usage:
        m = forecasting.model('nam')
        m.connect(database="weather",user="ubuntu",password="magic",hostname="localhost")

        If you're getting a 'Error connecting to database' exception, try connecting with psycgp2:

        import psycpg2 as pg
        pg.connect(PUT_ARGUMENTS_HERE)
        """

        self.database = Database(**connargs)

    def info(self):
        """
        Describe the current model. This includes things like the model name, url, number of lat/lon, etc

        Usage:
        m = forecasting.model('nam')
        m.connect(database='weather')
        m.info()
        """

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
        """
        Get the date range for the current model

        Usage:
        m = forecasting.model('nam')
        m.connect(database='weather')
        m.getdaterange()
        """

        regex = re.compile("%s(\d{8})" % self.modelname)
        f = urllib2.urlopen(self.timeurl)

        results = regex.findall(f.read())
        numdates = [int(i) for i in results]
        return [np.min(numdates), np.max(numdates)]

    def getlatesttime(self):
        """
        Get the datatime for the latest time available

        Usage:
        m = forecasting.model('nam')
        m.connect(database='weather')
        m.getlatesttime()
        """

        print 'Getting the latest time'

        # refresh the daterange
        self.daterange = self.getdaterange()
        lastday = self.daterange[1]

        # search for the largest hour which is true using the bisection method
        result = None
        range = [0,24]
        while (range[1]-range[0]) > 0:
            print range
            hour = (range[1]+range[0])/2 # nb: this will round down
            datatime = datetime.strptime('%s%02d' % (lastday, hour), '%Y%m%d%H')
            url = self._createurl(datatime)
            res = self._checkurl(url)
            if res == True:
                result = datatime
                if range[0] == hour:
                    range[0] = hour+1
                else:
                    range[0] = hour
            else:
                range[1] = hour
        return result


    def transfer(self, fields, datatime=None, geos=None, pressure=None):
        """
        Transfer a set of fields for a given timestamp into the connected postgis database

        Usage
        -----------
        m = models('nam')
        m.connect(database="weather")
        fields = ['acpcpsfc','tmp2m'] # gfs
        datatime = datetime.strptime('Aug 02 2013 12:00PM', '%b %d %Y %I:%M%p')
        nam.transfer(fields=fields, datatime=datatime)

        Arguments
        -----------
        Arguments are:
          * fields: a list of fields to be processed
            datatime: the datatime to pull the forecast. Defaults to most recent time
            geos: geographic bounding for the forecast. Defaults to the entire model. See below for format.
            pressure: Pressure levels to grab, where appropriate. Defaults to every fourth level. see below for format.


        Geos format
        -------------
        geos = [{ # Bounded Box
                'n': 41.00,   # * required
                's': 39.00,   # * required
                'e': -99.00,  # * required
                'w': -101.00, # * required
                'i':2         # (optional) download every ith datapoint, defaults to 1.
            },{ # Point with Neighbors
                'lat': 38.00, # * required
                'lon': -100.00, # * required
                'k':8 # (optional) nearest neighbors defaults to 1 (ie only itself).
            }]

        Pressure format
        ------------- 
        pressure = {'min': 25,   # * required, minimum pressure in mb
                    'max': 1000, # * required, max pressure in mb
                    'i': 4}      # (optional) download every ith pressure level, defaults to 1.

        Eventually, there will also be a geo dictionary that can be used to specify a prefered
        lat/lon boundary (ie only grab a subset of available data), but at the moment, it's all or nothing.

        """

        # check for proper grid, set up if not present, and cache gridids
        self._setup()

        if datatime == None:
            datatime = self.getlatesttime()


        if geos == None:
            geobounds=[[[0,self.nlat,1],[0,self.nlon,1]]]
        else:
            print '-----------------------------'
            print '-- parsing geos information:'
            print '-----------------------------'
            geobounds = self._parsegeos(geos)

        if pressure == None:
            levbounds = [0,self.nlev,4]
        else:
            if not all([x in pressure for x in ['min','max']]):
                raise Exception('Pressure requires a min and a max value')
            ilevs = self._indexf(self.lev,lambda x: x <= pressure['max'])
            if ilevs > 0:
                ilevs = ilevs-1
            ileve = self._indexf(self.lev,lambda x: x <= pressure['min'])
            if 'i' in pressure:
                ilevi = pressure['i']
            else:
                ilevi = 1
            levbounds = [ilevs, ileve, ilevi]


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
            for geobound in geobounds:
                self._processfield(field,datatime,geobound,levbounds)

        # calculate any calculated fields
        for calc in self.calcfields:
            for f, p in calc.items():
                print '------------------------'
                print '-- Calculating %s' % f
                print '------------------------'
                try:
                    self.database.calculatefield(f,p['dependents'],p['calculation'],datatime)
                except:
                    print 'Error calculating field for %s' % f

    def addcalculatedfield(self,fieldname,dependents,calculation):
        """
        Add a calculated field to the database. Each time new model data is added into the database, the calculated field will be run.


        Usage:
        m = forecasting.model('nam')
        m.connect(database='weather')

        fieldname = 'windspeed'
        dependents = ['uvelocity','vvelocity']
        calculation = 'sqrt(uvelocity^2 + vvelocity^2)'

        m.addcalculatedfield(fieldname, dependents, calculation)
        """

        self.calcfields.append({fieldname:{'dependents': dependents, 'calculation': calculation}})

    def _indexf(self,l,f):
        """
        simple little helper function to find the index of the first true evaluation
        """

        for i,il in enumerate(l):
            if f(il):
                return i

    def _createurl(self,datatime):
        """
        create appropriate url
        """

        date = datetime.strftime(datatime, '%Y%m%d')
        hour = datetime.strftime(datatime, '%H')
        return self.baseurl.format(date=date,hour=hour)

    def _checkurl(self,url):
        """
        We have to check the das file for an error
        """

        try:
            util.request(url+'.dds')
            return True
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except:
            return False




    def _setup(self):
        """
        Setup the grid and cache the gridpoints
        """

        self.database.cachemodelid(self.modelname)


        # Get the time range
        self.daterange = self.getdaterange()

        ## Check to see if grid has correct number of entries, and cache gridids locally
        # grab the shape of the lat lon points
        field = 'tmpprs'
        datatime = self.getlatesttime()
        url = self._createurl(datatime)
        self.modelconn = open_url(url)
        dat = self.modelconn[field]
        shp = dat.shape
        nlat = shp[2]
        nlon = shp[3]
        nlev = shp[1]
        self.nlat = nlat
        self.nlon = nlon
        self.nlev = nlev
        self.lat = dat.lat[:]
        self.lon = dat.lon[:]
        self.lev = dat.lev[:]


        numgridpoints = self.database.numberofgridpoints()
        if numgridpoints == nlat*nlon:
            print 'Correct grid initialized'
        else:
            print 'Initializing grid'
            self.database.setupgrid(self.lat,self.lon)

        # cache the gridpoints
        self.gridpointids = self.database.retrievegridids()



    def _processfield(self, field, datatime, geobound,levbound):

        print '------------------------'
        print '-- Processing %s' % field
        print '------------------------'

        # Tell pydap which field we're interested in
        fieldconn = self.modelconn[field]

        fieldid = self.database.getfieldid(field)

        # prepare a data structure for database entry
        dtype = ([('forecastid','i4'), ('gridpointid','i4'), ('value','f4')])

        # fetch shape information about the data
        fullshape = fieldconn.shape
        dim = fieldconn.dimensions

        # cases for datatypes
        TIMEONLY = 1
        TIMEANDLEV = 2

        # set the geobounds
        ilats = geobound[0][0]
        ilate = geobound[0][1]
        ilati = geobound[0][2]
        ilons = geobound[1][0]
        ilone = geobound[1][1]
        iloni = geobound[1][2]
        latrange = np.arange(ilats,ilate,ilati)
        lonrange = np.arange(ilons,ilone,iloni)

        # set the pressure bounds
        ilevs = levbound[0]
        ileve = levbound[1]
        ilevi = levbound[2]



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
            dat = fieldconn[:,ilevs:ileve:ilevi, ilats:ilate:ilati,ilons:ilone:iloni]

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
                lev = None
            else:
                idxlev = ilevs + ilev*ilevi
                lev = self.lev[idxlev]
            forecastid = self.database.getforecastid(fieldid,datatime,datatimeforecast,lev)


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
            data = data[data['value'] < 1e10]

            # Send to database
            self.database.senddata(data)



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
                results = self.database.getknn(geo['lat'],geo['lon'],geo['k'],self.nlon)
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

if __name__ == '__main__':
    #fields = ['apcpsfc','hgtsfc','shtflsfc','soill0_10cm','soill10_40cm','soill40_100cm','soill100_200cm','soilm0_200cm','sotypsfc','pressfc','lhtflsfc','tcdcclm','tmpsfc','tmp2m','tkeprs']

    rap = Model('nam')
    rap.connect(database="weather", user="salexander")
    datatime =  rap.getlatesttime()
    geos = {'lat': 39.97316, 'lon': -105.145}
    pressure = {'min':600,'max':1000};
    fields = [
            'tmpsfc',  # Surface temperature
            'pressfc', 
            'hpblsfc',
            'hgtprs', 'hgtsfc',
            'ugrdprs','ugrd10m',
            'vgrdprs','vgrd10m'
            ] # rap

    rap.addcalculatedfield('wndprs',['ugrdprs','vgrdprs'],'sqrt(ugrdprs^2+vgrdprs^2)')
    rap.addcalculatedfield('wnd10m',['ugrd10m','vgrd10m'],'sqrt(ugrd10m^2+vgrd10m^2)')
    rap.addcalculatedfield('rhosfc',['pressfc','tmpsfc'],'pressfc/(tmpsfc*287.058)')

    # Allow for calculations to mix pressure/surface variables
    # rap.addcalculatedfield('agl',['hgtprs','hgtsfc'],'hgtprs-hgtsfc')
    rap.transfer(fields, datatime,geos=geos,pressure=pressure)
