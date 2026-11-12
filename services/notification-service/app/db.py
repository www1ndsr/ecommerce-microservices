from pymongo import ASCENDING, DESCENDING, MongoClient

from .config import settings

client = MongoClient(
    settings.mongodb_url,
    serverSelectionTimeoutMS=settings.mongo_timeout_ms,
    tz_aware=True,
)
database = client[settings.mongodb_database]
notifications = database["notifications"]
processed_events = database["processed_events"]


def initialize():
    database.command("ping")
    notifications.create_index([("event_key", ASCENDING)], unique=True)
    notifications.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    notifications.create_index([
        ("user_id", ASCENDING),
        ("is_read", ASCENDING),
        ("created_at", DESCENDING),
    ])


def check_connection():
    database.command("ping")


def close():
    client.close()
