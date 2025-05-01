import redis.asyncio as redis
import uuid
import json
import base64
import traceback
import structlog
import time
from typing import Optional, Dict, Any
from pylon import settings, track_processing_time, update_queue_size, record_error

# redis client code
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

    def decode_message(self, message):
        try:
            _, raw_data = message
            decoded_message = json.loads(raw_data)
            self.logger.info("[Colossus] Decoded message ", message=decoded_message)
            return decoded_message
        except json.JSONDecodeError as e:
            record_error(error_type='invalid_json')
            self.logger.error("[Colossus hit] Invalid json ", error=str(e))
            return None

    def is_valid_message(self, message: Dict[str, Any], required_fields: Dict[str, Any]) -> bool:
        """Validate message structure and content"""

        for field in required_fields:
            if field not in message:
                self.logger.error(f"[Colossus hit] Missing required field: {field} ")
                return False
            
        if not message["content"]:
            self.logger.error(f"[Colossus hit] Empty content field ")
            return False
        
        try:
            base64.b64decode(message["content"])
        except Exception as e:
            self.logger.error(f"[Colossus hit] Invalid base64 content: {str(e)}")
            return False

        return True

# costum error class
class ProcessingError(Exception):
    """Custom exception for processing errors"""
    pass

# error suppressing
@contextlib.contextmanager
def suppress_stderr():
    with open(os.devnull, "w") as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr

# convertion to JSON
def json_to_text(obj, indent=0):
    if isinstance(obj, dict):
        return "\n".join(f"{'  ' * indent}{k}: {json_to_text(v, indent + 1)}" for k, v in obj.items())
    elif isinstance(obj, list):
        return "\n".join(f"{'  ' * indent}- {json_to_text(item, indent + 1)}" for item in obj)
    else:
        return str(obj)