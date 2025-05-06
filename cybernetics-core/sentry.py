import aiohttp
import asyncio
import base64
import magic
import traceback
import structlog
import os
from pylon import settings, RedisGateway, output_messages
from cybernetic_core_settings import watcher_settings

logger = structlog.get_logger()
mime = magic.Magic(mime=True)
timeout = aiohttp.ClientTimeout(total=settings.ASYNC_TIMEOUT) # 90 seconds
seen_files = set()
redis_gateway = RedisGateway()

def is_supported(filename):
    return any(filename.lower().endswith(ext) for ext in watcher_settings.supported_extensions)

def get_current_files():
    return {f for f in os.listdir(watcher_settings.WATCH_FOLDER) if is_supported(f)}

async def send_files(session, filepath):
    """Asynchronous file ingestion."""
    filename = os.path.basename(filepath)
    logger.warn(f"{output_messages.WATCHER_READ_FILE_START}", filename=filename)
    
    with open(filepath, 'rb') as f:
        file_content = f.read()
        content_mipe = mime.from_buffer(file_content)
        encoded_content = base64.b64encode(file_content).decode(settings.ENCODING)

        payload = redis_gateway.generate_message(encoded_content=encoded_content,filename=filename, content_mime=content_mipe)
        await redis_gateway.send_message(payload, settings.REDIS_QUEUE_FILES)

        processed_dir = os.path.join(watcher_settings.WATCH_FOLDER, watcher_settings.PROCESSED_FOLDER)
        logger.warn(f"{output_messages.WATCHER_MOVE_FILE_START}", directory=processed_dir)
        
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
                    full_path = os.path.join(watcher_settings.WATCH_FOLDER, filename)
                    tasks.append(send_files(session, full_path))

                # Wait for all tasks to complete
                if tasks:
                    await asyncio.gather(*tasks)

                seen_files.update(current_files)
            except Exception as e:
                logger.error(f"{output_messages.WATCHER_EXCEPTION}", error=str(e))
                traceback.print_exc()

            await asyncio.sleep(watcher_settings.CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        logger.info(f"{output_messages.WATCHER_INITIALIZATION}")
        asyncio.run(look_for_files())
    except KeyboardInterrupt:
        logger.info(f"{output_messages.WATCHER_TERMINATED}")
    except Exception as e:
        logger.info(f"{output_messages.WATCHER_KO}",
                    error=str(e),
                    traceback=traceback.format_exc())
        raise