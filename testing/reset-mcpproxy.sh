#!/bin/bash
#
# MCP Proxy Reset Script - Docker-based Isolated Testing
#
# This script provides complete isolation for MCP proxy testing using Docker.
# Each test session gets a clean environment with fresh configuration and logs.
#

set -e

# Configuration defaults
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$SCRIPT_DIR/docker"
TEST_SESSION="${TEST_SESSION:-$(date +%s)}"
TEST_PORT="${TEST_PORT:-8081}"
METRICS_PORT="${METRICS_PORT:-9091}"
LOG_LEVEL="${LOG_LEVEL:-info}"
MCPPROXY_SOURCE="${MCPPROXY_SOURCE:-/Users/user/repos/mcpproxy-go}"
MCP_SERVERS_CONFIG="/Users/user/repos/claude-eval-agents/claude-agent-project/mcp_servers_test.json"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo "======================================================"
    echo "🐳 MCP Proxy Reset - Docker Isolated Testing"
    echo "======================================================"
    echo "Test Session: $TEST_SESSION"
    echo "Test Port: $TEST_PORT"
    echo "Metrics Port: $METRICS_PORT"
    echo "Source: $MCPPROXY_SOURCE"
    echo "======================================================"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is not installed or not in PATH"
        echo "Please install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check Docker Compose
    if ! docker compose version >/dev/null 2>&1; then
        log_error "Docker Compose is not available"
        echo "Please install Docker Compose or use Docker Desktop"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running"
        echo "Please start Docker service"
        exit 1
    fi
    
    # Check jq for JSON manipulation
    if ! command -v jq >/dev/null 2>&1; then
        log_warn "jq is not installed - some features may be limited"
        echo "Install with: brew install jq"
    fi
    
    log_success "Dependencies check passed"
}

cleanup_previous_session() {
    log_info "Cleaning up previous test sessions..."
    
    # Stop and remove containers for this session
    cd "$DOCKER_DIR"
    TEST_SESSION="$TEST_SESSION" docker compose down --remove-orphans --volumes 2>/dev/null || true
    
    # Clean up any dangling containers with our pattern
    docker ps -a --filter "name=mcpproxy-test-" --format "table {{.Names}}" | grep -v NAMES | while read -r container; do
        log_info "Removing container: $container"
        docker rm -f "$container" 2>/dev/null || true
    done
    
    # Clean up unused networks
    docker network ls --filter "name=mcpproxy-test-" --format "{{.Name}}" | while read -r network; do
        log_info "Removing network: $network"
        docker network rm "$network" 2>/dev/null || true
    done
    
    # Clean up old volumes (keep only last 3 sessions)  
    local volumes=$(docker volume ls --filter "name=mcpproxy-data-" --format "{{.Name}}" | sort)
    local volume_count=$(echo "$volumes" | wc -l | tr -d ' ')
    if [ "$volume_count" -gt 3 ]; then
        echo "$volumes" | head -n $((volume_count - 3)) | while read -r volume; do
            if [ -n "$volume" ]; then
                log_info "Removing old volume: $volume"
                docker volume rm "$volume" 2>/dev/null || true
            fi
        done
    fi
    
    # Clean local logs directory
    if [ -d "$DOCKER_DIR/logs" ]; then
        rm -rf "$DOCKER_DIR/logs"
    fi
    mkdir -p "$DOCKER_DIR/logs"
    
    log_success "Cleanup completed"
}

build_mcpproxy_binary() {
    log_info "Building MCP Proxy binary..."
    
    # Set environment variables for build script
    export MCPPROXY_SOURCE="$MCPPROXY_SOURCE"
    export BUILD_FORCE="false"  # Only rebuild if needed
    export BUILD_CACHE="true"   # Use Go build cache for faster builds
    
    # Run the build script
    if ! bash "$SCRIPT_DIR/build-mcpproxy.sh"; then
        log_error "Failed to build MCP Proxy binary"
        exit 1
    fi
    
    # Verify binary exists
    if [ ! -f "$MCPPROXY_SOURCE/mcpproxy" ]; then
        log_error "MCP Proxy binary not found after build"
        exit 1
    fi
    
    log_success "MCP Proxy binary ready"
}

start_docker_environment() {
    log_info "Starting Docker environment..."
    
    cd "$DOCKER_DIR"
    
    # Copy mcpproxy binary to Docker context
    log_info "Copying mcpproxy binary to Docker context..."
    if [ ! -f "$MCPPROXY_SOURCE/mcpproxy" ]; then
        log_error "MCP Proxy binary not found at: $MCPPROXY_SOURCE/mcpproxy"
        exit 1
    fi
    
    cp "$MCPPROXY_SOURCE/mcpproxy" ./mcpproxy
    if [ $? -ne 0 ]; then
        log_error "Failed to copy mcpproxy binary"
        exit 1
    fi
    
    # Export environment variables for docker-compose
    export TEST_SESSION="$TEST_SESSION"
    export TEST_PORT="$TEST_PORT"
    export METRICS_PORT="$METRICS_PORT"
    export LOG_LEVEL="$LOG_LEVEL"
    export MCPPROXY_SOURCE="$MCPPROXY_SOURCE"
    export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
    
    # Build and start the container
    if ! docker compose up -d --build; then
        log_error "Failed to start Docker environment"
        exit 1
    fi
    
    # Wait for container to be healthy
    log_info "Waiting for MCP Proxy to become healthy..."
    local max_wait=60
    local wait_time=0
    
    while [ $wait_time -lt $max_wait ]; do
        if docker compose ps | grep -q "healthy"; then
            break
        fi
        sleep 2
        wait_time=$((wait_time + 2))
        echo -n "."
    done
    echo
    
    if [ $wait_time -ge $max_wait ]; then
        log_error "MCP Proxy failed to become healthy within ${max_wait}s"
        log_info "Container logs:"
        docker compose logs
        exit 1
    fi
    
    log_success "Docker environment started successfully"
}

