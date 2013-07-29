-- Function: insertmodel(character varying)

-- DROP FUNCTION insertmodel(character varying);

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
ALTER FUNCTION insertmodel(character varying)
  OWNER TO salexander;

