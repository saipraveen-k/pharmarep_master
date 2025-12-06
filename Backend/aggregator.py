from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

def aggregate_and_score(worker_results: Dict[str, List[Dict]]) -> List[Dict]:
    drug_map: Dict[str, Dict] = {}
    source_weights = {
        "clinical_trials": 0.4,
        "papers": 0.3,
        "patents": 0.15,
        "market": 0.1,
        "internal_docs": 0.05,
    }

    for source, hits in worker_results.items():
        weight = source_weights.get(source, 0.1)
        for hit in hits:
            drug = hit.get("drug", "Unknown")
            if drug not in drug_map:
                drug_map[drug] = {
                    "drug": drug,
                    "disease": hit.get("disease", ""),
                    "mechanism": hit.get("mechanism", ""),
                    "diseases": set(),
                    "sources": set(),
                    "confidence_sum": 0.0,
                    "hit_count": 0,
                    "evidence": [],
                }

            drug_map[drug]["diseases"].add(hit.get("disease", ""))
            drug_map[drug]["sources"].add(source)
            drug_map[drug]["confidence_sum"] += hit.get("confidence", 0.5) * weight
            drug_map[drug]["hit_count"] += 1
            drug_map[drug]["evidence"].append(
                {
                    "source": source,
                    "snippet": hit.get("evidence_snippet", ""),
                    "source_url": hit.get("source_url"),
                    "source_id": hit.get("source_id"),
                }
            )

    candidates = []
    for drug, data in drug_map.items():
        avg_confidence = data["confidence_sum"] / max(data["hit_count"], 1)
        multi_source_bonus = 0.1 if len(data["sources"]) >= 2 else 0
        deterministic_score = min(0.99, avg_confidence + multi_source_bonus)

        candidates.append(
            {
                "drug": drug,
                "disease": data["disease"],
                "mechanism": data["mechanism"],
                "diseases": list(data["diseases"]),
                "deterministic_score": deterministic_score,
                "llm_score": deterministic_score,
                "final_score": deterministic_score,
                "sources_count": len(data["sources"]),
                "evidence": data["evidence"],
            }
        )

    candidates.sort(key=lambda x: x["final_score"], reverse=True)
    return candidates
