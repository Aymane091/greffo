#!/usr/bin/env bash
# ============================================================================
#  Greffo - Demo end-to-end (provider stub OU gladia selon .env)
#
#  Pre-requis :
#    - API uvicorn lancee sur localhost:8000 (terminal 1)
#    - Worker ARQ lance (terminal 2)
#    - PostgreSQL local accessible via psql -d greffo
#    - jq installe (brew install jq)
#
#  Usage :
#    ./scripts/demo_e2e.sh                        # cherche test_audio_30s.m4a
#    ./scripts/demo_e2e.sh /chemin/vers/audio.m4a
# ============================================================================

set -euo pipefail

API="http://localhost:8000/api/v1"
AUDIO_FILE="${1:-test_audio_30s.m4a}"
DB_NAME="${DB_NAME:-greffo}"

# --- Couleurs pour lisibilite ---
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

step() { echo -e "${BLUE}==>${NC} $1"; }
ok()   { echo -e "   ${GREEN}OK${NC} $1"; }
warn() { echo -e "   ${YELLOW}!${NC}  $1"; }
err()  { echo -e "   ${RED}X${NC}  $1"; }

# --- Verifications prealables ---
if ! command -v jq >/dev/null 2>&1; then
  err "jq n'est pas installe. Lance : brew install jq"
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  err "psql n'est pas dans le PATH."
  exit 1
fi

if [ ! -f "$AUDIO_FILE" ]; then
  err "Fichier audio introuvable : $AUDIO_FILE"
  echo "    Passe le chemin en argument : ./scripts/demo_e2e.sh /chemin/audio.m4a"
  exit 1
fi

if ! curl -s -f -o /dev/null "$API/../docs" 2>/dev/null && ! curl -s -f -o /dev/null "http://localhost:8000/docs" 2>/dev/null; then
  warn "L'API ne semble pas repondre sur localhost:8000 (verifie uvicorn)."
fi

echo ""
echo "============================================================================"
echo " Greffo - Demo E2E"
echo " Audio : $AUDIO_FILE ($(du -h "$AUDIO_FILE" | cut -f1))"
echo " DB    : $DB_NAME"
echo "============================================================================"
echo ""

# --- 1. Creation organisation ---
step "1. Creation organisation"
SLUG="test-cabinet-$(date +%s)"
ORG_RESP=$(curl -s -X POST "$API/organizations" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Test Cabinet\",\"slug\":\"$SLUG\"}")

ORG_ID=$(echo "$ORG_RESP" | jq -r '.id // empty')
if [ -z "$ORG_ID" ]; then
  err "Reponse inattendue : $ORG_RESP"
  exit 1
fi
ok "ORG_ID=$ORG_ID  (slug=$SLUG)"

# --- 2. Creation utilisateur via SQL ---
step "2. Creation utilisateur (SQL direct)"
USER_ID="01KQ$(date +%s | tail -c 11)0000000USER01"
USER_ID="${USER_ID:0:26}"  # tronque a 26 chars (ULID)
EMAIL="demo-$(date +%s)@test.fr"

psql -d "$DB_NAME" -q -c "
INSERT INTO users (id, organization_id, email, email_hash, role, created_at)
VALUES (
  '$USER_ID',
  '$ORG_ID',
  '$EMAIL',
  encode(sha256('${EMAIL}'::bytea), 'hex'),
  'owner',
  NOW()
);" > /dev/null
ok "USER_ID=$USER_ID  (email=$EMAIL)"

# --- 3. Creation dossier ---
step "3. Creation dossier"
CASE_RESP=$(curl -s -X POST "$API/cases" \
  -H "Content-Type: application/json" \
  -H "X-Org-Id: $ORG_ID" \
  -H "X-User-Id: $USER_ID" \
  -d '{"name":"Test Gladia E2E","reference":"GLAD-DEMO"}')

CASE_ID=$(echo "$CASE_RESP" | jq -r '.id // empty')
if [ -z "$CASE_ID" ]; then
  err "Reponse inattendue : $CASE_RESP"
  exit 1
fi
ok "CASE_ID=$CASE_ID"

# --- 4. Creation transcription draft ---
step "4. Creation transcription (draft)"
TR_RESP=$(curl -s -X POST "$API/transcriptions" \
  -H "Content-Type: application/json" \
  -H "X-Org-Id: $ORG_ID" \
  -H "X-User-Id: $USER_ID" \
  -d "{\"case_id\":\"$CASE_ID\",\"title\":\"Audience Gladia test\"}")

TR_ID=$(echo "$TR_RESP" | jq -r '.id // empty')
if [ -z "$TR_ID" ]; then
  err "Reponse inattendue : $TR_RESP"
  exit 1
fi
ok "TR_ID=$TR_ID"

