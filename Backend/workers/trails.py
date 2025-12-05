import logging
from typing import List, Dict

import aiohttp

from .base import WorkerBase

logger = logging.getLogger(__name__)

class TrialsWorker(WorkerBase):
    async def fetch_raw_items(
        self,
        query_text: str,
        instructions: str,
        max_results: int,
    ) -> List[Dict]:
        base_url = "https://clinicaltrials.gov/api/v2/studies"
        params = {
            "query.cond": query_text,
            "sort": "LastUpdatePostDate",
            "pageSize": min(max_results, 50),
            "format": "json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"ClinicalTrials.gov error: {resp.status}")
                    return []
                data = await resp.json()
        studies = data.get("studies", []) or []
        out: List[Dict] = []
        for s in studies[:max_results]:
            prot = s.get("protocolSection", {})
            id_mod = prot.get("identificationModule", {})
            nct_id = id_mod.get("nctId", "")
            title = id_mod.get("briefTitle", "")
            summary = prot.get("descriptionModule", {}).get("briefSummary", "")
            out.append({
                "source_id": nct_id,
                "title": title,
                "summary": summary,
                "url": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
                "raw_text": f"{title}\n\n{summary}",
            })
        return out
