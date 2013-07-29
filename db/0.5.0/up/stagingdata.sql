-- Table: stagingdata

-- DROP TABLE stagingdata;

CREATE TABLE stagingdata
(
  lat real,
  lon real,
  value real
)
WITH (
  OIDS=FALSE
);
ALTER TABLE stagingdata
  OWNER TO salexander;

