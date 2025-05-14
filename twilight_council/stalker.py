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
                    
                    # decode message
                    decoded_documents = self.context.redis.decode_message(document_message)
                    if not decoded_documents:
                        continue
                    
                    # decode documents
                    base64_content = decoded_documents.get(settings.redis_content_field)
                    decoded_json = base64.b64decode(base64_content).decode(settings.encoding)
                    document_dicts = json.loads(decoded_json)

                    documents = [
                        Document(**d) if isinstance(d, dict) else Document(page_content=str(d))
                        for d in document_dicts
                    ]

                    # split the data into chunks (documents into pages)
                    pages = self.context.ollama.split_into_chunks(documents=documents)
                    
                    # send pages to their redis queue
                    await self.context.redis.send_it(queue=settings.redis_queue_pages, content=pages, message_id=self.context.redis.generate_message_id())

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
