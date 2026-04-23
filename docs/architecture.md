# Architecture technique

> Document de référence pour les décisions techniques. À lire avant d'implémenter toute nouvelle feature. Mis à jour par ADR (`docs/decisions/`) quand une décision évolue.

---

## 1. Vue d'ensemble

SaaS B2B de transcription audio pour professionnels du droit. Architecture 3 tiers classique + workers GPU asynchrones pour le traitement IA.

### Principes directeurs

1. **Souveraineté des données** : tout hébergé en France (Scaleway PAR-2). Aucune donnée ne quitte l'UE.
2. **Asynchrone par défaut** : les traitements lourds (transcription) se font en queue, jamais en requête HTTP synchrone.
3. **Chiffrement de bout en bout** : at-rest (S3 + DB) et in-transit (TLS 1.3).
4. **Tenant isolation stricte** : RLS PostgreSQL + scoping applicatif. Un client ne voit JAMAIS les données d'un autre.
5. **Auditabilité totale** : chaque action sensible est loguée dans `audit_logs`.
6. **Auto-scaling intelligent** : composants stateless scalables horizontalement, GPU scale à zéro en dehors des pics.
7. **Fail gracefully** : un worker qui plante n'impacte pas les autres jobs. Retry avec backoff, puis état `failed` explicite.

---

## 2. Diagramme global

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLIENT (navigateur)                      │
│                  Avocat, Cabinet, Notaire, Huissier              │
└────────────────────────────────┬─────────────────────────────────┘
                                 │ HTTPS / TLS 1.3
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                       CDN / WAF                                  │
│                   Cloudflare EU (ou Scaleway LB)                 │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                    FRONT-END (Next.js 15)                        │
│              Scaleway Serverless Containers (PAR)                │
│  - RSC + Server Actions pour les reads                           │
│  - Client Components pour l'UI interactive                       │
│  - Auth.js avec cookie httpOnly + CSRF                           │
│  - Upload direct via signed URL → S3 (bypass API)                │
└──┬───────────────────────────────────────────┬───────────────────┘
   │ API REST (JWT)                            │ Signed URL PUT
   ▼                                           ▼
┌─────────────────────────────────┐  ┌─────────────────────────────┐
│      API BACKEND (FastAPI)       │  │  OBJECT STORAGE (S3)        │
│   Scaleway Serverless (PAR)      │  │  Scaleway PAR-2             │
│  - Routes REST + WebSocket       │  │  - Audios (TTL 30j)         │
│  - Middleware auth + tenant      │  │  - Transcripts JSON         │
│  - Webhook Stripe                │  │  - Exports PV (.docx)       │
│  - Enqueue dans Redis            │  │  - AES-256 at-rest          │
└──┬──────────┬──────────┬─────────┘  └─────────────────────────────┘
   │          │          │
   ▼          ▼          ▼
┌────────┐ ┌──────┐ ┌──────────────────────────────────────────┐
│POSTGRES│ │REDIS │ │              GPU WORKERS                 │
│ 16 HA  │ │7  HA │ │   Scaleway L4 (on-demand → Kapsule)      │
│Scaleway│ │Queue │ │  - Poll queue ARQ                        │
│ PAR    │ │ +    │ │  - faster-whisper large-v3               │
│        │ │Cache │ │  - pyannote.audio 3.1                    │
│ RLS    │ │      │ │  - WhisperX (alignement)                 │
│ +      │ │      │ │  - Silero VAD                            │
│pgcrypto│ │      │ │  - Update DB + Notifie WS                │
└────────┘ └──────┘ └──────────────────────────────────────────┘
   │                             │
   │          ┌──────────────────┘
   ▼          ▼
┌──────────────────────────────────────────────────────────────────┐
│                     OBSERVABILITÉ & OPS                          │
│  Sentry EU · Grafana Cloud EU · Loki · Prometheus · Alertmanager │
│  Scaleway Secret Manager · Backups quotidiens · DR cross-AZ      │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Composants détaillés

### 3.1 Front-end (Next.js 15)

**Rôle** : servir l'UI utilisateur + site marketing.

