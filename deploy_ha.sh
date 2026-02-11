#!/bin/bash
# Deployment script for Home Assistant + Node-RED
# Usage: rm -rf /tmp/HA && cd /tmp && git clone https://github.com/romanbobruska/HA.git && bash /tmp/HA/deploy_ha.sh

set -e

REPO_DIR="/tmp/HA"
NODERED_SLUG="a0d7b954_nodered"

echo "=== HA Deployment Script ==="
echo ""

# 1. Copy Home Assistant config
echo "[1/4] Copying Home Assistant configuration..."
cp -r "$REPO_DIR/homeassistant/"* /config/

# 2. Copy Node-RED flows
echo "[2/4] Copying Node-RED flows..."
mkdir -p /config/node-red/flows
cp -r "$REPO_DIR/node-red/flows/"* /config/node-red/flows/

# 3. Restart Node-RED addon
echo "[3/4] Restarting Node-RED addon..."
if ha apps restart "$NODERED_SLUG" 2>/dev/null; then
    echo "Node-RED restarted via 'ha apps'."
elif ha addons restart "$NODERED_SLUG" 2>/dev/null; then
    echo "Node-RED restarted via 'ha addons'."
elif curl -sf -X POST -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
     -H "Content-Type: application/json" \
     "http://supervisor/addons/$NODERED_SLUG/restart" 2>/dev/null; then
    echo "Node-RED restarted via Supervisor API."
else
    echo "ERROR: Could not restart Node-RED automatically."
    echo "Please restart Node-RED manually: Settings -> Apps -> Node-RED -> Restart"
fi

# 4. Cleanup
echo "[4/4] Cleaning up..."
rm -rf "$REPO_DIR"

echo ""
echo "=== Deployment Complete ==="
