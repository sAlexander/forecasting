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
  CONSTRAINT forecasts_pkey PRIMARY KEY (forecastid)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE forecasts
  OWNER TO salexander;

