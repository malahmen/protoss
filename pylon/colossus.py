import redis
import redis.asyncio as redis_async
import uuid
import json
import base64
import traceback
import structlog
import time
from typing import Dict, Any
from pylon import settings, record_error, output_messages

# redis client code
class RedisGateway():

    def __init__(self, connection):
        self._logger = structlog.get_logger()
        self._connection = connection

    @classmethod
    async def create(cls):
        connection = await redis_async.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            socket_timeout=settings.redis_timeout,
            socket_connect_timeout=settings.redis_timeout,
            retry_on_timeout=bool(settings.redis_retry),
            health_check_interval=settings.redis_health_check_interval
        )
        return cls(connection)

    async def get_redis_connection(self):
        return self._connection

    async def send_it(self, queue, content, message_id):
        if content:
            if isinstance(content, list):
                content = json.dumps([doc.dict() if hasattr(doc, "dict") else str(doc) for doc in content])
                self._logger.debug(f"{output_messages.REDIS_CONTENT_TO_DOCUMENT_OK}")
            encoded_content = base64.b64encode(content.encode(settings.encoding)).decode(settings.encoding)
            payload = self.generate_message(
                id=message_id,
                encoded_content=encoded_content,
                filename=None,
                content_field=None,
                content_type=None,
                content_mime=None
            )
            await self.send_message(payload, queue)

    def generate_message_id(self):
        return str(uuid.uuid4())

    async def send_message(self, data, queue):
        try:
            if not queue:
                queue = settings.redis_queue
            redis = self._connection

            result = await redis.rpush(queue, json.dumps(data))
            if not result or result == 0:
                self._logger.error(output_messages.REDIS_MESSAGE_OUT_KO, result=result)
            else:     
                self._logger.debug(output_messages.REDIS_MESSAGE_OUT_OK, message_id=data['id'], queue=queue, result=result)
            await redis.aclose()
        except Exception as e:
            self._logger.error(output_messages.REDIS_MESSAGE_OUT_KO, error=str(e))
            traceback.print_exc()
            
    async def get_message(self, queue):
        try:
            if not queue:
                queue = settings.redis_queue
            redis_connection = await self._connection

            message = await redis_connection.blpop(queue, timeout=settings.redis_timeout)

            if not message:
                self._logger.debug(output_messages.REDIS_NO_MESSAGES)
                return None

            if message and not isinstance(message, tuple):
                self._logger.error(output_messages.REDIS_FAILED_TO_READ, message=message)
                return None

            return message
        except (redis.exceptions.ConnectionError) as e:
            record_error(error_type='redis')
            self._logger.error(output_messages.REDIS_FAILED_TO_CONNECT, error=str(e))
            time.sleep(settings.redis_retry_delay)
        except (redis.exceptions.TimeoutError) as e:
            self._logger.debug(output_messages.REDIS_NO_MESSAGES)
            time.sleep(settings.redis_retry_delay)

        except Exception as e:
            record_error(error_type='unexpected')
            self._logger.error(output_messages.REDIS_EXCEPTION, 
                        error=str(e),
                        traceback=traceback.format_exc())
            time.sleep(settings.redis_retry_delay)

    def get_queue_size(self, queue):
        if not queue:
            queue = settings.redis_queue
        redis = self._connection
        return redis.llen(queue)

    def decode_message(self, message):
        try:
            _, raw_data = message
            decoded_message = json.loads(raw_data)
            self._logger.debug(output_messages.REDIS_DECODED_OK)
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
            
        if not message[settings.redis_content_field]:
            self._logger.error(f"{output_messages.REDIS_MSG_CONTENT_EMPTY}")
            return False
        
        try:
            base64.b64decode(message[settings.redis_content_field])
        except Exception as e:
            self._logger.error(f"{output_messages.REDIS_MSG_FORMAT_KO}: {str(e)}")
            return False

        return True

    def generate_message(self, id, encoded_content, filename, content_field, content_type, content_mime):
        if not encoded_content:
            self._logger.error("[Colossus hit] No payload, skipping package ", filename=filename)
            return None

        message_id = id or self.generate_message_id()
        content_field = content_field or settings.redis_content_field
        content_type = content_type or settings.redis_content_type
        content_mime = content_mime or settings.redis_content_mime

        data = {
            'id': message_id,
            content_field: encoded_content,
            content_type: content_mime
        }

        if filename:
            data['filename'] = filename
        
        return data