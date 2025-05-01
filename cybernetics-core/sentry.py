import aiohttp
import asyncio
import base64
import magic
import traceback
import structlog
import os
from pylon import settings, redis_gateway
from cybernetic_core_settings import cybernetic_core_settings

logger = structlog.get_logger()
mime = magic.Magic(mime=True)
timeout = aiohttp.ClientTimeout(total=90)  # 90 seconds
seen_files = set()

def is_supported(filename):
    return any(filename.lower().endswith(ext) for ext in cybernetic_core_settings.supported_extensions)

def get_current_files():
    return {f for f in os.listdir(cybernetic_core_settings.WATCH_FOLDER) if is_supported(f)}

async def send_files(session, filepath):
    """Asynchronous file ingestion."""
    filename = os.path.basename(filepath)
    logger.warn("[Sentry] Reading file", filename=filename)
    with open(filepath, 'rb') as f:
        file_content = f.read()
        content_type = mime.from_buffer(file_content)
        encoded_content = base64.b64encode(file_content).decode("utf-8")

        data = {
            'id': redis_gateway.generate_message_id(),
            'filename': filename,
            'content': encoded_content,
            'content_type': content_type
        }

        await redis_gateway.send_message(data, settings.REDIS_QUEUE_FILES)

        processed_dir = os.path.join(cybernetic_core_settings.WATCH_FOLDER, cybernetic_core_settings.PROCESSED_FOLDER)
        logger.warn("[Sentry] Sending processed file into directory", directory=processed_dir)
        os.makedirs(processed_dir, exist_ok=True)
        os.rename(filepath, os.path.join(processed_dir, filename))

async def look_for_files():
    await asyncio.sleep(10)
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                current_files = get_current_files()
                new_files = current_files - seen_files
                modified_files = current_files & seen_files

                tasks = []
                for filename in new_files | modified_files:
                    full_path = os.path.join(cybernetic_core_settings.WATCH_FOLDER, filename)
                    tasks.append(send_files(session, full_path))

                # Wait for all tasks to complete
                if tasks:
                    await asyncio.gather(*tasks)

                seen_files.update(current_files)
            except Exception as e:
                logger.error("[Sentry down] Broken loop ", error=str(e))
                traceback.print_exc()

            await asyncio.sleep(cybernetic_core_settings.CHECK_INTERVAL)

if __name__ == "__main__":
    logger.info("[Sentry] Patrolling for new files...")
    asyncio.run(look_for_files())