**Choix techniques** :
- App Router (pas Pages Router)
- Server Components par défaut, Client Components uniquement pour interactivité
- Server Actions pour mutations simples (login, update profil)
- API routes Next.js **non utilisées** pour le métier → tout passe par l'API FastAPI
- TailwindCSS v4 + shadcn/ui pour UI cohérente
- i18n FR prioritaire, EN en V2

**Sécurité front** :
- CSP strict (pas de `unsafe-inline` sauf pour Tailwind inline hashes)
- Cookies `httpOnly; secure; sameSite=strict`
- CSRF token sur toutes les mutations non-GET
- Pas de `localStorage` pour données sensibles (utiliser uniquement pour préférences UI)

**Performance** :
- Images optimisées via `next/image`
- Streaming SSR pour les dashboards
- Cache aggressif pour les pages marketing

### 3.2 API Backend (FastAPI)

**Rôle** : point d'entrée unique pour le métier, orchestration des jobs, facturation.

**Structure** :
```
apps/api/src/
├── main.py                # Entry point, CORS, middlewares
├── config.py              # Pydantic Settings (12-factor)
├── db.py                  # Session SQLAlchemy async
├── redis.py               # Pool Redis
├── auth/
│   ├── middleware.py      # JWT validation
│   ├── rbac.py            # Rôles: owner, admin, member
│   └── tenant.py          # Scoping auto organization_id
├── routes/
│   ├── auth.py
│   ├── transcriptions.py
│   ├── cases.py
│   ├── billing.py
│   ├── webhooks.py        # Stripe
│   └── admin.py
├── models/                # SQLAlchemy models
├── schemas/               # Pydantic DTOs
├── services/              # Logique métier
│   ├── transcription_service.py
│   ├── export_service.py
│   └── billing_service.py
├── pipeline/              # Importé par workers
│   ├── vad.py
│   ├── transcribe.py
│   ├── diarize.py
│   └── align.py
└── workers/
    └── worker.py          # ARQ WorkerSettings
```

**Convention routes** :
- Versioning : `/api/v1/...`
- REST strict
- Pagination `?page=1&size=50`
- Filtres `?status=done&from=2026-01-01`
- Réponses JSON typées (jamais de `dict` non typé retourné)

**Rate limiting** :
- 100 req/min/user par défaut
- 5 upload/min/user pour éviter abus
- 1000 req/min/org global

### 3.3 Workers GPU

**Rôle** : traitement asynchrone des audios (transcription + diarization).

**Déploiement** :
- Phase 1-2 : 1 instance GPU L4 qui tourne en continu, workers ARQ Python qui polls Redis
- Phase 3+ : Kubernetes (Scaleway Kapsule) avec HPA (Horizontal Pod Autoscaler) basé sur la longueur de la queue

**Dockerfile** (idée) :
```dockerfile
FROM nvidia/cuda:12.4.0-cudnn-runtime-ubuntu22.04
# Install Python 3.12, ffmpeg, système
# Copy pyproject.toml, install deps avec uv
# Copy src/
# Download et cache les modèles (Whisper, pyannote) dans /models
CMD ["arq", "src.workers.WorkerSettings"]
```

**Pipeline détaillé** :
```python
async def process_transcription(ctx, transcription_id: str):
    # 1. Charger la transcription, marquer processing
    # 2. Télécharger audio depuis S3 vers /tmp chiffré
    # 3. VAD Silero → segments de parole
    # 4. Diarization pyannote → qui parle quand
    # 5. Pour chaque segment → faster-whisper → texte
    # 6. Alignement WhisperX → timestamps mot-à-mot
    # 7. Fusion diarization + transcription → JSON structuré
    # 8. Sauvegarder JSON dans S3 + DB (chiffré)
    # 9. Émettre event WS au client
    # 10. Supprimer fichier /tmp
```

**États possibles** :
```
queued → processing → transcribing → diarizing → aligning → finalizing → done
                                                                       ↘
                                                                        failed
```

**Gestion erreurs** :
- Max 3 retries avec backoff exponentiel (10s, 60s, 300s)
- Au-delà : état `failed` avec `error_code` et `error_message`
- Jamais de silent fail, toujours loguer et alerter via Sentry

**Optimisations** :
- Modèles chargés une fois au démarrage du worker, restent en VRAM
- Batching : si 3 audios courts en queue, traiter ensemble sur même instance
- Timeout global par job : 2h max
- Monitoring GPU (utilisation, température) via DCGM exporter → Prometheus

