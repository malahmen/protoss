import asyncio
import base64
import traceback
from pylon import settings, output_messages
from pylon.context import ApplicationContext
from twilight_council_settings import chunker_settings
import traceback
import json
from langchain_core.documents import Document

class ChunkerService:
    def __init__(self):
        self.context = None

    async def initialize(self):
        self.context = await ApplicationContext.create()
        self.context.logger.info(f"{output_messages.CHUNKER_INITIALIZATION}")

    async def run(self):
        try:
            await self.look_for_document_messages()
        except KeyboardInterrupt:
            self.context.logger.info(f"{output_messages.CHUNKER_TERMINATED}")
        except Exception as e:
            self.context.logger.info(f"{output_messages.CHUNKER_KO}",
                        error=str(e),
                        traceback=traceback.format_exc())
            raise

    async def look_for_document_messages(self):
        """Asynchronous pages ingestion."""
        self.context.logger.debug(f"{output_messages.CHUNKER_WAIT_START}")
        while True:
                try:
                    document_message = await self.context.redis.get_message(settings.redis_queue_documents)
                    if not document_message:
                        continue
                    
                    # decodes the message
                    decoded_documents = self.context.redis.decode_message(document_message)
                    if not decoded_documents:
                        continue
                    
                    # reads decoded message
                    filename = decoded_documents.get("filename")
                    message_id = decoded_documents.get("id")
                    content_mime = decoded_documents.get(settings.redis_content_type)
                    base64_content = decoded_documents.get(settings.redis_content_field)

                    # decodes the documents
                    base64_content = decoded_documents.get(settings.redis_content_field)
                    decoded_json = base64.b64decode(base64_content).decode(settings.encoding)
                    document_dicts = json.loads(decoded_json)

                    documents = [
                        Document(**d) if isinstance(d, dict) else Document(page_content=str(d))
                        for d in document_dicts
                    ]

                    # split the data into chunks (documents into pages)
                    # until here no reasoning has been called or llm engine
                    pages = self.context.ollama.split_into_chunks(documents=documents)

                    # Serialize pages and encode as base64
                    serialized = json.dumps([
                        p.dict() if hasattr(p, "dict") else str(p)
                        for p in pages
                    ])
                    encoded_content = base64.b64encode(serialized.encode(settings.encoding)).decode(settings.encoding)

                    
                    # sets the payload with informatio for metadata
                    payload = self.context.redis.generate_message(
                        id=message_id,
                        encoded_content=encoded_content,
                        filename=filename,
                        content_field=None,
                        content_type=None,
                        content_mime=content_mime
                    )

                    # send pages to their redis queue
                    await self.context.redis.send_message(payload, settings.redis_queue_pages)
                    #await self.context.redis.send_it(queue=settings.redis_queue_pages, content=payload, message_id=self.context.redis.generate_message_id())

                except Exception as e:
                    self.context.logger.error(f"{output_messages.CHUNKER_EXCEPTION}", error=str(e))
                    traceback.print_exc()

                await asyncio.sleep(chunker_settings.check_interval)

if __name__ == "__main__":
    async def main():
        service = ChunkerService()
        await service.initialize()
        await service.run()

    asyncio.run(main())
