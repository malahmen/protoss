import asyncio
import base64
import traceback
import structlog
from pylon import settings, RedisGateway, OllamaGateway, output_messages
from twilight_council_settings import chunker_settings
import traceback


logger = structlog.get_logger()
redis_gateway = RedisGateway()
ollama_gateway = OllamaGateway()

async def look_for_document_messages():
    """Asynchronous pages ingestion."""
    logger.warn(f"{output_messages.CHUNKER_WAIT_START}")
    while True:
            try:
                document_message = await redis_gateway.get_message(settings.redis_queue_documents)
                if not document_message:
                    continue
                
                # decode message
                decoded_documents = redis_gateway.decode_message(document_message)
                if not decoded_documents:
                    continue
                
                # decode documents
                base64_content = decoded_documents.get("content")
                documents = base64.b64decode(base64_content)

                # split the data into chunks (documents into pages)
                pages = ollama_gateway.split_into_chunks(documents=documents)
                
                # send pages to their redis queue
                await redis_gateway.send_it(settings.redis_queue_pages, pages, redis_gateway.generate_message_id())

            except Exception as e:
                logger.error(f"{output_messages.EXTRACTOR_EXCEPTION}", error=str(e))
                traceback.print_exc()

            await asyncio.sleep(chunker_settings.check_interval)

if __name__ == "__main__":
    try:
        logger.info(f"{output_messages.CHUNKER_INITIALIZATION}")
        asyncio.run(look_for_document_messages())
    except KeyboardInterrupt:
        logger.info(f"{output_messages.CHUNKER_TERMINATED}")
    except Exception as e:
        logger.info(f"{output_messages.CHUNKER_KO}",
                    error=str(e),
                    traceback=traceback.format_exc())
        raise
