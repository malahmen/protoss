ARG OLLAMA_VERSION=ollama/ollama:latest
FROM ${OLLAMA_VERSION}

ARG MODEL_NAME
ENV MODEL_NAME=${MODEL_NAME}

ARG STARGATE_FOLDER
ENV STARGATE_FOLDER=${STARGATE_FOLDER}

# Set the working directory
WORKDIR /carrier

# Install curl
RUN apt-get update && apt-get install -y curl

# Pre-pull the model during build time
RUN if [ -z "$MODEL_NAME" ]; then echo "❌ MODEL_NAME is not set"; exit 1; fi && \
    ollama serve & \
    sleep 10 && \
    ollama pull "$MODEL_NAME" && \
    pkill ollama

# Copy model config and entrypoint script
#COPY Modelfile ./Modelfile # not building a model so...
COPY docker-entrypoint.sh ./entrypoint.sh

# Make sure it's executable
RUN chmod +x ./entrypoint.sh

# Set the custom entrypoint
ENTRYPOINT ["./entrypoint.sh"]