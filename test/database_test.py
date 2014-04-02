import unittest
import os
import datetime
import numpy as np
import psycopg2 as pg


from forecasting.database import Database

class DatabaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # This is the setup proceedure discussed here: http://getforecasting.com/documentation/quick-start/
        self.database = 'test'
        q_createdb = 'create database {database}; grant all privileges on database {database} to salexander;'.format(database=self.database)
        os.system("echo '%s' | psql postgres" % q_createdb)
        q_postgis = 'CREATE EXTENSION postgis; CREATE EXTENSION postgis_topology;'
        os.system("echo '%s' | psql %s" % (q_postgis,self.database))
        self.d = Database(database=self.database)
        self.lat = [1,2]
        self.lon = [1,2]
        self.datatime = datetime.datetime.strptime('2014-02-22 18:00:00', "%Y-%m-%d %H:%M:%S")
        self.dfield1 = [1,2,3,4]
        self.dfield2 = [4,3,2,1]

    @classmethod
    def tearDownClass(self):
        self.d.close()
        q_dropdb = 'drop database test;'
        os.system("echo '%s' | psql postgres" % q_dropdb)

    def test_a_setupmodel(self):
        self.d.cachemodelid('rap')
        self.assertEqual(self.d.dbmodelid,1,'Model not properly setup')
        self.d.cachemodelid('rap')
        self.assertEqual(self.d.dbmodelid,1,'Model allowed duplication')

    def test_b_setupgrid(self):
        self.d.setupgrid(self.lat,self.lon)
        self.assertEqual(self.d.numberofgridpoints(),len(self.lat)*len(self.lon), 'Grid not initialized')

    def test_c_createfields(self):
        field1 = self.d.getfieldid('field1')
        self.assertEqual(field1,1,'Field not initialized')
        field1a = self.d.getfieldid('field1')
        self.assertEqual(field1,field1a,'Field allowed duplication')

        field2 = self.d.getfieldid('field2')
        self.assertEqual(field2,2,'Field not initialized')

    def test_d_createforecast(self): 

        field1 = self.d.getfieldid('field1')
        field2 = self.d.getfieldid('field2')

        datatime = self.datatime
        forecast1 = self.d.getforecastid(field1, datatime,datatime,None)
        self.assertEqual(forecast1,1,'Forecast not initialized')
        forecast1a = self.d.getforecastid(field1, datatime,datatime,None)
        self.assertEqual(forecast1,forecast1a,'Forecast duplicated')

        forecast2 = self.d.getforecastid(field2, datatime,datatime,None)
        self.assertEqual(forecast2,2,'Forecast not initialized')

    # Helper to count the number of datapoints for a forecast
    def forecastcount(self,forecastid):
        q = 'SELECT count(*) from data where forecastid = %d' % forecastid
        conn = pg.connect(database=self.database)
        curs = conn.cursor()
        curs.execute(q)
        rows = curs.fetchall()
        return rows[0][0]

    # Helper to get the datapoint values
    def forecastvalues(self,forecastid):
        q = 'SELECT value from data where forecastid = %d' % forecastid
        conn = pg.connect(database=self.database)
        curs = conn.cursor()
        curs.execute(q)
        rows = curs.fetchall()
        return [row[0] for row in rows]
    
    def test_d_senddata(self):
        field1, field2 = [1,2]
        forecast1, forecast2 = [1,2]
        datatime = self.datatime
        gridpointids = self.d.retrievegridids()

        dtype = ([('forecastid','i4'), ('gridpointid','i4'), ('value','f4')])

        # forecast 1
        data = np.empty(len(gridpointids),dtype)
        data['gridpointid'] = gridpointids
        data['forecastid'] = forecast1
        data['value'] = self.dfield1
        self.d.senddata(data)
        self.assertEqual(self.forecastcount(forecast1),4,'Incorrect forecast length')

        # forecast 1 repeated
        data = np.empty(len(gridpointids),dtype)
        data['gridpointid'] = gridpointids
        data['forecastid'] = forecast1
        data['value'] = self.dfield1
        self.d.senddata(data)
        self.assertEqual(self.forecastcount(forecast1),4,'Incorrect forecast length on repeat')

        # forecast 2
        data = np.empty(len(gridpointids),dtype)
        data['gridpointid'] = gridpointids
        data['forecastid'] = forecast2
        data['value'] = self.dfield2
        self.d.senddata(data)
        self.assertEqual(self.forecastcount(forecast2),4,'Incorrect forecast length')

    def test_e_knn(self):
        knn = self.d.getknn(1,1,1,len(self.lon))
        self.assertEqual(knn,[[[0,1,1],[0,1,1]]])

    def test_f_calcfield(self):
        datatime = self.datatime

        self.d.calculatefield('field3',['field1','field2'],'field1+field2',datatime)

        field3 = self.d.getfieldid('field3')
        forecast3 = self.d.getforecastid(field3,datatime,datatime,None)

        self.assertEqual(self.forecastcount(forecast3),4,'Incorrect forecast length')

        print self.forecastvalues(forecast3)

    def test_f_badcalcfield(self):
        datatime = self.datatime
        self.assertRaises(Exception,self.d.calculatefield,'field3',['field1','fieldnotexist'],'field1+field2',datatime)




if __name__ == '__main__':
    unittest.main()
