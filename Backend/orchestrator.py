# backend/orchestrator.py
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Callable

import openai

from prompts import MASTER_PLANNER_PROMPT
from aggregator import aggregate_and_score
from ranking import llm_rerank_candidates
from workers import PapersWorker, TrialsWorker, PatentsWorker, MarketWorker, InternalDocsWorker

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
        prompt = MASTER_PLANNER_PROMPT.format(query_text=query_text, max_results=max_results)
        resp = openai.ChatCompletion.create(
            model=os.getenv("OPENAI_MODEL_PLANNER", "gpt-4.1-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=800,
        )
        text = resp.choices[0].message.content.strip()
        return json.loads(text)

    async def run_workers(self, plan: Dict, query_text: str) -> Dict[str, List[Dict]]:
        subtasks = {st["name"]: st for st in plan.get("subtasks", [])}
        tasks: Dict[str, asyncio.Task] = {}
        self.status_callback(30, {n: "running" for n in self.workers.keys()})

        for name, worker in self.workers.items():
            st = subtasks.get(name)
            if not st:
                continue
            tasks[name] = asyncio.create_task(worker.execute(query_text, st))

        results: Dict[str, List[Dict]] = {}
        for name, t in tasks.items():
            try:
                results[name] = await asyncio.wait_for(t, timeout=self.worker_timeout + 5)
            except Exception as e:
                logger.error(f"Worker {name} failed: {e}")
                results[name] = []

        self.status_callback(60, {n: "done" for n in self.workers.keys()})
        return results

    async def run(self, query_id: str, query_text: str, max_results: int) -> Dict:
        plan = await self.plan_query(query_text, max_results)
        worker_results = await self.run_workers(plan, query_text)
        self.status_callback(75, {n: "aggregating" for n in self.workers.keys()})

        aggregated = aggregate_and_score(worker_results)
        self.status_callback(90, {n: "ranking" for n in self.workers.keys()})

        ranked = await llm_rerank_candidates(aggregated)

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
    orch = MasterOrchestrator(status_callback=status_callback)
    return await orch.run(query_id, query_text, max_results)
