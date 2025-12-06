import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import List, Dict

import openai
from prompts import WORKER_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class WorkerBase(ABC):
    def __init__(self, timeout: int = 25):
        self.timeout = timeout
        openai.api_key = os.getenv("OPENAI_API_KEY")

    @abstractmethod
    async def fetch_raw_items(
        self, query_text: str, instructions: str, max_results: int
    ) -> List[Dict]:
        ...

    async def _extract(self, raw_text: str, worker_prompt: str) -> List[Dict]:
        if not raw_text.strip():
            return []
        prompt = WORKER_EXTRACTION_PROMPT.format(raw_text=raw_text)
        resp = openai.ChatCompletion.create(
            model=os.getenv("OPENAI_MODEL_WORKER", "gpt-4.1-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=800,
        )
        text = resp.choices[0].message.content.strip()
        try:
            arr = json.loads(text)
            if isinstance(arr, dict):
                arr = [arr]
            return arr
        except Exception:
            logger.warning("Failed to parse worker extraction JSON")
            return []

    async def execute(self, query_text: str, subtask: Dict) -> List[Dict]:
        try:
            raw_items = await self.fetch_raw_items(
                query_text,
                subtask.get("fetch_instructions", ""),
                subtask.get("max_results", 10),
            )
        except Exception as e:
            logger.error(f"fetch_raw_items error: {e}")
            return []

        all_hits: List[Dict] = []
        for item in raw_items:
            try:
                hits = await asyncio.wait_for(
                    self._extract(item.get("raw_text", ""), subtask.get("worker_prompt", "")),
                    timeout=10,
                )
                for h in hits:
                    h["source"] = subtask["name"]
                    h["source_url"] = h.get("source_url") or item.get("url")
                    h["source_id"] = h.get("source_id") or item.get("source_id", "mock")
                all_hits.extend(hits)
            except Exception as e:
                logger.error(f"Extraction failed for item {item.get('source_id')}: {e}")
        return all_hits
