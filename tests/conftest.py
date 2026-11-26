import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

TEST_SECRET = "unit-test-only-secret"
PROJECT_ROOT = Path(__file__).resolve().parents[1]

_TEST_ENV = {
    "JWT_SECRET": TEST_SECRET,
    "DATABASE_URL": "sqlite://",
    "REDIS_URL": "redis://127.0.0.1:1/15",
    "PRODUCT_SERVICE_URL": "http://127.0.0.1:1",
    "CART_SERVICE_URL": "http://127.0.0.1:1",
    "RABBITMQ_URL": "amqp://127.0.0.1:1/",
    "MONGODB_URL": "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100",
    "MONGODB_DATABASE": "unit_test_only",
    "AUTH_SERVICE_URL": "http://127.0.0.1:1",
    "USER_SERVICE_URL": "http://127.0.0.1:1",
    "ORDER_SERVICE_URL": "http://127.0.0.1:1",
    "PAYMENT_SERVICE_URL": "http://127.0.0.1:1",
    "NOTIFICATION_SERVICE_URL": "http://127.0.0.1:1",
    "UPSTREAM_TIMEOUT_SECONDS": "1",
    "CORS_ORIGINS": "http://testserver",
}

# Force safe test-only values before application modules are imported.
os.environ.update(_TEST_ENV)


@dataclass
class ServiceContext:
    client: TestClient
    main: Any
    session_factory: Any = None


@pytest.fixture
def service_client_factory(monkeypatch):
    contexts = []
    engines = []

    def create(service_name: str) -> ServiceContext:
        from tests.support.service_loader import load_service

        main = load_service(service_name)
        session_factory = None

        if hasattr(main, "Base") and (
            hasattr(main, "get_db") or hasattr(main, "SessionLocal")
        ):
            engine = create_engine(
                "sqlite://",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
            engines.append(engine)
            if hasattr(main, "SERVICE_MODEL"):
                main.Base.metadata.create_all(
                    engine,
                    tables=[main.SERVICE_MODEL.__table__],
                )
            else:
                main.Base.metadata.create_all(engine)
            main.engine = engine
            session_factory = sessionmaker(
                bind=engine,
                autoflush=False,
                expire_on_commit=False,
            )

            if hasattr(main, "SessionLocal"):
                monkeypatch.setattr(main, "SessionLocal", session_factory)
            if hasattr(main, "get_db"):
                def override_get_db():
                    with session_factory() as session:
                        yield session

                main.app.dependency_overrides[main.get_db] = override_get_db

        context = ServiceContext(
            client=TestClient(main.app),
            main=main,
            session_factory=session_factory,
        )
        contexts.append(context)
        return context

    yield create

    for context in contexts:
        context.client.close()
        context.main.app.dependency_overrides.clear()
    for engine in engines:
        engine.dispose()
