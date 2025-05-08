#!/bin/sh
set -e

# Load env with defaults if not set
OLLAMA_HOST="${OLLAMA_HOST:-localhost}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"

# Start Ollama in the background
echo "🚀 Aen'vaan kash'vor... Starting Ollama server"
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama API to be ready
echo "Zhakul na'rah... Awaiting server readiness"
until curl -s http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/tags > /dev/null; do
  sleep 1
done
echo "✅ Zhakul, an'ul na'zeer. Ollama is ready!"

# Keep the process running careful with LF vs CRLF
wait $OLLAMA_PID