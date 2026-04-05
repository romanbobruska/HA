#!/bin/bash
# Test migrace — spusť na Mintu po migrace-na-mint.sh
set -e
PASS=0; FAIL=0

check() {
    if eval "$2" &>/dev/null; then
        echo "  ✅ $1"
        ((PASS++))
    else
        echo "  ❌ $1"
        ((FAIL++))
    fi
}

echo "=== TEST MIGRACE ==="
echo ""

check "Git nainstalován" "git --version"
check "Python3 nainstalován" "python3 --version"
check "Node.js nainstalován" "node --version"
check "npx nainstalován" "npx --version"
check "SSH klíč id_ha existuje" "test -f ~/.ssh/id_ha"
check "SSH klíč oprávnění 600" "test \$(stat -c %a ~/.ssh/id_ha) = '600'"
check "Repo naklonováno" "test -d ~/Programy/HA/.git"
check "ZAKONY.TXT existuje" "test -f ~/Programy/HA/User\ inputs/ZAKONY.TXT"
check "MCP config existuje" "test -f ~/.cursor/mcp.json"
check "MCP config valid JSON" "python3 -c 'import json; json.load(open(\"$HOME/.cursor/mcp.json\"))'"

echo ""
echo "🔌 SSH test..."
if ssh -i ~/.ssh/id_ha -o MACs=hmac-sha2-256-etm@openssh.com -o ConnectTimeout=5 roman@192.168.0.30 "echo OK" 2>/dev/null; then
    echo "  ✅ SSH k HA serveru"
    ((PASS++))
    
    echo ""
    echo "📡 NR test..."
    NR_NODES=$(ssh -i ~/.ssh/id_ha -o MACs=hmac-sha2-256-etm@openssh.com roman@192.168.0.30 \
        "cat /addon_configs/a0d7b954_nodered/flows.json" 2>/dev/null | \
        python3 -c 'import sys,json; print(len(json.load(sys.stdin)))' 2>/dev/null || echo "0")
    if [ "$NR_NODES" -gt 0 ] 2>/dev/null; then
        echo "  ✅ NR flows čitelné ($NR_NODES nodů)"
        ((PASS++))
    else
        echo "  ❌ NR flows nečitelné"
        ((FAIL++))
    fi
    
    echo ""
    echo "🔤 Encoding test..."
    ENC_OK=$(ssh -i ~/.ssh/id_ha -o MACs=hmac-sha2-256-etm@openssh.com roman@192.168.0.30 \
        "cat /addon_configs/a0d7b954_nodered/flows.json" 2>/dev/null | \
        python3 -c '
import sys, json
data = json.load(sys.stdin)
ok = 0
for n in data:
    name = n.get("name","")
    if "├" in name or "┼" in name or "─" in name:
        ok = -1
        break
if ok == 0: print("OK")
else: print("GARBLED")
' 2>/dev/null || echo "ERROR")
    if [ "$ENC_OK" = "OK" ]; then
        echo "  ✅ Kódování UTF-8 OK"
        ((PASS++))
    else
        echo "  ❌ Kódování: $ENC_OK"
        ((FAIL++))
    fi
else
    echo "  ❌ SSH nefunguje"
    ((FAIL++))
fi

echo ""
echo "==========================================="
echo "  Výsledek: $PASS OK, $FAIL FAIL"
echo "==========================================="
