CREATE TABLE forecasts
(
  forecastid serial primary key,
  fieldid serial NOT NULL,
  pressure_mb real,
  datatime timestamp without time zone NOT NULL,
  datatimeforecast timestamp without time zone
);