### 3.4 Base de données

**Moteur** : PostgreSQL 16 managé par Scaleway.

**Extensions** :
- `pgcrypto` : chiffrement applicatif
- `pgvector` (optionnel V2) : recherche sémantique dans les transcripts
- `pg_trgm` : recherche full-text tolérante aux fautes

**Haute dispo** :
- Phase 1 : mono-instance + backup quotidien
- Phase 2+ : réplication master/standby
- Backups : quotidiens rétention 30j, PITR 7j

### 3.5 Queue (Redis)

**Rôle** : file d'attente des jobs + cache éphémère + rate limiting + WebSocket pub/sub.

**Databases Redis** :
- DB 0 : queue ARQ
- DB 1 : cache sessions, rate limiting
- DB 2 : pub/sub WebSocket

**Persistence** :
- AOF everysec activé
- Backups quotidiens

### 3.6 Object Storage

**Provider** : Scaleway Object Storage (S3-compatible, région PAR-2).

**Buckets** :
- `audios-raw` : audios uploadés bruts. TTL 30j (lifecycle policy). Chiffrement AES-256.
- `transcripts-json` : transcriptions structurées JSON. TTL 7 ans.
- `exports-docx` : exports PV générés. TTL 90j (user peut re-générer).
- `backups` : backups DB. Cross-AZ replication.

**Accès** :
- Uploads via signed URL (expiration 15 min)
- Downloads via signed URL (expiration 5 min)
- Aucune lecture/écriture directe depuis le front

---

## 4. Schéma de base de données

### 4.1 Diagramme ER simplifié

```
organizations ──┬──< users
                │
                ├──< cases ──< transcriptions ──< transcription_segments
                │                    │
                │                    └──< exports
                │
                ├──< subscriptions
                │
                ├──< audit_logs
                │
                └──< usage_records
```

### 4.2 Tables principales

**`organizations`** (cabinets)
```sql
id              ULID PRIMARY KEY
name            TEXT NOT NULL
slug            TEXT UNIQUE
siret           TEXT
address         TEXT
dpa_signed_at   TIMESTAMPTZ  -- DPA signé, obligatoire avant usage
plan            TEXT  -- starter, cabinet, firm, enterprise
quota_minutes   INTEGER  -- minutes audio/mois
audio_retention_days INTEGER DEFAULT 30
created_at      TIMESTAMPTZ DEFAULT NOW()
updated_at      TIMESTAMPTZ
deleted_at      TIMESTAMPTZ
```

**`users`**
```sql
id              ULID PRIMARY KEY
organization_id ULID NOT NULL REFERENCES organizations(id)
email           TEXT UNIQUE NOT NULL  -- chiffré applicativement
email_hash      TEXT UNIQUE NOT NULL  -- hash pour lookup
name            TEXT  -- chiffré
role            TEXT NOT NULL  -- owner, admin, member
mfa_enabled     BOOLEAN DEFAULT FALSE
last_login_at   TIMESTAMPTZ
created_at      TIMESTAMPTZ
deleted_at      TIMESTAMPTZ
```

**`cases`** (dossiers)
```sql
id              ULID PRIMARY KEY
organization_id ULID NOT NULL
name            TEXT NOT NULL  -- chiffré
reference       TEXT  -- référence interne cabinet
description     TEXT  -- chiffré
created_by      ULID REFERENCES users(id)
archived_at     TIMESTAMPTZ
created_at      TIMESTAMPTZ
deleted_at      TIMESTAMPTZ
```

**`transcriptions`**
```sql
id                ULID PRIMARY KEY
organization_id   ULID NOT NULL
case_id           ULID REFERENCES cases(id)
user_id           ULID NOT NULL REFERENCES users(id)
title             TEXT  -- chiffré
audio_s3_key      TEXT  -- signée
audio_duration_s  INTEGER
audio_size_bytes  BIGINT
audio_format      TEXT
audio_deleted_at  TIMESTAMPTZ  -- quand l'audio brut sera purgé

status            TEXT NOT NULL  -- queued|processing|...|done|failed
error_code        TEXT
error_message     TEXT
progress_pct      SMALLINT

language          TEXT DEFAULT 'fr'
speaker_count     SMALLINT

transcript_s3_key TEXT  -- JSON dans S3
transcript_preview TEXT  -- premiers 500 chars chiffrés pour UI

processing_started_at  TIMESTAMPTZ
processing_ended_at    TIMESTAMPTZ
cost_minutes_used      INTEGER  -- pour quota

created_at        TIMESTAMPTZ
deleted_at        TIMESTAMPTZ
```

