# Requirements

## Description
Protoss is a distributed AI RAG system that requires several components to function properly. 

This document outlines the necessary requirements and setup instructions.

## Framework Version
- Python 3.8 or higher
- Docker 20.10 or higher
- Docker Compose 2.0 or higher

## Tools
### Required Development Tools
- Python IDE (VS Code recommended)
- Docker Desktop
- Git
- Make (for build automation)

### Recommended Tools
- RedisInsight (Redis client)
- Qdrant Cloud Console (Vector DB client)
- Postman (API testing)
- Prometheus & Grafana (Monitoring)

## Dependencies

### System Dependencies
| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | 3.8+ | Core programming language |
| Docker | 20.10+ | Containerization |
| Docker Compose | 2.0+ | Multi-container orchestration |
| Redis | 6.0+ | Queue management |
| Qdrant | 1.0+ | Vector database |
| Ollama | Latest | AI model inference |

### Python Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.68.0+ | API framework |
| redis | 4.0.0+ | Redis client |
| qdrant-client | 1.0.0+ | Qdrant client |
| python-dotenv | 0.19.0+ | Environment management |
| pydantic | 1.8.0+ | Data validation |
| uvicorn | 0.15.0+ | ASGI server |
| watchdog | 2.1.0+ | File system monitoring |
| beautifulsoup4 | 4.9.0+ | Web scraping |
| requests | 2.26.0+ | HTTP client |

## Makefile Commands
| Command | Description |
|---------|-------------|
| `make build` | Build all Docker containers |
| `make up` | Start all services |
| `make down` | Stop all services |
| `make logs` | View service logs |
| `make test` | Run test suite |
| `make lint` | Run code linting |
| `make clean` | Clean build artifacts |

## Setup - Local Environment

### Environment Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `REDIS_HOST` | Redis server host | localhost |
| `REDIS_PORT` | Redis server port | 6379 |
| `QDRANT_HOST` | Qdrant server host | localhost |
| `QDRANT_PORT` | Qdrant server port | 6333 |
| `OLLAMA_HOST` | Ollama server host | localhost |
| `OLLAMA_PORT` | Ollama server port | 11434 |
| `API_HOST` | API server host | 0.0.0.0 |
| `API_PORT` | API server port | 8000 |
| `FRONTEND_HOST` | Frontend server host | 0.0.0.0 |
| `FRONTEND_PORT` | Frontend server port | 3000 |

### Local Development Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/protoss.git
   cd protoss
   ```

2. Create and configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Build and start services:
   ```bash
   make build
   make up
   ```

4. Verify services are running:
   ```bash
   make logs
   ```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Postman Collection
A Postman collection is available in the `docs/postman` directory with example API requests.

## Monitoring Setup
1. Prometheus metrics are available at `/metrics` endpoint
2. Grafana dashboards are configured in `monitoring/grafana`
3. Log aggregation is handled by Docker logging drivers

## Security Considerations
1. All services run in isolated containers
2. Environment variables for sensitive data
3. API authentication required for all endpoints
4. Rate limiting implemented on API endpoints
5. Input validation on all endpoints 

   --
- [Home](../README.md)