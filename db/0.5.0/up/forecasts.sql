CREATE TABLE forecasts
(
  forecastid serial primary key,
  fieldid serial NOT NULL,
  pressure_mb real,
  datatime timestamp without time zone NOT NULL,
  datatimeforecast timestamp without time zone
);

create index forecasts_idx_fields on forecasts using btree (fieldid);
