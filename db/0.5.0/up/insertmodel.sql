CREATE OR REPLACE FUNCTION insertmodel(newname character varying)
  RETURNS integer AS
$BODY$
DECLARE
  rval int;
BEGIN
IF EXISTS (SELECT 1 from models where models.name = newname) THEN
  select INTO rval modelid from models where models.name = newname;
ELSE
  INSERT into models (name) values (newname) returning modelid into rval;
END IF;
return rval;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
