#!/bin/bash
# Deployment script for Home Assistant + Node-RED
# Usage: bash deploy_ha.sh

set -e

echo "=== HA Deployment Script ==="
echo ""

# 1. Cleanup old repo
echo "[1/6] Cleaning up old repository..."
rm -rf /tmp/HA

# 2. Clone latest from GitHub
echo "[2/6] Cloning latest version from GitHub..."
cd /tmp
git clone https://github.com/romanbobruska/HA.git

# 3. Copy Home Assistant config
echo "[3/6] Copying Home Assistant configuration..."
cp -r /tmp/HA/homeassistant/* /config/

# 4. Copy Node-RED flows
echo "[4/6] Copying Node-RED flows..."
mkdir -p /config/node-red/flows
cp -r /tmp/HA/node-red/flows/* /config/node-red/flows/

# 5. Restart Node-RED addon
echo "[5/6] Restarting Node-RED addon..."
ha addons restart core_nodered || echo "Warning: Could not restart Node-RED via 'ha addons'. Trying alternative method..."

# Alternative: Try supervisor API if ha command fails
if [ $? -ne 0 ]; then
    echo "Trying supervisor API..."
    curl -X POST -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
         -H "Content-Type: application/json" \
         http://supervisor/addons/core_nodered/restart || echo "Warning: Supervisor API also failed"
fi

# 6. Cleanup
echo "[6/6] Cleaning up..."
rm -rf /tmp/HA

echo ""
echo "=== Deployment Complete ==="
echo "Node-RED should be restarting now. Check the logs if changes don't appear."
echo ""
