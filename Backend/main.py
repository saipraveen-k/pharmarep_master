# backend/main.py
"""
FastAPI application for PharmaRep Master.
"""

from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime
import uuid
import os
import logging

from .db import init_db, save_query, save_result, get_candidates_by_query_id
from .orchestrator import run_orchestration
from .pdf_gen import generate_pdf_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PharmaRep Master API",
    description="Agentic AI for Rapid Drug Repurposing",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


class StartQueryRequest(BaseModel):
    query: str
    max_results: int = 20
    include_internal_docs: bool = False


class QueryStatus(BaseModel):
    query_id: str
    status: str
    progress_percent: int
    worker_status: Dict[str, str]
    error_message: Optional[str]
    timestamp: str


# in‑memory status store (for demo)
query_status_store: Dict[str, Dict] = {}


@app.get("/")
async def root():
    return {
        "app": "PharmaRep Master",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.post("/api/start_query")
async def start_query(request: StartQueryRequest, background_tasks: BackgroundTasks):
    query_id = str(uuid.uuid4())
    try:
        save_query(query_id, request.query, request.max_results)
    except Exception as e:
        logger.error(f"Error saving query: {e}")
        raise HTTPException(status_code=500, detail="Database error")

    query_status_store[query_id] = {
        "status": "running",
        "progress_percent": 0,
        "worker_status": {
            "papers": "pending",
            "clinical_trials": "pending",
            "patents": "pending",
            "market": "pending",
            "internal_docs": "pending",
        },
        "error_message": None,
        "timestamp": datetime.utcnow().isoformat(),
    }

    background_tasks.add_task(
        run_orchestration_task,
        query_id=query_id,
        query_text=request.query,
        max_results=request.max_results,
    )

    return {
        "query_id": query_id,
        "status": "running",
        "message": "Search initiated. Poll /api/status/{query_id} for progress.",
    }


@app.get("/api/status/{query_id}")
async def get_status(query_id: str):
    if query_id not in query_status_store:
        raise HTTPException(status_code=404, detail="Query not found")
    s = query_status_store[query_id]
    return QueryStatus(
        query_id=query_id,
        status=s["status"],
        progress_percent=s["progress_percent"],
        worker_status=s["worker_status"],
        error_message=s.get("error_message"),
        timestamp=s["timestamp"],
    )


@app.get("/api/candidates/{query_id}")
async def get_candidates(query_id: str):
    if query_id not in query_status_store or query_status_store[query_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Query not completed yet")
    try:
        candidates = get_candidates_by_query_id(query_id)
        return {"query_id": query_id, "candidates": candidates}
    except Exception as e:
        logger.error(f"Error fetching candidates: {e}")
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/api/report/{query_id}")
async def download_report(query_id: str):
    if query_id not in query_status_store or query_status_store[query_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Query not completed yet")

    reports_dir = os.getenv("REPORTS_DIR", "./reports")
    os.makedirs(reports_dir, exist_ok=True)
    pdf_path = os.path.join(reports_dir, f"{query_id}.pdf")

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Report not generated yet")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"pharmarep_{query_id}.pdf",
    )


@app.post("/api/review/{query_id}/{candidate}")
async def flag_for_review(query_id: str, candidate: str):
    return {
        "status": "flagged",
        "candidate": candidate,
        "query_id": query_id,
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Candidate flagged for human review (stubbed)",
    }


@app.post("/api/upload_docs")
async def upload_internal_docs(file: UploadFile = File(...)):
    # Stub: not wired to workers in this MVP
    upload_dir = "./uploads"
    os.makedirs(upload_dir, exist_ok=True)
    dest = os.path.join(upload_dir, file.filename)
    with open(dest, "wb") as f:
        f.write(await file.read())

    return {
        "file_name": file.filename,
        "status": "uploaded",
        "message": "Document stored (not yet used by internal_docs worker).",
    }


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


async def run_orchestration_task(query_id: str, query_text: str, max_results: int):
    try:
        logger.info(f"Starting orchestration for query_id={query_id}")
        query_status_store[query_id]["status"] = "running"
        query_status_store[query_id]["progress_percent"] = 10

        result = await run_orchestration(
            query_id=query_id,
            query_text=query_text,
            max_results=max_results,
            status_callback=lambda pct, ws: update_status(query_id, pct, ws),
        )

        reports_dir = os.getenv("REPORTS_DIR", "./reports")
        os.makedirs(reports_dir, exist_ok=True)
        pdf_path = os.path.join(reports_dir, f"{query_id}.pdf")
        generate_pdf_report(result, pdf_path)

        save_result(query_id, result)

        query_status_store[query_id]["status"] = "completed"
        query_status_store[query_id]["progress_percent"] = 100
        logger.info(f"Orchestration completed for query_id={query_id}")
    except Exception as e:
        logger.error(f"Orchestration failed for query_id={query_id}: {e}", exc_info=True)
        query_status_store[query_id]["status"] = "failed"
        query_status_store[query_id]["error_message"] = str(e)


def update_status(query_id: str, progress_percent: int, worker_status: Dict[str, str]):
    if query_id in query_status_store:
        query_status_store[query_id]["progress_percent"] = progress_percent
        query_status_store[query_id]["worker_status"] = worker_status
        query_status_store[query_id]["timestamp"] = datetime.utcnow().isoformat()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
