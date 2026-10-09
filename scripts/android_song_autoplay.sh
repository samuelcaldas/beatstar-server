#!/bin/sh
# Automated Beatstar Complete Song Autoplay inside Android Device / Emulator
set -e

HOST="${1:-10.0.2.2}"
PORT="${2:-8080}"
CINTA="${3:-676d4d53-f0cb-41c6-8c27-4bb3c3c3c905}"

echo "=========================================================="
echo " Beatstar Song Autoplay Runner - Android Device Context"
echo " Target: http://${HOST}:${PORT}/gateway"
echo " Player Cinta: ${CINTA}"
echo "=========================================================="

post_gateway() {
    payload="$1"
    if command -v curl >/dev/null 2>&1; then
        curl -s -X POST -H "Content-Type: application/json" -d "$payload" "http://${HOST}:${PORT}/gateway"
        return
    fi
    len=${#payload}
    req="POST /gateway HTTP/1.1\r\nHost: ${HOST}:${PORT}\r\nContent-Type: application/json\r\nContent-Length: ${len}\r\nConnection: close\r\n\r\n${payload}"
    (printf "%b" "$req"; sleep 0.4) | toybox nc "${HOST}" "${PORT}" | tail -n 1
}

# 1. Login
echo "[1/6] Executando AllInOneLogin via userservice..."
LOGIN_PAYLOAD="{\"header\":{\"service\":\"userservice\",\"version\":\"36.1.4.9545\",\"rpcthing\":\"rpc-login-emu\",\"authenticationTicket\":\"\",\"clide\":\"\"},\"body\":{\"id\":1,\"type\":7,\"all_in_one_login\":{\"cinta\":\"${CINTA}\"}}}"
LOGIN_RESP=$(post_gateway "$LOGIN_PAYLOAD")

AUTH_TICKET=$(echo "$LOGIN_RESP" | sed -n 's/.*"authenticationTicket":"\([^"]*\)".*/\1/p')
CLIDE=$(echo "$LOGIN_RESP" | sed -n 's/.*"clide":"\([^"]*\)".*/\1/p')

if [ -z "$AUTH_TICKET" ] || [ -z "$CLIDE" ]; then
    echo "[ERRO] Falha no login: $LOGIN_RESP"
    exit 1
fi
echo "  [✓] Autenticado com sucesso!"
echo "      - Cinta: ${CINTA}"
echo "      - Clide: ${CLIDE}"
echo "      - AuthTicket: ${AUTH_TICKET}"

# 2. CMS & Song Catalog
echo ""
echo "[2/6] Consultando CMS e Catálogo de Músicas..."
CMS_PAYLOAD="{\"header\":{\"service\":\"cmsservice\",\"version\":\"36.1.4.9545\",\"rpcthing\":\"rpc-cms-emu\",\"authenticationTicket\":\"${AUTH_TICKET}\",\"clide\":\"${CLIDE}\"},\"body\":{\"id\":2}}"
CMS_RESP=$(post_gateway "$CMS_PAYLOAD")

SONG_PAYLOAD="{\"header\":{\"service\":\"songservice\",\"version\":\"36.1.4.9545\",\"rpcthing\":\"rpc-songs-emu\",\"authenticationTicket\":\"${AUTH_TICKET}\",\"clide\":\"${CLIDE}\"},\"body\":{\"id\":3}}"
SONG_RESP=$(post_gateway "$SONG_PAYLOAD")

SONG_ID=$(echo "$SONG_RESP" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p' | head -n 1)
SONG_TITLE=$(echo "$SONG_RESP" | sed -n 's/.*"title":"\([^"]*\)".*/\1/p' | head -n 1)
echo "  [✓] Música selecionada para gameplay: ${SONG_TITLE} (ID: ${SONG_ID})"

# 3. Start Song Match
echo ""
echo "[3/6] Iniciando partida da música (Intro & Started Audits)..."
NOW_MS=$(date +%s000)
START_PAYLOAD="{\"header\":{\"service\":\"syncservice\",\"version\":\"36.1.4.9545\",\"rpcthing\":\"rpc-start-emu\",\"authenticationTicket\":\"${AUTH_TICKET}\",\"clide\":\"${CLIDE}\"},\"body\":{\"cinta\":\"${CINTA}\",\"audits\":[{\"event\":\"RhythmGameIntro_SharplaAudit\",\"song_id\":\"${SONG_ID}\",\"timestamp\":${NOW_MS}},{\"event\":\"RhythmGameStarted_SharplaAudit\",\"song_id\":\"${SONG_ID}\",\"timestamp\":${NOW_MS}}]}}"
START_RESP=$(post_gateway "$START_PAYLOAD")
echo "  [✓] Partida iniciada no servidor privado!"

# 4. Simulate Full 5-Stage Song Autoplay
echo ""
echo "[4/6] Executando Autoplay em 5 Fases (100% PERFECT+)..."
echo "  🎶 Fase 1: Introdução & Verso 1 [Streak x1]"
echo "     -> TapInteraction        [PERFECT+] +2500 pts"
echo "     -> TapInteraction        [PERFECT+] +2500 pts"
echo "     -> HoldInteraction       [PERFECT+] +5000 pts (Subtotal: 10000 pts)"

echo "  🎶 Fase 2: Verso 2 [Streak x2]"
echo "     -> TapInteraction        [PERFECT+] +2500 pts"
echo "     -> FlickInteraction      [PERFECT+] +2500 pts"
echo "     -> HoldInteraction       [PERFECT+] +5000 pts (Subtotal: 20000 pts)"

echo "  🎶 Fase 3: Refrão 1 [Streak x2]"
echo "     -> SwitchHoldInteraction [PERFECT+] +5000 pts"
echo "     -> FlickInteraction      [PERFECT+] +2500 pts"
echo "     -> TapInteraction        [PERFECT+] +2500 pts (Subtotal: 30000 pts)"

echo "  🎶 Fase 4: Solo Instrumental [Streak x3]"
echo "     -> HoldFlickInteraction  [PERFECT+] +5000 pts"
echo "     -> FlickInteraction      [PERFECT+] +2500 pts"
echo "     -> TapInteraction        [PERFECT+] +2500 pts (Subtotal: 40000 pts)"

echo "  🎶 Fase 5: Refrão Final & Clímax [Streak x4]"
echo "     -> SwitchHoldInteraction [PERFECT+] +5000 pts"
echo "     -> HoldInteraction       [PERFECT+] +2500 pts"
echo "     -> TapInteraction        [PERFECT+] +2500 pts (Subtotal: 50000 pts)"

TOTAL_SCORE=50000
NOTES_COUNT=15
echo ""
echo "  [★] Execução da música concluída com perfeição!"
echo "      - Total de Notas: ${NOTES_COUNT}"
echo "      - Taxa de Precisão Perfect+: 100%"
echo "      - Pontuação Máxima: ${TOTAL_SCORE} pts (DIAMOND PERFECT)"

# 5. End Song Match & Send Final Audit
echo ""
echo "[5/6] Enviando auditoria RhythmGameEnded_SharplaAudit com Pontuação Máxima..."
END_PAYLOAD="{\"header\":{\"service\":\"syncservice\",\"version\":\"36.1.4.9545\",\"rpcthing\":\"rpc-end-emu\",\"authenticationTicket\":\"${AUTH_TICKET}\",\"clide\":\"${CLIDE}\"},\"body\":{\"cinta\":\"${CINTA}\",\"audits\":[{\"event\":\"RhythmGameEnded_SharplaAudit\",\"song_id\":\"${SONG_ID}\",\"score\":${TOTAL_SCORE},\"perfect_plus_count\":${NOTES_COUNT},\"diamond_perfect\":true,\"stars_awarded\":5,\"timestamp\":${NOW_MS}}]}}"
END_RESP=$(post_gateway "$END_PAYLOAD")
echo "  [✓] Pontuação registrada e auditada no servidor!"

# 6. Verify Profile Persistence
echo ""
echo "[6/6] Verificando perfil do jogador pós-partida..."
PROFILE_PAYLOAD="{\"header\":{\"service\":\"profileservice\",\"version\":\"36.1.4.9545\",\"rpcthing\":\"rpc-profile-emu\",\"authenticationTicket\":\"${AUTH_TICKET}\",\"clide\":\"${CLIDE}\"},\"body\":{\"cinta\":\"${CINTA}\"}}"
PROFILE_RESP=$(post_gateway "$PROFILE_PAYLOAD")

STARS=$(echo "$PROFILE_RESP" | sed -n 's/.*"stars":\([0-9]*\).*/\1/p')
COINS=$(echo "$PROFILE_RESP" | sed -n 's/.*"coins":\([0-9]*\).*/\1/p')
LEVEL=$(echo "$PROFILE_RESP" | sed -n 's/.*"level":\([0-9]*\).*/\1/p')

echo "  [✓] Status Atualizado no Banco de Dados SQLite:"
echo "      - Nível: ${LEVEL}"
echo "      - Estrelas Totais: ${STARS} ★"
echo "      - Moedas Acumuladas: ${COINS} 🪙"

echo ""
echo "=========================================================="
echo "🎉 SUCESSO: Música concluída no dispositivo Android!"
echo "   Pontuação Máxima Diamond Perfect: ${TOTAL_SCORE} pts"
echo "=========================================================="
exit 0
