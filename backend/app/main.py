import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.api.assistant import router as assistant_router
from app.api.customers import router as customers_router
from app.api.dashboard import router as dashboard_router
from app.api.documents import router as documents_router
from app.api.invoices import router as invoices_router
from app.api.insights import router as insights_router
from app.api.payments import router as payments_router
from app.api.reports import router as reports_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.database import get_db

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "Application starting | app=%s environment=%s ai_provider_configured=%s ai_model=%s",
        settings.app_name,
        settings.environment,
        bool(settings.openai_api_key.get_secret_value()),
        settings.openai_invoice_model,
    )
    yield
    logger.info("Application stopping | app=%s", settings.app_name)


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.middleware("http")
async def log_unhandled_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception(
            "Unhandled request error | method=%s path=%s error_type=%s",
            request.method,
            request.url.path,
            type(exc).__name__,
        )
        raise


app.include_router(auth_router)
app.include_router(assistant_router)
app.include_router(customers_router)
app.include_router(dashboard_router)
app.include_router(documents_router)
app.include_router(invoices_router)
app.include_router(insights_router)
app.include_router(payments_router)
app.include_router(reports_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/db-health")
def db_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"database": "connected"}
