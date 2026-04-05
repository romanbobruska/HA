#!/bin/bash
# ============================================================
#  MIGRACE NA LINUX MINT — automatický setup pro HA/FVE projekt
#  Spusť na Mintu: bash migrace-na-mint.sh
# ============================================================
set -e

echo "==========================================="
echo "  Migrace HA/FVE projektu na Linux Mint"
echo "==========================================="
echo ""

# ---- 1. SYSTÉMOVÉ BALÍČKY ----
echo "📦 1/6 — Instalace balíčků..."
sudo apt update -qq
sudo apt install -y -qq git python3 python3-pip openssh-client curl jq nodejs npm

# ---- 2. CURSOR IDE ----
echo ""
echo "🖥️  2/6 — Cursor IDE..."
if command -v cursor &>/dev/null; then
    echo "   ✅ Cursor už nainstalován"
else
    echo "   ⬇️  Stáhni Cursor ručně z https://www.cursor.com/downloads"
    echo "   (AppImage pro Linux x64 — stáhni, chmod +x, přesuň do /usr/local/bin/cursor)"
    echo "   Po instalaci spusť tento skript znovu, nebo pokračuj dál."
    read -p "   Stiskni Enter pro pokračování..."
fi

# ---- 3. SSH KLÍČE ----
echo ""
echo "🔑 3/6 — SSH klíče..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh

if [ -f ~/.ssh/id_ha ]; then
    echo "   ✅ id_ha existuje"
else
    echo "   ❌ Chybí ~/.ssh/id_ha!"
    echo "   Zkopíruj z Windows: C:\\Users\\roman\\.ssh\\id_ha a id_ha.pub"
    echo "   Příkaz: cp /media/roman/USB/.ssh/id_ha* ~/.ssh/"
    read -p "   Zkopíruj klíče a stiskni Enter..."
fi

chmod 600 ~/.ssh/id_ha 2>/dev/null || true
chmod 644 ~/.ssh/id_ha.pub 2>/dev/null || true

# Test SSH
echo "   🧪 Test SSH připojení..."
if ssh -i ~/.ssh/id_ha -o MACs=hmac-sha2-256-etm@openssh.com -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new roman@192.168.0.30 "echo OK" 2>/dev/null; then
    echo "   ✅ SSH funguje"
else
    echo "   ⚠️  SSH nefunguje — zkontroluj klíče a síť (192.168.0.30)"
fi

# ---- 4. GIT REPO ----
echo ""
echo "📂 4/6 — Git repozitář..."
REPO_DIR="$HOME/Programy/HA"
mkdir -p "$HOME/Programy"

if [ -d "$REPO_DIR/.git" ]; then
    echo "   ✅ Repo existuje, aktualizuji..."
    cd "$REPO_DIR"
    git pull origin main
else
    echo "   ⬇️  Klonuji repo..."
    git clone https://github.com/romanbobruska/HA.git "$REPO_DIR"
fi

# ---- 5. CURSOR KONFIGURACE ----
echo ""
echo "⚙️  5/6 — Cursor MCP konfigurace..."

# Workspace rules — jsou v repu (.cursor/rules/)
WORKSPACE_RULES="$HOME/Programy/Node Red/.cursor/rules"
mkdir -p "$WORKSPACE_RULES"

# Zkopíruj rules z HA repa (jsou v workspace root)
if [ -f "$REPO_DIR/../.cursor/rules/ha-problemy.mdc" ]; then
    echo "   ✅ Workspace rules existují"
else
    # Vytvoř symlink nebo zkopíruj
    mkdir -p "$(dirname "$REPO_DIR")/.cursor/rules"
    echo "   ℹ️  Workspace rules budou v $REPO_DIR při otevření v Cursoru"
fi

# MCP config — globální
MCP_DIR="$HOME/.cursor"
mkdir -p "$MCP_DIR"

cat > "$MCP_DIR/mcp.json" << 'MCPEOF'
{
  "mcpServers": {
    "home-assistant": {
      "command": "npx",
      "env": {
        "HA_MCP_TOKEN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIyYzg3OGM0MGM4MzU0MzI1OGZiZDcxODFhM2ZlZTQyZiIsImlhdCI6MTc3MTg4NzE0MywiZXhwIjoyMDg3MjQ3MTQzfQ.y2NTKxC9b67IlReCS6e-S2TVNCiv1mc1-RGSFUcnwuc",
        "HA_MCP_URL": "http://192.168.0.30:8123"
      },
      "args": [
        "-y",
        "ha-mcp"
      ]
    }
  }
}
MCPEOF
echo "   ✅ MCP config vytvořen"

# ---- 6. ALIAS PRO DEPLOY ----
echo ""
echo "🚀 6/6 — Deploy alias..."

ALIAS_LINE='alias ha-deploy="cd ~/Programy/HA && ssh -i ~/.ssh/id_ha -o MACs=hmac-sha2-256-etm@openssh.com roman@192.168.0.30 \"rm -rf /tmp/HA; cd /tmp && git clone -b main https://github.com/romanbobruska/HA.git && cd /tmp/HA && bash deploy.sh --no-ha 2>&1\""'

if ! grep -q "ha-deploy" ~/.bashrc 2>/dev/null; then
    echo "" >> ~/.bashrc
    echo "# HA/FVE deploy aliases" >> ~/.bashrc
    echo "$ALIAS_LINE" >> ~/.bashrc
    echo 'alias ha-deploy-full="cd ~/Programy/HA && ssh -i ~/.ssh/id_ha -o MACs=hmac-sha2-256-etm@openssh.com roman@192.168.0.30 \"rm -rf /tmp/HA; cd /tmp && git clone -b main https://github.com/romanbobruska/HA.git && cd /tmp/HA && bash deploy.sh 2>&1\""' >> ~/.bashrc
    echo "   ✅ Aliasy přidány do .bashrc"
    echo "   ha-deploy     = deploy jen NR (--no-ha)"
    echo "   ha-deploy-full = deploy s restartem HA Core"
else
    echo "   ✅ Aliasy už existují"
fi

echo ""
echo "==========================================="
echo "  ✅ Migrace dokončena!"
echo "==========================================="
echo ""
echo "DALŠÍ KROKY:"
echo "  1. Otevři Cursor: cursor ~/Programy/HA"
echo "  2. Ověř MCP: Ctrl+Shift+P → 'MCP: List Servers'"
echo "  3. Spusť test: bash ~/Programy/HA/test-migrace.sh"
echo ""
echo "DEPLOY:"
echo "  ha-deploy       — jen Node-RED (výchozí)"
echo "  ha-deploy-full  — s restartem HA Core"
echo ""