**`transcription_segments`** (optionnel, si recherche SQL souhaitée)
```sql
id                ULID PRIMARY KEY
transcription_id  ULID NOT NULL
speaker_label     TEXT  -- "SPEAKER_00", "Me Dupont"
start_s           FLOAT
end_s             FLOAT
text              TEXT  -- chiffré
confidence        FLOAT
created_at        TIMESTAMPTZ
```

**`exports`**
```sql
id                ULID PRIMARY KEY
transcription_id  ULID NOT NULL
user_id           ULID NOT NULL
format            TEXT  -- docx, pdf, srt, json
template          TEXT  -- pv_audition, standard, etc.
s3_key            TEXT
expires_at        TIMESTAMPTZ
created_at        TIMESTAMPTZ
```

**`subscriptions`**
```sql
id                ULID PRIMARY KEY
organization_id   ULID NOT NULL UNIQUE
stripe_customer_id TEXT
stripe_subscription_id TEXT
plan              TEXT
status            TEXT  -- active, past_due, canceled, trialing
current_period_end TIMESTAMPTZ
created_at        TIMESTAMPTZ
```

**`usage_records`**
```sql
id                ULID PRIMARY KEY
organization_id   ULID NOT NULL
user_id           ULID
transcription_id  ULID
minutes_consumed  INTEGER
period_month      DATE  -- YYYY-MM-01
created_at        TIMESTAMPTZ
```

**`audit_logs`** (append-only)
```sql
id                ULID PRIMARY KEY
organization_id   ULID NOT NULL
user_id           ULID
actor_type        TEXT  -- user, system, api
action            TEXT NOT NULL  -- transcription.read, transcription.export, etc.
resource_type     TEXT
resource_id       TEXT
metadata          JSONB  -- contexte additionnel, PAS de PII
ip_hash           TEXT  -- IP hashée + tronquée /24
user_agent        TEXT
created_at        TIMESTAMPTZ DEFAULT NOW()
-- INDEX sur (organization_id, created_at DESC)
-- RLS: lecture seule, jamais UPDATE/DELETE
```

**`webhook_events`** (pour idempotence Stripe)
```sql
id                ULID PRIMARY KEY
source            TEXT  -- stripe
event_id          TEXT UNIQUE
event_type        TEXT
processed_at      TIMESTAMPTZ
payload           JSONB
```

### 4.3 Indexes critiques

```sql
-- Multi-tenant performance
CREATE INDEX ON transcriptions (organization_id, created_at DESC);
CREATE INDEX ON transcriptions (organization_id, status);
CREATE INDEX ON cases (organization_id, created_at DESC);

-- Audit
CREATE INDEX ON audit_logs (organization_id, created_at DESC);
CREATE INDEX ON audit_logs (user_id, created_at DESC);

-- Billing
CREATE INDEX ON usage_records (organization_id, period_month);
```

### 4.4 RLS (Row Level Security)

Activer sur toutes les tables métier :

```sql
ALTER TABLE transcriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON transcriptions
  USING (organization_id = current_setting('app.current_org_id')::uuid);
```

L'API FastAPI positionne `SET LOCAL app.current_org_id = '...'` au début de chaque transaction.

---

## 5. Data flow critiques

### 5.1 Upload et transcription

```
1. User → POST /api/v1/transcriptions/upload-url
           { filename, size, duration_estimated, case_id? }
2. API   → Vérifie quotas, MIME, taille
        → Génère signed URL PUT (15 min)
        → Crée transcription(status=queued, audio_s3_key=...)
        → Retourne { transcription_id, upload_url }
3. Client → PUT audio directement vers S3 signed URL
4. Client → POST /api/v1/transcriptions/{id}/confirm-upload
5. API   → Vérifie présence fichier S3
        → Enqueue job ARQ "process_transcription"
        → Audit log
        → WebSocket event "transcription.queued"
6. Worker→ Pull job, process (VAD → diarize → transcribe → align)
        → Update DB + S3
        → WebSocket event "transcription.done"
7. Client→ Affiche transcription éditable
```

