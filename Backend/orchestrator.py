# backend/orchestrator.py
"""
Master Orchestrator: planner LLM -> workers -> aggregation -> ranking.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Callable

import openai

from .prompts import MASTER_PLANNER_PROMPT
from .aggregator import aggregate_and_score
from .ranking import llm_rerank_candidates
from .workers import (
    PapersWorker,
    TrialsWorker,
    PatentsWorker,
    MarketWorker,
    InternalDocsWorker,
)

logger = logging.getLogger(__name__)


class MasterOrchestrator:
    def __init__(self, status_callback: Callable[[int, Dict[str, str]], None]):
        self.status_callback = status_callback
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.worker_timeout = int(os.getenv("WORKER_TIMEOUT_SECONDS", "25"))

        self.workers = {
            "papers": PapersWorker(timeout=self.worker_timeout),
            "clinical_trials": TrialsWorker(timeout=self.worker_timeout),
            "patents": PatentsWorker(timeout=self.worker_timeout),
            "market": MarketWorker(timeout=self.worker_timeout),
            "internal_docs": InternalDocsWorker(timeout=self.worker_timeout),
        }

    async def plan_query(self, query_text: str, max_results: int) -> Dict:
        prompt = MASTER_PLANNER_PROMPT.format(
            query_text=query_text,
            max_results=max_results,
        )
        resp = openai.ChatCompletion.create(
            model=os.getenv("OPENAI_MODEL_PLANNER", "gpt-4.1-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=2000,
        )
        text = resp.choices[0].message.content.strip()
        plan = json.loads(text)
        return plan

    async def run_workers(self, plan: Dict, query_text: str) -> Dict[str, List[Dict]]:
        subtasks_by_name = {st["name"]: st for st in plan.get("subtasks", [])}
        tasks: Dict[str, asyncio.Task] = {}

        self.status_callback(30, {name: "running" for name in self.workers.keys()})

        for name, worker in self.workers.items():
            subtask = subtasks_by_name.get(name)
            if not subtask:
                continue
            tasks[name] = asyncio.create_task(
                worker.execute(query_text, subtask)
            )

        results: Dict[str, List[Dict]] = {}
        for name, task in tasks.items():
            try:
                hits = await asyncio.wait_for(task, timeout=self.worker_timeout + 5)
                results[name] = hits
            except Exception as e:
                logger.error(f"Worker {name} failed: {e}")
                results[name] = []

        self.status_callback(60, {name: "done" for name in self.workers.keys()})
        return results

    async def run(self, query_id: str, query_text: str, max_results: int) -> Dict:
        plan = await self.plan_query(query_text, max_results)
        worker_results = await self.run_workers(plan, query_text)
        self.status_callback(70, {n: "aggregating" for n in self.workers.keys()})

        aggregated = aggregate_and_score(worker_results)
        self.status_callback(85, {n: "ranking" for n in self.workers.keys()})

        ranked = await llm_rerank_candidates(aggregated)
        self.status_callback(95, {n: "done" for n in self.workers.keys()})

        return {
            "query_id": query_id,
            "query": query_text,
            "plan": plan,
            "worker_results": worker_results,
            "candidates": ranked,
            "timestamp": datetime.utcnow().isoformat(),
        }


async def run_orchestration(
    query_id: str,
    query_text: str,
    max_results: int,
    status_callback: Callable[[int, Dict[str, str]], None],
) -> Dict:
    orchestrator = MasterOrchestrator(status_callback=status_callback)
    return await orchestrator.run(query_id, query_text, max_results)
