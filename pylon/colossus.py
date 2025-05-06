import redis.asyncio as redis
import uuid
import json
import base64
import traceback
import structlog
import time
from typing import Optional, Dict, Any
from pylon import settings, track_processing_time, update_queue_size, record_error, output_messages

# redis client code
class RedisGateway():

    def __init__(self):
        self._logger = structlog.get_logger()

    async def get_redis_connection():
        return await redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            socket_timeout=settings.REDIS_TIMEOUT,
            socket_connect_timeout=settings.REDIS_TIMEOUT,
            retry_on_timeout=bool(settings.REDIS_RETRY),
            health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL
        )

    async def send_it(self, queue, content, message_id):
        if content:
            encoded_content = base64.b64encode(content).decode(settings.ENCODING)
            payload=self.generate_message(id=message_id, encoded_content=encoded_content)
            await self.send_message(payload, queue)

    def generate_message_id():
        return str(uuid.uuid4())

    async def send_message(self, data, queue):
        try:
            if not queue:
                queue = settings.REDIS_QUEUE
            redis = await self.get_redis_connection()

            await redis.rpush(queue, json.dumps(data))
            self._logger.info(output_messages.REDIS_MESSAGE_OUT_OK, message_id=data['id'])
            await redis.aclose()
        except Exception as e:
            self._logger.error(output_messages.REDIS_MESSAGE_OUT_KO, error=str(e))
            traceback.print_exc()
            
    def get_message(self, queue):
        try:
            if not queue:
                queue = settings.REDIS_QUEUE
            redis = self.get_redis_connection()

            message = redis.blpop(queue, timeout=settings.REDIS_TIMEOUT)

            if not message or not isinstance(message, tuple):
                self._logger.error(output_messages.REDIS_FAILED_TO_READ)
        except (redis.exceptions.ConnectionError) as e:
            record_error(error_type='redis')
            self._logger.error(output_messages.REDIS_FAILED_TO_CONNECT, error=str(e))
            time.sleep(settings.RETRY_DELAY)
        except (redis.exceptions.TimeoutError) as e:
            self._logger.info(output_messages.REDIS_NO_MESSAGES)
            time.sleep(settings.RETRY_DELAY)

        except Exception as e:
            record_error(error_type='unexpected')
            self._logger.error(output_messages.REDIS_EXCEPTION, 
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
            self._logger.info(output_messages.REDIS_DECODED_OK, message=decoded_message)
            return decoded_message
        except json.JSONDecodeError as e:
            record_error(error_type='invalid_json')
            self._logger.error(output_messages.REDIS_DECODED_KO, error=str(e))
            return None

    def is_valid_message(self, message: Dict[str, Any], required_fields: Dict[str, Any]) -> bool:
        """Validate message structure and content"""

        for field in required_fields:
            if field not in message:
                self._logger.error(f"{output_messages.REDIS_MSG_FIELD_KO}: {field} ")
                return False
            
        if not message["content"]:
            self._logger.error(f"{output_messages.REDIS_MSG_CONTENT_EMPTY}")
            return False
        
        try:
            base64.b64decode(message["content"])
        except Exception as e:
            self._logger.error(f"{output_messages.REDIS_MSG_FORMAT_KO}: {str(e)}")
            return False

        return True

    def generate_message(self, id, encoded_content, filename, content_field, content_type, content_mime):
        if not encoded_content:
            return None

        message_id = id or self.generate_message_id()
        content_field = content_field or settings.REDIS_CONTENT_FIELD
        content_type = content_type or settings.REDIS_CONTENT_TYPE
        content_mime = content_mime or settings.REDIS_CONTENT_MIME

        data = {
            'id': message_id,
            content_field: encoded_content,
            content_type: content_mime
        }

        if filename:
            data['filename'] = filename
        
        return data