### 5.2 Export PV Word

```
1. User → POST /api/v1/transcriptions/{id}/export { template: "pv_audition" }
2. API  → Récupère transcript JSON + template DOCX
       → Enqueue job "generate_export" (ou synchrone si <10s)
3. Worker→ Remplit template avec transcript + métadonnées cabinet
        → Stocke DOCX dans S3
        → Update DB (exports table)
4. API  → Retourne signed URL download (5 min)
5. User → Download DOCX
```

### 5.3 Suppression RGPD

```
1. User → DELETE /api/v1/user/me
2. API  → Marque user.deleted_at = NOW()
       → Anonymise email, name (chiffrés → valeur "[DELETED]")
       → Enqueue job "purge_user_data" (async, 30j de delay)
3. Worker (après 30j) → Hard delete user + cascade transcriptions
                     → Supprime audios S3
                     → Conserve audit_logs (obligation légale 3 ans)
```

---

## 6. Sécurité

### 6.1 Chiffrement

**At-rest** :
- Disques Scaleway : chiffrement automatique (LUKS)
- S3 : AES-256 bucket-level
- DB colonnes sensibles : pgcrypto symétrique avec clé dans Scaleway Secret Manager

**In-transit** :
- TLS 1.3 sur tout endpoint public
- mTLS entre services internes (phase 3+)

**Clés** :
- Clé maître dans Scaleway Secret Manager
- Rotation annuelle prévue (processus documenté)
- Jamais de clé dans le code ni les variables d'env non sécurisées

### 6.2 Auth

- Hash password : **argon2id** (paramètres OWASP recommandés 2026)
- JWT court (15 min) + refresh token (7j, rotation à chaque usage)
- 2FA TOTP obligatoire pour rôles admin/owner
- Session revoquable côté serveur (Redis blocklist)

### 6.3 Autorisation

- RBAC avec 3 rôles : owner, admin, member
- Permissions granulaires par feature (future V2)
- Scoping tenant **automatique** via middleware + RLS

### 6.4 Validation inputs

- Toujours Pydantic (back) ou Zod (front)
- Whitelist, jamais blacklist
- Taille max sur chaque champ
- MIME sniffing côté serveur (pas de confiance au header Content-Type)
- Antivirus scan sur upload (ClamAV ou service tiers EU) — phase 3

### 6.5 Protection contre abus

