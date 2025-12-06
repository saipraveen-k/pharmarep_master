# backend/ranking.py
from typing import List, Dict
import json
import os
import openai

from prompts import LLM_RANKING_PROMPT


async def llm_rerank_candidates(candidates: List[Dict]) -> List[Dict]:
    if not candidates:
        return candidates

    openai.api_key = os.getenv("OPENAI_API_KEY")

    top = sorted(candidates, key=lambda c: c["deterministic_score"], reverse=True)[:10]
    prompt = LLM_RANKING_PROMPT.format(candidates_json=json.dumps(top, indent=2))

    resp = openai.ChatCompletion.create(
        model=os.getenv("OPENAI_MODEL_RANKING", "gpt-4.1-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1500,
    )
    text = resp.choices[0].message.content.strip()
    arr = json.loads(text)
    mp = {r["candidate"]: r for r in arr}

    for c in candidates:
        base = c["deterministic_score"]
        r = mp.get(c["drug"])
        if r:
            llm_score = float(r["llm_score"])
            c["llm_score"] = llm_score
            c["ranking_justification"] = r.get("justification", "")
            c["final_score"] = 0.6 * base + 0.4 * llm_score
        else:
            c["llm_score"] = base
            c["final_score"] = base

    candidates.sort(key=lambda x: x["final_score"], reverse=True)
    return candidates
