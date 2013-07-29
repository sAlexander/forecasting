-- Table: fields

-- DROP TABLE fields;

CREATE TABLE fields
(
  fieldid serial NOT NULL,
  modelid serial not null,
  name character varying(100),
  description character varying(1000),
  CONSTRAINT fields_pkey PRIMARY KEY (fieldid)
)
WITH (
  OIDS=FALSE
);
