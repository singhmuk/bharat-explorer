import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.exc import OperationalError
from .config import settings
from .db import Base, engine, SessionLocal
from .bot_protection import BotShield
from .routes import router
from .seed import seed

app = FastAPI(title="Bharat Explorer API", docs_url=None, redoc_url=None)  # hide docs in prod
app.add_middleware(BotShield)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","),
                   allow_methods=["GET", "POST", "PUT"], allow_headers=["*"])
app.include_router(router)
Instrumentator().instrument(app).expose(app, include_in_schema=False)  # /metrics for Prometheus


@app.on_event("startup")
def startup():
    for _ in range(30):  # wait for MySQL
        try:
            Base.metadata.create_all(engine); break
        except OperationalError:
            time.sleep(2)
    with SessionLocal() as db:
        seed(db)


@app.get("/health")
def health():
    return {"status": "ok"}
