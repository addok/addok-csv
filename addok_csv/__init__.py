import codecs
import csv
import io
import os
from collections import defaultdict

import falcon

from addok.config import config
from addok.core import reverse, search
from addok.helpers.text import EntityTooLarge
from addok.http import View, log_notfound, log_query


def register_http_endpoint(api):
    api.add_route('/search/csv', CSVSearch())
    api.add_route('/reverse/csv', CSVReverse())


def preconfigure(config):
    config.CSV_ENCODING = 'utf-8-sig'
    config.CSV_EXTRA_FIELDS = []


@config.on_load
def on_load():
    if not config.CSV_EXTRA_FIELDS:
        for field in config.FIELDS:
            if field.get('type') == 'housenumbers':
                continue
            config.CSV_EXTRA_FIELDS.append(field['key'])


class BaseCSV(View):

    MISSING_DELIMITER_MSG = ('Unable to detect delimiter, please add one with '
                             '"delimiter" parameter.')

    def compute_content(self, req, file, encoding):
        # Replace bad carriage returns, as per
        # http://tools.ietf.org/html/rfc4180
        # We may want not to load whole file in memory at some point.
        try:
            content = file.data.decode(encoding)
        except (LookupError, UnicodeDecodeError) as e:
            msg = 'Unable to decode with encoding "{}"'.format(encoding)
            raise falcon.HTTPBadRequest(title=msg, description=str(e))
        content = content.replace('\r', '').replace('\n', '\r\n')
        return content

    def compute_dialect(self, req, file, encoding):
        try:
            dialect = csv.Sniffer().sniff(file.data)
        except csv.Error:
            dialect = csv.unix_dialect()

        # Escape double quotes with double quotes if needed.
        # See 2.7 in http://tools.ietf.org/html/rfc4180
        dialect.doublequote = True
        delimiter = req.get_param('delimiter')
        if delimiter:
            dialect.delimiter = delimiter

        quote = req.get_param('quote')
        if quote:
            dialect.quotechar = quote

        # See https://github.com/etalab/addok/issues/90#event-353675239
        # and http://bugs.python.org/issue2078:
        # one column files will end up with non-sense delimiters.
        if dialect.delimiter.isalnum():
            # We guess we are in one column file, let's try to use a character
            # that will not be in the file content.
            for char in '|~^°':
                if char not in file.data:
                    dialect.delimiter = char
                    break
            else:
                raise falcon.HTTPBadRequest(self.MISSING_DELIMITER_MSG,
                                            self.MISSING_DELIMITER_MSG)

        return dialect

    def compute_rows(self, req, file, dialect):
        # Keep ends, not to glue lines when a field is multilined.
        return csv.DictReader(file.data.splitlines(keepends=True),
                              dialect=dialect)

    def compute_fieldnames(self, req, file, rows):
        fieldnames = rows.fieldnames[:]
        columns = req.get_param_as_list('columns') or fieldnames[:]  # noqa
        for column in columns:
            if column not in fieldnames:
                msg = "Cannot found column '{}' in columns {}".format(
                    column, fieldnames)
                raise falcon.HTTPBadRequest(title=msg)
        for key in self.result_headers:
            if key not in fieldnames:
                fieldnames.append(key)
        return fieldnames, columns

    def compute_output(self, req):
        return io.StringIO()

    def compute_writer(self, req, output, fieldnames, dialect, encoding):
        if (encoding.startswith('utf-8')
           and req.get_param_as_bool('with_bom')):
            # Make Excel happy with UTF-8
            output.write(codecs.BOM_UTF8.decode('utf-8'))
        writer = csv.DictWriter(output, fieldnames, dialect=dialect,
                                extrasaction='ignore')
        writer.writeheader()
        return writer

    def process_rows(self, req, writer, rows, filters, columns):
        for i, row in enumerate(rows):
            self.process_row(req, row, filters, columns, i)
            writer.writerow(row)

    def parse_multipart(self, req):
        # TODO move out from Falcon.
        form = defaultdict(list)
        file = None
        for part in req.get_media():
            if part.name == "data" and not file:
                file = part
                # Force reading the stream, otherwise Falcon will consume it while
                # parsing the rest of the multipart body…
                file.data
            else:
                form[part.name].append(part.text)
        req._params = form
        return file

    def on_post(self, req, resp, **kwargs):
        file = self.parse_multipart(req)
        if not file:
            raise falcon.HTTPBadRequest(title='Missing file')
        encoding = req.get_param('encoding', default=config.CSV_ENCODING)
        file._data = self.compute_content(req, file, encoding)
        if not file._data:
            raise falcon.HTTPBadRequest(title='Empty file')
        dialect = self.compute_dialect(req, file, encoding)
        rows = self.compute_rows(req, file, dialect)
        fieldnames, columns = self.compute_fieldnames(req, file, rows)
        output = self.compute_output(req)
        writer = self.compute_writer(req, output, fieldnames, dialect,
                                     encoding)
        filters = self.match_filters(req)
        self.process_rows(req, writer, rows, filters, columns)
        output.seek(0)
        try:
            resp.text = output.read().encode(encoding)
        except UnicodeEncodeError:
            raise falcon.HTTPBadRequest('Wrong encoding', 'Wrong encoding')
        filename, ext = os.path.splitext(file.filename)
        attachment = 'attachment; filename="{name}.geocoded.csv"'.format(
                                                                 name=filename)
        resp.set_header('Content-Disposition', attachment)
        content_type = 'text/csv; charset={encoding}'.format(encoding=encoding)
        resp.set_header('Content-Type', content_type)

    def add_extra_fields(self, row, result):
        for key in config.CSV_EXTRA_FIELDS:
            row['result_{}'.format(key)] = getattr(result, key, '')

    @property
    def result_headers(self):
        headers = []
        for key in config.CSV_EXTRA_FIELDS:
            header = 'result_{}'.format(key)
            if header not in headers:
                headers.append(header)
        return self.base_headers + headers

    def match_row_filters(self, row, filters):
        return {k: row.get(v, '') for k, v in filters.items()}


