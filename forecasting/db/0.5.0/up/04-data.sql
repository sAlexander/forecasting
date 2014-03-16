-- Table: data

-- DROP TABLE data;

CREATE TABLE data
(
  forecastid serial NOT NULL,
  gridpointid serial NOT NULL,
  value real,
  PRIMARY KEY (forecastid, gridpointid)
);
