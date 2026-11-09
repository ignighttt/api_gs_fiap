"""AutoVendas: aplicação Flask, API REST e SQLite."""
import hmac
import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, render_template, request

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv('DATABASE_PATH', str(BASE_DIR / 'instance' / 'autovendas.db')))
if not DB_PATH.is_absolute():
    DB_PATH = BASE_DIR / DB_PATH

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-only-change-me')

SCHEMA = '''
CREATE TABLE IF NOT EXISTS cars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    version TEXT NOT NULL,
    year INTEGER NOT NULL CHECK(year BETWEEN 1950 AND 2100),
    mileage INTEGER NOT NULL CHECK(mileage >= 0),
    price REAL NOT NULL CHECK(price > 0),
    category TEXT NOT NULL CHECK(category IN ('Hatch','Sedan','SUV','Picape','Utilitário')),
    image TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    featured INTEGER NOT NULL DEFAULT 0 CHECK(featured IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id INTEGER NOT NULL REFERENCES cars(id),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cars_category ON cars(category);
CREATE INDEX IF NOT EXISTS idx_cars_brand ON cars(brand);
'''

SEED = [
    ('Volkswagen', 'Polo', '1.0 TSI Comfortline', 2023, 28000, 89900, 'Hatch', 'polo.svg', 'Hatch compacto e econômico, com boa tecnologia embarcada.', 1),
    ('Toyota', 'Corolla', '2.0 XEi', 2022, 41000, 132900, 'Sedan', 'corolla.svg', 'Sedan espaçoso, confortável e confiável.', 1),
    ('Jeep', 'Renegade', '1.3 Turbo Longitude', 2023, 36000, 118900, 'SUV', 'renegade.svg', 'SUV com motor turbo e visual robusto.', 1),
    ('Chevrolet', 'Onix', '1.0 LT', 2022, 50000, 74900, 'Hatch', 'onix.svg', 'Hatch versátil para cidade e estrada.', 1),
    ('Fiat', 'Toro', '1.3 Turbo Freedom', 2024, 19000, 149900, 'Picape', 'toro.svg', 'Picape confortável com caçamba versátil.', 0),
    ('Renault', 'Kangoo', '1.6 Express', 2021, 63000, 69900, 'Utilitário', 'kangoo.svg', 'Utilitário prático para operações comerciais.', 0),
]

@contextmanager
def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with connection() as conn:
        conn.executescript(SCHEMA)
        if conn.execute('SELECT COUNT(*) FROM cars').fetchone()[0] == 0:
            conn.executemany('''INSERT INTO cars
                (brand,model,version,year,mileage,price,category,image,description,featured)
                VALUES (?,?,?,?,?,?,?,?,?,?)''', SEED)

def car_dict(row):
    data = dict(row)
    data['featured'] = bool(data['featured'])
    data['image_url'] = f"/static/img/{data['image']}"
    return data

def admin_required():
    expected = os.getenv('ADMIN_API_KEY', '')
    provided = request.headers.get('X-API-Key', '')
    if not expected or not hmac.compare_digest(provided, expected):
        abort(401, description='Chave de administração ausente ou inválida.')

def validated_car(payload):
    if not isinstance(payload, dict):
        raise ValueError('Envie um objeto JSON.')
    mandatory = ('brand','model','version','year','mileage','price','category','image')
    if any(key not in payload for key in mandatory):
        raise ValueError('Campos obrigatórios: ' + ', '.join(mandatory))
    data = {}
    for key in ('brand','model','version','category','image'):
        data[key] = str(payload[key]).strip()
        if not data[key] or len(data[key]) > 120:
            raise ValueError(f'Campo {key} inválido.')
    if data['category'] not in ('Hatch','Sedan','SUV','Picape','Utilitário'):
        raise ValueError('Categoria inválida.')
    if not re.fullmatch(r'[a-zA-Z0-9_-]+\.svg', data['image']):
        raise ValueError('Imagem deve ser um nome de SVG local (ex: polo.svg).')
    try:
        data['year'] = int(payload['year'])
        data['mileage'] = int(payload['mileage'])
        data['price'] = float(payload['price'])
    except (ValueError, TypeError):
        raise ValueError('Ano, quilometragem e preço devem ser numéricos.') from None
    if not 1950 <= data['year'] <= 2100 or data['mileage'] < 0 or not 0 < data['price'] < 100_000_000:
        raise ValueError('Ano, quilometragem ou preço fora dos limites.')
    data['description'] = str(payload.get('description','')).strip()[:1000]
    data['featured'] = int(bool(payload.get('featured', False)))
    return data

@app.errorhandler(400)
@app.errorhandler(401)
@app.errorhandler(404)
@app.errorhandler(405)
def api_http_error(error):
    if request.path.startswith('/api/'):
        return jsonify(error=error.description), error.code
    return error

