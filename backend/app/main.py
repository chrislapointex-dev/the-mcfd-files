from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import init_db
from . import models  # noqa: F401 — registers models with Base.metadata
from .routers import decisions


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="The MCFD Files",
    description="Document analysis and search API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(decisions.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "mcfd-backend"}


@app.get("/")
async def root():
    return {"message": "The MCFD Files API"}
