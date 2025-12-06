import asyncio
import logging
import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from orchestrator import run_orchestration
from db import init_db, save_result, get_candidates

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
active_queries: dict = {}

class QueryRequest(BaseModel):
    query: str
    max_results: int = 10
    include_internal_docs: bool = False

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/start_query")
async def start_query(req: QueryRequest):
    query_id = str(uuid.uuid4())
    active_queries[query_id] = {"status": "running", "progress": 0}

    def update_status(progress: int, details: dict):
        if query_id in active_queries:
            active_queries[query_id]["progress"] = progress
            active_queries[query_id]["details"] = details

    asyncio.create_task(
        run_orchestration_task(query_id, req.query, req.max_results, update_status)
    )
    return {"query_id": query_id}

async def run_orchestration_task(
    query_id: str, query_text: str, max_results: int, status_callback
):
    try:
        result = await run_orchestration(
            query_id, query_text, max_results, status_callback
        )
        save_result(query_id, result)
        if query_id in active_queries:
            active_queries[query_id]["status"] = "completed"
            active_queries[query_id]["progress"] = 100
    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        if query_id in active_queries:
            active_queries[query_id]["status"] = "failed"
            active_queries[query_id]["error_message"] = str(e)

@app.get("/api/status/{query_id}")
async def get_status(query_id: str):
    if query_id not in active_queries:
        raise HTTPException(status_code=404, detail="Query not found")
    q = active_queries[query_id]
    return {
        "query_id": query_id,
        "status": q.get("status", "unknown"),
        "progress_percent": q.get("progress", 0),
        "error_message": q.get("error_message"),
    }

@app.get("/api/candidates/{query_id}")
async def get_candidates_endpoint(query_id: str):
    candidates = get_candidates(query_id)
    return {"query_id": query_id, "candidates": candidates}

@app.get("/api/report/{query_id}")
async def get_report(query_id: str):
    from fastapi.responses import FileResponse

    pdf_path = f"./reports/{query_id}.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(
        pdf_path, media_type="application/pdf", filename=f"{query_id}.pdf"
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
