from pylon import settings, output_messages
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, PayloadSchemaType, SearchParams
import uuid
import structlog

class QdrantGateway:

    def __init__(self):
        self._qdrant_client = None
        self._logger = structlog.get_logger()

    def initialize_client(self):
        self._qdrant_client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            timeout=settings.QDRANT_TIMEOUT,
            prefer_grpc=True,
            check_compatibility=False
        )

    def health_check(self):
        return self._qdrant_client.health_check()

    def get_client(self):
        if not self._qdrant_client:
            self.initialize_client()
        return self._qdrant_client

    def recreate_collection(self):
        if self._qdrant_client:
            self._qdrant_client.recreate_collection(
                collection_name=settings.collection_name,
                vectors_config=VectorParams(
                    size=settings.VECTOR_DIMENSION,
                    distance=Distance.COSINE
                )
            )
            self._logger.info(f"{output_messages.QDRANT_COLLECTION_CREATION}", name=settings.collection_name)

    def create_payload_index(self, field_name="text", field_schema=PayloadSchemaType.TEXT):
        if self._qdrant_client:
            self._qdrant_client.create_payload_index(
                collection_name=settings.collection_name,
                field_name=field_name,
                field_schema=field_schema
            )
            self._logger.info(f"{output_messages.QDRANT_INXED_CREATION}", name=field_name)

    def search(self, query_vector, collection=settings.collection_name):
        results = self._qdrant_client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=int(settings.MAX_CHUNKS),
                score_threshold=float(settings.AI_MODEL_SCORE),
                search_params=SearchParams(hnsw_ef=int(settings.AI_MODEL_HNSW)),
            )
        
    def generate_points(self, vectors, documents):
        if not vectors or not documents:
            return None

        points = [
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={str(settings.QDRANT_INDEX_FIELD): document}
                    )
                    for vector, document in zip(vectors, documents)
                ]
        return points
    
    def add_points(self, points, collection=settings.collection_name):
        if points:
            self._qdrant_client.upsert(
                        collection_name=collection,
                        points=points,
                    )