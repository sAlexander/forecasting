-- Function: insertdata(real, real, integer, real)

-- DROP FUNCTION insertdata(real, real, integer, real);

CREATE OR REPLACE FUNCTION insertdata(lat real, lon real, iforecastid integer, rdata real)
  RETURNS void AS
$BODY$
DECLARE
	igridpointid int;
BEGIN
select into igridpointid gridpointid from gridpoint where St_DWithin(gridpoint.geom,st_geomfromtext('POINT(' || lat || ' ' || lon || ')',4326),.05);
IF NOT EXISTS (SELECT 1 from data d where d.gridpointid = igridpointid and d.forecastid = iforecastid ) THEN
	INSERT into data (gridpointid, forecastid, value) values (igridpointid, iforecastid, rdata);
END IF;

END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
ALTER FUNCTION insertdata(real, real, integer, real)
  OWNER TO salexander;

