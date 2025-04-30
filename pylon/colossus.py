# redis client code
import redis.asyncio as redis
import uuid
import json
import traceback
import structlog
import time
from pylon import settings, track_processing_time, update_queue_size, record_error

class redis_gateway():
    logger = structlog.get_logger()


    async def get_redis_connection():
        return await redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            socket_timeout=settings.REDIS_TIMEOUT,
            socket_connect_timeout=settings.REDIS_TIMEOUT,
            retry_on_timeout=True,
            health_check_interval=30
        )

    def generate_message_id():
        return str(uuid.uuid4())

    async def send_message(self, data, queue):
        try:
            if not queue:
                queue = settings.REDIS_QUEUE
            redis = await self.get_redis_connection()

            await redis.rpush(queue, json.dumps(data))
            self.logger.info("[Colossus] Message fired with key ", synapse_id=data['id'])
            await redis.aclose()
        except Exception as e:
            self.logger.error("[Colossus down] Failed to fire message ", error=str(e))
            traceback.print_exc()
            
    def get_message(self, queue):
        try:
            if not queue:
                queue = settings.REDIS_QUEUE
            redis = self.get_redis_connection()

            message = redis.blpop(queue, timeout=settings.REDIS_TIMEOUT)

            if not message or not isinstance(message, tuple):
                self.logger.error("[Colossus down] Failed to get message")
        except (redis.exceptions.ConnectionError) as e:
            record_error(error_type='redis')
            self.logger.error("[Colossus down] Message blocked, no connection ", error=str(e))
            time.sleep(settings.RETRY_DELAY)
        except (redis.exceptions.TimeoutError) as e:
            self.logger.info("[Colossus] No messages, survailing...")
            time.sleep(settings.RETRY_DELAY)

        except Exception as e:
            record_error(error_type='unexpected')
            self.logger.error("[Colossus down] Just exploded ", 
                        error=str(e),
                        traceback=traceback.format_exc())
            time.sleep(settings.RETRY_DELAY)
            
    def get_queue_size(self, queue):
        if not queue:
            queue = settings.REDIS_QUEUE
        redis = self.get_redis_connection()
        return redis.llen(queue)
