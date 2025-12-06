import logging
from typing import List, Dict

from .base import WorkerBase

logger = logging.getLogger(__name__)

class MarketWorker(WorkerBase):
    async def fetch_raw_items(
        self, query_text: str, instructions: str, max_results: int
    ) -> List[Dict]:
        logger.info(f"MarketWorker mock for query={query_text}")
        items = []
        for i in range(max_results):
            items.append(
                {
                    "source_id": f"market_{i}",
                    "url": f"https://market-data.example.com/drug/{i}",
                    "raw_text": (
                        f"Market report {i}: Drug approved for {query_text}. "
                        f"Sales growing 15% YoY. Market cap $2B."
                    ),
                }
            )
        return items
