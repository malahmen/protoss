import asyncio
import base64
import json
import traceback
from pylon import settings, output_messages
from pylon.context import ApplicationContext
from nexus_settings import embedder_settings
from langchain_core.documents import Document

class EmbedderService:
    def __init__(self):
        self.context = None

    async def initialize(self):
        self.context = await ApplicationContext.create()
        self.context.logger.info(f"{output_messages.EMBEDDER_INITIALIZATION}")

    async def run(self):
        try:
            await self.look_for_pages_messages()
        except KeyboardInterrupt:
            self.context.logger.info(f"{output_messages.EMBEDDER_TERMINATED}")
        except Exception as e:
            self.context.logger.info(f"{output_messages.EMBEDDER_KO}",
                        error=str(e),
                        traceback=traceback.format_exc())
            raise

    async def look_for_pages_messages(self):
        """Asynchronous embeddings generation."""
        self.context.logger.debug(f"{output_messages.EMBEDDER_WAIT_START}")
        while True:
                try:
                    pages_message = await self.context.redis.get_message(settings.redis_queue_pages)
                    if not pages_message:
                        continue
                    
                    # decode message
                    decoded_pages = self.context.redis.decode_message(pages_message)
                    if not decoded_pages:
                        self.context.logger.debug(f"{output_messages.EMBEDDER_NO_MESSAGES_DECODED}", decoded_pages=len(decoded_pages))
                        continue
                    
                    # reads decoded message
                    filename = decoded_pages.get("filename")
                    message_id = decoded_pages.get("id")
                    content_mime = decoded_pages.get(settings.redis_content_type)
                    self.context.logger.debug(f"{message_id} - {filename} - {content_mime}")

                    # decode documents
                    base64_content = decoded_pages.get(settings.redis_content_field)
                    if not base64_content:
                        continue
                    # Decode from base64
                    raw_bytes = base64.b64decode(base64_content)
                    # Deserialize into Document objects
                    pages = [Document(**page) for page in json.loads(raw_bytes.decode(settings.encoding))]
                    # Extract page content
                    document_page = [page.page_content for page in pages if page.page_content.strip()] 

                    self.context.logger.debug(f"{output_messages.EMBEDDER_REQUEST_VECTORS_START}")
                    # generate the vectors for the extracted page content - reasoning heavy load
                    vectors = self.context.ollama.get_vectors(documents=document_page)
                    self.context.logger.debug(f"{output_messages.EMBEDDER_REQUEST_VECTORS_ENDED}")

                    # add metadata to the vectors
                    documents_with_metadata = []
                    for i, content in enumerate(document_page):
                        documents_with_metadata.append({
                            "vector": vectors[i],
                            "text": content,
                            "metadata": {
                                "source": filename,
                                "chunk_index": i
                            }
                        })

                    # extract vectors, texts, and metadata
                    vectors = [doc["vector"] for doc in documents_with_metadata]
                    texts = [doc["text"] for doc in documents_with_metadata]
                    metadata = [doc["metadata"] for doc in documents_with_metadata]

                    # add data to qdrant
                    #self.context.qdrant.add_to_qdrant(documents_with_metadata)
                    self.context.qdrant.add_to_qdrant(vectors, texts, metadata)
                except Exception as e:
                    self.context.logger.error(f"{output_messages.EMBEDDER_EXCEPTION}", error=str(e))
                    traceback.print_exc()

                await asyncio.sleep(embedder_settings.check_interval)

if __name__ == "__main__":
    async def main():
        service = EmbedderService()
        await service.initialize()
        await service.run()

    asyncio.run(main())
