import codecs
import csv
import io
import os

from werkzeug.exceptions import BadRequest
from werkzeug.wrappers import Response

from addok import config, hooks
from addok.core import reverse, search
from addok.http import View, log_notfound, log_query


@hooks.register
def addok_register_http_endpoints(endpoints):
    endpoints.extend([
        ('/search/csv/', 'search.csv'),
        ('/reverse/csv/', 'reverse.csv'),
        ('/csv/', 'search.csv'),  # Retrocompat.
    ])


class BaseCSV(View):

    MISSING_DELIMITER_MSG = ('Unable to sniff delimiter, please add one with '
                             '"delimiter" parameter.')

    def compute_encodings(self):
        self.input_encoding = 'utf-8'
        self.output_encoding = 'utf-8'
        file_encoding = self.f.mimetype_params.get('charset')
        # When file_encoding is passed as charset in the file mimetype,
        # Werkzeug will reencode the content to utf-8 for us, so don't try
        # to reencode.
        if not file_encoding:
            self.input_encoding = self.request.form.get('encoding',
                                                        self.input_encoding)

    def compute_content(self):

        # Replace bad carriage returns, as per
        # http://tools.ietf.org/html/rfc4180
        # We may want not to load whole file in memory at some point.
        self.content = self.f.read().decode(self.input_encoding)
        self.content = self.content.replace('\r', '').replace('\n', '\r\n')
        self.f.seek(0)

    def compute_dialect(self):
        try:
            extract = self.f.read(4096).decode(self.input_encoding)
        except (LookupError, UnicodeDecodeError):
            raise BadRequest('Unknown encoding {}'.format(self.input_encoding))
        try:
            dialect = csv.Sniffer().sniff(extract)
        except csv.Error:
            dialect = csv.unix_dialect()
        self.f.seek(0)

        # Escape double quotes with double quotes if needed.
        # See 2.7 in http://tools.ietf.org/html/rfc4180
        dialect.doublequote = True
        delimiter = self.request.form.get('delimiter')
        if delimiter:
            dialect.delimiter = delimiter

        # See https://github.com/etalab/addok/issues/90#event-353675239
        # and http://bugs.python.org/issue2078:
        # one column files will end up with non-sense delimiters.
        if dialect.delimiter.isalnum():
            # We guess we are in one column file, let's try to use a character
            # that will not be in the file content.
            for char in '|~^°':
                if char not in self.content:
                    dialect.delimiter = char
                    break
            else:
                raise BadRequest(self.MISSING_DELIMITER_MSG)

        self.dialect = dialect

    def compute_rows(self):
        # Keep ends, not to glue lines when a field is multilined.
        self.rows = csv.DictReader(self.content.splitlines(keepends=True),
                                   dialect=self.dialect)

    def compute_fieldnames(self):
        self.fieldnames = self.rows.fieldnames[:]
        self.columns = self.request.form.getlist('columns') or self.rows.fieldnames  # noqa
        for column in self.columns:
            if column not in self.fieldnames:
                raise BadRequest("Cannot found column '{}' in columns "
                                 "{}".format(column, self.fieldnames))
        for key in self.result_headers:
            if key not in self.fieldnames:
                self.fieldnames.append(key)

    def compute_output(self):
        self.output = io.StringIO()

    def compute_writer(self):
        if (self.output_encoding == 'utf-8'
                and self.request.form.get('with_bom')):
            # Make Excel happy with UTF-8
            self.output.write(codecs.BOM_UTF8.decode('utf-8'))
        self.writer = csv.DictWriter(self.output, self.fieldnames,
                                     dialect=self.dialect)
        self.writer.writeheader()

    def compute_filters(self):
        self.filters = self.match_filters()

    def process_rows(self):
        for row in self.rows:
            self.process_row(row)
            self.writer.writerow(row)
        self.output.seek(0)

    def compute_response(self):
        self.response = Response(
                            self.output.read().encode(self.output_encoding))
        filename, ext = os.path.splitext(self.f.filename)
        attachment = 'attachment; filename="{name}.geocoded.csv"'.format(
                                                                 name=filename)
        self.response.headers['Content-Disposition'] = attachment
        content_type = 'text/csv; charset={encoding}'.format(
            encoding=self.output_encoding)
        self.response.headers['Content-Type'] = content_type

    def post(self):
        self.f = self.request.files['data']
        self.compute_encodings()
        self.compute_content()
        self.compute_dialect()
        self.compute_rows()
        self.compute_fieldnames()
        self.compute_output()
        self.compute_writer()
        self.compute_filters()
        self.process_rows()
        self.compute_response()
        return self.response

    def add_fields(self, row, result):
        for field in config.FIELDS:
            if field.get('type') == 'housenumbers':
                continue
            key = field['key']
            row['result_{}'.format(key)] = getattr(result, key, '')

    @property
    def result_headers(self):
        if not hasattr(self, '_result_headers'):
            headers = []
            for field in config.FIELDS:
                if field.get('type') == 'housenumbers':
                    continue
                key = 'result_{}'.format(field['key'])
                if key not in headers:
                    headers.append(key)
            self._result_headers = self.base_headers + headers
        return self._result_headers

    def match_row_filters(self, row):
        return {k: row.get(v) for k, v in self.filters.items()}


class CSVSearch(BaseCSV):

    endpoint = 'search.csv'
    base_headers = ['latitude', 'longitude', 'result_label', 'result_score',
                    'result_type', 'result_id', 'result_housenumber']

    def process_row(self, row):
        # We don't want None in a join.
        q = ' '.join([row[k] or '' for k in self.columns])
        filters = self.match_row_filters(row)
        lat_column = self.request.form.get('lat')
        lon_column = self.request.form.get('lon')
        if lon_column and lat_column:
            lat = row.get(lat_column)
            lon = row.get(lon_column)
            if lat and lon:
                filters['lat'] = float(lat)
                filters['lon'] = float(lon)
        results = search(q, autocomplete=False, limit=1, **filters)
        log_query(q, results)
        if results:
            result = results[0]
            row.update({
                'latitude': result.lat,
                'longitude': result.lon,
                'result_label': str(result),
                'result_score': round(result.score, 2),
                'result_type': result.type,
                'result_id': result.id,
                'result_housenumber': result.housenumber,
            })
            self.add_fields(row, result)
        else:
            log_notfound(q)


class CSVReverse(BaseCSV):

    endpoint = 'reverse.csv'
    base_headers = ['result_latitude', 'result_longitude', 'result_label',
                    'result_distance', 'result_type', 'result_id',
                    'result_housenumber']

    def process_row(self, row):
        lat = row.get('latitude', row.get('lat', None))
        lon = row.get('longitude', row.get('lon', row.get('lng', row.get('long',None))))
        try:
            lat = float(lat)
            lon = float(lon)
        except (ValueError, TypeError):
            return
        filters = self.match_row_filters(row)
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
            self.add_fields(row, result)
