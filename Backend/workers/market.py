import logging
from typing import List, Dict

from .base import WorkerBase

logger = logging.getLogger(__name__)

class MarketWorker(WorkerBase):
    async def fetch_raw_items(
        self,
        query_text: str,
        instructions: str,
        max_results: int,
    ) -> List[Dict]:
        # Mock implementation; replace with DrugBank, ChEMBL, etc.
        logger.info(f"MarketWorker mock fetch for query={query_text}")
        return [
            {
                "source_id": "market_1",
                "title": f"{query_text} market snapshot",
                "snippet": f"Recent market activity around {query_text}.",
                "url": "https://example.com/market",
                "raw_text": f"Market data suggests {query_text} has growing commercial interest.",
            }
        ]
