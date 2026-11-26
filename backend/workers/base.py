import asyncio
import json
import logging
import os
import random
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
        For testing, return mock data to avoid API quota issues.
        """
        if not raw_text.strip():
            return []

        # MOCK DATA - Returns realistic candidates instantly
        # Remove this section when your OpenAI API quota is set up
        drugs = [
            "Memantine", 
            "Donepezil", 
            "Rivastigmine", 
            "Galantamine", 
            "Lecanemab",
            "Aducanumab",
            "Tacrine",
            "Physostigmine"
        ]
        diseases = [
            "Alzheimer's disease", 
            "Dementia", 
            "Cognitive Impairment", 
            "Neurodegeneration",
            "Mild Cognitive Decline",
            "Age-related Memory Loss"
        ]
        mechanisms = [
            "Acetylcholinesterase inhibitor", 
            "NMDA antagonist", 
            "Amyloid inhibitor", 
            "Receptor modulator",
            "Tau protein inhibitor",
            "Neuroinflammation reducer"
        ]
        
        mock_hits = []
        num_drugs = random.randint(2, 4)
        
        for _ in range(num_drugs):
            mock_hits.append({
                "drug": random.choice(drugs),
                "disease": random.choice(diseases),
                "mechanism": random.choice(mechanisms),
                "evidence_snippet": f"Clinical studies demonstrate effectiveness. Multiple phase trials show positive outcomes. Evidence supports repurposing.",
                "confidence": round(random.uniform(0.75, 0.98), 2),
                "source_url": "https://pubmed.ncbi.nlm.nih.gov/example/",
                "source_id": f"PMID{random.randint(1000000, 9999999)}",
            })
        
        return mock_hits

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
