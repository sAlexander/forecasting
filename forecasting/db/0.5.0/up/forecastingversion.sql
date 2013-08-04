CREATE OR REPLACE FUNCTION forecastingversion()
  RETURNS varchar(10) AS
$BODY$
declare
  rval varchar(10);
begin
  select into rval'0.5.0';
  return rval;
end
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
