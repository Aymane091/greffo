# Checklist RGPD — Greffo

> À compléter avant le lancement. Chaque point doit être validé et daté.

## Bases légales et consentements
- [ ] Base légale documentée pour chaque traitement (contrat, obligation légale, intérêt légitime)
- [ ] DPA signé avant création de compte (`dpa_signed_at` en DB)
- [ ] Consentements séparés : CGU, DPA, marketing (opt-in explicite)
- [ ] Politique de confidentialité à jour et accessible

## Hébergement et transferts
- [ ] 100% Scaleway PAR-2 (France) pour données personnelles
- [ ] Aucun service US hébergeant des données clients
- [ ] Sous-traitants listés dans le registre des traitements (Stripe IE, Resend EU, Sentry EU)
- [ ] DPA signé avec chaque sous-traitant

## Chiffrement
- [ ] Chiffrement at-rest S3 (AES-256 bucket-level)
- [ ] Chiffrement applicatif colonnes sensibles (pgcrypto)
- [ ] Clé maître dans Scaleway Secret Manager
- [ ] TLS 1.3 sur tous les endpoints publics

## Rétention et suppression
- [ ] Audios supprimés après 30j (configurable, max 365j)
- [ ] Lifecycle policy S3 configurée sur `audios-raw`
- [ ] Route `DELETE /api/v1/user/me` fonctionnelle (suppression sous 30j)
- [ ] Route `GET /api/v1/user/me/export` fonctionnelle
- [ ] Audit logs conservés 3 ans, puis supprimés automatiquement

## Audit trail
- [ ] Table `audit_logs` append-only avec RLS
- [ ] Chaque lecture/écriture/export de transcription loguée
- [ ] Logs sans PII ni contenu de transcription
- [ ] Interface admin pour consulter les logs (par cabinet)

## Droits des personnes
- [ ] Droit d'accès (export JSON + ZIP)
- [ ] Droit à l'effacement (suppression sous 30j)
- [ ] Droit à la portabilité (format JSON standardisé)
- [ ] Droit de rectification (édition du profil)

## Sécurité
- [ ] 2FA obligatoire pour rôles owner/admin
- [ ] RLS PostgreSQL activé en prod
- [ ] Tests d'isolation tenant (`tests/security/tenant-isolation`)
- [ ] Procédure de notification de violation (72h CNIL)

## Registre des traitements
- [ ] Registre formalisé (responsable : Aymane ABCHIR)
- [ ] DPO désigné (TODO)
- [ ] AIPD réalisée si traitement à risque élevé
