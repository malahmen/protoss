from pylon import settings, output_messages
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, PayloadSchemaType, SearchParams, Filter, FieldCondition, MatchText, MatchValue
import uuid
import structlog
import grpc

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
            try:
                exists = self._qdrant_client.collection_exists(settings.collection_name)
                self._logger.info(f"QDRANT DEBUG ", name=settings.collection_name, exists=exists)
                if not exists:
                    self._qdrant_client.create_collection(
                        collection_name=settings.collection_name,
                        vectors_config=VectorParams(
                            size=settings.vector_dimension,
                            distance=Distance.COSINE
                        )
                    )
                    self._logger.info(f"{output_messages.QDRANT_COLLECTION_CREATION}", name=settings.collection_name)
                else:
                    self._logger.info(f"{output_messages.QDRANT_COLLECTION_EXISTS}", result=self._qdrant_client.collection_exists(settings.collection_name))
            except grpc.RpcError as e:
                if "already exists" not in str(e).lower():
                    raise

    def create_payload_index(self, field_name="text", field_schema=PayloadSchemaType.TEXT):
        if self._qdrant_client:
            collection_info = self._qdrant_client.get_collection(collection_name=settings.collection_name)
            existing_indexes = collection_info.payload_schema or {}
            if field_name not in existing_indexes:
                self._qdrant_client.create_payload_index(
                    collection_name=settings.collection_name,
                    field_name=field_name,
                    field_schema=field_schema
                )
                self._logger.info(f"{output_messages.QDRANT_INDEX_CREATION}", name=field_name)

    def search(self, query_vector, question, collection=settings.collection_name):
        # Create a filter that matches the text field with the question
        # Using a combination of must and should for better results
        filter = Filter(
            must=[
                FieldCondition(
                    key=settings.index_field,
                    match=MatchText(
                        text=question
                    )
                )
            ],
            should=[
                FieldCondition(
                    key=settings.index_field,
                    match=MatchValue(
                        value=question,
                        text={"type": "bm25"}
                    )
                )
            ]
        )

        results = self._qdrant_client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=int(settings.max_chunks),
            score_threshold=float(settings.model_score),
            search_params=SearchParams(hnsw_ef=int(settings.model_hnsw)),
            query_filter=filter
        )
        self._logger.debug(f"{output_messages.QDRANT_SEARCH_RESULT}", search_results=results)

        return results
        
    def generate_points(self, vectors, documents):
        if not vectors or not documents:
            self._logger.debug(f"{output_messages.QDRANT_POINTS_SKIPPED}")
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

    def add_to_qdrant(self, vectors, texts):
        if not vectors or not texts:
            return
        points = self.generate_points(vectors, texts)
        self.add_points(points)

    def get_relevant_documents(self, vector, query):
        return self.search(query_vector=vector, question=query)