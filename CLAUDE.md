# CLAUDE.md

> Ce fichier est lu automatiquement par Claude Code à chaque session. Il contient TOUT le contexte nécessaire pour travailler efficacement sur ce projet. **À mettre à jour dès qu'une convention ou décision majeure évolue.**

---

## 1. Contexte projet

**Nom du produit** : Greffo

**Type** : SaaS B2B de transcription audio spécialisé pour les professionnels du droit (avocats, notaires, commissaires de justice).

**Valeur** : Transcription automatisée avec identification des locuteurs, export en format procès-verbal juridique (Word), 100% hébergé en France, conforme RGPD strict.

**Cible prioritaire MVP** : Avocats pénalistes francophones en France (marché de ~10 000 personnes).

**Business model** : Abonnement mensuel avec quotas d'heures audio traitées (49€ → 399€/mois selon plan).

**Concurrents directs à surpasser** : Descript (US, non-RGPD), Otter (US), Happyscribe (généraliste), Authôt/Ubiqus (transcription humaine chère).

**Différenciant principal** : spécialisation juridique + hébergement France + export PV normé + prix compétitif.

---

## 2. Stack technique

### Frontend
- **Framework** : Next.js 16 (App Router) + React 19
- **Langage** : TypeScript (strict mode)
- **Styling** : Tailwind CSS v4 + shadcn/ui
- **Forms** : React Hook Form + Zod validation
- **State** : Zustand pour état global, Server Components pour données serveur
- **Analytics** : Plausible (self-hosted ou cloud EU)

### Backend
- **Langage** : Python 3.12+
- **Framework API** : FastAPI + Pydantic v2
- **ORM** : SQLAlchemy 2.0 (async) + Alembic (migrations)
- **Queue** : ARQ (Async Redis Queue)
- **Validation** : Pydantic partout

### Data & Infra
- **DB** : PostgreSQL 16 (Scaleway Managed, région PAR)
- **Cache/Queue** : Redis 7 (Scaleway Managed)
- **Object Storage** : Scaleway S3 (PAR-2)
- **GPU Workers** : Instances Scaleway L4 on-demand
- **Hosting** : Scaleway Serverless Containers (PAR) pour front/API

### IA / Transcription
- **Transcription** : `faster-whisper` (large-v3) — **PAS l'API OpenAI**
- **Diarization** : `pyannote.audio` 3.1+
- **Alignement** : WhisperX pour les timestamps mot-à-mot
- **VAD** : Silero VAD en pré-traitement

