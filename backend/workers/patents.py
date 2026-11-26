import logging
from typing import List, Dict

from .base import WorkerBase

logger = logging.getLogger(__name__)

class PatentsWorker(WorkerBase):
    async def fetch_raw_items(
        self, query_text: str, instructions: str, max_results: int
    ) -> List[Dict]:
        logger.info(f"PatentsWorker mock for query={query_text}")
        items = []
        for i in range(max_results):
            items.append(
                {
                    "source_id": f"US{10000000 + i}B2",
                    "url": f"https://patents.google.com/patent/US{10000000 + i}",
                    "raw_text": (
                        f"Patent {i}: Composition for treating {query_text}. "
                        f"Claims methods and formulations. Granted 2023."
                    ),
                }
            )
        return items
    