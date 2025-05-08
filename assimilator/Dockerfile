# Use Redis version from ARG (with default to latest version if not provided)
ARG REDIS_VERSION=redis:latest
FROM ${REDIS_VERSION}

# Set the working directory if needed (optional)
WORKDIR /carrier

# Expose the required ports for Redis communication
EXPOSE ${REDIS_PORT}

# Default command to run Redis server
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]