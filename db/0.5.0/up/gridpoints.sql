-- Table: gridpoints

-- DROP TABLE gridpoints;

CREATE TABLE gridpoints
(
  gridpointid serial primary key,
  modelid serial not null,
  geom geometry
)
WITH (
  OIDS=FALSE
);
ALTER TABLE gridpoints
  OWNER TO salexander;

-- Index: gridpoints_gist

-- DROP INDEX gridpoints_gist;

CREATE INDEX gridpoints_gist
  ON gridpoints
  USING gist
  (geom);

CREATE INDEX gridpoints_model
  ON gridpoints
  using btree
  (modelid);
