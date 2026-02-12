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
rm -rf /config/backup_* 2>/dev/null && echo "   ✅ Zálohy smazány" || echo "   ℹ️  Žádné zálohy k smazání"

# --- 3. Kopie HA konfiguračních souborů ---
echo ""
echo "📋 Kopíruji HA konfiguraci..."
for f in configuration.yaml automations.yaml scripts.yaml scenes.yaml mqtt.yaml modbus.yaml input_numbers.yaml template_sensors.yaml template_switches.yaml; do
    if [ -f "$REPO_DIR/homeassistant/$f" ]; then
        cp -f "$REPO_DIR/homeassistant/$f" "$HA_CONFIG/$f"
        echo "   ✅ $f"
    else
        echo "   ⚠️  $f nenalezen v repo"
    fi
done

# --- 4. Sloučení všech Node-RED flows do jednoho flows.json ---
echo ""
echo "🔧 Slučuji Node-RED flows..."

# Zastav Node-RED PŘED zápisem (jinak při restartu přepíše flows.json starými daty)
echo "   ⏹️  Zastavuji Node-RED..."
ha apps stop a0d7b954_nodered 2>/dev/null || ha addons stop a0d7b954_nodered 2>/dev/null || true
sleep 3

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
    # Python skript pro sloučení JSON souborů
    python3 -c "
import json, glob, os, sys

flows_dir = '$REPO_DIR/node-red/flows'
output_file = '$NODERED_DIR/flows.json'

all_nodes = []
seen_ids = set()
files_merged = 0

for fpath in sorted(glob.glob(os.path.join(flows_dir, '*.json'))):
    fname = os.path.basename(fpath)
    try:
        with open(fpath, 'r', encoding='utf-8-sig') as f:
            content = f.read().rstrip().rstrip('.')
            nodes = json.loads(content)
        
        added = 0
        for node in nodes:
            nid = node.get('id', '')
            # Přeskočit duplicitní globální konfigurační nody (server, global-config)
            if nid in seen_ids:
                continue
            seen_ids.add(nid)
            all_nodes.append(node)
            added += 1
        
        files_merged += 1
        print(f'   ✅ {fname} ({added} nodes)')
    except Exception as e:
        print(f'   ❌ {fname}: {e}', file=sys.stderr)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_nodes, f, ensure_ascii=False, indent=4)

print(f'')
print(f'   📊 Celkem: {files_merged} flows, {len(all_nodes)} nodes')
print(f'   📁 Uloženo do: {output_file}')
" 2>&1

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
    ha core check 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "   ✅ Konfigurace OK"
    else
        echo "   ⚠️  ha core check selhal (může být OK pokud nejste na HA OS)"
    fi
fi

# --- 6. Restart ---
echo ""
echo "🔄 Restartuji služby..."
echo "   Spouštím Node-RED..."
ha apps start a0d7b954_nodered 2>/dev/null || ha addons start a0d7b954_nodered 2>/dev/null || echo "   ⚠️  Spusťte Node-RED ručně"

if $RESTART_HA; then
    echo "   Restartuji Home Assistant..."
    ha core restart 2>/dev/null || echo "   ⚠️  Restartujte HA ručně: Nastavení → Systém → Restartovat"
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
