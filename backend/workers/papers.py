import logging
from typing import List, Dict

from .base import WorkerBase

logger = logging.getLogger(__name__)

class PapersWorker(WorkerBase):
    async def fetch_raw_items(
        self, query_text: str, instructions: str, max_results: int
    ) -> List[Dict]:
        logger.info(f"PapersWorker mock for query={query_text}")
        items = []
        for i in range(max_results):
            items.append(
                {
                    "source_id": f"PMID{1000000 + i}",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{1000000 + i}/",
                    "raw_text": (
                        f"Study {i}: Drug X shows promise in {query_text}. "
                        f"Results indicate mechanism Y. Phase 2 trial completed."
                    ),
                }
            )
        return items
