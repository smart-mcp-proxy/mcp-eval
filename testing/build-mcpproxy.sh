#!/bin/bash
#
# Build MCP Proxy Binary - Pre-hook for fresh builds
#
# This script ensures we have a fresh mcpproxy binary for testing

set -e

# Configuration
MCPPROXY_SOURCE="${MCPPROXY_SOURCE:-../mcpproxy-go}"
BUILD_FORCE="${BUILD_FORCE:-false}"
BUILD_CACHE="${BUILD_CACHE:-true}"

echo "🔨 MCP Proxy Build Script"
echo "========================="

# Check if source exists
if [ ! -d "$MCPPROXY_SOURCE" ]; then
    echo "❌ MCP Proxy source not found at: $MCPPROXY_SOURCE"
    echo "Please set MCPPROXY_SOURCE environment variable or ensure the path exists"
    exit 1
fi

# Check if Go is available
if ! command -v go >/dev/null 2>&1; then
    echo "❌ Go is not installed or not in PATH"
    echo "Please install Go: https://golang.org/doc/install"
    exit 1
fi

echo "📂 Source directory: $MCPPROXY_SOURCE"
echo "🔄 Force rebuild: $BUILD_FORCE"
echo "💾 Use build cache: $BUILD_CACHE"

# Navigate to source directory
cd "$MCPPROXY_SOURCE"

# Check Git status for changes
if command -v git >/dev/null 2>&1 && [ -d ".git" ]; then
    CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null | cut -c1-8 || echo "unknown")
    DIRTY_STATUS=$(git diff --quiet 2>/dev/null && echo "clean" || echo "dirty")
    
    echo "📝 Git status:"
    echo "  Commit: $CURRENT_COMMIT"
    echo "  Status: $DIRTY_STATUS"
    
    # Store build info
    BUILD_INFO_FILE="build-info.json"
    cat > "$BUILD_INFO_FILE" <<EOF
{
  "buildTime": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "commit": "$CURRENT_COMMIT",
  "status": "$DIRTY_STATUS",
  "builder": "$(whoami)@$(hostname)",
  "goVersion": "$(go version | cut -d' ' -f3)"
}
EOF
    echo "💾 Build info saved to: $BUILD_INFO_FILE"
fi

# Check if binary exists and is recent
BINARY_PATH="./mcpproxy"
SHOULD_BUILD=false

if [ "$BUILD_FORCE" = "true" ]; then
    echo "🔄 Force rebuild requested"
    SHOULD_BUILD=true
elif [ ! -f "$BINARY_PATH" ]; then
    echo "📦 Binary not found, building..."
    SHOULD_BUILD=true
else
    # Check if source is newer than binary
    if [ -n "$(find . -name '*.go' -newer "$BINARY_PATH" 2>/dev/null)" ]; then
        echo "🔄 Source files newer than binary, rebuilding..."
        SHOULD_BUILD=true
    else
        echo "✅ Binary is up to date"
    fi
fi

# Build if needed
if [ "$SHOULD_BUILD" = "true" ]; then
    echo "🏗️  Building MCP Proxy..."
    
    # Clean previous build if not using cache
    if [ "$BUILD_CACHE" = "false" ]; then
        echo "🧹 Cleaning module cache..."
        go clean -modcache
    fi
    
    # Download dependencies
    echo "📥 Downloading dependencies..."
    go mod tidy
    go mod download
    
    # Build with optimizations
    echo "⚙️  Compiling binary..."
    CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
        -a \
        -installsuffix cgo \
        -ldflags="-w -s -X main.buildTime=$(date -u +%Y-%m-%dT%H:%M:%SZ) -X main.buildCommit=$CURRENT_COMMIT" \
        -o mcpproxy \
        ./cmd/mcpproxy
    
    if [ $? -eq 0 ]; then
        echo "✅ Build successful!"
        
        # Display binary info
        BINARY_SIZE=$(du -h "$BINARY_PATH" | cut -f1)
        echo "📊 Binary info:"
        echo "  Size: $BINARY_SIZE"
        echo "  Path: $(realpath "$BINARY_PATH")"
        
        # Test binary
        if "$BINARY_PATH" --version >/dev/null 2>&1; then
            VERSION_INFO=$("$BINARY_PATH" --version 2>/dev/null || echo "Version info not available")
            echo "  Version: $VERSION_INFO"
        fi
        
        # Make executable
        chmod +x "$BINARY_PATH"
        
    else
        echo "❌ Build failed!"
        exit 1
    fi
else
    echo "⏩ Skipping build (binary is up to date)"
fi

echo ""
echo "🎉 MCP Proxy build completed successfully!"
echo "📍 Binary location: $MCPPROXY_SOURCE/mcpproxy"
echo "🚀 Ready for Docker container deployment"