# --- 5. Demande URL upload signee ---
step "5. Demande URL d'upload signee (HMAC)"
UPLOAD_RESP=$(curl -s -X POST "$API/transcriptions/$TR_ID/upload-url" \
  -H "X-Org-Id: $ORG_ID" \
  -H "X-User-Id: $USER_ID")

UPLOAD_URL=$(echo "$UPLOAD_RESP" | jq -r '.upload_url // empty')
if [ -z "$UPLOAD_URL" ]; then
  err "Reponse inattendue : $UPLOAD_RESP"
  exit 1
fi
ok "URL signee recuperee"

# --- 6. Upload du fichier audio ---
step "6. Upload du fichier audio"
EXT="${AUDIO_FILE##*.}"
case "$EXT" in
  mp3)  CONTENT_TYPE="audio/mpeg" ;;
  m4a)  CONTENT_TYPE="audio/mp4" ;;
  wav)  CONTENT_TYPE="audio/wav" ;;
  ogg)  CONTENT_TYPE="audio/ogg" ;;
  flac) CONTENT_TYPE="audio/flac" ;;
  *)    CONTENT_TYPE="audio/mpeg" ;;
esac

UPLOAD_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$UPLOAD_URL" \
  --data-binary "@$AUDIO_FILE" \
  -H "Content-Type: $CONTENT_TYPE")

if [ "$UPLOAD_HTTP" != "200" ] && [ "$UPLOAD_HTTP" != "204" ]; then
  err "Upload echoue (HTTP $UPLOAD_HTTP)"
  exit 1
fi
ok "Upload reussi (HTTP $UPLOAD_HTTP, content-type $CONTENT_TYPE)"

# --- 7. Confirm upload ---
step "7. Confirm-upload (declenche le worker ARQ)"
CONFIRM_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/transcriptions/$TR_ID/confirm-upload" \
  -H "X-Org-Id: $ORG_ID" \
  -H "X-User-Id: $USER_ID")

if [ "$CONFIRM_HTTP" != "200" ] && [ "$CONFIRM_HTTP" != "202" ]; then
  err "Confirm-upload echoue (HTTP $CONFIRM_HTTP)"
  exit 1
fi
ok "Worker declenche (HTTP $CONFIRM_HTTP)"

# --- 8. Polling du statut ---
step "8. Polling du statut (toutes les 5s, timeout 5 min)"
FINAL_STATUS=""
for i in $(seq 1 60); do
  STATUS=$(curl -s "$API/transcriptions/$TR_ID" \
    -H "X-Org-Id: $ORG_ID" \
    -H "X-User-Id: $USER_ID" \
    | jq -r '.status')

  printf "   [%2d/60] status=%s\n" "$i" "$STATUS"

  if [ "$STATUS" = "done" ]; then
    FINAL_STATUS="done"
    break
  fi
  if [ "$STATUS" = "failed" ]; then
    FINAL_STATUS="failed"
    break
  fi
  sleep 5
done

if [ -z "$FINAL_STATUS" ]; then
  warn "Timeout atteint - la transcription est encore en cours."
  FINAL_STATUS="timeout"
fi

echo ""
echo "============================================================================"
echo " Resultat final"
echo "============================================================================"

# --- Resume final transcription ---
step "Transcription"
curl -s "$API/transcriptions/$TR_ID" \
  -H "X-Org-Id: $ORG_ID" \
  -H "X-User-Id: $USER_ID" | jq '{id, status, audio_duration_s, language, error_code, error_message}'

# --- Premiers segments ---
echo ""
step "Premiers segments en DB (max 10)"
psql -d "$DB_NAME" -P "format=aligned" -c "
SELECT
  speaker,
  ROUND(start_s::numeric, 2) AS start,
  ROUND(end_s::numeric, 2) AS \"end\",
  substring(text, 1, 80) AS text
FROM transcription_segments
WHERE transcription_id='$TR_ID'
ORDER BY start_s
LIMIT 10;"

# --- Compte total des segments ---
SEG_COUNT=$(psql -d "$DB_NAME" -tAc "SELECT COUNT(*) FROM transcription_segments WHERE transcription_id='$TR_ID';" 2>/dev/null || echo "?")
echo ""
echo "   Total segments en DB : $SEG_COUNT"

echo ""
echo "============================================================================"
case "$FINAL_STATUS" in
  done)    echo -e "${GREEN} Demo terminee avec succes${NC}" ;;
  failed)  echo -e "${RED} Demo en echec - regarde les logs du worker${NC}" ;;
  timeout) echo -e "${YELLOW} Timeout - verifie le worker${NC}" ;;
esac
echo " IDs : ORG=$ORG_ID  USER=$USER_ID  CASE=$CASE_ID  TR=$TR_ID"
echo "============================================================================"
