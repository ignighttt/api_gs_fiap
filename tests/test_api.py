import importlib


def test_routes(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'test.sqlite3'))
    monkeypatch.setenv('ADMIN_API_KEY', 'test-secret')
    import app
    importlib.reload(app)
    client = app.app.test_client()
    assert client.get('/').status_code == 200
    response = client.get('/api/cars?q=Toyota')
    assert response.status_code == 200
    assert response.json['total'] == 1
    assert client.get('/api/cars/999').status_code == 404
    assert client.post('/api/cars', json={}).status_code == 401
    lead = client.post('/api/leads', json={'car_id':1,'name':'Teste Cliente','email':'a@b.com','phone':'11999999999'})
    assert lead.status_code == 201
    assert client.get('/api/leads', headers={'X-API-Key':'test-secret'}).json['items'][0]['name'] == 'Teste Cliente'
    payload = {'brand':'Honda','model':'Civic','version':'EXL','year':2023,'mileage':15000,'price':125000,'category':'Sedan','image':'corolla.svg'}
    created = client.post('/api/cars', json=payload, headers={'X-API-Key':'test-secret'})
    assert created.status_code == 201
    assert client.get(f"/api/cars/{created.json['id']}").status_code == 200
    assert client.delete(f"/api/cars/{created.json['id']}", headers={'X-API-Key':'test-secret'}).status_code == 204
