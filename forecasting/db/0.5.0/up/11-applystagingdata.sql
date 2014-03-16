create function applystagingdata() RETURNS void AS 
'insert into data
select * from stagingdata
where (select count(*) from data where data.forecastid = stagingdata.forecastid and data.gridpointid = stagingdata.gridpointid)=0;
delete from stagingdata;' language sql;
