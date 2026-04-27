# Greffo API

Backend FastAPI — transcription audio juridique.

## Prérequis

- Python 3.12+
- PostgreSQL 16 (`brew install postgresql@16`)
- Redis 7 (`brew install redis && brew services start redis`)
- libmagic (`brew install libmagic`)
- uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Lancer en local

```bash
# 1. Services (terminal dédié ou brew services)
brew services start postgresql@16
brew services start redis

# 2. Base de données
createdb -O greffo greffo_dev    # première fois
uv run alembic upgrade head

# 3. API
uv run uvicorn src.main:app --reload --port 8000

# 4. Worker ARQ (terminal séparé)
uv run arq src.workers.WorkerSettings
```

## Seeding (données de démo)

Crée une organisation + user owner en DB pour les démos manuelles :

```bash
uv run python scripts/seed_dev.py
```

Sortie exemple :

```
[seed] Données de démo créées :
       org_id  = 01JXXXXX…  (Cabinet Greffo Demo)
       user_id = 01JXXXXX…  (demo@greffo.fr, role=owner)

Utilisation dans les requêtes curl :
  -H "X-Org-Id: 01JXXXXX…" -H "X-User-Id: 01JXXXXX…"
```

Le script est **idempotent** : relancé deux fois, il affiche les IDs existants sans créer de doublon.

## Tests

```bash
# Créer la DB de test (une seule fois)
createdb -O greffo greffo_test

# Lancer la suite complète
uv run pytest

# Tests de sécurité uniquement
uv run pytest tests/security/
```

## Migrations

```bash
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
uv run alembic downgrade -1
```

## Lint / Format

```bash
uv run ruff check . && uv run ruff format .
```
