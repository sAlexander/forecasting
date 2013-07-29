-- Table: data

-- DROP TABLE data;

CREATE TABLE data
(
  forecastid serial NOT NULL,
  gridid serial NOT NULL,
  value double precision,
  CONSTRAINT data_pkey PRIMARY KEY (forecastid, gridid)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE data
  OWNER TO salexander;

-- Index: data_dataentryid_gridid_idx

-- DROP INDEX data_dataentryid_gridid_idx;

CREATE INDEX data_forecastid_gridid_idx
  ON data
  USING btree
  (forecastid, gridid);


