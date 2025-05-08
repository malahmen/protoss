import aiohttp
import asyncio
import base64
import json
import magic
import traceback
import structlog
import tempfile
import os
from pylon import settings, RedisGateway, record_error, ProcessingError, json_to_text, suppress_stderr, output_messages
from gateway_settings import extractor_settings
from typing import Dict, Any
import traceback
from langchain_community.document_loaders import PDFPlumberLoader
from pathlib import Path


logger = structlog.get_logger()
mime = magic.Magic(mime=True)
timeout = aiohttp.ClientTimeout(total=settings.async_timeout)
seen_files = set()
redis_gateway = RedisGateway()

def extract_documents(file_bytes: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        try:
            # Write to temp file for PDFPlumberLoader
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temporary_file:
                temporary_file.write(file_bytes)
                temporary_file_path = temporary_file.name
            with suppress_stderr():
                loader = PDFPlumberLoader(temporary_file_path)
                documents = loader.load()
            os.unlink(temporary_file_path)
            return documents
        except Exception as e:
            logger.error(f"{output_messages.EXTRACTOR_PDF_KO}", error=str(e), filename=filename)
            raise ProcessingError(f"{output_messages.EXTRACTOR_PDF_KO}: {e}")
        finally:
            if temporary_file_path and os.path.exists(temporary_file_path):
                try:
                    os.unlink(temporary_file_path)
                except Exception as e:
                    logger.error(f"{output_messages.EXTRACTOR_CLEANUP_KO}", error=str(e))

    elif ext in [".txt", ".md"]:
        try:
            return file_bytes.decode(settings.encoding)
        except UnicodeDecodeError as e:
            logger.error(f"{output_messages.EXTRACTOR_TEXT_KO}", error=str(e), filename=filename)
            raise ProcessingError(f"{output_messages.EXTRACTOR_TEXT_KO}: {e}")

    elif ext == ".json":
        try:
            obj = json.loads(file_bytes.decode(settings.encoding))
            return json_to_text(obj)
        except json.JSONDecodeError as e:
            logger.error(f"{output_messages.EXTRACTOR_JSON_KO}", error=str(e), filename=filename)
            raise ProcessingError(f"{output_messages.EXTRACTOR_JSON_KO_MSG}: {e}")
        except UnicodeDecodeError as e:
            logger.error(f"{output_messages.EXTRACTOR_JSON_KO}", error=str(e), filename=filename)
            raise ProcessingError(f"{output_messages.EXTRACTOR_JSON_DECODE_KO}: {e}")

    raise ProcessingError(f"{output_messages.EXTRACTOR_UNSUPPORTED_TYPE}: {ext}")

def read_documents_from_message(message_id: str, filename: str, file_bytes: bytes, content_mime: str) -> Dict[str, Any]:
    """Process a single file"""
    try:
        documents = extract_documents(file_bytes, filename)
        if not documents:
            record_error(error_type=output_messages.EXTRACTOR_READ_KO)
            logger.error(f"{output_messages.EXTRACTOR_READ_KO}", 
                    synapse_id=message_id,
                    filename=filename, 
                    error=output_messages.EXTRACTOR_READ_KO_MSG,
                    content_type=content_mime)
            return None
        logger.info(f"{output_messages.EXTRACTOR_READ_OK}")
        return documents
    except Exception as e:
        record_error(error_type=output_messages.EXTRACTOR_READ_EXCEPTION)
        logger.error(f"{output_messages.EXTRACTOR_READ_EXCEPTION}", 
                    filename=filename, 
                    error=str(e),
                    content_type=content_mime
                    )
        return None

async def look_for_file_messages():
    """Asynchronous documents ingestion."""
    logger.warn(f"{output_messages.EXTRACTOR_WAIT_START}")
    while True:
            try:
                file_message = await redis_gateway.get_message(settings.redis_queue_files)
                if not file_message:
                    continue
                
                # decode message
                decoded_message = redis_gateway.decode_message(file_message)
                if not decoded_message:
                    continue
                
                # validate message
                required_fields = ["filename", "id", settings.redis_content_field, settings.redis_content_type]
                valid = redis_gateway.is_valid_message(decoded_message, required_fields)
                if not valid:
                    continue
                
                # read decoded message - all fields have been checked
                filename = decoded_message.get("filename")
                message_id = decoded_message.get("id")
                content_mime = decoded_message.get(settings.redis_content_type)
                base64_content = decoded_message.get(settings.redis_content_field)
                file_bytes = base64.b64decode(base64_content)
                
                # extract documents from message
                documents = read_documents_from_message(message_id, filename, file_bytes, content_mime)
                if not documents:
                    continue

                # send documents to their redis queue
                await redis_gateway.send_it(queue=settings.redis_queue_documents, content=documents, message_id=message_id)

            except Exception as e:
                logger.error(f"{output_messages.EXTRACTOR_EXCEPTION}", error=str(e))
                traceback.print_exc()

            await asyncio.sleep(extractor_settings.check_interval)

if __name__ == "__main__":
    try:
        logger.info(f"{output_messages.EXTRACTOR_INITIALIZATION}")
        asyncio.run(look_for_file_messages())
    except KeyboardInterrupt:
        logger.info(f"{output_messages.EXTRACTOR_TERMINATED}")
    except Exception as e:
        logger.info(f"{output_messages.EXTRACTOR_KO}",
                    error=str(e),
                    traceback=traceback.format_exc())
        raise
