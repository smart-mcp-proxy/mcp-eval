#!/bin/sh
set -e

echo "🚀 Starting MCP Proxy Test Environment..."

# Create necessary directories
mkdir -p /app/logs /app/data

# Fix Docker socket permissions if mounted
if [ -S /var/run/docker.sock ]; then
    echo "🐳 Fixing Docker socket permissions..."
    # Change the group of docker socket to match the container's docker group
    sudo chgrp docker /var/run/docker.sock
    sudo chmod g+rw /var/run/docker.sock
fi

# Set environment variables with defaults
export MCPPROXY_CONFIG="${MCPPROXY_CONFIG:-/app/config/config.json}"
export MCPPROXY_LOG_LEVEL="${MCPPROXY_LOG_LEVEL:-info}"
export MCPPROXY_DATA_DIR="${MCPPROXY_DATA_DIR:-/app/data}"

# Display configuration info
echo "📋 Configuration:"
echo "  Config file: $MCPPROXY_CONFIG"
echo "  Log level: $MCPPROXY_LOG_LEVEL"
echo "  Data directory: $MCPPROXY_DATA_DIR"
echo "  Port: 8080 (internal)"

# Check if config file exists
if [ ! -f "$MCPPROXY_CONFIG" ]; then
    echo "❌ Config file not found: $MCPPROXY_CONFIG"
    exit 1
fi

# Display config summary
echo "📊 Server configuration:"
jq -r '.server | "  Host: " + .host + ":" + (.port | tostring)' "$MCPPROXY_CONFIG" 2>/dev/null || echo "  Host: 0.0.0.0:8080"
jq -r '.security.quarantine | "  Quarantine: " + (.enabled | tostring)' "$MCPPROXY_CONFIG" 2>/dev/null || echo "  Quarantine: enabled"

# Start the MCP proxy
echo "🎯 Starting MCP Proxy..."
exec /app/mcpproxy \
    --config="$MCPPROXY_CONFIG" \
    --log-level="$MCPPROXY_LOG_LEVEL" \
    --data-dir="$MCPPROXY_DATA_DIR"