from typing import List, Dict
import json
import os
import openai

from .prompts import LLM_RANKING_PROMPT

async def llm_rerank_candidates(candidates: List[Dict]) -> List[Dict]:
    if not candidates:
        return candidates

    openai.api_key = os.getenv("OPENAI_API_KEY")

    top = sorted(
        candidates,
        key=lambda c: c.get("deterministic_score", 0.0),
        reverse=True,
    )[:10]

    prompt = LLM_RANKING_PROMPT.format(
        candidates_json=json.dumps(top, indent=2)
    )

    resp = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1500,
    )

    ranking_text = resp.choices[0].message.content.strip()
    ranking = json.loads(ranking_text)
    ranking_map = {r["candidate"]: r for r in ranking}

    for c in candidates:
        name = c.get("drug")
        base = c.get("deterministic_score", 0.0)
        if name in ranking_map:
            r = ranking_map[name]
            llm_score = float(r.get("llm_score", base))
            c["llm_score"] = llm_score
            c["ranking_justification"] = r.get("justification", "")
            c["final_score"] = 0.6 * base + 0.4 * llm_score
        else:
            c["llm_score"] = base
            c["final_score"] = base

    candidates.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
    return candidates
