MASTER_PLANNER_PROMPT = """
SYSTEM: You are the Master Planner for PharmaRep Master. Output ONLY valid JSON.

USER:
Query: "{query_text}"
MaxResults: {max_results}

TASK:
Return a JSON object with subtasks. Each subtask has: name, description,
fetch_instructions, worker_prompt, max_results, timeout_seconds.

Return ONLY this JSON structure (no extra text):

{{
  "query": "{query_text}",
  "subtasks": [
    {{"name": "papers", "description": "Search biomedical literature",
      "fetch_instructions": "", "worker_prompt": "",
      "max_results": {max_results}, "timeout_seconds": 10}},
    {{"name": "clinical_trials", "description": "Search clinical trials",
      "fetch_instructions": "", "worker_prompt": "",
      "max_results": {max_results}, "timeout_seconds": 10}},
    {{"name": "patents", "description": "Search patents",
      "fetch_instructions": "", "worker_prompt": "",
      "max_results": {max_results}, "timeout_seconds": 10}},
    {{"name": "market", "description": "Search market data",
      "fetch_instructions": "", "worker_prompt": "",
      "max_results": {max_results}, "timeout_seconds": 10}},
    {{"name": "internal_docs", "description": "Search internal docs",
      "fetch_instructions": "", "worker_prompt": "",
      "max_results": {max_results}, "timeout_seconds": 10}}
  ],
  "postprocess_instructions": "Use deterministic multi-source scoring",
  "output_format": "JSON with candidates"
}}
"""

WORKER_EXTRACTION_PROMPT = """
You are a biomedical extraction assistant. Extract drug mentions from text.

TEXT:
{raw_text}

Return ONLY a JSON array with objects:
drug, disease, mechanism, evidence_snippet, confidence,
source_url, source_id, notes.

If no drugs found, return: []

Example:
[{{"drug": "Memantine", "disease": "Alzheimer's disease",
   "mechanism": "NMDA antagonist", "evidence_snippet": "...",
   "confidence": 0.85, "source_url": null,
   "source_id": "PMID123", "notes": ""}}]
"""

LLM_RANKING_PROMPT = """
You are a ranking assistant. Re-score these candidates.

INPUT:
{candidates_json}

Return ONLY a JSON array with: candidate, llm_score, justification.

Example:
[{{"candidate": "Memantine", "llm_score": 0.92,
   "justification": "Strong evidence"}}]
"""
