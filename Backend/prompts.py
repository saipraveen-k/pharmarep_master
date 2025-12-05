MASTER_PLANNER_PROMPT = """
SYSTEM: You are the Master Planner for PharmaRep Master. Output ONLY valid JSON.

USER:
Query: "{query_text}"
MaxResults: {max_results}

TASK:
Decompose the query into these subtasks: papers, clinical_trials, patents, market, internal_docs.
For each subtask produce:
- name
- description
- fetch_instructions
- worker_prompt
- max_results
- timeout_seconds

Also produce:
- postprocess_instructions: exact scoring formula
- output_format: description of final aggregated JSON schema

Return ONLY a JSON object:
{
  "query": "<original>",
  "subtasks": [
    {
      "name": "papers",
      "description": "...",
      "fetch_instructions": "...",
      "worker_prompt": "...",
      "max_results": 20,
      "timeout_seconds": 25
    },
    ...
  ],
  "postprocess_instructions": "...",
  "output_format": "..."
}
"""

WORKER_EXTRACTION_PROMPT = """
SYSTEM: You are a biomedical extraction assistant. Output JSON only (a valid JSON array).

INSTRUCTION:
Given the following text, extract all drug mentions and return an array of objects:
{
 "drug": "anonical drug>",
 "disease": "dition/disease mentioned or inferred>",
 "mechanism": "<one-line mechanism or empty string>",
 "evidence_snippet": "<direct quote up to 200 chars>",
 "confidence": <0.0-1.0>,
 "source_url": "<url or null>",
 "source_id": "<pmid/NCT/patent id or filename>",
 "notes": "<optional short note>"
}

Rules:
- Use canonical drug names when possible.
- If you cannot find a mechanism, set it to empty string.
- Do NOT invent URLs. If none present, set source_url to null.
- Confidence is your estimate of evidence strength.
- If no drugs found, return [].
- Output ONLY a JSON array, no extra text.

TEXT:
<<TEXT>>
{raw_text}
<<END_TEXT>>
"""

LLM_RANKING_PROMPT = """
SYSTEM: You are a ranking assistant. Output ONLY a valid JSON array.

INPUT:
A JSON array of candidate objects with deterministic_score and evidence:
{candidates_json}

TASK:
For each candidate produce:
{
  "candidate": "<drug>",
  "llm_score": 0.0-1.0,
  "justification": "one-line reason"
}

Rules:
- llm_score should start from deterministic_score and adjust by at most ±0.2.
- Consider recency, mechanism plausibility, and study design quality.
- Return ONLY the JSON array.
"""

PDF_SUMMARIZER_PROMPT = """
SYSTEM: You are a technical summarizer. Output JSON only.

INPUT:
Aggregated JSON with top candidates, scores, and evidence.

TASK:
Produce:
{
 "title": "PharmaRep Master — Report: <query>",
 "executive_summary": "<1 short paragraph>",
 "top_candidates_text": [
   {
     "candidate": "<drug>",
     "summary": "one short paragraph",
     "score": <0-1>,
     "top_evidence": ["snippet1", "snippet2"]
   }
 ],
 "methodology": "<short description>",
 "data_sources": ["..."],
 "limitations_disclaimer": "<short medical disclaimer>"
}
"""
