CREATE TABLE fields
(
  fieldid serial primary key,
  modelid serial not null,
  name character varying(100),
  description character varying(1000)
);
CREATE INDEX fields_idx_name on fields using btree (name);
CREATE INDEX fields_idx_modelid_name on fields using btree (modelid,name);
