import logging
from typing import List, Dict

from .base import WorkerBase

logger = logging.getLogger(__name__)


class PapersWorker(WorkerBase):
    async def fetch_raw_items(
        self, query_text: str, instructions: str, max_results: int
    ) -> List[Dict]:
        logger.info(f"PapersWorker mock for query={query_text}")
        return [
            {
                "source_id": "PMID1234",
                "title": f"Paper about {query_text}",
                "abstract": f"This paper describes repurposing of memantine for {query_text}.",
                "url": "https://example.org/pmid1234",
                "raw_text": (
                    f"Randomized trial NCT1234: memantine improved cognition in "
                    f"moderate Alzheimer's disease."
                ),
            }
        ]
