import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

from openai import OpenAI
from prompts import WORKER_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)
client = OpenAI()

class WorkerBase(ABC):
    def __init__(self, timeout: int = 25):
        self.timeout = timeout

    @abstractmethod
    async def fetch_raw_items(
        self, query_text: str, instructions: str, max_results: int
    ) -> List[Dict]:
        """
        Implement in subclasses.
        Should return a list of dicts with at least:
        {
          "source_id": str,
          "url": str or None,
          "raw_text": str
        }
        """
        ...

    async def _extract(self, raw_text: str, worker_prompt: str) -> List[Dict]:
        """
        Call LLM to extract structured drug evidence from raw_text.
        """
        if not raw_text.strip():
            return []

        prompt = WORKER_EXTRACTION_PROMPT.format(raw_text=raw_text)

        try:
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL_WORKER", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=800,
            )
            text = resp.choices[0].message.content.strip()
            logger.info(f"Worker extraction LLM response: {text[:500]!r}")
        except Exception as e:
            logger.error(f"Worker LLM API call failed: {e}")
            return []

        hits = self._safe_json_parse(text)
        if hits is not None and len(hits) > 0:
            logger.info(f"Successfully extracted {len(hits)} hits")
            return hits

        logger.warning(f"No valid JSON hits extracted from: {text[:300]!r}")
        return []

    def _safe_json_parse(self, text: str) -> Optional[List[Dict]]:
        """
        Try to parse LLM output as JSON.
        If wrapped in markdown code fences, strip them first.
        Returns list[dict] or None.
        """
        cleaned = text.strip()

        # Remove markdown code fences by looking for the backtick pattern
        backtick = chr(96)  # ASCII code for backtick
        triple = backtick + backtick + backtick
        
        if triple in cleaned:
            parts = cleaned.split(triple)
            if len(parts) >= 3:
                cleaned = parts[1].strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}. Text was: {cleaned[:300]!r}")
            return None

        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            logger.warning(f"Expected list or dict, got {type(data)}")
            return None

        return data

    async def execute(self, query_text: str, subtask: Dict) -> List[Dict]:
        """
        End-to-end worker execution:
        1. fetch_raw_items
        2. run extraction on each
        3. normalize and attach source metadata
        """
        try:
            raw_items = await self.fetch_raw_items(
                query_text,
                subtask.get("fetch_instructions", ""),
                subtask.get("max_results", 10),
            )
        except Exception as e:
            logger.error(f"fetch_raw_items failed in {subtask.get('name')}: {e}")
            return []

        all_hits: List[Dict] = []
        for item in raw_items:
            try:
                hits = await asyncio.wait_for(
                    self._extract(
                        item.get("raw_text", ""),
                        subtask.get("worker_prompt", "")
                    ),
                    timeout=self.timeout,
                )
                for h in hits:
                    h["source"] = subtask["name"]
                    h["source_url"] = h.get("source_url") or item.get("url")
                    h["source_id"] = h.get("source_id") or item.get("source_id", "")
                all_hits.extend(hits)
            except asyncio.TimeoutError:
                logger.warning(f"Extraction timeout for {item.get('source_id')}")
            except Exception as e:
                logger.error(f"Extraction error for {item.get('source_id')}: {e}")

        return all_hits
