import logging
from typing import List, Dict

from .base import WorkerBase

logger = logging.getLogger(__name__)

class InternalDocsWorker(WorkerBase):
    async def fetch_raw_items(
        self, query_text: str, instructions: str, max_results: int
    ) -> List[Dict]:
        logger.info("InternalDocsWorker stub: no internal docs wired.")
        return []
