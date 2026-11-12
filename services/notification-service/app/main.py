import time
from contextlib import asynccontextmanager

import pika
from bson import ObjectId
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError

from . import db, events, models, schemas
from .common import request_id_var, setup


@asynccontextmanager
async def lifespan(app):
    for _ in range(20):
        try:
            db.initialize()
            break
        except PyMongoError as error:
            log.warning(f"MongoDB not ready, retrying: {error!r}")
            time.sleep(2)
    else:
        raise RuntimeError("MongoDB unavailable during startup")

    events.start_consumer(handle_event)
    yield
    db.close()


app = FastAPI(title="Notification Service", lifespan=lifespan)
log = setup(app, "notification-service")


@app.exception_handler(PyMongoError)
async def mongo_error(request, exc):
    log.error(f"MongoDB error: {exc!r}")
    return JSONResponse(
        {"error": "Notification storage unavailable",
         "request_id": request_id_var.get()},
        status_code=503,
    )


def handle_event(event_type: str, payload: dict):
    request_id_var.set(payload.get("request_id", "-"))
    notification = models.from_event(event_type, payload)
    event_key = notification["event_key"]
    ledger_entry = db.processed_events.find_one_and_update(
        {"_id": event_key},
        {"$setOnInsert": {"status": "pending"}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    if ledger_entry is None:
        raise RuntimeError(f"Could not create event ledger entry for {event_key}")
    if ledger_entry["status"] == "processed":
        log.info(f"Duplicate event {event_key}, skipped")
        return

    db.notifications.update_one(
        {"event_key": event_key},
        {"$setOnInsert": notification},
        upsert=True,
    )
    db.processed_events.update_one(
        {"_id": event_key},
        {"$set": {"status": "processed"}},
    )
    log.info(
        f"Notification created for user {notification['user_id']} "
        f"from {event_type}"
    )


def current_user_id(x_user_id: str = Header(default="")) -> int:
    if not x_user_id.isdigit() or int(x_user_id) < 1:
        raise HTTPException(401, "Authentication required")
    return int(x_user_id)


def to_response(document: dict) -> schemas.NotificationOut:
    return schemas.NotificationOut(
        id=str(document["_id"]),
        user_id=document["user_id"],
        order_id=document["order_id"],
        event_type=document["event_type"],
        title=document["title"],
        text=document["text"],
        created_at=document["created_at"],
        is_read=document["is_read"],
    )


def list_notifications(user_id: int, unread_only: bool, limit: int, skip: int):
    query = {"user_id": user_id}
    if unread_only:
        query["is_read"] = False
    documents = (
        db.notifications.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    return [to_response(document) for document in documents]


@app.get("/api/notifications", response_model=list[schemas.NotificationOut])
def get_notifications(
    user_id: int = Depends(current_user_id),
    limit: int = Query(default=50, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
):
    return list_notifications(user_id, unread_only=False, limit=limit, skip=skip)


@app.get("/api/notifications/unread", response_model=list[schemas.NotificationOut])
def get_unread_notifications(
    user_id: int = Depends(current_user_id),
    limit: int = Query(default=50, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
):
    return list_notifications(user_id, unread_only=True, limit=limit, skip=skip)


@app.patch(
    "/api/notifications/{notification_id}/read",
    response_model=schemas.NotificationOut,
)
def mark_as_read(
    notification_id: str,
    user_id: int = Depends(current_user_id),
):
    if not ObjectId.is_valid(notification_id):
        raise HTTPException(404, "Notification not found")

    document = db.notifications.find_one_and_update(
        {"_id": ObjectId(notification_id), "user_id": user_id},
        {"$set": {"is_read": True}},
        return_document=ReturnDocument.AFTER,
    )
    if document is None:
        raise HTTPException(404, "Notification not found")
    return to_response(document)


@app.delete("/api/notifications/{notification_id}", status_code=204)
def delete_notification(
    notification_id: str,
    user_id: int = Depends(current_user_id),
):
    if not ObjectId.is_valid(notification_id):
        raise HTTPException(404, "Notification not found")

    result = db.notifications.delete_one({
        "_id": ObjectId(notification_id),
        "user_id": user_id,
    })
    if result.deleted_count == 0:
        raise HTTPException(404, "Notification not found")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    try:
        db.check_connection()
        events.check_connection()
    except (PyMongoError, pika.exceptions.AMQPError, OSError) as error:
        log.warning(f"Dependency unavailable: {error!r}")
        raise HTTPException(503, "MongoDB or RabbitMQ unavailable")
    return {"status": "ready"}