@app.route('/')
def home():
    return render_template('index.html')

@app.get('/api/health')
def health():
    return jsonify(status='ok')

@app.get('/api/cars')
def list_cars():
    q = request.args.get('q','').strip()
    category = request.args.get('category','').strip()
    featured = request.args.get('featured','').strip()
    try:
        limit = min(max(int(request.args.get('limit', 30)), 1), 100)
        offset = max(int(request.args.get('offset', 0)), 0)
    except ValueError:
        return jsonify(error='limit e offset devem ser inteiros.'), 400
    clauses, params = [], []
    if q:
        clauses.append('(brand LIKE ? OR model LIKE ? OR version LIKE ?)')
        params.extend([f'%{q}%'] * 3)
    if category and category != 'Todos':
        clauses.append('category = ?')
        params.append(category)
    if featured in ('true','1'):
        clauses.append('featured = 1')
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    with connection() as conn:
        total = conn.execute('SELECT COUNT(*) FROM cars' + where, params).fetchone()[0]
        rows = conn.execute('SELECT * FROM cars' + where + ' ORDER BY featured DESC, id DESC LIMIT ? OFFSET ?', params + [limit, offset]).fetchall()
    return jsonify(items=[car_dict(row) for row in rows], total=total, limit=limit, offset=offset)

@app.get('/api/cars/<int:car_id>')
def get_car(car_id):
    with connection() as conn:
        row = conn.execute('SELECT * FROM cars WHERE id=?', (car_id,)).fetchone()
    if row is None:
        abort(404, description='Veículo não encontrado.')
    return jsonify(car_dict(row))

@app.post('/api/cars')
def create_car():
    admin_required()
    try:
        data = validated_car(request.get_json(silent=True))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    columns = list(data)
    with connection() as conn:
        cursor = conn.execute(f"INSERT INTO cars ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", list(data.values()))
        row = conn.execute('SELECT * FROM cars WHERE id=?', (cursor.lastrowid,)).fetchone()
    return jsonify(car_dict(row)), 201

@app.put('/api/cars/<int:car_id>')
def update_car(car_id):
    admin_required()
    try:
        data = validated_car(request.get_json(silent=True))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    with connection() as conn:
        if not conn.execute('SELECT 1 FROM cars WHERE id=?', (car_id,)).fetchone():
            abort(404, description='Veículo não encontrado.')
        conn.execute('UPDATE cars SET ' + ','.join(f'{k}=?' for k in data) + ' WHERE id=?', list(data.values()) + [car_id])
        row = conn.execute('SELECT * FROM cars WHERE id=?', (car_id,)).fetchone()
    return jsonify(car_dict(row))

@app.delete('/api/cars/<int:car_id>')
def delete_car(car_id):
    admin_required()
    with connection() as conn:
        if not conn.execute('SELECT 1 FROM cars WHERE id=?', (car_id,)).fetchone():
            abort(404, description='Veículo não encontrado.')
        if conn.execute('SELECT 1 FROM leads WHERE car_id=?', (car_id,)).fetchone():
            return jsonify(error='Veículo possui contatos registrados; não pode ser excluído.'), 409
        conn.execute('DELETE FROM cars WHERE id=?', (car_id,))
    return '', 204

@app.post('/api/leads')
def create_lead():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='Envie dados JSON.'), 400
    try:
        car_id = int(data.get('car_id'))
    except (TypeError, ValueError):
        return jsonify(error='Veículo inválido.'), 400
    name = str(data.get('name','')).strip()
    email = str(data.get('email','')).strip()
    phone = str(data.get('phone','')).strip()
    message = str(data.get('message','')).strip()
    if not (2 <= len(name) <= 100 and len(email) <= 254 and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email)
            and 8 <= len(phone) <= 25 and len(message) <= 1000):
        return jsonify(error='Preencha nome, e-mail e telefone válidos.'), 400
    with connection() as conn:
        if not conn.execute('SELECT 1 FROM cars WHERE id=?', (car_id,)).fetchone():
            abort(404, description='Veículo não encontrado.')
        conn.execute('INSERT INTO leads (car_id,name,email,phone,message) VALUES (?,?,?,?,?)',
                     (car_id,name,email,phone,message))
    return jsonify(message='Interesse registrado com sucesso.'), 201

@app.get('/api/leads')
def list_leads():
    admin_required()
    with connection() as conn:
        rows = conn.execute('SELECT * FROM leads ORDER BY id DESC LIMIT 100').fetchall()
    return jsonify(items=[dict(row) for row in rows])

init_db()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.getenv('PORT', 5000)), debug=os.getenv('FLASK_DEBUG') == '1')
