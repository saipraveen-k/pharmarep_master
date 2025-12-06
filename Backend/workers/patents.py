import logging
from typing import List, Dict

from .base import WorkerBase

logger = logging.getLogger(__name__)


class PatentsWorker(WorkerBase):
    async def fetch_raw_items(
        self, query_text: str, instructions: str, max_results: int
    ) -> List[Dict]:
        logger.info(f"PatentsWorker mock for query={query_text}")
        return [
            {
                "source_id": "US10123456B2",
                "title": f"Method for treating {query_text}",
                "abstract": "Patent describing memantine formulations.",
                "url": "https://patents.google.com/patent/US10123456B2",
                "raw_text": f"Use of memantine for treatment of {query_text}.",
            }
        ]
