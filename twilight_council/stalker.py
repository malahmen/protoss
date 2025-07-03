import asyncio
import base64
import traceback
from pylon import settings, output_messages, ProcessingError
from pylon.context import ApplicationContext
from twilight_council_settings import chunker_settings
import traceback
import json
from langchain_core.documents import Document
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
import uvicorn

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

    def process_documents_payload(self, payload: dict, raise_on_error: bool = False) -> Optional[Dict[str, Any]]:
        # reads decoded message
        filename = payload.get("filename")
        if not filename and raise_on_error:
            self.context.logger.error(f"{output_messages.CHUNKER_REQUIRED_FILENAME_KO}")
            raise ProcessingError(f"{output_messages.CHUNKER_REQUIRED_FILENAME_KO}")
        message_id = payload.get("id")
        if not message_id and raise_on_error:
            self.context.logger.error(f"{output_messages.CHUNKER_REQUIRED_MESSAGE_ID_KO}")
            raise ProcessingError(f"{output_messages.CHUNKER_REQUIRED_MESSAGE_ID_KO}")
        content_mime = payload.get(settings.redis_content_type)
        base64_content = payload.get(settings.redis_content_field)
        if not base64_content and raise_on_error:
            self.context.logger.error(f"{output_messages.CHUNKER_REQUIRED_CONTENT_KO}")
            raise ProcessingError(f"{output_messages.CHUNKER_REQUIRED_CONTENT_KO}")

        # decodes the documents
        try:
            decoded_json = base64.b64decode(base64_content).decode(settings.encoding)
            document_dicts = json.loads(decoded_json)
        except Exception as e:
            self.context.logger.error(f"{output_messages.CHUNKER_BASE64_KO}", error=str(e))
            if raise_on_error:
                raise ProcessingError(f"{output_messages.CHUNKER_BASE64_KO}")

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
        response_payload = self.context.redis.generate_message(
            id=message_id,
            encoded_content=encoded_content,
            filename=filename,
            content_field=None,
            content_type=None,
            content_mime=content_mime
        )

        return response_payload

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
                    
                payload = self.process_documents_payload(decoded_documents)

                # send pages to their redis queue
                await self.context.redis.send_message(payload, settings.redis_queue_pages)
                #await self.context.redis.send_it(queue=settings.redis_queue_pages, content=payload, message_id=self.context.redis.generate_message_id())

            except Exception as e:
                self.context.logger.error(f"{output_messages.CHUNKER_EXCEPTION}", error=str(e))
                traceback.print_exc()

            await asyncio.sleep(chunker_settings.check_interval)

chunker_api = FastAPI()
chunker_service = ChunkerService()

@chunker_api.post("/chop")
async def extract_payload(request: Request):
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{output_messages.CHUNKER_PAYLOAD_KO}: {str(e)}")

    try:
        response_payload = chunker_service.process_documents_payload(payload, True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{output_messages.CHUNKER_PAYLOAD_PROCESSING_KO}: {str(e)}")

    return response_payload

if __name__ == "__main__":
    async def main():
        await chunker_service.initialize()
        config = uvicorn.Config(chunker_api, host="0.0.0.0", port=8002, log_level="info")
        server = uvicorn.Server(config)

        await asyncio.gather(
            server.serve(),
            chunker_service.run()
        )

    asyncio.run(main())
