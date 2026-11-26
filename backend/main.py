#!/usr/bin/env python3
"""
PharmaRep Master - Backend Server (FastAPI)
Handles orchestration, worker coordination, and result persistence.
Run: uvicorn main:app --reload --port 8000
"""

import asyncio
import logging
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List
import os
import os.path

# Import components
from db import init_db, save_result, get_candidates
from orchestrator import run_orchestration

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="PharmaRep Master API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
async def startup():
    init_db()
    logger.info("✅ Database initialized")

# Request/Response models
class QueryRequest(BaseModel):
    query_text: str
    max_results: int = 5

class QueryResponse(BaseModel):
    query_id: str
    query_text: str
    status: str
    message: str

class StatusResponse(BaseModel):
    query_id: str
    progress: int
    status: Dict[str, str]
    completed: bool

# Global state for tracking queries
query_states: Dict[str, Dict] = {}
query_results: Dict[str, Dict] = {}

def update_status(query_id: str, progress: int, status: Dict[str, str]):
    """Callback for orchestrator to update progress"""
    query_states[query_id] = {
        "progress": progress,
        "status": status,
        "completed": progress >= 100
    }
    logger.info(f"Query {query_id}: {progress}% - {status}")

@app.post("/api/query", response_model=QueryResponse)
async def create_query(request: QueryRequest):
    """Start a new query"""
    query_id = str(uuid.uuid4())
    
    # Initialize state
    query_states[query_id] = {
        "progress": 0,
        "status": {"stage": "initializing"},
        "completed": False
    }
    
    logger.info(f"🔍 New query: {query_id} - {request.query_text}")
    
    # Run orchestration in background
    async def run_query():
        try:
            result = await run_orchestration(
                query_id=query_id,
                query_text=request.query_text,
                max_results=request.max_results,
                status_callback=lambda progress, status: update_status(query_id, progress, status)
            )
            query_results[query_id] = result
            save_result(query_id, result)
            logger.info(f"✅ Query {query_id} completed")
            
            query_states[query_id]["progress"] = 100
            query_states[query_id]["completed"] = True
            query_states[query_id]["status"]["stage"] = "completed"
        except Exception as e:
            logger.error(f"❌ Query {query_id} failed: {e}")
            query_states[query_id]["status"]["error"] = str(e)
            query_states[query_id]["completed"] = True
    
    asyncio.create_task(run_query())
    
    return QueryResponse(
        query_id=query_id,
        query_text=request.query_text,
        status="processing",
        message="Query started"
    )

@app.get("/api/status/{query_id}", response_model=StatusResponse)
async def get_status(query_id: str):
    """Get query status"""
    if query_id not in query_states:
        raise HTTPException(status_code=404, detail="Query not found")
    
    state = query_states[query_id]
    return StatusResponse(
        query_id=query_id,
        progress=state["progress"],
        status=state["status"],
        completed=state["completed"]
    )

@app.get("/api/candidates/{query_id}")
async def get_query_candidates(query_id: str):
    """Get candidates for a query"""
    if query_id not in query_results:
        # Try to get from DB
        candidates = get_candidates(query_id)
        if not candidates:
            raise HTTPException(status_code=404, detail="No candidates found")
        return {
            "query_id": query_id,
            "candidates": candidates,
            "count": len(candidates)
        }
    
    result = query_results[query_id]
    candidates = result.get("candidates", [])
    
    return {
        "query_id": query_id,
        "candidates": candidates,
        "count": len(candidates),
        "timestamp": result.get("timestamp")
    }

@app.get("/api/report/{query_id}")
async def get_report(query_id: str):
    """Download PDF report for a query"""
    pdf_path = f"./reports/{query_id}.pdf"
    
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail=f"PDF report not found: {pdf_path}")
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"pharmarep_report_{query_id[:8]}.pdf"
    )

@app.get("/api/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "service": "PharmaRep Master API",
        "version": "1.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 