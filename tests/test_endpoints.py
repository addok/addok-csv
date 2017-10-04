import falcon


def test_csv_endpoint(client, factory):
    factory(name='rue des avions', postcode='31310', city='Montbrun-Bocage')
    content = ('name,street,postcode,city\n'
               'Boulangerie Brûlé,rue des avions,31310,Montbrun-Bocage')
    files = {'data': (content, 'file.csv')}
    form = {'columns': ['street', 'postcode', 'city']}
    resp = client.post('/search/csv', data=form, files=files)
    assert resp.status == falcon.HTTP_200
    assert 'file.geocoded.csv' in resp.headers['Content-Disposition']
    data = resp.body
    assert 'latitude' in data
    assert 'longitude' in data
    assert 'result_label' in data
    assert 'result_score' in data
    assert data.count('Montbrun-Bocage') == 3
    assert data.count('Boulangerie Brûlé') == 1  # Make sure accents are ok.


def test_csv_endpoint_with_accent_in_filename(client, factory):
    factory(name='rue des avions', postcode='31310', city='Montbrun-Bocage')
    content = ('name,street,postcode,city\n'
               'Boulangerie Brûlé,rue des avions,31310,Montbrun-Bocage')
    files = {'data': (content, 'liste.médecins.csv')}
    form = {'columns': ['street', 'postcode', 'city']}
    resp = client.post('/search/csv', data=form, files=files)
    assert resp.status == falcon.HTTP_200
    assert 'liste.médecins.geocoded.csv' in resp.headers['Content-Disposition']
    data = resp.body
    assert data.count('Montbrun-Bocage') == 3
    assert data.count('Boulangerie Brûlé') == 1  # Make sure accents are ok.


def test_csv_endpoint_with_housenumber(client, factory):
    factory(name='rue des avions', postcode='31310', city='Montbrun-Bocage',
            housenumbers={'118': {'lat': 10.22334401, 'lon': 12.33445501}})
    content = ('name,housenumber,street,postcode,city\n'
               'Boulangerie Brûlé,118,rue des avions,31310,Montbrun-Bocage')
    files = {'data': (content, 'file.csv')}
    form = {'columns': ['housenumber', 'street', 'postcode', 'city']}
    resp = client.post('search/csv', data=form, files=files)
    assert resp.status == falcon.HTTP_200
    assert 'result_housenumber' in resp.body
    assert resp.body.count('118') == 3


def test_csv_endpoint_with_no_rows(client, factory):
    factory(name='rue des avions', postcode='31310', city='Montbrun-Bocage')
    content = ('name,street,postcode,city\n'
               ',,,')
    resp = client.post('/search/csv', files={'data': (content, 'file.csv')})
    assert resp.status == falcon.HTTP_200
    assert resp.body


def test_csv_endpoint_with_empty_file(client, factory):
    factory(name='rue des avions', postcode='31310', city='Montbrun-Bocage')
    resp = client.post('/search/csv', files={'data': ('', 'file.csv')})
    assert resp.status == falcon.HTTP_400


def test_csv_endpoint_with_bad_column(client, factory):
    content = 'name,street,postcode,city\n,,,'
    resp = client.post('/search/csv', files={'data': (content, 'file.csv')},
                       data={'columns': 'xxxxx'})
    assert resp.status == falcon.HTTP_400


def test_csv_endpoint_with_multilines_fields(client, factory):
    factory(name='rue des avions', postcode='31310', city='Montbrun-Bocage')
    content = ('name,adresse\n'
               '"Boulangerie Brûlé","rue des avions\n31310\nMontbrun-Bocage"\n'
               '"Pâtisserie Crème","rue des avions\n31310\nMontbrun-Bocage"\n')
    resp = client.post('/search/csv', files={'data': (content, 'file.csv')},
                       data={'columns': ['adresse']})
    assert resp.status == falcon.HTTP_200
    assert 'latitude' in resp.body
    assert 'longitude' in resp.body
    assert 'result_label' in resp.body
    assert 'result_score' in resp.body
    # \n as been replaced by \r\n
    assert 'rue des avions\r\n31310\r\nMontbrun-Bocage' in resp.body


def test_csv_endpoint_with_tab_as_delimiter(client, factory):
    factory(name='rue des avions', postcode='31310', city='Montbrun-Bocage')
    content = ('name\tadresse\n'
               'Boulangerie\true des avions Montbrun')
    resp = client.post('/search/csv', files={'data': (content, 'file.csv')},
                       data={'columns': ['adresse']})
    assert resp.status == falcon.HTTP_200
    assert 'Boulangerie\true des avions Montbrun' in resp.body


def test_csv_endpoint_with_one_column(client, factory):
    factory(name='rue des avions', postcode='31310', city='Montbrun-Bocage')
    factory(name='rue des bateaux', postcode='31310', city='Montbrun-Bocage')
    content = ('adresse\n'
               'rue des avions Montbrun\nrue des bateaux Montbrun')
    resp = client.post('/search/csv/', files={'data': (content, 'file.csv')},
                       data={'columns': ['adresse']})
    assert resp.status == falcon.HTTP_200
    assert 'rue des avions Montbrun' in resp.body


def test_csv_endpoint_with_not_enough_content(client, factory):
    factory(name='rue', postcode='80688', type='city')
    resp = client.post('/search/csv/', files={'data': ('q\nrue', 'file.csv')})
    assert resp.status == falcon.HTTP_200
    assert '80688' in resp.body


