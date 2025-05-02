import asyncio
import base64
import traceback
import structlog
from pylon import settings, redis_gateway, track_processing_time, update_queue_size, record_error, ProcessingError, json_to_text, suppress_stderr, output_messages
from nexus_settings import embedder_settings
from typing import Dict, Any
import traceback
from langchain_ollama import OllamaEmbeddings
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, PayloadSchemaType

logger = structlog.get_logger()

# Initialize Qdrant client
qdrant = QdrantClient(
    host=settings.QDRANT_HOST,
    port=settings.QDRANT_PORT,
    timeout=settings.QDRANT_TIMEOUT,
    prefer_grpc=True,
    check_compatibility=False
)

# Create collection once at startup
qdrant.recreate_collection(
    collection_name=settings.COLLECTION_NAME,
    vectors_config=VectorParams(
        size=settings.VECTOR_DIMENSION,
        distance=Distance.COSINE
    )
)

# create the collection index for serching it
qdrant.create_payload_index(
    collection_name=settings.COLLECTION_NAME,
    field_name="text",
    field_schema=PayloadSchemaType.TEXT
)


async def send_pages(pages, message_id):
    encoded_content = base64.b64encode(pages).decode("utf-8")
    
    data = {
            'id': message_id,
            'content': encoded_content,
            'content_type': 'text/plain' # still has to be text
    }

    await redis_gateway.send_message(data, settings.REDIS_QUEUE_PAGES)

async def look_for_pages_messages():
    """Asynchronous embeddings generation."""
    logger.warn(f"{output_messages.EMBEDDER_WAIT_START}")
    while True:
            try:
                pages_message = await redis_gateway.get_message(settings.REDIS_QUEUE_PAGES)
                if not pages_message:
                    continue
                
                # decode message
                decoded_pages = redis_gateway.decode_message(pages_message)
                if not decoded_pages:
                    continue
                
                # decode documents
                base64_content = decoded_pages.get("content")
                pages = base64.b64decode(base64_content)

                # Initialize Embedder
                embedder = OllamaEmbeddings(model=settings.AI_MODEL, base_url=settings.AI_BASE_URL)
                
                document_page = [page.page_content for page in pages if page.page_content.strip()] 
                vectors = embedder.embed_documents(document_page)

                # Prepare points for qdrant
                points = [
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={"text": document}
                    )
                    for vector, document in zip(vectors, document_page)
                ]

                logger.info("qdrant_points_generated", points_count=len(points))
                qdrant.upsert(
                    collection_name=settings.COLLECTION_NAME,
                    points=points,
                )

            except Exception as e:
                logger.error(f"{output_messages.EMBEDDER_EXCEPTION}", error=str(e))
                traceback.print_exc()

            await asyncio.sleep(embedder_settings.CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        logger.info(f"{output_messages.EMBEDDER_INITIALIZATION}")
        asyncio.run(look_for_pages_messages())
    except KeyboardInterrupt:
        logger.info(f"{output_messages.EMBEDDER_TERMINATED}")
    except Exception as e:
        logger.info(f"{output_messages.EMBEDDER_KO}",
                    error=str(e),
                    traceback=traceback.format_exc())
        raise
