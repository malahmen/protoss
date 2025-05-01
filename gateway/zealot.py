import aiohttp
import asyncio
import base64
import json
import magic
import traceback
import structlog
import tempfile
import os
from pylon import settings, redis_gateway, track_processing_time, update_queue_size, record_error, ProcessingError, json_to_text, suppress_stderr
from gateway_settings import gateway_settings
from typing import Dict, Any
import traceback
from langchain_community.document_loaders import PDFPlumberLoader
from pathlib import Path


logger = structlog.get_logger()
mime = magic.Magic(mime=True)
timeout = aiohttp.ClientTimeout(total=90)  # 90 seconds
seen_files = set()

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
            # Clean up temp file
            os.unlink(temporary_file_path)
            #return text
            return documents
        except Exception as e:
            logger.error("[Zealot hit] pdf extraction failed ", error=str(e), filename=filename)
            raise ProcessingError(f"[Zealot hit] Failed to read PDF: {e}")
        finally:
            if temporary_file_path and os.path.exists(temporary_file_path):
                try:
                    os.unlink(temporary_file_path)
                except Exception as e:
                    logger.error("[Zealot hit] temporary file cleanup failed", error=str(e))

    elif ext in [".txt", ".md"]:
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            logger.error("[Zealot hit] Text decode failed", error=str(e), filename=filename)
            raise ProcessingError(f"[Zealot hit] Invalid text file encoding: {e}")

    elif ext == ".json":
        try:
            obj = json.loads(file_bytes.decode("utf-8"))
            return json_to_text(obj)
        except json.JSONDecodeError as e:
            logger.error("[Zealot hit] json decode failed", error=str(e), filename=filename)
            raise ProcessingError(f"[Zealot hit] Invalid JSON: {e}")
        except UnicodeDecodeError as e:
            logger.error("[Zealot hit] json decode failed", error=str(e), filename=filename)
            raise ProcessingError(f"[Zealot hit] Invalid file encoding: {e}")

    raise ProcessingError(f"[Zealot hit] Unsupported file type: {ext}")

def read_documents_from_message(message_id: str, filename: str, file_bytes: bytes, content_type: str) -> Dict[str, Any]:
    """Process a single file"""
    try:
        documents = extract_documents(file_bytes, filename)
        if not documents:
            record_error(error_type='[Zealot hit] Unreadable orders.')
            logger.error("[Zealot hit] Unreadable orders.", 
                    synapse_id=message_id,
                    filename=filename, 
                    error="No text content found in order ",
                    content_type=content_type)
            return None
        logger.info("[Zealot] Orders received.")
        return documents
    except Exception as e:
        record_error(error_type='[Zealot hit] Failed to process orders.')
        logger.error(f"[Zealot hit] Failed to process orders.", 
                    filename=filename, 
                    error=str(e),
                    content_type=content_type
                    )
        return None

async def send_documents(documents, message_id):
    encoded_content = base64.b64encode(documents).decode("utf-8")
    
    data = {
            'id': message_id,
            'content': encoded_content,
            'content_type': 'text/plain' # at this point it has to be text
    }

    await redis_gateway.send_message(data, settings.REDIS_QUEUE_DOCUMENTS)

async def look_for_file_messages():
    """Asynchronous documents ingestion."""
    logger.warn("[Zealot] Wating for orders.")
    while True:
            try:
                file_message = await redis_gateway.get_message(settings.REDIS_QUEUE_FILES)
                
                # decode message
                decoded_message = redis_gateway.decode_message(file_message)
                if not decoded_message:
                    continue
                
                # validate message
                required_fields = ["filename", "id", "content_type", "content"]
                valid = redis_gateway.is_valid_message(decoded_message, required_fields)
                if not valid:
                    continue
                
                # read decoded message - all fields have been checked
                filename = decoded_message.get("filename")
                message_id = decoded_message.get("id")
                content_type = decoded_message.get("content_type")
                base64_content = decoded_message.get("content")
                file_bytes = base64.b64decode(base64_content)
                
                # extract documents from message
                documents = read_documents_from_message(message_id, filename, file_bytes, content_type)
                if not documents:
                    continue

                # send documents to their redis queue
                send_documents(message_id, documents)

            except Exception as e:
                logger.error("[Zealot down] Exploded ", error=str(e))
                traceback.print_exc()

            await asyncio.sleep(gateway_settings.CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        logger.info("[Zealot] Ready to serve.")
        asyncio.run(look_for_file_messages())
    except KeyboardInterrupt:
        logger.info("[Zealot] Returning to base...")
    except Exception as e:
        logger.info("[Zealot] Destroyed.",
                    error=str(e),
                    traceback=traceback.format_exc())
        raise
