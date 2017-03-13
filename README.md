# Addok plugin add CSV geocoding endpoints

## Install

    pip install addok-csv

## API

This plugin adds the following endpoints:


### /search/csv/

Batch geocode a csv file.

#### Parameters

- **data**: the CSV file to be processed
- **columns** (multiple): the columns, ordered, to be used for geocoding; if no
  column is given, all columns will be used
- **encoding** (optional): encoding of the file (you can also specify a `charset` in the
  file mimetype), such as 'utf-8' or 'iso-8859-1' (default to 'utf-8-sig')
- **delimiter** (optional): CSV delimiter (`,` or `;`); if not given, we try to
  guess
- **with_bom**: if true, and if the encoding if utf-8, the returned CSV will contain
  a BOM (for Excel users…)
- `lat` and `lon` parameters (optionals), like filters, can be used to
  define columns names that contain latitude and longitude
  values, for adding a preference center in the geocoding of each row

#### Examples

    http -f POST http://localhost:7878/search/csv/ columns='voie' columns='ville' data@path/to/file.csv
    http -f POST http://localhost:7878/search/csv/ columns='rue' postcode='code postal' data@path/to/file.csv

### /reverse/csv/

Batch reverse geocode a csv file.

#### Parameters

- **data**: the CSV file to be processed; must contain columns `latitude` (or `lat`) and
  `longitude` (or `lon` or `lng`)
- **encoding** (optional): encoding of the file (you can also specify a `charset` in the
  file mimetype), such as 'utf-8' or 'iso-8859-1' (default to 'utf-8-sig')
- **delimiter** (optional): CSV delimiter (`,` or `;`); if not given, we try to
  guess


Any filter can be passed as `key=value` querystring, where `key` is the filter
name and `value` is the column name containing the filter value for each row.
For example, if there is a column "code_insee" and we want to use it for
"citycode" filtering, we would pass `citycode=code_insee` as query string
parameter.

## Config

- CSV_ENCODING: default encoding to open CSV files (default: 'utf-8-sig')
