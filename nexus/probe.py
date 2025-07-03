import asyncio
import base64
import json
import traceback
import os
from pylon import settings, output_messages, ProcessingError
from pylon.context import ApplicationContext
from nexus_settings import embedder_settings
from langchain_core.documents import Document
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
import uvicorn

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

    def process_pages_payload(self, payload: dict, raise_on_error: bool = False) -> Optional[Dict[str, Any]]:
        # reads decoded message
        filename = payload.get("filename")
        if not filename and raise_on_error:
            self.context.logger.error(f"{output_messages.EMBEDDER_REQUIRED_FILENAME_KO}")
            raise ProcessingError(f"{output_messages.EMBEDDER_REQUIRED_FILENAME_KO}")
        
        message_id = payload.get("id")
        if not message_id and raise_on_error:
            self.context.logger.error(f"{output_messages.EMBEDDER_REQUIRED_MESSAGE_ID_KO}")
            raise ProcessingError(f"{output_messages.EMBEDDER_REQUIRED_MESSAGE_ID_KO}")
                    
        content_mime = payload.get(settings.redis_content_type)
        self.context.logger.debug(f"{message_id} - {filename} - {content_mime}")

        # decode documents
        base64_content = payload.get(settings.redis_content_field)
        if not base64_content and raise_on_error:
            self.context.logger.error(f"{output_messages.EMBEDDER_REQUIRED_CONTENT_KO}")
            raise ProcessingError(f"{output_messages.EMBEDDER_REQUIRED_CONTENT_KO}")
                    
        # Decode from base64
        try:
            raw_bytes = base64.b64decode(base64_content)
        except Exception as e:
            self.context.logger.error(f"{output_messages.EMBEDDER_BASE64_KO}", error=str(e))
            if raise_on_error:
                raise ProcessingError(f"{output_messages.EMBEDDER_BASE64_KO}", error=str(e))
        
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

        # After successful insertion into Qdrant, set the file status
        try:
            status_folder = embedder_settings.processed_folder
            os.makedirs(status_folder, exist_ok=True)
            status_file = os.path.join(status_folder, f"{filename}.status")
            with open(status_file, "w") as f:
                f.write("processed")
            self.context.logger.info(f"{output_messages.EMBEDDER_STATUS_WOK}: {status_file}")
            self.context.logger.info(f"{output_messages.EMBEDDER_OK}")
        except Exception as e:
            self.context.logger.error(f"{output_messages.EMBEDDER_STATUS_WKO}", error=str(e))

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
                        self.context.logger.debug(f"{output_messages.EMBEDDER_NO_MESSAGES_DECODED}")
                        continue
                    
                    try:
                        self.process_pages_payload(decoded_pages)
                    except Exception as e:
                         # don't care about errors in this flow
                         # they are logged, proceed to next one
                        continue

                except Exception as e:
                    self.context.logger.error(f"{output_messages.EMBEDDER_EXCEPTION}", error=str(e))
                    traceback.print_exc()

                await asyncio.sleep(embedder_settings.check_interval)

embedder_api = FastAPI()
embedder_service = EmbedderService()

@embedder_api.post("/embed")
async def extract_payload(request: Request):
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{output_messages.EMBEDDER_PAYLOAD_KO}: {str(e)}")

    try:
        embedder_service.process_pages_payload(payload, True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{output_messages.EMBEDDER_PAYLOAD_PROCESSING_KO}: {str(e)}")

    return {
        "status": "ok",
        "filename": payload.get("filename"),
        "id": payload.get("id"),
        "message": f"{output_messages.EMBEDDER_OK}"
    }

if __name__ == "__main__":
    async def main():
        await embedder_service.initialize()
        config = uvicorn.Config(embedder_api, host="0.0.0.0", port=8003, log_level="info")
        server = uvicorn.Server(config)

        await asyncio.gather(
            server.serve(),
            embedder_service.run()
        )

    asyncio.run(main())
