FROM alpine:3.19

# Install runtime dependencies and Docker
RUN apk add --no-cache ca-certificates tzdata curl jq docker docker-compose sudo

# Create app user for security and add to docker group
RUN adduser -D -s /bin/sh mcpproxy && \
    addgroup mcpproxy docker && \
    echo "mcpproxy ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/mcpproxy

# Create directories
RUN mkdir -p /app/config /app/logs /app/data && \
    chown -R mcpproxy:mcpproxy /app

# Copy pre-built mcpproxy binary (must exist in docker context)
COPY mcpproxy /app/mcpproxy

# Copy configuration templates  
COPY config-template.json /app/config/config.json
COPY entrypoint.sh /app/entrypoint.sh

# Make scripts executable
RUN chmod +x /app/entrypoint.sh /app/mcpproxy

# Switch to app user
USER mcpproxy

# Set working directory
WORKDIR /app

# Expose port 8080 (internal port)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/mcp || exit 1

# Entry point
ENTRYPOINT ["/app/entrypoint.sh"]