# ADR 0002 — Gladia comme provider de transcription pour le MVP

**Date** : 2026-04-28  
**Statut** : Accepté  
**Décideur** : Aymane ABCHIR

---

## Contexte

Greffo doit transcrire des fichiers audio juridiques (audiences, entretiens, dictées) avec identification des locuteurs (diarization). Deux approches s'affrontent :

- **Self-hosted** : faster-whisper (large-v3) + pyannote.audio sur GPU Scaleway L4, entièrement sous notre contrôle.
- **SaaS API** : Gladia, API de transcription hébergée en Europe, avec diarization incluse.

Le MVP doit être livré rapidement. Les instances GPU L4 sont onéreuses à opérer (cold start, maintenance des modèles, mise à l'échelle). Gladia déclare héberger ses données en UE et dispose d'une API v2 documentée couvrant upload + transcription + diarization en un seul appel.

---

## Décision

**Utiliser Gladia comme provider de transcription pour le MVP.**

L'abstraction `TranscriptionProvider` (ABC) est en place dès maintenant. Le `StubProvider` reste disponible en dev/test. Le `GladiaProvider` devient le provider par défaut en staging et production via `TRANSCRIPTION_PROVIDER=gladia`.

---

## Conséquences

### Positives
- Zéro GPU à provisionner pour le MVP — réduction du time-to-market.
- Diarization incluse dans l'API Gladia, pas d'intégration pyannote à maintenir.
- Facturation à l'usage (minutes transcrites), alignée avec notre modèle d'abonnement à quotas.
- L'abstraction `TranscriptionProvider` permet de switcher vers le self-hosted sans changer le pipeline.

### Négatives / Risques
- **Dépendance tierce** : toute panne Gladia impacte les utilisateurs. Mitigation : retry 3× avec backoff exponentiel, timeout configurables, `error_code` persisté en DB pour le support.
- **Coût variable** : si le volume d'audio explose, le coût Gladia peut dépasser une instance GPU fixe. Seuil à surveiller (~500h audio/mois selon tarifs actuels).
- **Conformité RGPD** : les fichiers audio transitent vers Gladia. Il faut vérifier et signer leur DPA avant toute mise en production avec de vraies données clients. Blocant avant la prod.
- **Qualité vocabulaire juridique** : faster-whisper large-v3 fine-tuné sur du français juridique peut surpasser Gladia. Benchmark à réaliser dès que nous avons 20+ enregistrements réels.

---

## Alternatives écartées

### faster-whisper self-hosted (phase 2)
- Meilleur contrôle RGPD (aucune donnée ne sort de notre infrastructure).
- Nécessite des instances GPU L4 H24 ou cold-start de 15-30s — complexité ops non justifiée pour le MVP.
- **Prévu en phase 2** : si les benchmarks de qualité ou les coûts Gladia le justifient, `GladiaProvider` est remplaçable sans modifier le pipeline.

### OpenAI Whisper API
- ❌ Exclu dès le départ : hébergement US, incompatible RGPD strict (voir CLAUDE.md §5).

### Happyscribe / Authôt
- APIs moins flexibles, pas de SDK async Python, tarifs moins compétitifs à volume.

---

## Checklist avant mise en production

- [ ] DPA Gladia signé et archivé
- [ ] `GLADIA_API_KEY` stockée dans Scaleway Secret Manager (jamais en clair)
- [ ] Benchmark qualité sur 20 enregistrements d'audiences réelles
- [ ] Monitoring Sentry EU sur les `error_code` Gladia (AUTH_ERROR, TIMEOUT, AUDIO_INVALID)
- [ ] Alerte si taux d'erreur Gladia > 5% sur 1h