- Rate limiting Redis
- WAF Cloudflare / Scaleway
- Captcha hCaptcha sur signup
- Email vérification obligatoire avant usage
- Détection comportement suspect (trop d'uploads, patterns bizarres) → alerte admin

---

## 7. Observabilité

### 7.1 Logs

- Format : JSON structuré
- Fields obligatoires : `timestamp`, `level`, `service`, `trace_id`, `org_id?`, `user_id?`, `action`
- **Jamais** : contenu sensible, PII, secrets
- Agrégateur : Grafana Loki (EU)
- Rétention : 90j hot, 1 an archive

### 7.2 Métriques

- Prometheus + Grafana Cloud EU
- Dashboards : API latency, queue depth, GPU utilization, DB connections, error rate
- SLO cible : API p95 < 300ms, uptime 99.5% phase 1, 99.9% phase 3+

### 7.3 Tracing

- OpenTelemetry sur API + workers
- Traces full request lifecycle : front → API → worker → DB
- Sampling 10% en prod, 100% en dev

### 7.4 Alerting

- Alertmanager + PagerDuty EU (ou Ilert)
- Alertes critiques : uptime, error rate > 5%, queue backlog > 1h, GPU crash, paiement Stripe failed
- On-call rotation (même solo : prévoir une astreinte)

---

## 8. CI/CD

### 8.1 Pipeline GitHub Actions

**Sur chaque PR** :
1. Lint (ESLint, Prettier, Ruff, Black)
2. Type check (tsc, mypy)
3. Tests unitaires
4. Tests integration (avec DB/Redis dockérisés)
5. Tests sécurité (scan Snyk, Trivy image)
6. Build Docker images

**Sur merge main** :
1. Tout le pipeline PR
2. Tests E2E Playwright sur staging
3. Deploy automatique staging
4. Manual approval pour prod
5. Deploy prod blue/green
6. Smoke tests post-deploy

### 8.2 Environnements

| Env | Données | Accès | Déploiement |
|-----|---------|-------|-------------|
| local | Fake + MinIO | Dev | Docker compose |
| dev | Fake | Dev team | Auto sur push feature/* |
| staging | Fake (volume réaliste) | Dev + bêta testeurs | Auto sur merge main |
| prod | Réelles | Clients | Manual approval |

### 8.3 Secrets management

- `.env.example` committé (sans secrets)
- Secrets locaux : `.env` dans `.gitignore`
- Secrets CI : GitHub Secrets (chiffrés)
- Secrets prod : Scaleway Secret Manager, injection au runtime

---

## 9. Plan de mise à l'échelle

### Phase 1 : MVP (0-15 clients)
- 1 instance front, 1 API
- 1 worker GPU L4 on-demand (démarré à la main ou cron)
- Postgres DEV-S, Redis DEV
- Coût infra : ~85€/mois

### Phase 2 : Lancement (15-50 clients)
- 2 instances front/API (HA)
- 1 worker GPU continu + 1 on-demand pour pics
- Postgres PRO-S, Redis standard
- Coût : ~330€/mois

### Phase 3 : Traction (50-200 clients)
- Kubernetes (Scaleway Kapsule)
- HPA front/API/workers
- Postgres PRO-M HA, Redis HA
- 2-4 GPUs actifs en moyenne
- ISO 27001 processus lancé
- Coût : ~950€/mois

### Phase 4 : Scale (200-500 clients)
- Multi-AZ
- Replica DB lecture
- Reserved GPU capacity
- Équipe : 2-3 devs, 1 ops, 1 support
- Coût infra : ~2 650€/mois

---

## 10. Disaster Recovery

- **RTO** (Recovery Time Objective) cible : 4h
- **RPO** (Recovery Point Objective) cible : 1h

### Stratégie backup
- DB : snapshot quotidien + WAL continu (PITR 7j)
- S3 : versioning activé + cross-region replication (PAR-2 ↔ AMS)
- Secrets : backup chiffré hebdomadaire offline

### Runbooks
À rédiger dans `docs/runbooks/` :
- Restauration DB point-in-time
- Bascule région en cas d'incident PAR
- Rotation des clés de chiffrement
- Incident sécurité (data breach)

---

## 11. Roadmap technique

### V1.0 — MVP
- Auth + orgs + users
- Upload + pipeline transcription français
- Éditeur de transcript basique
- Export DOCX PV standard
- Facturation Stripe abonnement

### V1.1 — Consolidation
- 2FA + RBAC complet
- Templates PV personnalisables
- Multi-langues FR/EN
- API publique (webhook dispo)

### V1.2 — Productivité
- Recherche full-text dans les transcripts
- Tags et annotations
- Export SRT/VTT pour vidéos
- Intégration directe logiciels cabinet (Secib, Diapaz)

### V2.0 — IA avancée
- Résumés automatiques avec LLM self-hosted (Mistral large, Llama 3.3)
- Classification automatique (type d'audition, sujet)
- Recherche sémantique multi-dossier

### V3.0 — Enterprise
- Single-tenant dédié
- SSO SAML/OIDC
- Audit exports SOC 2
- On-premise appliance (optionnel)

---

## 12. Décisions ouvertes (à trancher)

Ces points sont notés ici pour qu'on se souvienne qu'ils ne sont pas fixés. À traiter dans des ADR dédiés :

- [ ] Auth.js self-hosted vs Clerk EU (cost vs time-to-market)
- [ ] Gladia API (MVP rapide) vs self-hosted pipeline dès le départ
- [ ] Monolith apps/api ou split en microservices (recommandé : monolith tant que < 10 devs)
- [ ] Traitement temps réel (live transcription) : V2 ou plus tôt ?
- [ ] Application mobile : nécessaire ou PWA suffit ?

---

**Dernière mise à jour** : 22/04/2026
**Auteur principal** : Aymane ABCHIR
