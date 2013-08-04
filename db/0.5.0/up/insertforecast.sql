CREATE OR REPLACE FUNCTION insertforecast(ifieldid integer, iheight real, tdatatime timestamp without time zone, tdatatimeforecast timestamp without time zone)
  RETURNS integer AS
$BODY$
DECLARE
rval int;
BEGIN
IF EXISTS (SELECT 1 from forecasts de where de.fieldid = ifieldid and (de.pressure_mb = iheight or de.pressure_mb is null) and de.datatime = tdatatime and de.datatimeforecast = tdatatimeforecast ) THEN
select INTO rval forecastid from forecasts de where de.fieldid = ifieldid and de.pressure_mb = iheight and de.datatime = tdatatime and de.datatimeforecast = tdatatimeforecast;
ELSE
INSERT into forecasts (fieldid, pressure_mb, datatime, datatimeforecast) values (ifieldid, iheight, tdatatime, tdatatimeforecast) returning forecastid into rval;
END IF;
return rval;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

