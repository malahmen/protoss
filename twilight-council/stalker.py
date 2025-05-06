import asyncio
import base64
import traceback
import structlog
from pylon import settings, RedisGateway, suppress_stderr, output_messages
from twilight_council_settings import chunker_settings
import traceback
from langchain_experimental.text_splitter import SemanticChunker
from langchain_ollama import OllamaEmbeddings


logger = structlog.get_logger()
redis_gateway = RedisGateway()

async def look_for_document_messages():
    """Asynchronous pages ingestion."""
    logger.warn(f"{output_messages.CHUNKER_WAIT_START}")
    while True:
            try:
                document_message = await redis_gateway.get_message(settings.REDIS_QUEUE_DOCUMENTS)
                if not document_message:
                    continue
                
                # decode message
                decoded_documents = redis_gateway.decode_message(document_message)
                if not decoded_documents:
                    continue
                
                # decode documents
                base64_content = decoded_documents.get("content")
                documents = base64.b64decode(base64_content)

                # Initialize Semantic Splitter
                embedder = OllamaEmbeddings(model=settings.AI_MODEL, base_url=settings.AI_BASE_URL)
                chunker = SemanticChunker(embedder)
                logger.info(f"{output_messages.CHUNKER_READY}")

                logger.info(f"[Stalker] Need to chunk {documents}") # for debug only

                # Execute the document split into chunks
                with suppress_stderr(): # because of the stupid "tfs_z" warning
                    pages = chunker.split_documents(documents)
                logger.info(f"{output_messages.CHUNKER_DONE}", chunks_count=len(pages))

                # send pages to their redis queue
                await redis_gateway.send_it(settings.REDIS_QUEUE_PAGES, pages, redis_gateway.generate_message_id())

            except Exception as e:
                logger.error(f"{output_messages.EXTRACTOR_EXCEPTION}", error=str(e))
                traceback.print_exc()

            await asyncio.sleep(chunker_settings.CHECK_INTERVAL)

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
