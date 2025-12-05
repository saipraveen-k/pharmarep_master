import logging
import re
from typing import Dict, List
from collections import defaultdict

logger = logging.getLogger(__name__)

def _norm(drug: str) -> str:
    s = (drug or "").lower().strip()
    return re.sub(r"[^\w\s]", "", s)

def aggregate_and_score(worker_results: Dict[str, List[Dict]]) -> List[Dict]:
    groups = defaultdict(lambda: {"hits": [], "sources": set()})

    for source, hits in worker_results.items():
        if not hits:
            continue
        for h in hits:
            drug = (h.get("drug") or "").strip()
            if not drug:
                continue
            key = _norm(drug)
            groups[key]["hits"].append({
                "source": source,
                "drug": drug,
                "disease": h.get("disease", ""),
                "mechanism": h.get("mechanism", ""),
                "evidence_snippet": h.get("evidence_snippet", ""),
                "confidence": float(h.get("confidence", 0.5)),
                "source_url": h.get("source_url"),
                "source_id": h.get("source_id", ""),
                "notes": h.get("notes", ""),
            })
            groups[key]["sources"].add(source)

    candidates: List[Dict] = []

    for key, data in groups.items():
        hits = data["hits"]
        sources = data["sources"]
        if not hits:
            continue
        det_score = _compute_score(hits, sources)
        evidence = [
            {
                "source": h["source"],
                "source_id": h["source_id"],
                "source_url": h["source_url"],
                "snippet": h["evidence_snippet"],
                "confidence": h["confidence"],
            }
            for h in hits
        ]
        diseases = list({h["disease"] for h in hits if h["disease"]})
        mechanisms = list({h["mechanism"] for h in hits if h["mechanism"]})
        avg_conf = sum(h["confidence"] for h in hits) / len(hits)

        candidates.append({
            "drug": hits[0]["drug"],
            "deterministic_score": det_score,
            "llm_score": None,
            "final_score": det_score,
            "sources_count": len(sources),
            "evidence": evidence,
            "mechanism": mechanisms[0] if mechanisms else "",
            "diseases": diseases,
            "average_confidence": avg_conf,
            "aggregated_meta": {
                "sources": list(sources),
                "hit_count": len(hits),
                "diseases": diseases,
                "mechanisms": mechanisms,
            },
        })

    candidates.sort(key=lambda c: c["deterministic_score"], reverse=True)
    return candidates

def _compute_score(hits: List[Dict], sources: set) -> float:
    src_conf = defaultdict(list)
    for h in hits:
        src_conf[h["source"]].append(h["confidence"])

    # clinical_trials component
    clinical_trial_component = 0.0
    if "clinical_trials" in src_conf:
        confs = src_conf["clinical_trials"]
        positive = any(
            ("positive" in (h.get("notes", "").lower())
             or "improved" in (h.get("evidence_snippet", "").lower()))
            for h in hits if h["source"] == "clinical_trials"
        )
        if positive:
            trial_conf = 1.0
        else:
            trial_conf = 0.5 * (max(confs) if confs else 0.5)
        clinical_trial_component = 0.5 * trial_conf

    # papers
    paper_component = 0.0
    if "papers" in src_conf:
        confs = src_conf["papers"]
        if confs:
            paper_component = 0.3 * (sum(confs) / len(confs))

    # patents
    patent_component = 0.0
    if "patents" in src_conf:
        confs = src_conf["patents"]
        if confs:
            patent_component = 0.1 * max(confs)

    # market
    market_component = 0.0
    if "market" in src_conf:
        confs = src_conf["market"]
        if confs:
            market_component = 0.1 * max(confs)

    base = clinical_trial_component + paper_component + patent_component + market_component
    distinct = len(sources)
    bonus = 1.0 + 0.05 * max(0, distinct - 1)
    final = base * bonus
    if final > 1.0:
        final = 1.0
    return round(final, 3)
