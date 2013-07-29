
create table dataentries (dataentryid serial primary key, fieldid serial not null, datatime timestamp not null, datatimeforecast timestamp);

create table fields (fieldid serial primary key, name varchar(100), description varchar(1000));

create table data (dataentryid serial not null, gridid serial not null, value float);

create table grid (gridid serial primary key, geom geometry);

create index on data (dataentryid, gridid);

CREATE OR REPLACE FUNCTION insertfield(newname varchar(100)) RETURNS int LANGUAGE plpgsql AS $$
DECLARE
	rval int;
BEGIN
IF EXISTS (SELECT 1 from fields where fields.name = newname) THEN
	select INTO rval fieldid from fields where fields.name = newname;
ELSE
	INSERT into fields (name) values (newname) returning fieldid into rval;
END IF;
return rval;
END;
$$;

CREATE OR REPLACE FUNCTION insertdataentry(ifieldid int, tdatatime timestamp, tdatatimeforecast timestamp) RETURNS int LANGUAGE plpgsql AS $$
DECLARE
	rval int;
BEGIN
IF EXISTS (SELECT 1 from dataentries de where de.fieldid = ifieldid and de.datatime = tdatatime and de.datatimeforecast = tdatatimeforecast ) THEN
	select INTO rval dataentryid from dataentries de where de.fieldid = ifieldid and de.datatime = tdatatime and de.datatimeforecast = tdatatimeforecast;
ELSE
	INSERT into dataentries (fieldid, datatime, datatimeforecast) values (ifieldid, tdatatime, tdatatimeforecast) returning dataentryid into rval;
END IF;
return rval;
END;
$$;


CREATE OR REPLACE FUNCTION insertdata(lat real, lon real, idataentryid int, rdata real) RETURNS void LANGUAGE plpgsql AS $$
DECLARE
	igridid int;
BEGIN
select into igridid gridid from grid where St_DWithin(grid.geom,st_geomfromtext('POINT(' || lat || ' ' || lon || ')',4326),.05);
IF NOT EXISTS (SELECT 1 from data d where d.gridid = igridid and d.dataentryid = idataentryid ) THEN
	INSERT into data (gridid, dataentryid, value) values (igridid, idataentryid, rdata);
END IF;

END;
$$;

--select somefuncname('testing2')
--select insertdataentry(8,'2013-07-26 18:00','2013-07-26 20:00');
--select insertdata(61.1756545455,-102.762999593,4,999);

