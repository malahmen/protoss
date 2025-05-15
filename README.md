# Protoss - AI RAG System

## Description
Protoss is a AI-powered RAG (Retrieval-Augmented Generation) system that processes documents, creates embeddings, and provides intelligent responses through a distributed microservices architecture.

The system is designed with a StarCraft-inspired naming convention, where each service represents a different unit with specific responsibilities (for now).

## Features
- Document processing pipeline for various file types
- Vector database storage and retrieval
- AI-powered question answering
- RESTful API endpoints
- Web interface for interaction
- Distributed queue-based processing

## Extra Features
- Containerized microservices architecture
- Redis-based queue system for reliable message passing
- Qdrant vector database for efficient similarity search
- Ollama integration for AI model inference
- Automated file processing pipeline

## Planned Features
- Web scraping and data extraction capabilities
- Real-time file monitoring and processing
- Monitoring and metrics collection
- MAKEFILE with proper commands
- API collection (for Postman and others)

## Additional Information
- [Architecture Details](docs/architecture.md)
- [System Requirements](docs/requirements.md)
- [General Information](docs/informations.md)

## Development Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.8+
- Redis
- Qdrant
- Ollama

### Environment Variables
The system uses environment variables defined in the `.env` file for configuration. Key variables include:
- Database connection strings
- API keys and secrets
- Service ports and endpoints
- Queue configurations

### Getting Started
1. Clone the repository
2. Copy `.env.example` to `.env` and configure variables
3. Run `docker-compose up` to start all services
4. Access the web interface at `http://localhost:3000`

## Planned Support Features
- Prometheus metrics collection
- Grafana dashboards
- Log aggregation
- Health monitoring endpoints

## Known Issues
- Document processing pipeline may have delays with large files
- Vector search accuracy depends on chunk size and overlap 