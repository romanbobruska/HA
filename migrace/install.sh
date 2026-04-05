#!/bin/bash
# ============================================================
#  JEDNOKLIKOVÁ MIGRACE NA LINUX MINT
#  Otevři terminál a spusť: bash install.sh
#  Vše se nastaví automaticky — SSH, repo, Cursor, MCP.
# ============================================================
set -e
RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'; NC='\033[0m'
ok() { echo -e "  ${GRN}✅ $1${NC}"; }
fail() { echo -e "  ${RED}❌ $1${NC}"; }
info() { echo -e "  ${YEL}ℹ️  $1${NC}"; }

echo ""
echo "==========================================="
echo "  🚀 HA/FVE — Migrace na Linux Mint"
echo "==========================================="
echo ""

# ---- BALÍČKY ----
echo "📦 Systémové balíčky..."
sudo apt update -qq 2>/dev/null
sudo apt install -y -qq git python3 openssh-client curl jq 2>/dev/null
# Node.js LTS
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - 2>/dev/null
    sudo apt install -y -qq nodejs 2>/dev/null
fi
ok "git, python3, node, ssh"

# ---- SSH KLÍČE (zabalené v base64) ----
echo ""
echo "🔑 SSH klíče..."
mkdir -p ~/.ssh && chmod 700 ~/.ssh

echo "LS0tLS1CRUdJTiBPUEVOU1NIIFBSSVZBVEUgS0VZLS0tLS0KYjNCbGJuTnphQzFyWlhrdGRqRUFBQUFBQkc1dmJtVUFBQUFFYm05dVpRQUFBQUFBQUFBQkFBQUFNd0FBQUF0emMyZ3RaVwpReU5UVXhPUUFBQUNEc2pJUEh0NmZCelR1RU4zK1Z1c01TS3hwcVpvREh6eVIvWGVRcTRMbWthQUFBQUpoclBuNnphejUrCnN3QUFBQXR6YzJndFpXUXlOVFV4T1FBQUFDRHNqSVBIdDZmQnpUdUVOMytWdXNNU0t4cHFab0RIenlSL1hlUXE0TG1rYUEKQUFBRUIxMFV6RlM4QnNlNjJhR1NycjNNQW45SWdMVi81UUowMkRzcEdPLzMwRmUreU1nOGUzcDhITk80UTNmNVc2d3hJcgpHbXBtZ01mUEpIOWQ1Q3JndWFSb0FBQUFFSEp2YldGdVFGSlBUVUZPTFVGVFZWTUJBZ01FQlE9PQotLS0tLUVORCBPUEVOU1NIIFBSSVZBVEUgS0VZLS0tLS0K" | base64 -d > ~/.ssh/id_ha
chmod 600 ~/.ssh/id_ha

echo "c3NoLWVkMjU1MTkgQUFBQUMzTnphQzFsWkRJMU5URTVBQUFBSU95TWc4ZTNwOEhOTzRRM2Y1VzZ3eElyR21wbWdNZlBKSDlkNUNyZ3VhUm8gcm9tYW5AUk9NQU4tQVNVUw0K" | base64 -d > ~/.ssh/id_ha.pub
chmod 644 ~/.ssh/id_ha.pub

# known_hosts — HA server
echo "MTkyLjE2OC4wLjMwIHNzaC1lZDI1NTE5IEFBQUFDM056YUMxbFpESTFOVEU1QUFBQUlCNS9BMnhiaVJzLzJHN0E3NmR5K2ltOEhKUjhFemRDNFVEVnovem54eTFn" | base64 -d >> ~/.ssh/known_hosts
echo "MTkyLjE2OC4wLjMwIHNzaC1yc2EgQUFBQUIzTnphQzF5YzJFQUFBQURBUUFCQUFBQmdRQ3VYQXI2QjYrQ3RDSzVpY2xLM3VheWx4c0NMcllIVEFOOTk2Wm84Ti9uSStkV1dDU2JZTVZRbHVOQ3ZaNGh4UW9Xem45M0RzSEJTUXo4REl6TzA5aWo1dDE1WEdYSUFoOE4xdzFzQWs0VXVJOGFVZnREMmlaRC9kbmdTR0pDQStDT1hoeEVDZHVMbXJLL3llUUU0TTlxK1hpMVVCVTRGQ05JSkk4eEJvVWZUZ1BHVytQTHFJVS9xQWYwbVhVSVdJaU5hOVFQNjhrSUVPOWFQellLNDZQdEN3aWFGMlhxTEpReWN0S0pyZnVXT3VGQ2dRNUNKMmZ3bVUzOWV4aXc3SEhMWjRqL3VTVzFSMCs1akVGUUVIYkZHSHo1VzR0emtoN1BYa0d1NjllaTZZVVZrREJPdGFkWWV3eTByaGdidUwyRGNnMnRJTVlzTnNQK1BZbml3TTJ0WExyRTY5a0crMXNVOTdtTlV4dmNXQWdPYzlpRWZYUTZRTVkxU1lXYnp6cVd4ZHJPZ3QzUWdCdjlLYVVidXh6cXBFaVllWjhRVnZkT1djcjVuMjNHMk90SHJaT1REeHZVOUo1V25OcDBHWktpZzk3QWZuMDZBaFRnSUdFUExnMEdwM01hZHpSWTNTL2hsSXhXd2lpRjhIempxdEdKb1o2V0JFelBOY3FLNTRFPQ==" | base64 -d >> ~/.ssh/known_hosts
ok "SSH klíče nastaveny"

# Test SSH
echo ""
echo "🔌 SSH test..."
if ssh -i ~/.ssh/id_ha -o MACs=hmac-sha2-256-etm@openssh.com -o ConnectTimeout=5 roman@192.168.0.30 "echo OK" 2>/dev/null; then
    ok "SSH k HA serveru funguje"
else
    fail "SSH nefunguje — zkontroluj síť (192.168.0.30)"
    info "Zbytek instalace pokračuje, SSH opravíš později"
fi

# ---- GIT REPO ----
echo ""
echo "📂 Git repozitář..."
REPO="$HOME/Programy/HA"
mkdir -p "$HOME/Programy"
if [ -d "$REPO/.git" ]; then
    cd "$REPO" && git pull origin main 2>/dev/null
    ok "Repo aktualizováno"
else
    git clone https://github.com/romanbobruska/HA.git "$REPO" 2>/dev/null
    ok "Repo naklonováno do $REPO"
fi

# ---- CURSOR MCP CONFIG ----
echo ""
echo "⚙️  Cursor MCP..."
mkdir -p "$HOME/.cursor"
cat > "$HOME/.cursor/mcp.json" << 'EOF'
{
  "mcpServers": {
    "home-assistant": {
      "command": "npx",
      "env": {
        "HA_MCP_TOKEN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIyYzg3OGM0MGM4MzU0MzI1OGZiZDcxODFhM2ZlZTQyZiIsImlhdCI6MTc3MTg4NzE0MywiZXhwIjoyMDg3MjQ3MTQzfQ.y2NTKxC9b67IlReCS6e-S2TVNCiv1mc1-RGSFUcnwuc",
        "HA_MCP_URL": "http://192.168.0.30:8123"
      },
      "args": ["-y", "ha-mcp"]
    }
  }
}
EOF
ok "MCP config vytvořen"

# ---- BASH ALIASY ----
echo ""
echo "🚀 Deploy aliasy..."
if ! grep -q "ha-deploy" ~/.bashrc 2>/dev/null; then
    cat >> ~/.bashrc << 'ALIASES'

# === HA/FVE deploy ===
alias ha-deploy='cd ~/Programy/HA && ssh -i ~/.ssh/id_ha -o MACs=hmac-sha2-256-etm@openssh.com roman@192.168.0.30 "rm -rf /tmp/HA; cd /tmp && git clone -b main https://github.com/romanbobruska/HA.git && cd /tmp/HA && bash deploy.sh --no-ha 2>&1"'
alias ha-deploy-full='cd ~/Programy/HA && ssh -i ~/.ssh/id_ha -o MACs=hmac-sha2-256-etm@openssh.com roman@192.168.0.30 "rm -rf /tmp/HA; cd /tmp && git clone -b main https://github.com/romanbobruska/HA.git && cd /tmp/HA && bash deploy.sh 2>&1"'
ALIASES
    ok "Aliasy: ha-deploy (NR), ha-deploy-full (NR+HA)"
else
    ok "Aliasy už existují"
fi

# ---- CURSOR INSTALACE ----
echo ""
echo "🖥️  Cursor..."
if command -v cursor &>/dev/null; then
    ok "Cursor nainstalován"
else
    info "Cursor není nainstalován — stáhni z https://www.cursor.com/downloads"
    info "Po stažení: chmod +x cursor-*.AppImage && sudo mv cursor-*.AppImage /usr/local/bin/cursor"
fi

# ---- VERIFIKACE ----
echo ""
echo "==========================================="
echo "  🧪 VERIFIKACE"
echo "==========================================="
echo ""
PASS=0; FAIL=0
t() { if eval "$2" &>/dev/null; then ok "$1"; ((PASS++)); else fail "$1"; ((FAIL++)); fi; }

t "git" "git --version"
t "python3" "python3 --version"
t "node" "node --version"
t "SSH klíč" "test -f ~/.ssh/id_ha"
t "Repo" "test -d ~/Programy/HA/.git"
t "ZAKONY.TXT" "test -f ~/Programy/HA/User\ inputs/ZAKONY.TXT"
t "MCP config" "python3 -c 'import json; json.load(open(\"$HOME/.cursor/mcp.json\"))'"

# NR test
if ssh -i ~/.ssh/id_ha -o MACs=hmac-sha2-256-etm@openssh.com -o ConnectTimeout=5 roman@192.168.0.30 \
    "cat /addon_configs/a0d7b954_nodered/flows.json" 2>/dev/null | \
    python3 -c 'import sys,json; d=json.load(sys.stdin); assert len(d)>100' 2>/dev/null; then
    ok "NR flows čitelné (UTF-8)"
    ((PASS++))
else
    fail "NR flows nečitelné"
    ((FAIL++))
fi

echo ""
echo "==========================================="
if [ $FAIL -eq 0 ]; then
    echo -e "  ${GRN}✅ VŠE OK ($PASS testů)${NC}"
else
    echo -e "  ${YEL}⚠️  $PASS OK, $FAIL FAIL${NC}"
fi
echo "==========================================="
echo ""
echo "DALŠÍ KROK:"
echo "  cursor ~/Programy/HA"
echo ""
echo "DEPLOY:"
echo "  ha-deploy       — jen Node-RED"
echo "  ha-deploy-full  — s restartem HA Core"
echo ""
