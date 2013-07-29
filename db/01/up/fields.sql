-- Table: fields

-- DROP TABLE fields;

CREATE TABLE fields
(
  fieldid serial NOT NULL,
  name character varying(100),
  description character varying(1000),
  CONSTRAINT fields_pkey PRIMARY KEY (fieldid)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE fields
  OWNER TO salexander;

