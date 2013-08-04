CREATE TABLE fields
(
  fieldid serial primary key,
  modelid serial not null,
  name character varying(100),
  description character varying(1000)
);
