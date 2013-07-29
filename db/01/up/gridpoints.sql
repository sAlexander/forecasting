-- Table: gridpoints

-- DROP TABLE gridpoints;

CREATE TABLE gridpoints
(
  gridpointid serial NOT NULL,
  geom geometry,
  CONSTRAINT gridpoint_pkey PRIMARY KEY (gridpointid)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE gridpointid
  OWNER TO salexander;

-- Index: gridpoints_gist

-- DROP INDEX gridpoints_gist;

CREATE INDEX gridpoints_gist
  ON gridpoints
  USING gist
  (geom);


