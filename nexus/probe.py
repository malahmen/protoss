import asyncio
import base64
import structlog
import traceback
from pylon import settings, output_messages, RedisGateway, QdrantGateway, OllamaGateway
from nexus_settings import embedder_settings

logger = structlog.get_logger()
ollama_gateway = OllamaGateway()
redis_gateway = RedisGateway()
qdrant = QdrantGateway()
qdrant.recreate_collection()
qdrant.create_payload_index()

async def look_for_pages_messages():
    """Asynchronous embeddings generation."""
    logger.warn(f"{output_messages.EMBEDDER_WAIT_START}")
    while True:
            try:
                pages_message = await redis_gateway.get_message(settings.redis_queue_pages)
                if not pages_message:
                    continue
                
                # decode message
                decoded_pages = redis_gateway.decode_message(pages_message)
                if not decoded_pages:
                    continue
                
                # decode documents
                base64_content = decoded_pages.get(settings.redis_content_field)
                pages = base64.b64decode(base64_content)
                document_page = [page.page_content for page in pages if page.page_content.strip()] 

                vectors = OllamaGateway.get_vectors(documents=document_page)

                # Prepare points for qdrant
                points = qdrant.generate_points(vectors, document_page)
                logger.info(f"{output_messages.EMBEDDER_POINTS_GENERATED}", points_count=len(points))
                
                qdrant.add_points(points)
            except Exception as e:
                logger.error(f"{output_messages.EMBEDDER_EXCEPTION}", error=str(e))
                traceback.print_exc()

            await asyncio.sleep(embedder_settings.check_interval)

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
