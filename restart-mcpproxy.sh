#!/bin/bash
# Handy script to restart MCPProxy Docker container
# Usage: ./restart-mcpproxy.sh

set -e

echo "🔄 Restarting MCPProxy Docker container..."

# Change to docker directory
cd testing/docker

# Stop and remove existing container
echo "🛑 Stopping existing container..."
TEST_SESSION=test777-dind docker compose down

# Start fresh container
echo "🚀 Starting fresh container..."  
TEST_SESSION=test777-dind docker compose up -d

# Wait for container to be ready
echo "⏳ Waiting for container to be ready..."
sleep 10

# Check status
echo "📊 Container status:"
docker ps --filter "name=mcpproxy" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check logs
echo "📝 Recent logs:"
docker logs mcpproxy-test-test777-dind --tail 5

echo "✅ MCPProxy restarted successfully!"
echo "🌐 Available on: http://localhost:8081"