update_mcp_servers_config() {
    log_info "Updating mcp_servers.json configuration..."
    
    # Backup existing configuration
    if [ -f "$MCP_SERVERS_CONFIG" ]; then
        cp "$MCP_SERVERS_CONFIG" "${MCP_SERVERS_CONFIG}.backup.$(date +%s)"
        log_info "Backed up existing mcp_servers.json"
    fi
    
    # Ensure directory exists
    mkdir -p "$(dirname "$MCP_SERVERS_CONFIG")"
    
    # Create or update configuration
    local proxy_config
    if command -v jq >/dev/null 2>&1; then
        # Use jq for JSON manipulation
        proxy_config=$(jq -n \
            --arg url "http://localhost:$TEST_PORT" \
            --arg session "$TEST_SESSION" \
            '{
                "mcpproxy": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-fetch"],
                    "env": {
                        "PROXY_URL": $url,
                        "PROXY_SESSION": $session
                    }
                }
            }')
        
        # Write to file
        echo "$proxy_config" > "$MCP_SERVERS_CONFIG"
    else
        # Fallback without jq
        cat > "$MCP_SERVERS_CONFIG" <<EOF
{
  "mcpproxy": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-fetch"],
    "env": {
      "PROXY_URL": "http://localhost:$TEST_PORT",
      "PROXY_SESSION": "$TEST_SESSION"
    }
  }
}
EOF
    fi
    
    log_success "Updated mcp_servers.json for test session $TEST_SESSION"
}

display_connection_info() {
    echo
    echo "======================================================"
    echo "🚀 MCP Proxy Test Environment Ready"
    echo "======================================================"
    echo "Test Session: $TEST_SESSION"
    echo "Proxy URL: http://localhost:$TEST_PORT"
    echo "MCP Endpoint: http://localhost:$TEST_PORT/mcp"
    echo "Metrics URL: http://localhost:$METRICS_PORT"
    echo
    echo "Docker Commands:"
    echo "  View logs:    cd $DOCKER_DIR && docker compose logs -f"
    echo "  Stop:         cd $DOCKER_DIR && TEST_SESSION=$TEST_SESSION docker compose down"
    echo "  Restart:      cd $DOCKER_DIR && TEST_SESSION=$TEST_SESSION docker compose restart"
    echo
    echo "Configuration:"
    echo "  MCP Config:   $MCP_SERVERS_CONFIG"
    echo "  Docker Logs:  $DOCKER_DIR/logs/"
    echo "  Data Volume:  mcpproxy-data-$TEST_SESSION"
    echo "======================================================"
}

run_health_check() {
    log_info "Running health check..."
    
    local health_url="http://localhost:$TEST_PORT/mcp"
    
    if command -v curl >/dev/null 2>&1; then
        if curl -f -s "$health_url" >/dev/null; then
            log_success "Health check passed - MCP Proxy is responding"
        else
            log_warn "Health check failed - MCP Proxy may not be fully ready"
            return 1
        fi
    else
        log_warn "curl not available - skipping health check"
    fi
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --session SESSION    Set test session ID (default: timestamp)"
    echo "  --port PORT          Set test port (default: 8081)"
    echo "  --metrics PORT       Set metrics port (default: 9091)"
    echo "  --log-level LEVEL    Set log level (default: info)"
    echo "  --source PATH        Set mcpproxy source path"
    echo "  --build-force        Force rebuild of mcpproxy binary"
    echo "  --no-cleanup         Skip cleanup of previous sessions"
    echo "  --no-config          Skip updating mcp_servers.json"
    echo "  --help               Show this help message"
    echo
    echo "Environment Variables:"
    echo "  TEST_SESSION         Test session ID"
    echo "  TEST_PORT            Test port"
    echo "  METRICS_PORT         Metrics port"
    echo "  LOG_LEVEL            Log level"
    echo "  MCPPROXY_SOURCE      MCP Proxy source path"
    echo "  ANTHROPIC_API_KEY    Claude API key"
    echo
    echo "Examples:"
    echo "  $0                                    # Default settings"
    echo "  $0 --session test123 --port 8082     # Custom session and port"
    echo "  $0 --build-force --no-cleanup        # Force build without cleanup"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --session)
            TEST_SESSION="$2"
            shift 2
            ;;
        --port)
            TEST_PORT="$2"
            shift 2
            ;;
        --metrics)
            METRICS_PORT="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --source)
            MCPPROXY_SOURCE="$2"
            shift 2
            ;;
        --build-force)
            export BUILD_FORCE="true"
            shift
            ;;
        --no-cleanup)
            SKIP_CLEANUP="true"
            shift
            ;;
        --no-config)
            SKIP_CONFIG="true"
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_header
    check_dependencies
    
    if [ "$SKIP_CLEANUP" != "true" ]; then
        cleanup_previous_session
    fi
    
    build_mcpproxy_binary
    start_docker_environment
    
    if [ "$SKIP_CONFIG" != "true" ]; then
        update_mcp_servers_config
    fi
    
    sleep 2  # Give container a moment to fully initialize
    
    if run_health_check; then
        display_connection_info
        log_success "MCP Proxy reset completed successfully!"
    else
        log_error "Setup completed but health check failed"
        log_info "Check logs with: cd $DOCKER_DIR && docker compose logs"
        exit 1
    fi
}

# Run main function
main "$@"