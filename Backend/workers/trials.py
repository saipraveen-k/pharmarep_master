import logging
from typing import List, Dict

from .base import WorkerBase

logger = logging.getLogger(__name__)

class TrialsWorker(WorkerBase):
    async def fetch_raw_items(
        self, query_text: str, instructions: str, max_results: int
    ) -> List[Dict]:
        logger.info(f"TrialsWorker mock for query={query_text}")
        items = []
        for i in range(max_results):
            items.append(
                {
                    "source_id": f"NCT{2000000 + i}",
                    "url": f"https://clinicaltrials.gov/ct2/show/NCT{2000000 + i}",
                    "raw_text": (
                        f"Clinical trial {i}: Testing drug compound for {query_text}. "
                        f"60 subjects, phase 3. Primary outcome met."
                    ),
                }
            )
        return items
