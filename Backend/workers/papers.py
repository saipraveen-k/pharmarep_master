import logging
from typing import List, Dict

import aiohttp

from .base import WorkerBase

logger = logging.getLogger(__name__)

class PapersWorker(WorkerBase):
    async def fetch_raw_items(
        self,
        query_text: str,
        instructions: str,
        max_results: int,
    ) -> List[Dict]:
        base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        search_query = f"({query_text}) AND (drug OR medication OR treatment OR therapy)"
        params = {
            "query": search_query,
            "pageSize": min(max_results, 50),
            "format": "json",
            "sortby": "RELEVANCE",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Europe PMC error: {resp.status}")
                    return []
                data = await resp.json()
        results = data.get("resultList", {}).get("result", []) or []
        out: List[Dict] = []
        for r in results[:max_results]:
            pmid = r.get("id", "")
            title = r.get("title", "")
            abstract = r.get("abstractText", "")
            out.append({
                "source_id": pmid,
                "title": title,
                "abstract": abstract,
                "url": f"https://europepmc.org/article/PMC/{pmid}" if pmid else "",
                "raw_text": f"{title}\n\n{abstract}",
            })
        return out