def test_csv_endpoint_with_not_enough_content_but_delimiter(client, factory):
    factory(name='rue', postcode='80688', type='city')
    resp = client.post('/search/csv/', files={'data': ('q\nrue', 'file.csv')},
                       data={'delimiter': ','})
    assert resp.status == falcon.HTTP_200
    assert '80688' in resp.body


def test_csv_reverse_endpoint(client, factory):
    factory(name='rue des brûlés', postcode='31310', city='Montbrun-Bocage',
            lat=10.22334401, lon=12.33445501)
    content = ('latitude,longitude\n'
               '10.223344,12.334455')
    resp = client.post('/reverse/csv/', files={'data': (content, 'file.csv')})
    assert resp.status == falcon.HTTP_200
    assert 'file.geocoded.csv' in resp.headers['Content-Disposition']
    assert 'result_latitude' in resp.body
    assert '10.22334401' in resp.body
    assert 'result_longitude' in resp.body
    assert '12.33445501' in resp.body
    assert 'result_label' in resp.body
    assert 'result_distance' in resp.body
    assert 'Montbrun-Bocage' in resp.body
    assert 'rue des brûlés' in resp.body


def test_csv_endpoint_can_be_filtered(client, factory):
    factory(name='rue des avions', postcode='31310', city='Montbrun-Bocage')
    factory(name='rue des avions', postcode='09350', city='Fornex')
    content = ('rue,code postal,ville\n'
               'rue des avions,31310,Montbrun-Bocage')
    # We are asking to filter by 'postcode' using the column 'code postal'.
    resp = client.post('/search/csv/', files={'data': (content, 'file.csv')},
                       data={'columns': ['rue'], 'postcode': 'code postal'})
    assert resp.status == falcon.HTTP_200
    assert resp.body.count('31310') == 3
    assert resp.body.count('09350') == 0
    content = ('rue,code postal,ville\n'
               'rue des avions,09350,Fornex')
    resp = client.post('/search/csv/', files={'data': (content, 'file.csv')},
                       data={'columns': ['rue'], 'postcode': 'code postal'})
    assert resp.status == falcon.HTTP_200
    assert resp.body.count('09350') == 3
    assert resp.body.count('31310') == 0


def test_csv_endpoint_skip_empty_filter_value(client, factory):
    factory(name='rue des avions', postcode='31310', city='Montbrun-Bocage')
    content = ('rue,code postal,ville\n'
               'rue des avions,,Montbrun-Bocage')
    # We are asking to filter by 'postcode' using the column 'code postal'.
    resp = client.post('/search/csv/', files={'data': (content, 'file.csv')},
                       data={'columns': ['rue'], 'postcode': 'code postal'})
    assert resp.status == falcon.HTTP_200
    assert resp.body.count('31310') == 2


def test_csv_endpoint_can_use_geoboost(client, factory):
    factory(name='rue des avions', postcode='31310', city='Montbrun-Bocage',
            lat=10.22334401, lon=12.33445501)
    factory(name='rue des avions', postcode='59118', city='Wambrechies',
            lat=50.6845, lon=3.0480)
    content = ('rue,latitude,longitude\n'
               'rue des avions,10.22334401,12.33445501')
    # We are asking to center with 'lat' & 'lon'.
    resp = client.post('/search/csv/', files={'data': (content, 'file.csv')},
                       data={'columns': ['rue'], 'lat': 'latitude',
                             'lon': 'longitude'})
    assert resp.status == falcon.HTTP_200
    assert resp.body.count('31310') == 2
    assert resp.body.count('59118') == 0
    content = ('rue,latitude,longitude\n'
               'rue des avions,50.6845,3.0480')
    resp = client.post('/search/csv/', files={'data': (content, 'file.csv')},
                       data={'columns': ['rue'], 'lat': 'latitude',
                             'lon': 'longitude'})
    assert resp.status == falcon.HTTP_200
    assert resp.body.count('59118') == 2
    assert resp.body.count('31310') == 0


def test_csv_reverse_endpoint_can_be_filtered(client, factory):
    factory(name='rue des brûlés', postcode='31310', city='Montbrun-Bocage',
            lat=10.22334401, lon=12.33445501,
            housenumbers={'118': {'lat': 10.22334401, 'lon': 12.33445501}})
    # First we ask for a street.
    content = ('latitude,longitude,object\n'
               '10.223344,12.334455,street\n')
    resp = client.post('/reverse/csv/', files={'data': (content, 'file.csv')},
                       data={'type': 'object'})
    assert resp.status == falcon.HTTP_200
    assert resp.body.count('118') == 0
    # Now we ask for a housenumber.
    content = ('latitude,longitude,object\n'
               '10.223344,12.334455,housenumber\n')
    resp = client.post('/reverse/csv/', files={'data': (content, 'file.csv')},
                       data={'type': 'object'})
    assert resp.body.count('118') == 2


def test_csv_endpoint_with_pipe_as_quote(client, factory):
    factory(name='rue', postcode='80688', type='city')
    content = ('q\n'
               '|rue|')
    resp = client.post('/search/csv/',
                       files={'data': (content, 'file.csv')},
                       data={'quote': '|'})
    assert '|rue|' in resp.body
    assert '|city|' in resp.body


def test_query_too_large_should_raise(client, factory, config):
    config.QUERY_MAX_LENGTH = 10
    content = ('name,street,postcode,city\n'
               'Boulangerie Brûlé,rue des avions,31310,Montbrun-Bocage')
    files = {'data': (content, 'file.csv')}
    form = {'columns': ['street', 'postcode', 'city']}
    resp = client.post('/search/csv', data=form, files=files)
    assert resp.status == falcon.HTTP_413
    assert resp.json['title'] == \
        'Query too long, 36 chars, limit is 10 (row number 1)'
