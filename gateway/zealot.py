import asyncio
import base64
import json
import traceback
import tempfile
import os
from pylon import settings, record_error, ProcessingError, json_to_text, output_messages
from pylon.context import ApplicationContext
from gateway_settings import extractor_settings
from typing import Dict, Any, Optional
from langchain_community.document_loaders import PDFPlumberLoader
from pathlib import Path
import warnings
import logging
from fastapi import FastAPI, HTTPException, Request
import uvicorn

class ExtractorService:
    def __init__(self):
        self.context = None
        logging.getLogger("pdfminer").setLevel(logging.ERROR)

    async def initialize(self):
        self.context = await ApplicationContext.create()
        self.context.logger.info(f"{output_messages.EXTRACTOR_INITIALIZATION}")

    async def run(self):
        try:
            await self.look_for_file_messages()
        except KeyboardInterrupt:
            self.context.logger.info(f"{output_messages.EXTRACTOR_TERMINATED}")
        except Exception as e:
            self.context.logger.info(f"{output_messages.EXTRACTOR_KO}", error=str(e), traceback=traceback.format_exc())

    def extract_documents(self, file_bytes: bytes, filename: str) -> Any:
        ext = Path(filename).suffix.lower()
        temporary_file_path = None

        if ext == ".pdf":
            try:
                # Write to temp file for PDFPlumberLoader
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temporary_file:
                    temporary_file.write(file_bytes)
                    temporary_file_path = temporary_file.name
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    loader = PDFPlumberLoader(temporary_file_path)
                    documents = loader.load()
                if temporary_file_path:
                    os.unlink(temporary_file_path)
                return documents
            except Exception as e:
                self.context.logger.error(f"{output_messages.EXTRACTOR_PDF_KO}", error=str(e), filename=filename)
                raise ProcessingError(f"{output_messages.EXTRACTOR_PDF_KO}: {e}")
            finally:
                if temporary_file_path and os.path.exists(temporary_file_path):
                    try:
                        os.unlink(temporary_file_path)
                    except Exception as e:
                        self.context.logger.error(f"{output_messages.EXTRACTOR_CLEANUP_KO}", error=str(e))

        elif ext in [".txt", ".md"]:
            try:
                return file_bytes.decode(settings.encoding)
            except UnicodeDecodeError as e:
                self.context.logger.error(f"{output_messages.EXTRACTOR_TEXT_KO}", error=str(e), filename=filename)
                raise ProcessingError(f"{output_messages.EXTRACTOR_TEXT_KO}: {e}")

        elif ext == ".json":
            try:
                obj = json.loads(file_bytes.decode(settings.encoding))
                return json_to_text(obj)
            except json.JSONDecodeError as e:
                self.context.logger.error(f"{output_messages.EXTRACTOR_JSON_KO}", error=str(e), filename=filename)
                raise ProcessingError(f"{output_messages.EXTRACTOR_JSON_KO_MSG}: {e}")
            except UnicodeDecodeError as e:
                self.context.logger.error(f"{output_messages.EXTRACTOR_JSON_KO}", error=str(e), filename=filename)
                raise ProcessingError(f"{output_messages.EXTRACTOR_JSON_DECODE_KO}: {e}")

        raise ProcessingError(f"{output_messages.EXTRACTOR_UNSUPPORTED_TYPE}: {ext}")

    def read_documents_from_message(self, message_id: str, filename: str, file_bytes: bytes, content_mime: str) -> Dict[str, Any]:
        """Process a single file"""
        try:
            documents = self.extract_documents(file_bytes, filename)
            if not documents:
                record_error(error_type=output_messages.EXTRACTOR_READ_KO)
                self.context.logger.error(f"{output_messages.EXTRACTOR_READ_KO}", 
                        synapse_id=message_id,
                        filename=filename, 
                        error=output_messages.EXTRACTOR_READ_KO_MSG,
                        content_type=content_mime)
                return None
            self.context.logger.debug(f"{output_messages.EXTRACTOR_READ_OK}")
            return documents
        except Exception as e:
            record_error(error_type=output_messages.EXTRACTOR_READ_EXCEPTION)
            self.context.logger.error(f"{output_messages.EXTRACTOR_READ_EXCEPTION}", 
                        filename=filename, 
                        error=str(e),
                        content_type=content_mime
                        )
            return None

    def process_file_payload(self, payload: dict, raise_on_error: bool = False) -> Optional[dict]:
        # validates message
        required_fields = ["filename", "id", settings.redis_content_field, settings.redis_content_type]
        valid = self.context.redis.is_valid_message(payload, required_fields)
        if not valid and raise_on_error:
            self.context.logger.error(f"{output_messages.EXTRACTOR_REQUIRED_FIELDS_KO}")
            raise ProcessingError(f"{output_messages.EXTRACTOR_REQUIRED_FIELDS_KO}")
                    
        # reads decoded message - all fields have been checked
        filename = payload.get("filename")
        message_id = payload.get("id")
        content_mime = payload.get(settings.redis_content_type)
        base64_content = payload.get(settings.redis_content_field)
        
        try:
            file_bytes = base64.b64decode(base64_content)
        except Exception as e:
            self.context.logger.error(f"{output_messages.EXTRACTOR_BASE64_KO}", error=str(e))
            if raise_on_error:
                raise ProcessingError(f"{output_messages.EXTRACTOR_BASE64_KO}")
                    
        # extracts documents from message
        documents = self.read_documents_from_message(message_id, filename, file_bytes, content_mime)
        if not documents and raise_on_error:
            self.context.logger.error(f"{output_messages.EXTRACTOR_DOCUMENT_KO}")
            raise ProcessingError(f"{output_messages.EXTRACTOR_DOCUMENT_KO}")

        serialized = json.dumps([
            d.dict() if hasattr(d, "dict") else str(d)
            for d in documents
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

    async def look_for_file_messages(self):
        """Asynchronous documents ingestion."""
        self.context.logger.debug(f"{output_messages.EXTRACTOR_WAIT_START}")
        while True:
            try:
                file_message = await self.context.redis.get_message(settings.redis_queue_files)
                if not file_message:
                    continue
                    
                # decodes the message
                decoded_message = self.context.redis.decode_message(file_message)
                if not decoded_message:
                    continue

                # process the decoded_message for documents
                try:
                    payload = self.process_file_payload(decoded_message)
                except Exception as e:
                    continue

                # sends documents to their redis queue
                await self.context.redis.send_message(payload, settings.redis_queue_documents)
                #await self.context.redis.send_it(queue=settings.redis_queue_documents, content=payload, message_id=message_id)

            except Exception as e:
                self.context.logger.error(f"{output_messages.EXTRACTOR_EXCEPTION}", error=str(e))
                traceback.print_exc()

            await asyncio.sleep(extractor_settings.check_interval)

extractor_api = FastAPI()
extractor_service = ExtractorService()

@extractor_api.post("/extract")
async def extract_payload(request: Request):
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{output_messages.EXTRACTOR_PAYLOAD_KO}: {str(e)}")

    try:
        response_payload = extractor_service.process_file_payload(payload, True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{output_messages.EXTRACTOR_PAYLOAD_PROCESSING_KO}: {str(e)}")

    return response_payload

if __name__ == "__main__":
    async def main():
        await extractor_service.initialize()
        config = uvicorn.Config(extractor_api, host="0.0.0.0", port=8002, log_level="info")
        server = uvicorn.Server(config)

        await asyncio.gather(
            server.serve(),
            extractor_service.run()
        )

    asyncio.run(main())
