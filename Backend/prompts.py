# backend/prompts.py

MASTER_PLANNER_PROMPT = """
SYSTEM: You are the Master Planner for PharmaRep Master. Output ONLY valid JSON.

USER:
Query: "{query_text}"
MaxResults: {max_results}

TASK:
Return a JSON object:
{
  "query": "<same query>",
  "subtasks": [
    {"name": "papers", "fetch_instructions": "", "worker_prompt": "", "max_results": 10, "timeout_seconds": 10},
    {"name": "clinical_trials", "fetch_instructions": "", "worker_prompt": "", "max_results": 10, "timeout_seconds": 10},
    {"name": "patents", "fetch_instructions": "", "worker_prompt": "", "max_results": 10, "timeout_seconds": 10},
    {"name": "market", "fetch_instructions": "", "worker_prompt": "", "max_results": 10, "timeout_seconds": 10},
    {"name": "internal_docs", "fetch_instructions": "", "worker_prompt": "", "max_results": 10, "timeout_seconds": 10}
  ],
  "postprocess_instructions": "Use deterministic scoring + multi-source bonus.",
  "output_format": "JSON with query, candidates[], scores, evidence."
}
"""

WORKER_EXTRACTION_PROMPT = """
SYSTEM: You are a biomedical extraction assistant. Output JSON only (array).

Given the text, extract drug repurposing signals:
[
  {
    "drug": "<drug name>",
    "disease": "<disease/condition>",
    "mechanism": "<mechanism or ''>",
    "evidence_snippet": "<snippet up to 200 chars>",
    "confidence": 0.0-1.0,
    "source_url": "<url or null>",
    "source_id": "<id or 'mock'>",
    "notes": "<optional>"
  }
]

If no drugs, return [].

TEXT:
<<TEXT>>
{raw_text}
<<END_TEXT>>
"""

LLM_RANKING_PROMPT = """
SYSTEM: You are a ranking assistant. Output ONLY a JSON array.

INPUT:
{candidates_json}

TASK:
For each candidate output:
{"candidate": "<drug>", "llm_score": 0.0-1.0, "justification": "one line"}

Rules:
- Start from deterministic_score, adjust max ±0.2.
- Return only JSON array.
"""
