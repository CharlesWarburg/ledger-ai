from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db

app = FastAPI(title="Ledger AI API")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/db-health")
def db_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"database": "connected"}