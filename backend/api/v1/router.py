from fastapi import APIRouter

from modules.chat.router import router as chat_router
from modules.evaluation.router import router as evaluation_router
from modules.embeddings.router import router as embeddings_router
from modules.ingestion.router import router as ingestion_router
from modules.projects.router import router as projects_router
from modules.rag.router import router as rag_router
from modules.sources.router import router as sources_router
from modules.users.auth_router import router as auth_router
from modules.users.router import router as users_router
from modules.vectordb.router import router as vectordb_router


api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(sources_router, prefix="/sources", tags=["sources"])
api_router.include_router(ingestion_router, prefix="/ingestion", tags=["ingestion"])
api_router.include_router(embeddings_router, prefix="/embeddings", tags=["embeddings"])
api_router.include_router(vectordb_router, prefix="/vectordb", tags=["vectordb"])
api_router.include_router(rag_router, prefix="/rag", tags=["rag"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(evaluation_router, prefix="/evaluation", tags=["evaluation"])
