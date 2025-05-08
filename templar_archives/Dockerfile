# Use Qdrant version from ARG (set default value in case not provided)
ARG DB_VERSION=qdrant/qdrant:v1.8.3
FROM ${DB_VERSION}

# Set the working directory
WORKDIR /carrier

# Set the default environment variables (you can override these using .env files)
ENV DB_HOST="${DB_HOST:-localhost}"
ENV DB_PORT="${DB_PORT:-6333}"

# Optional: mount stasis_ward folder for Qdrant's data storage
VOLUME ["${DB_VOLUME}"]

# Expose the Qdrant port dynamically from QDRANT_PORT
EXPOSE ${DB_PORT}

# Entry point (Qdrant will start with the default entrypoint)
ENTRYPOINT ["/bin/bash", "-c", "qdrant"]
