import os
import psycopg2 as pg
import numpy as np
from io import BytesIO
from struct import pack

class Database:

    conn = None
    curs = None
    dbversion = None
    dbmodelid = None

    fpath = os.path.dirname(os.path.abspath(__file__))

    def _version(self):
        return '0.5.0'

    def __init__(self, **connargs):
        self.conn = pg.connect(**connargs)
        self.curs = self.conn.cursor()
        try:
            print 'made it'
        except:
            raise Exception('Error connecting to database. Can you connect with the same parameters using psycpg2?')
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
        self.conn.close()

    def _migrate(self,version):
        """ Migrate the database to the correct version. This should be moved into a new class"""
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

        # Get modelid
        self.curs.execute("select insertmodel('%s');" % modelname)
        self.dbmodelid = self.curs.fetchone()[0]

    def numberofgridpoints(self):

        # grab number of gridpoints
        self.curs.execute("select count(1) from gridpoints where modelid = %d" % self.dbmodelid)
        numgridpoints = self.curs.fetchone()[0]
        return numgridpoints

    def setupgrid(self,lat,lon):

        nlat = len(lat)
        nlon = len(lon)

        for i in range(0,nlat):
            print 'Loading lat ',i
            for j in range(0,nlon):
                order = i*nlon+j
                self.curs.execute("insert into public.gridpoints (modelid,geom,ord) values(%d, ST_SetSRID(ST_MakePoint(%f, %f), 4326),%d);" % (self.dbmodelid, lon[i], lat[j], order))
        self.conn.commit()
        print 'Finished initializing grid'

    def getfieldid(self,field):
        # Select the fieldid from the database
        self.curs.execute("select insertfield(%d,'%s');" % (self.dbmodelid,field))
        fieldid = self.curs.fetchone()[0]
        return fieldid

    def getforecastid(self,fieldid,datatime,datatimeforecast,ilev):
        # Select (or create) the forecastid
        if ilev == None or np.isnan(ilev):
            self.curs.execute("select insertforecast(%d,null,'%s',date_trunc('minute',timestamp '%s' + interval '30 seconds'));" % (fieldid, datatime, datatimeforecast))
        else:
            lev = dat.lev[ilev]
            self.curs.execute("select insertforecast(%d,%f,'%s',date_trunc('minute',timestamp '%s' + interval '30 seconds'));" % (fieldid, lev, datatime, datatimeforecast))
        forecastid = self.curs.fetchone()[0]
        return forecastid

    def getknn(self,lat,lon,k,nlon):
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
        selectgridids = "select gridpointid from gridpoints where gridpoints.modelid = %d order by ord;" % self.dbmodelid
        self.conn.commit()
        self.curs.execute(selectgridids)
        rows = self.curs.fetchall()
        gridids = np.array(rows)
        gridids = np.reshape(gridids,np.size(gridids))
        return gridids

    def copybinary(self,dat, table,columns=''):
        cpy = self._preparebinary(dat)
        cpy.seek(0)
        self.curs.copy_expert('COPY ' + table + ' FROM STDIN WITH BINARY', cpy)
        self.conn.commit()

    def senddata(self,data):
        try:
            # this will fail if there are duplicates, but it's way faster
            self.conn.commit()
            self.copybinary(data, 'data')
        except:
            # try to insert more safely
            self.conn.rollback()
            self.copybinary(data, 'stagingdata')
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












