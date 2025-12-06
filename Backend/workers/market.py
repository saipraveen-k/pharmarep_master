import logging
from typing import List, Dict

from .base import WorkerBase

logger = logging.getLogger(__name__)


class MarketWorker(WorkerBase):
    async def fetch_raw_items(
        self, query_text: str, instructions: str, max_results: int
    ) -> List[Dict]:
        logger.info(f"MarketWorker mock for query={query_text}")
        return [
            {
                "source_id": "market_1",
                "title": f"{query_text} market snapshot",
                "snippet": "Memantine shows growing market interest.",
                "url": "https://example.com/market",
                "raw_text": "Market data suggests memantine has strong commercial potential.",
            }
        ]
