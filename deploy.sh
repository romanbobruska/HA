#!/bin/bash
# ============================================================
# Deploy skript pro HA + Node-RED
# Spusťte přes SSH na Home Assistant
# Usage: bash /tmp/HA/deploy.sh
# ============================================================

set -e

REPO_DIR="/tmp/HA"
HA_CONFIG="/config"
NODERED_DIR="/config/node-red"
BACKUP_DIR="/config/backup_$(date +%Y%m%d_%H%M%S)"

echo "=========================================="
echo "  Deploy HA + Node-RED z GitHub repo"
echo "=========================================="

# --- 1. Kontrola, že repo existuje ---
if [ ! -d "$REPO_DIR" ]; then
    echo "❌ Repo neexistuje v $REPO_DIR"
    echo "   Nejprve spusťte: cd /tmp && git clone https://github.com/romanbobruska/HA.git"
    exit 1
fi

# --- 2. Záloha stávající konfigurace ---
echo ""
echo "📦 Vytvářím zálohu do $BACKUP_DIR ..."
mkdir -p "$BACKUP_DIR"
cp -f "$HA_CONFIG/configuration.yaml" "$BACKUP_DIR/" 2>/dev/null || true
cp -f "$HA_CONFIG/automations.yaml" "$BACKUP_DIR/" 2>/dev/null || true
cp -f "$HA_CONFIG/mqtt.yaml" "$BACKUP_DIR/" 2>/dev/null || true
cp -f "$HA_CONFIG/input_numbers.yaml" "$BACKUP_DIR/" 2>/dev/null || true
cp -f "$HA_CONFIG/template_sensors.yaml" "$BACKUP_DIR/" 2>/dev/null || true
cp -f "$HA_CONFIG/template_switches.yaml" "$BACKUP_DIR/" 2>/dev/null || true
if [ -f "$NODERED_DIR/flows.json" ]; then
    cp -f "$NODERED_DIR/flows.json" "$BACKUP_DIR/flows.json.bak"
fi
echo "   ✅ Záloha vytvořena"

# --- 3. Kopie HA konfiguračních souborů ---
echo ""
echo "📋 Kopíruji HA konfiguraci..."
for f in configuration.yaml automations.yaml mqtt.yaml modbus.yaml input_numbers.yaml template_sensors.yaml template_switches.yaml; do
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
        with open(fpath, 'r', encoding='utf-8') as f:
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
echo ""
echo "🔍 Kontroluji HA konfiguraci..."
ha core check 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ Konfigurace OK"
else
    echo "   ⚠️  ha core check selhal (může být OK pokud nejste na HA OS)"
fi

# --- 6. Restart ---
echo ""
echo "🔄 Restartuji služby..."
echo "   Restartuji Node-RED..."
ha addons restart core_node_red 2>/dev/null || supervisorctl restart node-red 2>/dev/null || echo "   ⚠️  Restartujte Node-RED ručně"
echo "   Restartuji Home Assistant..."
ha core restart 2>/dev/null || echo "   ⚠️  Restartujte HA ručně: Nastavení → Systém → Restartovat"

echo ""
echo "=========================================="
echo "  ✅ Deploy dokončen!"
echo "=========================================="
echo ""
echo "Záloha:     $BACKUP_DIR"
echo "Rollback:   cp $BACKUP_DIR/* $HA_CONFIG/"
echo "            cp $BACKUP_DIR/flows.json.bak $NODERED_DIR/flows.json"
echo ""
