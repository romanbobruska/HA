#!/bin/bash
# ============================================================
# Deploy skript pro HA + Node-RED
# Spusťte přes SSH na Home Assistant
# Usage: bash deploy.sh                       # klonuje/aktualizuje repo + deploy Node-RED
#        bash deploy.sh --with-ha             # + restart Home Assistant
#        bash deploy.sh --branch=feature/xyz  # deploy z jiné branch
# ============================================================

set -e

REPO_DIR="/tmp/HA"
REPO_URL="https://github.com/romanbobruska/HA.git"
BRANCH="main"
HA_CONFIG="/config"
NODERED_DIR="/addon_configs/a0d7b954_nodered"
RESTART_HA=false

for arg in "$@"; do
    case $arg in
        --with-ha) RESTART_HA=true ;;
        --branch=*) BRANCH="${arg#*=}" ;;
    esac
done
echo "=========================================="
echo "  Deploy HA + Node-RED z GitHub repo"
echo "  Branch: $BRANCH"
if $RESTART_HA; then
    echo "  (s restartem Home Assistant)"
else
    echo "  (pouze Node-RED)"
fi
echo "=========================================="

# --- 1. Kontrola / klonování repozitáře ---
echo ""
if [ -d "$REPO_DIR/.git" ]; then
    echo "📥 Repo existuje, přepínám na branch $BRANCH..."
    cd "$REPO_DIR"
    git fetch origin
    git checkout "$BRANCH" 2>/dev/null || git checkout -b "$BRANCH" "origin/$BRANCH"
    git reset --hard "origin/$BRANCH"
    echo "   ✅ Repo aktualizováno (branch: $BRANCH)"
else
    echo "📥 Klonuji repo (branch: $BRANCH)..."
    rm -rf "$REPO_DIR"
    cd /tmp
    git clone -b "$BRANCH" "$REPO_URL"
    echo "   ✅ Repo naklonováno (branch: $BRANCH)"
fi

# --- 2. Úklid starých záloh ---
echo ""
echo "🧹 Mažu staré zálohy..."
sudo -n rm -rf /config/backup_* 2>/dev/null && echo "   ✅ Zálohy smazány" || echo "   ℹ️  Žádné zálohy k smazání"

# --- 3. Kopie HA konfiguračních souborů ---
echo ""
echo "📋 Kopíruji HA konfiguraci..."
sudo -n python3 /tmp/HA/deploy_copy_ha.py || true

# --- 4. Sloučení všech Node-RED flows do jednoho flows.json ---
echo ""
echo "🔧 Slučuji Node-RED flows..."

# Zastav Node-RED PŘED zápisem přes HA API
echo "   ⏹️  Zastavuji Node-RED..."
HA_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIyYzg3OGM0MGM4MzU0MzI1OGZiZDcxODFhM2ZlZTQyZiIsImlhdCI6MTc3MTg4NzE0MywiZXhwIjoyMDg3MjQ3MTQzfQ.y2NTKxC9b67IlReCS6e-S2TVNCiv1mc1-RGSFUcnwuc"
curl -s -o /dev/null -X POST "http://localhost:8123/api/services/hassio/addon_stop" \
    -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    --data-raw '{"addon":"a0d7b954_nodered"}' || true
sleep 5

# Najdi Node-RED adresář
if [ ! -d "$NODERED_DIR" ]; then
    echo "   ⚠️  Node-RED adresář $NODERED_DIR neexistuje, zkouším alternativy..."
    for d in /addon_configs/a0d7b954_nodered \
             /addon_configs/*/node-red \
             /addon_configs/*nodered* \
             /share/node-red \
             /data/node-red \
             /config/nodered; do
        if [ -d "$d" ]; then
            NODERED_DIR="$d"
            echo "   Nalezen: $NODERED_DIR"
            break
        fi
    done
fi

# Poslední pokus: hledání flows.json pomocí find
if [ ! -d "$NODERED_DIR" ]; then
    echo "   🔍 Hledám flows.json na disku..."
    FOUND=$(find / -name "flows.json" -not -path "*/tmp/*" -not -path "*/.git/*" -not -path "*/backup*" 2>/dev/null | head -1)
    if [ -n "$FOUND" ]; then
        NODERED_DIR=$(dirname "$FOUND")
        echo "   Nalezen přes find: $NODERED_DIR"
    fi
fi

if [ ! -d "$NODERED_DIR" ]; then
    echo "   ❌ Node-RED adresář nenalezen! Flows musíte importovat ručně."
    echo "   Tip: spusťte 'find / -name flows.json 2>/dev/null' a upravte NODERED_DIR v tomto skriptu"
else
    FLOWS_DIR="$REPO_DIR/node-red/flows" OUTPUT_FILE="$NODERED_DIR/flows.json" \
        sudo -n -E python3 /tmp/HA/deploy_merge_flows.py 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✅ Flows sloučeny úspěšně"
    else
        echo "   ❌ Chyba při slučování flows"
        exit 1
    fi
fi

# --- 5. Kontrola HA konfigurace ---
if $RESTART_HA; then
    echo ""
    echo "🔍 Kontroluji HA konfiguraci..."
    sudo -n ha core check 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "   ✅ Konfigurace OK"
    else
        echo "   ⚠️  ha core check selhal (může být OK pokud nejste na HA OS)"
    fi
fi

# --- 6. Restart ---
echo ""
echo "🔄 Restartuji služby..."
echo "   Restartuji Node-RED přes HA API..."
HA_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIyYzg3OGM0MGM4MzU0MzI1OGZiZDcxODFhM2ZlZTQyZiIsImlhdCI6MTc3MTg4NzE0MywiZXhwIjoyMDg3MjQ3MTQzfQ.y2NTKxC9b67IlReCS6e-S2TVNCiv1mc1-RGSFUcnwuc"
RESULT=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:8123/api/services/hassio/addon_restart" \
    -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    --data-raw "{\"addon\":\"a0d7b954_nodered\"}")
if [ "$RESULT" = "200" ] || [ "$RESULT" = "201" ]; then
    echo "   ✅ Node-RED restartován (HTTP $RESULT)"
else
    echo "   ⚠️  Restart selhal (HTTP $RESULT), spusťte Node-RED ručně v HA UI"
fi

if $RESTART_HA; then
    echo "   Restartuji Home Assistant..."
    sudo -n ha core restart 2>/dev/null || echo "   ⚠️  Restartujte HA ručně: Nastavení → Systém → Restartovat"
else
    echo "   ℹ️  Home Assistant NEBYL restartován (použijte --with-ha pro restart HA)"
fi

# --- 7. Úklid repozitáře ---
echo ""
echo "🧹 Mažu dočasný repozitář..."
rm -rf "$REPO_DIR"
echo "   ✅ Úklid dokončen"

echo ""
echo "=========================================="
echo "  ✅ Deploy dokončen!"
echo "=========================================="
echo ""
