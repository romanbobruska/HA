#!/bin/bash
# Deploy script for Home Assistant - clone repo and deploy changes
# Usage: bash deploy_from_scratch.sh

set -e

echo "=== HA Deploy from Scratch ==="

# Determine working directory
if [ -d "/config" ]; then
    WORK_DIR="/config"
elif [ -d "/homeassistant" ]; then
    WORK_DIR="/homeassistant"
else
    WORK_DIR="/tmp"
fi

REPO_DIR="$WORK_DIR/HA"

echo "Working directory: $WORK_DIR"
echo "Repository will be cloned to: $REPO_DIR"

# Remove old repo if exists
if [ -d "$REPO_DIR" ]; then
    echo "Removing old repository..."
    rm -rf "$REPO_DIR"
fi

# Clone repository
echo "Cloning repository from GitHub..."
cd "$WORK_DIR"
git clone https://github.com/romanbobruska/HA.git
cd "$REPO_DIR"

echo "Repository cloned successfully"
echo "Current branch: $(git branch --show-current)"
echo "Latest commit: $(git log -1 --oneline)"

# Run deploy script
echo ""
echo "=== Running deploy.sh ==="
bash deploy.sh --with-ha

echo ""
echo "=== Deploy completed ==="
echo "Repository location: $REPO_DIR"