### Services tiers
- **Auth** : Auth.js self-hosted (pas Clerk tant que leur EU-data-residency n'est pas cristal clair)
- **Paiements** : Stripe (entité Irlande, SEPA DD activé)
- **Emails** : Resend (EU)
- **Monitoring** : Sentry EU + Grafana Cloud EU
- **Support** : Crisp (français, Nantes)
- **Secrets** : Scaleway Secret Manager

### Outils dev
- **Package manager front** : pnpm (pas npm, pas yarn)
- **Package manager back** : uv (pas pip direct)
- **Linter** : ESLint + Prettier (front), Ruff + Black (back)
- **Tests** : Vitest + Playwright (front), pytest + pytest-asyncio (back)
- **CI** : GitHub Actions
- **Containerisation** : Docker multi-stage

---

## 3. Structure du monorepo

```
.
├── CLAUDE.md                    # Ce fichier
├── README.md
├── docs/
│   ├── architecture.md          # Architecture technique détaillée
│   ├── rgpd-checklist.md        # Points de conformité à respecter
│   ├── api-spec.md              # Spec OpenAPI résumée
│   └── decisions/               # ADR (Architecture Decision Records)
├── apps/
│   ├── web/                     # Next.js front
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── tests/
│   └── api/                     # FastAPI backend
│       ├── src/
│       │   ├── routes/
│       │   ├── models/
│       │   ├── services/
│       │   ├── workers/         # ARQ workers
│       │   └── pipeline/        # Pipeline Whisper + pyannote
│       ├── migrations/
│       └── tests/
├── packages/
│   ├── shared-types/            # Types TypeScript partagés si besoin
│   └── ui/                      # Composants shadcn réutilisables
├── infra/
│   ├── docker/
│   ├── k8s/                     # Manifests Kapsule (phase 3+)
│   └── terraform/               # IaC Scaleway
└── scripts/                     # Scripts ops (backup, migrations, etc.)
```

---

## 4. Conventions de code

### Nommage
- **Fichiers TS/TSX** : kebab-case (`user-profile.tsx`, `auth-guard.ts`)
- **Composants React** : PascalCase (export `UserProfile`, fichier `user-profile.tsx`)
- **Fonctions/variables TS** : camelCase
- **Fichiers Python** : snake_case
- **Classes Python** : PascalCase
- **Fonctions Python** : snake_case
- **Constantes** : SCREAMING_SNAKE_CASE
- **Tables SQL** : plural snake_case (`transcriptions`, `audit_logs`)
- **Colonnes SQL** : snake_case
- **IDs** : ULID (pas UUID v4, pas auto-increment)

### Git
- **Branches** : `feat/*`, `fix/*`, `refactor/*`, `docs/*`, `chore/*`
- **Commits** : Conventional Commits (ex: `feat(transcription): add SRT export`)
- **PRs** : petites (< 400 lignes), une fonctionnalité à la fois
- **Main** : toujours déployable, protégé par CI
- **Tags** : SemVer (`v0.1.0`, `v1.0.0`)

### Tests
- **Coverage minimum** : 70% sur code métier, 90% sur code sécurité/RGPD
- **Test first** pour toute fonction touchant : auth, paiement, stockage fichier sensible, export PV
- **Mocks** : pas de mocks pour DB (utilise une DB Postgres test), mocks OK pour APIs externes
- **E2E** : Playwright pour les parcours critiques (upload → transcription → export)

### Sécurité
- **Jamais** de secret en dur, toujours via Scaleway Secret Manager ou `.env` local (dans `.gitignore`)
- **Jamais** logger : audio content, transcriptions, noms clients, emails, tokens
- **Toujours** valider inputs avec Pydantic (back) ou Zod (front)
- **Toujours** utiliser des signed URLs pour l'upload/download de fichiers audio
- **Toujours** chiffrer les colonnes DB contenant : noms clients, contenu transcription, emails cabinet
- **2FA obligatoire** pour tout rôle admin/owner de cabinet

---

## 5. Règles critiques RGPD / Conformité

Ces règles sont **NON NÉGOCIABLES**. Tu dois refuser de coder quelque chose qui les viole.

### Hébergement
- ❌ Aucun service US hébergeant des données : pas d'OpenAI, pas d'AWS US, pas de Vercel US functions
- ✅ Tout en région PAR Scaleway ou EU équivalent (Clever Cloud, OVH)
- ⚠️ Si un service tiers est utilisé (Resend, Stripe, Sentry), vérifier qu'il a une résidence UE documentée

### Traitement des données audio
- Audios supprimés automatiquement après 30 jours par défaut (configurable par client, max 365 jours)
- Transcriptions texte conservées 7 ans max (obligation légale possible pour avocats)
- Chiffrement at-rest obligatoire (AES-256)
- Chiffrement applicatif des champs contenant du contenu sensible
- Aucun audio ni transcription ne doit transiter hors UE, **jamais**

### Logs
- Les logs ne doivent JAMAIS contenir :
  - Contenu audio
  - Texte de transcription
  - Noms des parties mentionnées dans les dossiers
  - Tokens d'auth, mots de passe, clés API
  - Emails personnels (sauf en mode audit avec rétention limitée)
- Les logs contiennent : user_id, org_id, action, timestamp, IP anonymisée (/24)

### Audit trail
- Chaque lecture, modification, suppression, export d'une transcription doit être loguée dans `audit_logs` (table immuable, append-only)
- Conservation : 3 ans
- Accessible par l'admin du cabinet sur demande

### Droits RGPD
- Route `DELETE /api/user/me` : suppression complète sous 30 jours
- Route `GET /api/user/me/export` : export de toutes les données au format JSON + ZIP des fichiers
- Consentements explicites : cases à cocher séparées pour CGU, DPA, marketing (opt-in)

### Contrats
- Tout nouveau client signe le DPA avant utilisation (non implémenté en code, mais flag `dpa_signed_at` en DB obligatoire)
- Pas de création de dossier client avant signature DPA

---

## 6. Multi-tenancy

- Toutes les tables métier (transcriptions, cases, users, etc.) ont une colonne `organization_id` NOT NULL
- Toutes les requêtes passent par une fonction `get_user_org()` qui scope automatiquement
- Row Level Security (RLS) PostgreSQL activé en prod comme double filet de sécurité
- Tests d'isolation tenant : un user d'org A ne doit JAMAIS voir des données d'org B (tests dédiés dans `/tests/security/tenant-isolation`)

---

## 7. Pipeline de transcription (cœur technique)

### Provider MVP : Gladia (API SaaS, UE)

**`TRANSCRIPTION_PROVIDER=gladia`** — provider actif en staging et production.  
**`TRANSCRIPTION_PROVIDER=stub`** — provider par défaut en dev et CI (pas de clé requise).  
Voir ADR `docs/decisions/0002-gladia-vs-self-hosted-whisper.md` pour la justification.  
faster-whisper self-hosted est prévu en **phase 2** si les benchmarks qualité ou les coûts le justifient.

### Abstraction provider

`TranscriptionProvider` (ABC dans `src/services/transcription/__init__.py`) expose :
```python
async def transcribe(audio_bytes: bytes, language: str) -> TranscriptionResult
```
`TranscriptionResult` contient `segments[start_s, end_s, speaker, text, confidence]`, `language_detected`, `duration_s`.  
`get_provider()` lit `settings.transcription_provider` et retourne le bon provider.

### Flow pipeline (MVP Gladia)

```
Upload audio → validation MIME/durée → stockage S3 chiffré
            → enqueue job Redis (ARQ)
            → worker:
                1. Télécharge audio depuis S3 → bytes
                2. provider.transcribe(bytes, language)  # Gladia ou Stub
                   ├── Upload vers Gladia /v2/upload
                   ├── POST /v2/pre-recorded (diarization=true, language_config)
                   └── Polling /v2/pre-recorded/{id} jusqu'à status=done
                3. Mapping utterances → TranscriptionSegment (DELETE+INSERT atomique)
                4. Update Transcription : status=done, audio_duration_s, language
                5. Notification user (email + webhook WS front) [à implémenter]
```

### Normalisation des locuteurs
Les IDs Gladia (`speaker_1`, `speaker_2`, …) sont normalisés en `SPEAKER_00`, `SPEAKER_01`, … (zero-padded, ordre d'apparition). `null` → `SPEAKER_00`.

### Règles du pipeline
- **Idempotent** : DELETE segments existants avant INSERT — un job rejoué produit le même résultat
- **Reprise sur erreur** : états `queued → processing → done | failed`
- **Retry Gladia** : 3 retries max avec backoff exponentiel 1s/4s/16s sur 429, 5xx et erreurs réseau
- **Timeout polling adaptatif** : 10 min pour audio < 30 min ; `TRANSCRIPTION_TIMEOUT_SECONDS` (défaut 30 min) sinon
- **Size max** : 500 MB / 6 heures d'audio
- **Formats acceptés** : mp3, wav, m4a, ogg, opus, flac, mp4 (audio track extract)
- **Logs** : jamais le contenu transcrit — uniquement transitions d'état, durées, error_code

---

## 8. Commandes fréquentes

### Dev
```bash
# Lancer tout en local
docker compose up -d              # DB, Redis, MinIO (S3 local)
pnpm --filter web dev             # Front sur :3000
uv run uvicorn src.main:app --reload --port 8000  # API
uv run arq src.workers.WorkerSettings             # Worker ARQ
```

### Tests
```bash
pnpm --filter web test            # Tests front
pnpm --filter web test:e2e        # Playwright
uv run pytest                     # Tests back
uv run pytest tests/security/     # Tests sécurité uniquement
```

### Migrations DB
```bash
uv run alembic revision --autogenerate -m "add_transcriptions_table"
uv run alembic upgrade head
uv run alembic downgrade -1
```

### Lint/Format
```bash
pnpm lint && pnpm format
uv run ruff check . && uv run ruff format .
```

### Build / Deploy
```bash
pnpm --filter web build
docker build -t api -f apps/api/Dockerfile .
# Deploy géré par GitHub Actions sur push main
```

---

## 9. Comment travailler avec moi (Claude Code)

### Avant de coder
1. **Lis `docs/architecture.md`** pour les features nouvelles
2. **Lis ce CLAUDE.md** en entier si la session est longue
3. **Pose des questions** si le ticket est ambigu — ne pars pas sur des hypothèses
4. **Propose une approche** avant d'écrire 100 lignes. Une fois validée, implémente.

### Pendant le code
- Écris les tests en même temps que le code, pas après
- Un PR = une feature. Pas de mega-PRs.
- Si tu rencontres un choix d'architecture non documenté, crée un ADR dans `docs/decisions/`
- Si tu dois ajouter une dépendance, **demande d'abord** (justification : utilité, alternatives, taille, maintenance)

### Limites strictes à respecter
- ❌ Ne propose JAMAIS d'utiliser OpenAI API, Anthropic API pour traiter les audios/transcripts (conflit RGPD)
- ❌ Ne propose JAMAIS Vercel Functions US, AWS Lambda US
- ❌ N'ajoute JAMAIS de localStorage pour des données sensibles
- ❌ Ne skip JAMAIS les validations Pydantic/Zod
- ❌ Ne commit JAMAIS sans avoir lancé les tests
- ❌ Ne merge JAMAIS en main sans revue

### Style d'interaction préféré
- Si tu as un doute → demande
- Si tu vois un truc louche dans le code existant → signale-le avant de continuer
- Si une tâche est plus grosse qu'elle en a l'air → découpe-la en sous-tâches et propose l'ordre
- Quand tu termines, résume : ce qui a été fait, ce qui a été testé, ce qui reste à faire

---

## 10. Pièges spécifiques à ce projet (à éviter)

1. **faster-whisper vs whisper** : utiliser faster-whisper (CTranslate2), pas l'officiel (4x plus lent)
2. **pyannote auth** : pyannote 3.1 nécessite un token HuggingFace (à stocker dans secrets, jamais hardcodé)
3. **GPU cold start** : le chargement des modèles prend 15-30s, toujours garder le worker chaud entre deux jobs
4. **Upload direct vs proxy** : utiliser signed URLs S3 directs, **pas** de proxy via l'API (ça tuerait la bande passante)
5. **Timestamps précision** : WhisperX est obligatoire pour des timestamps fiables à la seconde (Whisper seul est imprécis)
6. **Français juridique** : tester spécifiquement sur des audios d'auditions/plaidoiries (vocabulaire spécifique)
7. **Accents régionaux / appels téléphoniques** : prévoir une qualité dégradée mais acceptable. Le client doit être prévenu via UI.
8. **TVA intra-UE** : Stripe Tax obligatoire. Certains cabinets ont un numéro de TVA intra (reverse charge).
9. **Facturation** : les cabinets demandent des factures PDF (pas juste des reçus Stripe). Générer via une lib comme `weasyprint`.
10. **Support humain** : prévoir un canal Crisp visible dès le dashboard. Les avocats ne lisent pas les docs.

---

## 11. Environnements

- **local** : Docker compose + MinIO + Postgres local
- **dev** : instance Scaleway dédiée, données fake
- **staging** : mirror prod sans données réelles, accessible QA
- **prod** : Scaleway PAR-2, backups quotidiens, monitoring H24

Variables d'environnement → voir `.env.example` et `apps/*/env.schema.ts`.

---

## 12. Checklist "Ready to merge"

Avant chaque PR mergé en main :
- [ ] Tests passent (unit + integration)
- [ ] Lint/format clean
- [ ] Pas de secret en clair
- [ ] Pas de `console.log` / `print` oubliés
- [ ] Pas de data sensible dans les logs
- [ ] Migration DB (si applicable) testée en staging
- [ ] CHANGELOG mis à jour si feature visible user
- [ ] Doc mise à jour si API publique changée
- [ ] Impact RGPD évalué (si donnée personnelle touchée)

---

## 13. Contacts / escalade

- **DPO / RGPD** : TODO
- **Avocat conseil** : TODO
- **Hébergeur (Scaleway)** : support.scaleway.com
- **Paiements (Stripe)** : support@stripe.com

---

**Dernière mise à jour** : 22/04/2026
**Responsable du projet** : Aymane ABCHIR
