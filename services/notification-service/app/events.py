import json
import logging
import threading
import time

import pika

from .config import settings
from .models import InvalidEventError

log = logging.getLogger("notification-service")
EXCHANGE = "shop.events"
QUEUE = "notification.events"
EVENT_TYPES = ("order.created", "payment.completed", "payment.failed")


def check_connection():
    connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
    try:
        connection.channel()
    finally:
        connection.close()


def start_consumer(handler):
    def run():
        while True:
            connection = None
            try:
                connection = pika.BlockingConnection(
                    pika.URLParameters(settings.rabbitmq_url)
                )
                channel = connection.channel()
                channel.exchange_declare(
                    EXCHANGE, exchange_type="topic", durable=True
                )
                channel.queue_declare(QUEUE, durable=True)
                for event_type in EVENT_TYPES:
                    channel.queue_bind(QUEUE, EXCHANGE, event_type)
                channel.basic_qos(prefetch_count=1)

                def on_message(ch, method, properties, body):
                    try:
                        payload = json.loads(body)
                        if not isinstance(payload, dict):
                            raise InvalidEventError("Event payload must be a JSON object")
                        handler(method.routing_key, payload)
                    except (json.JSONDecodeError, InvalidEventError) as error:
                        log.error(f"Invalid event rejected: {error!r}")
                        ch.basic_nack(method.delivery_tag, requeue=False)
                    except Exception:
                        log.exception("Event processing failed; message will be retried")
                        ch.basic_nack(method.delivery_tag, requeue=True)
                    else:
                        ch.basic_ack(method.delivery_tag)

                channel.basic_consume(QUEUE, on_message)
                log.info("RabbitMQ consumer started")
                channel.start_consuming()
            except Exception as error:
                log.warning(f"RabbitMQ unavailable, retry in 5s: {error!r}")
                time.sleep(5)
            finally:
                if connection is not None and connection.is_open:
                    connection.close()

    threading.Thread(target=run, daemon=True).start()
