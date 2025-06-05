from pylon import settings, output_messages
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, PayloadSchemaType, SearchParams, Filter, FieldCondition, MatchText, MatchValue
import uuid
import structlog
import grpc
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError
import logging 

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
        results = self._qdrant_client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=int(settings.max_chunks),
            with_payload=True,
            with_vectors=True,
            score_threshold=float(settings.model_score),
            search_params=SearchParams(hnsw_ef=int(settings.model_hnsw))
        )
        self._logger.debug(f"{output_messages.QDRANT_SEARCH_RESULT}", search_results=results)

        return results
        
    def generate_points(self, vectors, documents, metadata):
        if not vectors or not documents:
            self._logger.debug(f"{output_messages.QDRANT_POINTS_SKIPPED}")
            return None

        points = [
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={str(settings.index_field): document, **metadata[i]}
                    )
                    for i, (vector, document) in enumerate(zip(vectors, documents))
                ]
        return points
    
    def add_points(self, points, collection=settings.collection_name):
        if points:
            self._qdrant_client.upsert(
                        collection_name=collection,
                        points=points,
                    )

    def add_to_qdrant(self, vectors, texts, metadata):
        if not vectors or not texts:
            return
        points = self.generate_points(vectors, texts, metadata)
        self.add_points(points)

    def get_relevant_documents(self, vector, query):
        return self.search(query_vector=vector, question=query)

class MongoGateway:
    def __init__(self):
        self._client = None
        self._db = None
        self._logger = structlog.get_logger()

    def initialize_client(self):
        try:
            self._client = MongoClient(
                host=settings.mongodb_host,
                port=int(settings.mongodb_port),
                username=settings.mongodb_user,
                password=settings.mongodb_pass,
                serverSelectionTimeoutMS=5000
            )
            logging.getLogger("pymongo").setLevel(logging.WARNING)
            self._db = self._client[settings.mongodb_database]
            self._logger.info(output_messages.MONGO_CONNECTION_ESTABLISHED)
        except PyMongoError as e:
            self._logger.error(output_messages.MONGO_CONNECTION_FAILED, error=str(e))
            raise

    def get_client(self):
        if not self._client:
            self.initialize_client()
        return self._client

    def get_database(self):
        if not self._db:
            self.initialize_client()
        return self._db

    def health_check(self):
        try:
            self._client.admin.command('ping')
            return True
        except Exception as e:
            self._logger.error(output_messages.MONGO_HEALTH_CHECK_FAILED, error=str(e))
            return False

    def create_index(self, collection_name, field_name, ascending=True):
        db = self.get_database()
        direction = ASCENDING if ascending else DESCENDING
        db[collection_name].create_index([(field_name, direction)])
        self._logger.info(output_messages.MONGO_INDEX_CREATED, collection=collection_name, field=field_name)

    def insert_documents(self, collection_name, documents):
        if not documents:
            self._logger.debug(output_messages.MONGO_NO_DOCUMENTS_TO_INSERT)
            return
        db = self.get_database()
        result = db[collection_name].insert_many(documents)
        self._logger.info(output_messages.MONGO_INSERT_SUCCESS, inserted_ids=result.inserted_ids)

    def find_documents(self, collection_name, query, limit=10):
        db = self.get_database()
        cursor = db[collection_name].find(query).limit(limit)
        results = list(cursor)
        self._logger.debug(output_messages.MONGO_FIND_RESULTS, count=len(results))
        return results

    def drop_collection(self, collection_name):
        db = self.get_database()
        db.drop_collection(collection_name)
        self._logger.info(output_messages.MONGO_COLLECTION_DROPPED, collection=collection_name)