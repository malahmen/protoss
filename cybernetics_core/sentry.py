import aiohttp
import asyncio
import base64
import magic
import traceback
import os
import shutil
from pylon import settings, output_messages
from pylon.context import ApplicationContext
from cybernetic_core_settings import watcher_settings

class WatcherService:
    def __init__(self):
        self.context = None
        self.mime = magic.Magic(mime=True)
        self.timeout = aiohttp.ClientTimeout(total=settings.async_timeout) # 90 seconds
        self.seen_files = set()

    async def initialize(self):
        self.context = await ApplicationContext.create()
        self.context.logger.info(f"{output_messages.WATCHER_INITIALIZATION}")

    async def run(self):
        try:
            await self.look_for_files()
        except KeyboardInterrupt:
            self.context.logger.info(f"{output_messages.WATCHER_TERMINATED}")
        except Exception as e:
            self.context.logger.info(f"{output_messages.WATCHER_KO}",
                    error=str(e),
                    traceback=traceback.format_exc())
            raise

    def is_supported(self, filename):
        return any(filename.lower().endswith(ext) for ext in watcher_settings.supported_extensions)

    def get_current_files(self):
        if not os.path.exists(watcher_settings.watch_folder):
            raise RuntimeError(f"{output_messages.WATCHER_NO_FOLDER_KO}: {watcher_settings.watch_folder}")
        return {f for f in os.listdir(watcher_settings.watch_folder) if self.is_supported(f)}

    async def send_files(self, session, filepath):
        """Asynchronous file ingestion."""
        filename = os.path.basename(filepath)
        self.context.logger.debug(f"{output_messages.WATCHER_READ_FILE_START}", filename=filename)
        
        with open(filepath, 'rb') as f:
            file_content = f.read()
            content_mime = self.mime.from_buffer(file_content)
            encoded_content = base64.b64encode(file_content).decode(settings.encoding)

            payload = self.context.redis.generate_message(
                id=None,
                encoded_content=encoded_content,
                filename=filename,
                content_field=None,
                content_type=None,
                content_mime=content_mime
            )

            self.context.logger.debug(f"{output_messages.WATCHER_QUEUE_TARGET}", queue=settings.redis_queue_files)
            await self.context.redis.send_message(payload, settings.redis_queue_files)

            processed_dir = os.path.join(watcher_settings.watch_folder, watcher_settings.processed_folder.lstrip("/"))
            self.context.logger.debug(f"{output_messages.WATCHER_MOVE_FILE_START}", directory=processed_dir)
            
            os.makedirs(processed_dir, exist_ok=True)
            shutil.move(filepath, os.path.join(processed_dir, filename))

    async def look_for_files(self):
        await asyncio.sleep(10)
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    current_files = self.get_current_files()
                    new_files = current_files - self.seen_files
                    modified_files = current_files & self.seen_files

                    tasks = []
                    for filename in new_files | modified_files:
                        full_path = os.path.join(watcher_settings.watch_folder, filename)
                        tasks.append(self.send_files(session, full_path))

                    # Wait for all tasks to complete
                    if tasks:
                        await asyncio.gather(*tasks)

                    self.seen_files.update(current_files)
                except Exception as e:
                    self.context.logger.error(f"{output_messages.WATCHER_EXCEPTION}", error=str(e))
                    traceback.print_exc()

                await asyncio.sleep(watcher_settings.check_interval)

if __name__ == "__main__":
    async def main():
        service = WatcherService()
        await service.initialize()
        await service.run()

    asyncio.run(main())