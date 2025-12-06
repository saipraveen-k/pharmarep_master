import logging
from typing import List, Dict

from .base import WorkerBase

logger = logging.getLogger(__name__)


class TrialsWorker(WorkerBase):
    async def fetch_raw_items(
        self, query_text: str, instructions: str, max_results: int
    ) -> List[Dict]:
        logger.info(f"TrialsWorker mock for query={query_text}")
        return [
            {
                "source_id": "NCT1234",
                "title": f"Trial for {query_text}",
                "summary": f"Randomized, double-blind trial of memantine for {query_text}.",
                "url": "https://clinicaltrials.gov/study/NCT1234",
                "raw_text": (
                    f"Randomized trial NCT1234: memantine improved outcome in {query_text}."
                ),
            }
        ]
