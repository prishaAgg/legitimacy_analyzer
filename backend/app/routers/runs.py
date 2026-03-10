"""
routers/runs.py
===============
Internal polling API — exposes raw SearchRun records.
Used for background-task workflows and debugging.

POST   /api/runs/        → start a run (background task)
GET    /api/runs/        → list all runs
GET    /api/runs/{id}    → get a single run
DELETE /api/runs/{id}    → delete a run
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timezone

from app.database import get_db, AsyncSessionLocal
from app.models.search_run import SearchRun
from app.schemas.request import SearchRequest
from app.schemas.response import SearchRunResponse, SearchRunSummary
from app.services.orchestrator import run_analysis

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("/", response_model=SearchRunResponse, status_code=201)
async def create_run(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Start a new analysis run. Returns immediately; analysis runs in background."""
    run = SearchRun(
        business_name=request.business_name.strip(),
        location=request.location,
        extra_context=request.extra_context,
        status="running",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    background_tasks.add_task(_run_analysis_task, run.id, request)
    return run


@router.get("/", response_model=list[SearchRunSummary])
async def list_runs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """List all runs, newest first."""
    result = await db.execute(
        select(SearchRun).order_by(desc(SearchRun.created_at)).limit(limit)
    )
    return result.scalars().all()


@router.get("/{run_id}", response_model=SearchRunResponse)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SearchRun).where(SearchRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.delete("/{run_id}", status_code=204)
async def delete_run(run_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SearchRun).where(SearchRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    await db.delete(run)
    await db.commit()


async def _run_analysis_task(run_id: int, request: SearchRequest) -> None:
    """Background task: run analysis and update the DB record when done."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SearchRun).where(SearchRun.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            return

        try:
            analysis  = await run_analysis(request.business_name, request.location, request.extra_context)
            synthesis = analysis["synthesis"]

            run.signals          = {**analysis["signals"], "_synthesis": synthesis}
            run.confidence_score = synthesis.get("confidence_score")
            run.verdict          = synthesis.get("verdict")
            run.verdict_summary  = synthesis.get("verdict_summary")
            run.status           = "complete"
            run.completed_at     = datetime.now(timezone.utc)
        except Exception as e:
            run.status        = "error"
            run.error_message = str(e)

        await db.commit()
