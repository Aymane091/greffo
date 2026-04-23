# API Spec — Greffo

> Résumé des endpoints REST. La spec OpenAPI complète est générée automatiquement par FastAPI sur `/api/v1/docs`.

Base URL : `https://api.greffo.fr/api/v1`

---

## Auth

| Méthode | Route | Description |
|---------|-------|-------------|
| POST | `/auth/register` | Création de compte (org + owner) |
| POST | `/auth/login` | Login → access token + refresh token |
| POST | `/auth/refresh` | Rafraîchir l'access token |
| POST | `/auth/logout` | Révocation du refresh token |
| POST | `/auth/2fa/setup` | Initialiser TOTP 2FA |
| POST | `/auth/2fa/verify` | Valider code TOTP |

## Utilisateurs

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/user/me` | Profil courant |
| PATCH | `/user/me` | Modifier profil |
| DELETE | `/user/me` | Suppression compte (RGPD) |
| GET | `/user/me/export` | Export données (RGPD) |

## Organisations

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/org` | Infos du cabinet courant |
| PATCH | `/org` | Modifier le cabinet |
| GET | `/org/members` | Liste des membres |
| POST | `/org/members/invite` | Inviter un membre |
| DELETE | `/org/members/{user_id}` | Retirer un membre |

## Dossiers (Cases)

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/cases` | Liste des dossiers |
| POST | `/cases` | Créer un dossier |
| GET | `/cases/{id}` | Détail d'un dossier |
| PATCH | `/cases/{id}` | Modifier un dossier |
| DELETE | `/cases/{id}` | Archiver un dossier |

## Transcriptions

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/transcriptions` | Liste des transcriptions |
| POST | `/transcriptions/upload-url` | Obtenir une signed URL d'upload |
| POST | `/transcriptions/{id}/confirm-upload` | Confirmer l'upload et enqueuer |
| GET | `/transcriptions/{id}` | Détail + statut |
| PATCH | `/transcriptions/{id}` | Modifier titre/métadonnées |
| DELETE | `/transcriptions/{id}` | Supprimer |
| POST | `/transcriptions/{id}/export` | Générer un export (docx, srt, json) |
| GET | `/transcriptions/{id}/exports` | Liste des exports générés |

## Facturation

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/billing/subscription` | Abonnement courant |
| GET | `/billing/usage` | Consommation du mois |
| POST | `/billing/portal` | URL portail Stripe (factures, CB) |

## Webhooks

| Méthode | Route | Description |
|---------|-------|-------------|
| POST | `/webhooks/stripe` | Événements Stripe |

## WebSocket

| Route | Description |
|-------|-------------|
| `wss://api.greffo.fr/ws/{transcription_id}` | Mises à jour temps réel du statut de transcription |

---

## Conventions

- Pagination : `?page=1&size=50` (max 100)
- Filtres : `?status=done&from=2026-01-01&to=2026-12-31`
- Erreurs : `{ "error": "code", "message": "...", "details": {} }`
- Tous les IDs sont des ULIDs
- Toutes les dates sont en ISO 8601 UTC
