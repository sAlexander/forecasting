import os
import psycopg2 as pg
import numpy as np
from io import BytesIO
from struct import pack

class Database:
    """
    DATABASE instance for the forecasting module.

    The database instance takes care of all the interactions with the underlying database, currently PostGRES. 
    All queries are routed through the Database class to seperate database logic from model logic.
    Currently, the Database class is not meant to be publicly consumed (ie you should never directly call database methods),
    but only used as a helper for the Model class.

    Usage:
    d = Database(database='weather', user='chef')
    d.cachemodelid('nam')
    d.numberofgridpoints()

    """

    conn = None
    curs = None
    dbversion = None
    dbmodelid = None

    fpath = os.path.dirname(os.path.abspath(__file__))

    def _version(self):
        """
        Version of the database

        Class dependencies:
            none
        """
        return '0.5.0'

    def __init__(self, **connargs):
        """
        Initialize the connection to the underlying database

        Usage:
        d = Database(database='weather',user='chef')

        All arguments are the same as those for the psycopg2 module

        Class dependencies:
            self.dbversion
            self.conn
            self.curs
            self._version()
            self._migrage()

        """
        self.conn = pg.connect(**connargs)
        self.curs = self.conn.cursor()
        print 'Successfully connected to database'

        print 'Checking database version'
        try:
            self.curs.execute('select forecastingversion()')
            self.dbversion = self.curs.fetchone()[0]
            if self.dbversion != self._version():
                self._migrate(self._version())
        except:
            self.conn.rollback()
            self._migrate(self._version())
        print 'Database initialized'

    def close(self):
        """
        CLOSE the database connection

        Usage:
        d = Database(database='weather',user='chef')
        d.close()

        Class dependencies:
            none
        """

        self.conn.close()

    def _migrate(self,version):
        """ 
        Migrate the database to the correct version. 

        This sets up all of the internal tables and functions

        Class dependencies:
            self.fpath
            self.curs
            self.conn
        
        """

        # TODO: This method should be moved into a new class

        files = os.listdir(os.path.join(self.fpath,"db/{version}/up".format(version=version)))
        files.sort()
        for file in files:
            if file.endswith('.sql'):
                filename = os.path.join(self.fpath,"db/{version}/up".format(version=version),file)
                print 'Running migration: %s' % filename
                cmd = open(filename,'r').read()
                print cmd
                self.curs.execute(cmd)
        self.conn.commit()

    def cachemodelid(self, modelname):
        """
        CACHEMODELID accepts the modelname and caches the associated modelid. If no model of that name exists, one will be created

        Usage:
        d = Database(database='weather',user='chef')
        d.cachemodelid('nam')

        Class dependencies:
            self.curs
            self.dbmodlid
        """

        # Get modelid
        self.curs.execute("select insertmodel('%s');" % modelname)
        self.dbmodelid = self.curs.fetchone()[0]

    def numberofgridpoints(self):
        """
        NUMBEROFGRIDPOINTS queries for the number of grid points associated with a model

        Usage:
        d = Database(database='weather',user='chef')
        d.cachemodelid('nam')
        nogp = d.numberofgridpoints()

        Class dependencies:
            self.curs
            self.dbmodelid
        """

        # TODO: Add error catching in the case that the model hasn't been initialized

        self.curs.execute("select count(1) from gridpoints where modelid = %d" % self.dbmodelid)
        numgridpoints = self.curs.fetchone()[0]
        return numgridpoints

    def setupgrid(self,lat,lon):
        """
        SETUPGRID inserts a set of lat/long lists into the database.

        Usage:
        d = Database(database='weather',user='chef')
        d.cachemodelid('nam')
        d.setupgrid(lat,lon)

        Note: lat and lon should each only contain distinct elements... there should be no duplicates.

        Class dependencies:
            self.dbmodelid
            self.curs
            self.conn
        """

        nlat = len(lat)
        nlon = len(lon)

        for i in range(0,nlat):
            print 'Loading lat ',i
            for j in range(0,nlon):
                order = i*nlon+j
                self.curs.execute("insert into public.gridpoints (modelid,geom,ord) values(%d, ST_SetSRID(ST_MakePoint(%f, %f), 4326),%d);" % (self.dbmodelid, lon[j], lat[i], order))
        self.conn.commit()
        print 'Finished initializing grid'


    def getfieldid(self,field):
        """
        GETFILEDID accepts a field name and returns the associated fieldid. If the field name does not exist, it will be created.

        Usage:
        d = Database(database='weather',user='chef')
        d.cachemodelid('nam')
        d.getfieldid('temperature')

        Class dependencies:
            self.curs
            self.dbmodelid
        """

        self.curs.execute("select insertfield(%d,'%s');" % (self.dbmodelid,field))
        fieldid = self.curs.fetchone()[0]
        return fieldid


    def getforecastid(self,fieldid,datatime,datatimeforecast,lev=None):
        """
        GETFORECASTID accepts information about a forecast and returns the associated forecastid. If the forecast does not exist, it will be created.

        Usage:
        d = Database(database='weather',user='chef')
        d.cachemodelid('nam')
        fieldid = d.getfieldid('temperature')
        forecastid = d.getforecastid(fieldid, datatime.now(), datatime.now())

        Class dependencies:
            self.curs
            self.conn
        """
        # Select (or create) the forecastid
        if lev == None or np.isnan(lev):
            self.curs.execute("select insertforecast(%d,null,'%s',date_trunc('minute',timestamp '%s' + interval '30 seconds'));" % (fieldid, datatime, datatimeforecast))
        else:
            self.curs.execute("select insertforecast(%d,%f,'%s',date_trunc('minute',timestamp '%s' + interval '30 seconds'));" % (fieldid, lev, datatime, datatimeforecast))
        forecastid = self.curs.fetchone()[0]
        return forecastid

    def getknn(self,lat,lon,k,nlon):
        """
        GETKNN accepts a location and returns a set of the k nearest neighbors.

        Usage:
        d = Database(database='weather',user='chef')
        d.cachemodelid('nam')
        nlon = 1234 # the number of lon points in the model
        d.getknn(40.0,-105,10,nlon)

        Class dependencies:
            self.curs
            self.dbmodelid
        """

        results = []
        q = "select ord, ST_AsText(geom) from gridpoints gp where gp.modelid = %d order by gp.geom <-> ST_SetSRID(ST_MakePoint(%f,%f),4326) limit %d;" % (self.dbmodelid, lon, lat, k)
        self.curs.execute(q)
        rows = self.curs.fetchall()
        for order in rows:
            order = order[0]
            ilat = int(order/nlon)
            ilon = order % nlon
            results.append([[ilat,ilat+1,1],[ilon,ilon+1,1]])

        return results

    def retrievegridids(self):
        """
        RETRIEVEGRIDIDS returns all of the associated gridpointids for use in the model.

        Usage:
        d = Database(database='weather',user='chef')
        d.cachemodelid('nam')
        gridids = d.retrievegridids()

        Class dependencies:
            self.curs
            self.conn
            self.dbmodelid
        """

        selectgridids = "select gridpointid from gridpoints where gridpoints.modelid = %d order by ord;" % self.dbmodelid
        self.conn.commit()
        self.curs.execute(selectgridids)
        rows = self.curs.fetchall()
        gridids = np.array(rows)
        gridids = np.reshape(gridids,np.size(gridids))
        return gridids

    def _copybinary(self,dat, table,columns=''):
        """
        COPYBINARY inserts binary data into the provided table
        """

        cpy = self._preparebinary(dat)
        cpy.seek(0)
        self.curs.copy_expert('COPY ' + table + ' FROM STDIN WITH BINARY', cpy)
        self.conn.commit()

    def senddata(self,data):
        """
        SENDDATA sends the data to the database using the fastest method available.

        Usage:
        d.senddata(data)

        where data is a numpy named array with columns of gridpointid, forecastid, and value

        Class dependencies:
            self.conn
            self.curs
            self._copybinary()
        """

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

    def calculatefield(self,calcname,fieldnames,calculation, datatime):
        """
        CALCULATEFIELD runs a calculation based upon existing data and inserts it into the database

        Usage:
        d.calculatefield(self,calcname,fieldnames,calculation, datatime):

        Class dependencies:
            self.dbmodelid
            self.conn
            self.curs
            self.getfieldid()
            self.getforecastid()
        """

        ## Grab all of the forecast datatimes
        grps = ', '.join(map((lambda name: "min(CASE WHEN fld.name = '{name}' THEN forecastid else NULL end) as {name}".format(name=name)),fieldnames))
        lst  = ', '.join(map((lambda name: "'{name}'".format(name=name)),fieldnames))

        ## returns datatime, datatimeforecast, forecastid1, forecastid2, ...
        q = """
        select datatime, datatimeforecast, pressure_mb, {grps}
        from forecasts fcst
        inner join fields fld on fcst.fieldid = fld.fieldid
        where fld.modelid = {modelid} and fld.name in ({lst}) and datatime = '{datatime}'
        group by datatime, datatimeforecast, pressure_mb;
        """.format(grps=grps, modelid=self.dbmodelid, lst=lst, datatime=datatime )
        self.curs.execute(q)
        rows = self.curs.fetchall()

        ## create the calculated field for each forecast
        fieldid = self.getfieldid(calcname)
        for row in rows:
            datatime = row[0]
            datatimeforecast = row[1]
            pressure_mb = row[2]
            forecastids = row[3:]
            if any(map(lambda x: x==None,forecastids)): # if any are None
                raise Exception('One or more fieldnames not present in database')
            zipped = zip(forecastids, fieldnames)
            grps = ', '.join(map((lambda x: "min(CASE WHEN forecastid = '{id}' THEN value else NULL end) as {name}".format(id=x[0],name=x[1])),zipped))
            lst  = ', '.join(map((lambda x: "'{id}'".format(id=x[0])),zipped))
            forecastid = self.getforecastid(fieldid,datatime,datatimeforecast, pressure_mb)
            q = """
            insert into stagingdata (gridpointid, forecastid, value) (
                select gridpointid, {forecastid}, ({calculation}) as value
                from (
                    select gridpointid, {grps}
                    from data
                    where forecastid in ({lst})
                    group by gridpointid
                ) as foo
            );
            """.format(grps=grps, lst=lst, forecastid=forecastid, calculation=calculation)
            try:
                self.curs.execute(q, datatime)
            except:
                raise Exception('Bad Calculation')
            self.curs.execute('select applystagingdata();')
        self.conn.commit()












