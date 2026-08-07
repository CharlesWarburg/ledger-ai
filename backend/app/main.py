import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.api.customers import router as customers_router
from app.api.invoices import router as invoices_router
from app.api.payments import router as payments_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.database import get_db

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "Application starting | app=%s environment=%s",
        settings.app_name,
        settings.environment,
    )
    yield
    logger.info("Application stopping | app=%s", settings.app_name)


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(invoices_router)
app.include_router(payments_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/db-health")
def db_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"database": "connected"}
