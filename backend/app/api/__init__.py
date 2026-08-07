from app.api.auth import router as auth_router
from app.api.customers import router as customers_router
from app.api.dependencies import get_current_user, require_admin

__all__ = [
    "auth_router",
    "customers_router",
    "get_current_user",
    "require_admin",
]
