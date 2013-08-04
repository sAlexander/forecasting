-- Table: data

-- DROP TABLE data;

CREATE TABLE data
(
  forecastid serial NOT NULL,
  gridid serial NOT NULL,
  value real,
  PRIMARY KEY (forecastid, gridid)
);
