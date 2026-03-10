"""
routers/analyze.py
==================
The single endpoint the frontend calls.

POST /api/analyze-business/          → run analysis, return DossierReport
GET  /api/analyze-business/history   → list of past DossierReports
GET  /api/analyze-business/{id}      → single report by id
DELETE /api/analyze-business/{id}    → delete a report
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.models.search_run import SearchRun
from app.schemas.request import AnalyzeRequest
from app.services.orchestrator import run_analysis
from app.services.formatter import build_dossier_report

router = APIRouter(prefix="/api/analyze-business", tags=["analyze"])


@router.post("/")
async def analyze_business(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze a business and return a complete DossierReport.
    Runs all signal collectors in parallel (~15–30s), synthesizes with Claude.
    """
    # Return cached result if the same business was analyzed within the last 7 days
    if not request.forceRefresh:
        cache_cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)  # naive UTC to match SQLite storage
        cached = await db.execute(
            select(SearchRun)
            .where(
                SearchRun.business_name == request.businessName.strip(),
                SearchRun.location == request.location,
                SearchRun.status == "complete",
                SearchRun.created_at >= cache_cutoff,
            )
            .order_by(desc(SearchRun.created_at))
            .limit(1)
        )
        existing = cached.scalar_one_or_none()
        if existing:
            return _to_dossier(existing)

    run = SearchRun(
        business_name=request.businessName.strip(),
        location=request.location,
        status="running",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    try:
        analysis  = await run_analysis(request.businessName, request.location, None)
        synthesis = analysis["synthesis"]

        run.signals  = {**analysis["signals"], "_synthesis": synthesis}
        run.confidence_score = synthesis.get("confidence_score")
        run.verdict   = synthesis.get("verdict")
        run.verdict_summary  = synthesis.get("verdict_summary")
        run.status = "complete"
        run.completed_at  = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(run)

    except Exception as e:
        run.status        = "error"
        run.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    return _to_dossier(run)


@router.get("/history")
async def get_history(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Return the last N completed analyses as DossierReport objects."""
    result = await db.execute(
        select(SearchRun)
        .where(SearchRun.status == "complete")
        .order_by(desc(SearchRun.created_at))
        .limit(limit)
    )
    return [_to_dossier(r) for r in result.scalars().all()]


@router.get("/{report_id}")
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch a single past report by ID."""
    try:
        run_id = int(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID")

    result = await db.execute(select(SearchRun).where(SearchRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Report not found")
    return _to_dossier(run)


@router.delete("/{report_id}", status_code=204)
async def delete_report(report_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a report."""
    try:
        run_id = int(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID")

    result = await db.execute(select(SearchRun).where(SearchRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Report not found")
    await db.delete(run)
    await db.commit()


def _to_dossier(run: SearchRun) -> dict:
    """Convert a SearchRun DB record → DossierReport dict."""
    signals_raw = dict(run.signals or {})
    synthesis   = signals_raw.pop("_synthesis", {})
    # Restore for future calls without mutating the ORM object
    if synthesis:
        signals_raw["_synthesis"] = synthesis

    return build_dossier_report(
        run_id=run.id,
        business_name=run.business_name,
        location=run.location,
        created_at=run.created_at,
        signals_raw={k: v for k, v in signals_raw.items() if not k.startswith("_")},
        synthesis=synthesis,
    )
