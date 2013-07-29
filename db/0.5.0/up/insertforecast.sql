-- Function: insertforecast(integer, timestamp without time zone, timestamp without time zone)

-- DROP FUNCTION insertforecast(integer, timestamp without time zone, timestamp without time zone);

CREATE OR REPLACE FUNCTION insertforecast(ifieldid integer, iheight real, tdatatime timestamp without time zone, tdatatimeforecast timestamp without time zone)
  RETURNS integer AS
$BODY$
DECLARE
	rval int;
BEGIN
IF EXISTS (SELECT 1 from dataentries de where de.fieldid = ifieldid and de.pressure_mb = iheight and de.datatime = tdatatime and de.datatimeforecast = tdatatimeforecast ) THEN
	select INTO rval forecastid from dataentries de where de.fieldid = ifieldid and de.pressure_mb = iheight and de.datatime = tdatatime and de.datatimeforecast = tdatatimeforecast;
ELSE
	INSERT into dataentries (fieldid, pressure_mb, datatime, datatimeforecast) values (ifieldid, iheight, tdatatime, tdatatimeforecast) returning forecastid into rval;
END IF;
return rval;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

