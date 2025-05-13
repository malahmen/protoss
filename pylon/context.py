from pylon import RedisGateway, QdrantGateway, OllamaGateway
import structlog

class ApplicationContext:
    def __init__(self, redis_gateway, qdrant_gateway, ollama_gateway, logger):
        self.redis = redis_gateway
        self.qdrant = qdrant_gateway
        self.ollama = ollama_gateway
        self.logger = logger

    @classmethod
    async def create(cls):
        redis = await RedisGateway.create()
        qdrant = QdrantGateway()
        ollama = OllamaGateway()

        qdrant.initialize_client()
        qdrant.recreate_collection()
        qdrant.create_payload_index()

        logger = structlog.get_logger()

        return cls(redis, qdrant, ollama, logger)