# AutoVendas — Landing page + API REST

Aplicação demonstrativa de vendas de veículos com **Flask (Python)**, **SQLite**, **HTML/CSS/JavaScript**. Não exige PHP ou Docker: o próprio Flask serve a landing page e os endpoints da API.

## Requisitos
- Python 3.10+
- Git

## Executar localmente

```bash
git clone https://github.com/SEU-USUARIO/auto-vendas.git
cd auto-vendas
python -m venv .venv
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

**Linux/macOS:**
```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Acesse **http://127.0.0.1:5000**. A base de dados `instance/autovendas.db` é criada automaticamente com seis veículos fictícios. Edite `.env` para definir uma chave administrativa forte antes de testar o CRUD.

## Funcionalidades
- Catálogo, categorias e busca por marca/modelo/versão
- Favoritos no navegador via `localStorage`
- Detalhes dos veículos e formulário de interesse (salvo em SQLite)
- API REST para leitura e administração do catálogo
- Layout responsivo com ilustrações SVG locais

## API

| Método | Endpoint | Descrição | Autenticação |
| --- | --- | --- | --- |
| GET | `/api/health` | Verifica a API | Não |
| GET | `/api/cars` | Lista veículos; aceita `q`, `category`, `featured`, `limit`, `offset` | Não |
| GET | `/api/cars/1` | Detalha veículo | Não |
| POST | `/api/cars` | Cria veículo | `X-API-Key` |
| PUT | `/api/cars/1` | Atualiza veículo (JSON completo) | `X-API-Key` |
| DELETE | `/api/cars/1` | Exclui veículo sem leads vinculados | `X-API-Key` |
| POST | `/api/leads` | Registra interesse | Não |
| GET | `/api/leads` | Lista contatos | `X-API-Key` |

Exemplo de busca: `GET /api/cars?q=Toyota&category=Sedan`.

**Criar veículo:**
```bash
curl -X POST http://127.0.0.1:5000/api/cars \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: SUA_CHAVE_DO_ENV' \
  -d '{"brand":"Honda","model":"Civic","version":"EXL","year":2023,"mileage":18000,"price":145000,"category":"Sedan","image":"corolla.svg","description":"Seminovo"}'
```

**Registrar interesse:**
```bash
curl -X POST http://127.0.0.1:5000/api/leads \
  -H 'Content-Type: application/json' \
  -d '{"car_id":1,"name":"Cliente Teste","email":"teste@example.com","phone":"11999999999"}'
```

## Publicar no GitHub

```bash
git init
git add .
git commit -m "feat: landing page e API Flask SQLite"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/auto-vendas.git
git push -u origin main
```

Crie o repositório vazio na sua conta do GitHub antes de executar `git push` e substitua `SEU-USUARIO`.

## Nuvem Azure (próxima etapa)

O GitHub armazena o código, mas **GitHub Pages não executa Python nem SQLite**. Para colocar a API no ar, será necessário um serviço de hospedagem, por exemplo Azure App Service com runtime Python. O comando de inicialização pode ser `gunicorn --bind 0.0.0.0:8000 app:app`.

**Atenção:** SQLite é ótimo para desenvolvimento, mas os arquivos locais de algumas configurações de hospedagem podem ser efêmeros ou inadequados a instâncias múltiplas. Antes de publicar comercialmente, migrar os dados para um banco persistente (por exemplo, Azure Database for PostgreSQL), configurar segredos como variáveis de ambiente, autenticação real, prevenção de spam e política de privacidade/LGPD. Os SVGs, preços e veículos do exemplo são ilustrativos.
