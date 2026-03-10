from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers.analyze import router as analyze_router
from app.routers.runs    import router as runs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Socratix — Business Legitimacy Analyzer",
    description="Automated business due-diligence for analysts",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://frontend:5173",   # Docker service name
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# POST /api/analyze-business/         → run analysis, return DossierReport
# GET  /api/analyze-business/history  → past reports
# GET  /api/analyze-business/{id}     → single report
app.include_router(analyze_router)

# POST/GET/DELETE /api/runs/          → internal background-task API
app.include_router(runs_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
