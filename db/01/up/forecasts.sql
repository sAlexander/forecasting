-- Table: forecasts

-- DROP TABLE forecasts;

CREATE TABLE forecasts
(
  forecastid serial NOT NULL,
  fieldid serial NOT NULL,
  height_m real,
  pressure_mb real,
  datatime timestamp without time zone NOT NULL,
  datatimeforecast timestamp without time zone,
  CONSTRAINT dataentries_pkey PRIMARY KEY (dataentryid)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE dataentries
  OWNER TO salexander;

