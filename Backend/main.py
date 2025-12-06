# backend/main.py
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime
import uuid
import os
import logging

from db import init_db, save_query, save_result, get_candidates_by_query_id
from orchestrator import run_orchestration
from pdf_gen import generate_pdf_report

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
    max_results: int = 10
    include_internal_docs: bool = False


class QueryStatus(BaseModel):
    query_id: str
    status: str
    progress_percent: int
    worker_status: Dict[str, str]
    error_message: Optional[str]
    timestamp: str


query_status_store: Dict[str, Dict] = {}


@app.get("/")
async def root():
    return {"app": "PharmaRep Master", "version": "1.0.0"}


@app.get("/api/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/start_query")
async def start_query(req: StartQueryRequest, background_tasks: BackgroundTasks):
    query_id = str(uuid.uuid4())
    save_query(query_id, req.query, req.max_results)

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
        run_orchestration_task, query_id=query_id, query_text=req.query, max_results=req.max_results
    )

    return {
        "query_id": query_id,
        "status": "running",
        "message": "Search started. Poll /api/status/{query_id}.",
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
        error_message=s["error_message"],
        timestamp=s["timestamp"],
    )


@app.get("/api/candidates/{query_id}")
async def get_candidates(query_id: str):
    if query_id not in query_status_store or query_status_store[query_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Query not completed yet")
    return {
        "query_id": query_id,
        "candidates": get_candidates_by_query_id(query_id),
    }


@app.get("/api/report/{query_id}")
async def get_report(query_id: str):
    if query_id not in query_status_store or query_status_store[query_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Query not completed yet")

    reports_dir = os.getenv("REPORTS_DIR", "./reports")
    pdf_path = os.path.join(reports_dir, f"{query_id}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Report not ready")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"pharmarep_{query_id}.pdf",
    )


@app.post("/api/upload_docs")
async def upload_docs(file: UploadFile = File(...)):
    # Stored but not used by internal_docs worker in this MVP
    upload_dir = "./uploads"
    os.makedirs(upload_dir, exist_ok=True)
    out_path = os.path.join(upload_dir, file.filename)
    with open(out_path, "wb") as f:
        f.write(await file.read())
    return {"status": "uploaded", "file_name": file.filename}


async def run_orchestration_task(query_id: str, query_text: str, max_results: int):
    try:
        def status_cb(pct: int, ws: Dict[str, str]):
            if query_id in query_status_store:
                query_status_store[query_id]["progress_percent"] = pct
                query_status_store[query_id]["worker_status"] = ws
                query_status_store[query_id]["timestamp"] = datetime.utcnow().isoformat()

        result = await run_orchestration(
            query_id=query_id,
            query_text=query_text,
            max_results=max_results,
            status_callback=status_cb,
        )

        reports_dir = os.getenv("REPORTS_DIR", "./reports")
        os.makedirs(reports_dir, exist_ok=True)
        pdf_path = os.path.join(reports_dir, f"{query_id}.pdf")
        generate_pdf_report(result, pdf_path)

        save_result(query_id, result)

        query_status_store[query_id]["status"] = "completed"
        query_status_store[query_id]["progress_percent"] = 100
    except Exception as e:
        logger.exception(f"Orchestration failed: {e}")
        query_status_store[query_id]["status"] = "failed"
        query_status_store[query_id]["error_message"] = str(e)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
