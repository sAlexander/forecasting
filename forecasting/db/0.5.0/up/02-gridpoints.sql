CREATE TABLE gridpoints
(
  gridpointid serial primary key,
  modelid serial not null,
  geom geometry,
  ord int
);
CREATE INDEX gridpoints_gist
  ON gridpoints
  USING gist
  (geom);

CREATE INDEX gridpoints_model
  ON gridpoints
  using btree
  (modelid);
CREATE INDEX gridpoints_modelord
  ON gridpoints
  using btree
  (modelid,ord);
