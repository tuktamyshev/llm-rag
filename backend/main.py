import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


def create_app() -> FastAPI:
    app = FastAPI(title="LLM RAG Modular Monolith")
    allowed_origins = os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5175,http://127.0.0.1:5175",
    ).split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()

# Simple bootstrap for local development.
Base.metadata.create_all(bind=engine)
