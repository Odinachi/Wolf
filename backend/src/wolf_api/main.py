import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import auth, builds, config, projects
from .db import init_db

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Wolf API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    # Auth is a bearer token, not a cookie, so the web app can live on another domain.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(builds.router)

init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": config.MODEL}
