"""ResumeGPT backend entrypoint."""
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, experts, job_descriptions, resumes, users
from app.core.config import settings
from app.core.database import init_db
from app.services.expert_seed import seed_default_experts

logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_default_experts()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ResumeGPT API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(resumes.router)
app.include_router(experts.router)
app.include_router(job_descriptions.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
