# backend/aggregator.py
import logging
import re
from typing import Dict, List
from collections import defaultdict

logger = logging.getLogger(__name__)


def _norm(name: str) -> str:
    s = (name or "").lower().strip()
    return re.sub(r"[^\w\s]", "", s)


def aggregate_and_score(worker_results: Dict[str, List[Dict]]) -> List[Dict]:
    groups = defaultdict(lambda: {"hits": [], "sources": set()})

    for source, hits in worker_results.items():
        for h in hits:
            drug = (h.get("drug") or "").strip()
            if not drug:
                continue
            key = _norm(drug)
            groups[key]["hits"].append(h | {"source": source})
            groups[key]["sources"].add(source)

    candidates: List[Dict] = []
    for key, data in groups.items():
        hits = data["hits"]
        sources = data["sources"]
        if not hits:
            continue

        det = _score(hits, sources)
        evidence = [
            {
                "source": h["source"],
                "source_id": h.get("source_id", ""),
                "source_url": h.get("source_url"),
                "snippet": h.get("evidence_snippet", ""),
                "confidence": float(h.get("confidence", 0.5)),
            }
            for h in hits
        ]
        diseases = list({h.get("disease", "") for h in hits if h.get("disease")})
        mechs = list({h.get("mechanism", "") for h in hits if h.get("mechanism")})
        avg_conf = sum(float(h.get("confidence", 0.5)) for h in hits) / len(hits)

        candidates.append(
            {
                "drug": hits[0].get("drug", ""),
                "deterministic_score": det,
                "llm_score": None,
                "final_score": det,
                "sources_count": len(sources),
                "evidence": evidence,
                "mechanism": mechs[0] if mechs else "",
                "diseases": diseases,
                "average_confidence": avg_conf,
                "aggregated_meta": {
                    "sources": list(sources),
                    "hit_count": len(hits),
                    "diseases": diseases,
                    "mechanisms": mechs,
                },
            }
        )

    candidates.sort(key=lambda c: c["deterministic_score"], reverse=True)
    return candidates


def _score(hits: List[Dict], sources: set) -> float:
    src_conf = defaultdict(list)
    for h in hits:
        src_conf[h["source"]].append(float(h.get("confidence", 0.5)))

    # simple weights for demo
    clinical = 0.0
    if "clinical_trials" in src_conf:
        mx = max(src_conf["clinical_trials"]) if src_conf["clinical_trials"] else 0.5
        clinical = 0.5 * mx

    papers = 0.0
    if "papers" in src_conf and src_conf["papers"]:
        papers = 0.3 * (sum(src_conf["papers"]) / len(src_conf["papers"]))

    patents = 0.0
    if "patents" in src_conf and src_conf["patents"]:
        patents = 0.1 * max(src_conf["patents"])

    market = 0.0
    if "market" in src_conf and src_conf["market"]:
        market = 0.1 * max(src_conf["market"])

    base = clinical + papers + patents + market
    bonus = 1.0 + 0.05 * max(0, len(sources) - 1)
    final = base * bonus
    return round(min(final, 1.0), 3)
