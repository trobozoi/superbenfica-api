# Super Benfica API

API REST + WebSocket do sistema de gerenciamento de supermercados **Super Benfica**: multi-filial com estoque independente, pedidos com fluxo de separação, notificações em tempo real, tarefas assíncronas e relatórios em cache.

**Stack:** Python 3.12+ · Django 5.2 LTS · Django REST Framework · SimpleJWT · drf-spectacular (Swagger) · Django Channels · Celery · Redis · PostgreSQL (Supabase) · Nginx · SonarQube

## Início rápido

```bash
# 1. Ambiente virtual e dependências
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt

# 2. Variáveis de ambiente
copy .env.example .env            # Linux/macOS: cp .env.example .env
# edite o .env: DJANGO_SECRET_KEY, DB_*, senhas da carga inicial

# 3. Criar as tabelas no banco do .env
python manage.py migrate

# 4. Popular com a carga inicial (idempotente)
python manage.py carga_inicial

# 5. Subir o servidor (HTTP + WebSocket via Daphne)
python manage.py runserver
```

Acesse:

| URL | Conteúdo |
|-----|----------|
| http://localhost:8000/api/docs/ | Swagger UI (interativo) |
| http://localhost:8000/api/redoc/ | ReDoc |
| http://localhost:8000/api/schema/ | Schema OpenAPI 3 (YAML) |
| http://localhost:8000/admin/ | Django Admin |

> Sem `REDIS_URL` no `.env`, cache e WebSocket usam memória local e o Celery executa as tasks de forma síncrona. Isso basta para desenvolver; para usar o Redis, preencha `REDIS_URL` ou suba com Docker.

## Banco de dados (Supabase)

As credenciais ficam **somente** no `.env` (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SSLMODE=require`). Se alguma estiver faltando, o Django não inicia e informa quais variáveis estão ausentes.

- Todas as tabelas do domínio usam o prefixo `sb_` no schema `public` (ex.: `sb_produto`, `sb_pedido`).
- O host direto `db.<projeto>.supabase.co` só responde via **IPv6**. Se a rede ou o Docker não tiver IPv6, use o host do **Session pooler** (painel do Supabase → *Connect*). Nesse caso o usuário fica `postgres.<projeto>`.
- Os testes **nunca** usam o Supabase: rodam em SQLite em memória (`config.settings.test`).

## Carga inicial

```bash
python manage.py carga_inicial            # cria o que ainda não existe
python manage.py carga_inicial -v 2       # lista cada registro
python manage.py carga_inicial --reset    # apaga e recria os dados de exemplo (somente DEBUG=True)
```

Ela cria 3 filiais, 1 usuário por perfil, 30 produtos, o estoque de todos os produtos nas 3 filiais (alguns abaixo do mínimo), 10 clientes com endereço e 5 pedidos em status diferentes, 2 deles com separação. Os dados ficam em [apps/core/seed_data/](apps/core/seed_data/).

| E-mail | Perfil | Senha |
|--------|--------|-------|
| valor de `DJANGO_SUPERUSER_EMAIL` | superusuário | `DJANGO_SUPERUSER_PASSWORD` |
| admin.rede@superbenfica.com.br | ADMIN | `SEED_DEFAULT_PASSWORD` |
| gerente.centro@superbenfica.com.br | GERENTE | `SEED_DEFAULT_PASSWORD` |
| separador.centro@superbenfica.com.br | SEPARADOR | `SEED_DEFAULT_PASSWORD` |
| caixa.centro@superbenfica.com.br | CAIXA | `SEED_DEFAULT_PASSWORD` |
| cliente.demo@superbenfica.com.br | CLIENTE | `SEED_DEFAULT_PASSWORD` |

## Docker

```bash
docker compose up --build                       # API, worker, beat, Redis e Nginx (http://localhost:8080)
docker compose --profile local-db up --build    # + PostgreSQL local (use DB_HOST=db no .env)
docker compose --profile quality up sonarqube   # SonarQube em http://localhost:9000
```

## Qualidade

```bash
ruff check . && ruff format --check .     # lint e formatação
pytest                                    # testes + cobertura (coverage.xml)
sonar-scanner                             # análise no SonarQube (usa sonar-project.properties)
```

O pipeline [.github/workflows/ci.yml](.github/workflows/ci.yml) roda lint, testes e SonarQube, e falha o build se o Quality Gate não passar. Para isso, configure os secrets `SONAR_TOKEN` e `SONAR_HOST_URL` no repositório.

## Documentação

- [docs/arquitetura.md](docs/arquitetura.md): estrutura, modelo de dados, fluxos e decisões.
- [docs/api.md](docs/api.md): autenticação, perfis, endpoints e WebSocket.
- [docs/openapi.yaml](docs/openapi.yaml): schema OpenAPI exportado. Para regenerar: `python manage.py spectacular --file docs/openapi.yaml`.
- [docs/sonarqube.md](docs/sonarqube.md): regras seguidas e Security Hotspots para revisão manual.
