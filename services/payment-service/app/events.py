import json
import logging
import threading
import time

import pika

from .config import settings

log = logging.getLogger("payment-service")
EXCHANGE = "shop.events"
QUEUE = "payment.order-events"


def publish(routing_key: str, payload: dict):
    conn = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
    try:
        ch = conn.channel()
        ch.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
        ch.basic_publish(EXCHANGE, routing_key, json.dumps(payload).encode(),
                         pika.BasicProperties(delivery_mode=2,
                                              content_type="application/json"))
    finally:
        conn.close()


def check_connection():
    conn = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
    try:
        conn.channel()
    finally:
        conn.close()


def start_consumer(handler):
    def run():
        while True:
            try:
                conn = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
                ch = conn.channel()
                ch.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
                ch.queue_declare(QUEUE, durable=True)
                ch.queue_bind(QUEUE, EXCHANGE, "order.created")

                def on_message(channel, method, props, body):
                    try:
                        handler(json.loads(body))
                        channel.basic_ack(method.delivery_tag)
                    except Exception as e:
                        log.error(f"Event handling failed: {e!r}")
                        channel.basic_nack(method.delivery_tag, requeue=False)

                ch.basic_consume(QUEUE, on_message)
                log.info("Consumer started")
                ch.start_consuming()
            except Exception as e:
                log.warning(f"RabbitMQ unavailable, retry in 5s: {e!r}")
                time.sleep(5)

    threading.Thread(target=run, daemon=True).start()