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
            host=settings.db_host,
            port=settings.db_port,
            timeout=settings.db_timeout,
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
                    size=settings.vector_dimension,
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
            self._logger.info(f"{output_messages.QDRANT_INDEX_CREATION}", name=field_name)

    def search(self, query_vector, collection=settings.collection_name):
        results = self._qdrant_client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=int(settings.max_chunks),
                score_threshold=float(settings.model_score),
                search_params=SearchParams(hnsw_ef=int(settings.model_hnsw)),
            )
        
        return results
        
    def generate_points(self, vectors, documents):
        if not vectors or not documents:
            self._logger.warning("[Warp Prism] Skipped point generation - empty vectors/documents")
            return None

        points = [
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={str(settings.index_field): document}
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