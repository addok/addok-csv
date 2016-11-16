# Addok plugin add CSV geocoding endpoints

## API

This plugin adds the following endpoints:


- /search/csv
- /reverse/csv

### Query parameters

- data: the CSV file to process
- delimiter (optional): the CSV delimiter (`,` or `;`); if not given, we try to
  guess
- encoding (optional): the encoding of the file (default to 'utf-8-sig')
- columns (multiple): the columns, ordered, to be used for geocoding; if no
  column is given, all columns will be used
- with_bom: if true, and if the encoding if utf-8, the returned CSV will contain
  a BOM (for Excel users…)
- lat/lon (optional): center to bias the search

Any filter can be passed as `key=value` querystring, where `key` is the filter
name and `value` is the column name containing the filter value for each row.
For example, if there is a column "code_insee" and we want to use it for
"citycode" filtering, we would pass `citycode=code_insee` as query string
parameter.

## Config

- CSV_ENCODING: default encoding to open CSV files (default: 'utf-8-sig')
