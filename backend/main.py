import logging
import os
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.v1.router import api_router
from core.db import Base, engine
from modules.chat import models as chat_models  # noqa: F401
from modules.embeddings import models as embeddings_models  # noqa: F401
from modules.ingestion import models as ingestion_models  # noqa: F401
from modules.projects import models as project_models  # noqa: F401
from modules.rag import models as rag_models  # noqa: F401
from modules.sources import models as source_models  # noqa: F401
from modules.users import models as user_models  # noqa: F401
from modules.vectordb import models as vectordb_models  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s — %(message)s")


def _run_migrations() -> None:
    """Apply pending Alembic migrations on startup."""
    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
        command.upgrade(alembic_cfg, "head")
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "Alembic migration skipped (falling back to create_all): %s", exc,
        )
        Base.metadata.create_all(bind=engine)


def create_app() -> FastAPI:
    app = FastAPI(title="LLM RAG Modular Monolith")
    allowed_origins = os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5175,http://127.0.0.1:5175",
    ).split(",")
    # Доступ к UI по IP в LAN (http://192.168.x.x:3000) без ручного перечисления каждого origin
    _lan_regex = os.getenv(
        "CORS_ALLOW_ORIGIN_REGEX",
        r"^http://(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3})(:\d+)?$",
    ).strip()
    cors_kw: dict = {
        "allow_origins": [origin.strip() for origin in allowed_origins if origin.strip()],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    if _lan_regex and _lan_regex.lower() not in ("0", "false", "no", "off"):
        cors_kw["allow_origin_regex"] = _lan_regex
    app.add_middleware(CORSMiddleware, **cors_kw)
    app.include_router(api_router, prefix="/api/v1")

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logging.getLogger("uvicorn.error").error(
            "Unhandled exception on %s %s:\n%s",
            request.method,
            request.url.path,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )

    return app


app = create_app()
_run_migrations()
