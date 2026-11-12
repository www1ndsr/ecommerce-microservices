import importlib
import importlib.util
import sys
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICE_APP_PATHS = {
    "auth-service": PROJECT_ROOT / "services" / "auth-service" / "app",
    "user-service": PROJECT_ROOT / "services" / "user-service" / "app",
    "product-service": PROJECT_ROOT / "services" / "product-service" / "app",
    "cart-service": PROJECT_ROOT / "services" / "cart-service" / "app",
    "order-service": PROJECT_ROOT / "services" / "order-service" / "app",
    "payment-service": PROJECT_ROOT / "services" / "payment-service" / "app",
    "notification-service": PROJECT_ROOT / "services" / "notification-service" / "app",
    "gateway": PROJECT_ROOT / "gateway" / "app",
}


@lru_cache(maxsize=None)
def load_service(service_name: str):
    app_path = SERVICE_APP_PATHS[service_name]
    package_name = f"_qa_{service_name.replace('-', '_')}"
    package_spec = importlib.util.spec_from_file_location(
        package_name,
        app_path / "__init__.py",
        submodule_search_locations=[str(app_path)],
    )
    if package_spec is None or package_spec.loader is None:
        raise ImportError(f"Cannot load application package for {service_name}")

    package = importlib.util.module_from_spec(package_spec)
    sys.modules[package_name] = package
    package_spec.loader.exec_module(package)
    return importlib.import_module(f"{package_name}.main")