class CSVSearch(BaseCSV):

    endpoint = 'search.csv'
    base_headers = ['latitude', 'longitude', 'result_label', 'result_score',
                    'result_score_next', 'result_type', 'result_id',
                    'result_housenumber']

    def process_row(self, req, row, filters, columns, index):
        # We don't want None in a join.
        q = ' '.join([row[k] or '' for k in columns])
        filters = self.match_row_filters(row, filters)
        lat_column = req.get_param('lat')
        lon_column = req.get_param('lon')
        if lon_column and lat_column:
            lat = row.get(lat_column)
            lon = row.get(lon_column)
            if lat and lon:
                filters['lat'] = float(lat)
                filters['lon'] = float(lon)
        try:
            results = search(q, autocomplete=False, limit=3, **filters)
        except EntityTooLarge as e:
            msg = '{} (row number {})'.format(str(e), index+1)
            raise falcon.HTTPPayloadTooLarge(title=msg)
        log_query(q, results)
        if results:
            result = results[0]
            row.update({
                'latitude': result.lat,
                'longitude': result.lon,
                'result_label': str(result),
                'result_score': round(result.score, 2),
                'result_score_next': 0 if len(results)<2
                                        else round(results[1].score, 2),
                'result_type': result.type,
                'result_id': result.id,
                'result_housenumber': result.housenumber,
            })
            self.add_extra_fields(row, result)
        else:
            log_notfound(q)


class CSVReverse(BaseCSV):

    endpoint = 'reverse.csv'
    base_headers = ['result_latitude', 'result_longitude', 'result_label',
                    'result_distance', 'result_type', 'result_id',
                    'result_housenumber']

    def process_row(self, req, row, filters, columns, index):
        lat = row.get('latitude', row.get('lat', None))
        lon = row.get('longitude', row.get('lon', row.get('lng', row.get('long', None))))
        try:
            lat = float(lat)
            lon = float(lon)
        except (ValueError, TypeError):
            return
        filters = self.match_row_filters(row, filters)
        results = reverse(lat=lat, lon=lon, limit=1, **filters)
        if results:
            result = results[0]
            row.update({
                'result_latitude': result.lat,
                'result_longitude': result.lon,
                'result_label': str(result),
                'result_distance': int(result.distance),
                'result_type': result.type,
                'result_id': result.id,
                'result_housenumber': result.housenumber,
            })
            self.add_extra_fields(row, result)
