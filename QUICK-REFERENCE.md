"""
Quick Reference Guide — PharmaRep Master Commands & Architecture
"""

# ============================================================================
# 🏗️ SYSTEM ARCHITECTURE
# ============================================================================

ARCHITECTURE_ASCII = """
┌─────────────────────────────────────────────────────────────────────────┐
│                          PHARMAREP MASTER SYSTEM                        │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│   FRONTEND UI    │
│   (Streamlit)    │
│  :8501           │
└────────┬─────────┘
         │
    HTTP │ (JSON)
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI BACKEND                                │
│                         (:8000 /docs)                                   │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  POST /api/start_query                                                 │
│     ↓                                                                   │
│  [Background Task]                                                     │
│     ↓                                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │              MASTER ORCHESTRATOR                               │  │
│  ├─────────────────────────────────────────────────────────────────┤  │
│  │                                                                 │  │
│  │  1. Call Master Planner LLM                                    │  │
│  │     Input: user_query                                          │  │
│  │     Output: {subtasks[], postprocess_instructions}             │  │
│  │                                                                 │  │
│  │  2. Spawn Worker Agents (PARALLEL)                             │  │
│  │                                                                 │  │
│  │     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │  │
│  │     │ PapersWorker │  │TrialsWorker  │  │PatentsWorker │       │  │
│  │     │              │  │              │  │              │       │  │
│  │     │Europe PMC    │  │Clinical      │  │PatentsView   │       │  │
│  │     │+ PubMed      │  │trials.gov    │  │+ Google      │       │  │
│  │     └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │  │
│  │            │                 │                 │                │  │
│  │     (Mocked) ┌──────────────┐                 │                │  │
│  │            │ MarketWorker   │                 │                │  │
│  │            │                │                 │                │  │
│  │            │DrugBank/       │                 │                │  │
│  │            │ChEMBL/News     │                 │                │  │
│  │            └────────┬────────┘                 │                │  │
│  │                     │                          │                │  │
│  │  Each worker:                                  │                │  │
│  │    a) Fetch raw items (API)                   │                │  │
│  │    b) For each item: Call Worker Extraction LLM                │  │
│  │    c) LLM extracts: {drug, disease, mechanism, ...}            │  │
│  │    d) Return hits list                        │                │  │
│  │                     │                          │                │  │
│  │                     └─────────┬────────────────┘                │  │
│  │                               │                                │  │
│  │  3. Aggregator & Scoring                                       │  │
│  │     - Group hits by drug (normalized)                          │  │
│  │     - Compute deterministic_score                              │  │
│  │     - Apply multisource bonus                                  │  │
│  │       Result: [{drug, score, evidence[], sources_count}]       │  │
│  │                               │                                │  │
│  │  4. LLM Re-Ranking (Optional)                                  │  │
│  │     - Re-score top 10 candidates                               │  │
│  │     - Compute final_score = 0.6*det + 0.4*llm                 │  │
│  │       Result: same + llm_score, justification                  │  │
│  │                               │                                │  │
│  │  5. PDF Generation                                             │  │
│  │     - Call LLM summarizer                                      │  │
│  │     - Generate professional report                             │  │
│  │     - Save to /reports/{query_id}.pdf                          │  │
│  │                               │                                │  │
│  │                               ▼                                │  │
│  │  [Result saved to DB + Status: COMPLETED]                     │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  GET /api/status/{query_id}     ← Poll for progress                   │
│  GET /api/candidates/{query_id} ← Fetch results                       │
│  GET /api/report/{query_id}     ← Download PDF                        │
│                                                                         │
└──────────────────────────────────────────────────────────────────────────┘
         │
    HTTP │ (JSON)
         │
         ▼
┌──────────────────────────────────────┐
│        SQLITE DATABASE               │
│                                      │
│  • queries table                     │
│  • hits table (raw extractions)      │
│  • candidates table                  │
│  • results table                     │
│  • human_reviews table               │
└──────────────────────────────────────┘
"""

# ============================================================================
# 🚀 QUICK START (Copy-Paste)
# ============================================================================

QUICK_START = """
# 1. Clone & Setup
git clone <repo>
cd pharmarep-master
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Create .env
cat > .env << EOF
OPENAI_API_KEY=sk-your-api-key
WORKER_TIMEOUT_SECONDS=25
MAX_RESULTS_PER_WORKER=20
REPORTS_DIR=./reports
DB_PATH=./pharmarep.db
EOF

# 3. Initialize DB
python backend/db.py

# 4. Terminal 1 - Start Backend
cd backend
python main.py
# → FastAPI on http://localhost:8000

# 5. Terminal 2 - Start Frontend
cd frontend
streamlit run app.py
# → Streamlit on http://localhost:8501

# 6. Open browser
# → http://localhost:8501
# → Enter query: "Alzheimer's disease treatment"
# → Click "Start Research"
# → Watch progress
# → Download PDF when done!
"""

# ============================================================================
# 📊 SCORING FORMULA (Reference)
# ============================================================================

SCORING_FORMULA = """
DETERMINISTIC SCORING:

Step 1: Extract source-specific confidences
   clinical_confidences = [0.9, 0.85, ...]    from trials
   paper_confidences = [0.8, 0.75, ...]       from papers
   patent_confidences = [0.6, ...]            from patents
   market_confidences = [0.7, ...]            from market

Step 2: Compute weighted components
   clinical_component = 0.5 × (1.0 if positive_outcome else 0.5 × max(clinical_conf))
   paper_component = 0.3 × avg(paper_conf)
   patent_component = 0.1 × max(patent_conf)
   market_component = 0.1 × max(market_conf)

Step 3: Base score
   base_score = clinical_component + paper_component + patent_component + market_component

Step 4: Apply multi-source bonus
   distinct_sources = len(set(sources))  # e.g., {trials, papers, patents} = 3
   multisource_bonus = 1.0 + 0.05 × (distinct_sources - 1)
   
   Examples:
   - 1 source: 1.0 + 0.05×0 = 1.0   (no bonus)
   - 2 sources: 1.0 + 0.05×1 = 1.05 (+5%)
   - 3 sources: 1.0 + 0.05×2 = 1.10 (+10%)
   - 4 sources: 1.0 + 0.05×3 = 1.15 (+15%)

Step 5: Final score
   final_score = base_score × multisource_bonus
   if final_score > 1.0: final_score = 1.0  (cap at 1.0)

Example Calculation:
─────────────────────
Drug: "Donepezil" for "Alzheimer's"

Sources:
✓ Clinical trial NCT1234: "improved cognition" → confidence 0.92 (marked as positive)
✓ Paper PMID5678: abstract mentions mechanism → confidence 0.80
✓ Patent US10123456: describes use → confidence 0.65
✓ Market data: FDA approved status → confidence 0.75

Components:
  clinical (0.5): 1.0 if positive = YES → 0.5 × 1.0 = 0.50
  paper (0.3): avg([0.80]) = 0.80 → 0.3 × 0.80 = 0.24
  patent (0.1): max([0.65]) = 0.65 → 0.1 × 0.65 = 0.065
  market (0.1): max([0.75]) = 0.75 → 0.1 × 0.75 = 0.075

Base score: 0.50 + 0.24 + 0.065 + 0.075 = 0.88

Multisource: 4 distinct sources → 1.0 + 0.05×3 = 1.15

Final: 0.88 × 1.15 = 1.012 → CAPPED AT 1.0

RESULT: Donepezil scores 1.0 (maximum confidence) ✨
"""

# ============================================================================
# 🔌 API CHEAT SHEET
# ============================================================================

API_CHEAT_SHEET = """
BASE URL: http://localhost:8000

─────────────────────────────────────────────────────────────────

1. START QUERY
   POST /api/start_query
   
   Request:
   {
     "query": "Alzheimer's disease treatment",
     "max_results": 20,
     "include_internal_docs": false
   }
   
   Response:
   {
     "query_id": "a1b2c3d4-...",
     "status": "running",
     "message": "Search initiated..."
   }

─────────────────────────────────────────────────────────────────

2. CHECK STATUS (Poll every 2 seconds)
   GET /api/status/{query_id}
   
   Example: GET /api/status/a1b2c3d4
   
   Response:
   {
     "query_id": "a1b2c3d4",
     "status": "running|completed|failed",
     "progress_percent": 45,
     "worker_status": {
       "papers": "done",
       "clinical_trials": "running",
       "patents": "pending",
       "market": "done",
       "internal_docs": "pending"
     },
     "error_message": null,
     "timestamp": "2024-01-15T10:30:45.123Z"
   }

─────────────────────────────────────────────────────────────────

3. GET CANDIDATES (when status == "completed")
   GET /api/candidates/{query_id}
   
   Response:
   {
     "query_id": "a1b2c3d4",
     "candidates": [
       {
         "drug": "Donepezil",
         "deterministic_score": 0.880,
         "llm_score": 0.85,
         "final_score": 0.868,
         "sources_count": 4,
         "mechanism": "Acetylcholinesterase inhibitor",
         "evidence": [
           {
             "source": "clinical_trials",
             "source_id": "NCT1234",
             "source_url": "https://clinicaltrials.gov/study/NCT1234",
             "snippet": "memantine improved cognition in moderate Alzheimer's disease",
             "confidence": 0.92
           },
           {
             "source": "papers",
             "source_id": "PMID5678",
             "source_url": "https://europepmc.org/article/PMC/5678",
             "snippet": "NMDA antagonist mechanism well-established",
             "confidence": 0.80
           }
         ],
         "diseases": ["Alzheimer's disease", "Memory loss"],
         "aggregated_meta": {
           "sources": ["clinical_trials", "papers", "patents", "market"],
           "hit_count": 12,
           "diseases": ["Alzheimer's disease"],
           "mechanisms": ["Acetylcholinesterase inhibitor"]
         }
       }
       // ... more candidates
     ]
   }

─────────────────────────────────────────────────────────────────

4. DOWNLOAD PDF REPORT
   GET /api/report/{query_id}
   
   Returns: PDF binary file
   Content-Type: application/pdf
   Filename: pharmarep_a1b2c3d4.pdf

─────────────────────────────────────────────────────────────────

5. FLAG FOR HUMAN REVIEW
   POST /api/review/{query_id}/{candidate}
   
   Example: POST /api/review/a1b2c3d4/Donepezil
   
   Response:
   {
     "status": "flagged",
     "candidate": "Donepezil",
     "query_id": "a1b2c3d4",
     "timestamp": "2024-01-15T10:35:20Z",
     "message": "Candidate flagged for human review"
   }

─────────────────────────────────────────────────────────────────

6. HEALTH CHECK
   GET /api/health
   
   Response:
   {
     "status": "healthy",
     "timestamp": "2024-01-15T10:30:00Z"
   }

─────────────────────────────────────────────────────────────────

7. API DOCUMENTATION
   GET http://localhost:8000/docs
   
   (Swagger UI - interactive API explorer)
"""

# ============================================================================
# 🧪 TESTING EXAMPLES
# ============================================================================

TESTING_EXAMPLES = """
# Test 1: Basic End-to-End
curl -X POST http://localhost:8000/api/start_query \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "Alzheimer disease treatment repurposing",
    "max_results": 20
  }'

Response: {"query_id": "abc123", "status": "running"}

# Poll status every 2 seconds
for i in {1..150}; do
  curl http://localhost:8000/api/status/abc123 | jq .progress_percent
  sleep 2
done

# Get results when done
curl http://localhost:8000/api/candidates/abc123 | jq '.candidates | length'
# Should output: number of candidates (typically 15-30)

# Download PDF
curl http://localhost:8000/api/report/abc123 -o report.pdf
file report.pdf
# Should output: PDF document, version 1.4

─────────────────────────────────────────────────────────────────

# Test 2: Python Script
import requests
import time

BASE_URL = "http://localhost:8000"

# Start
r = requests.post(f"{BASE_URL}/api/start_query", json={
    "query": "Parkinson disease dopamine",
    "max_results": 20
})
query_id = r.json()["query_id"]

# Poll
while True:
    r = requests.get(f"{BASE_URL}/api/status/{query_id}")
    status = r.json()
    print(f"Progress: {status['progress_percent']}%")
    if status["status"] == "completed":
        break
    time.sleep(2)

# Get results
r = requests.get(f"{BASE_URL}/api/candidates/{query_id}")
candidates = r.json()["candidates"]
print(f"Found {len(candidates)} candidates")
print(f"Top: {candidates[0]['drug']} (score: {candidates[0]['final_score']:.3f})")

# Download
r = requests.get(f"{BASE_URL}/api/report/{query_id}")
with open("report.pdf", "wb") as f:
    f.write(r.content)
print("Report saved!")

─────────────────────────────────────────────────────────────────

# Test 3: Performance
# Query: "Parkinson disease"
# Expected: <7 seconds total time
# Expected candidates: 20-40
# Expected top score: 0.7-0.95

# Query: "rare disease orphan drug"
# Expected: slower (less data available)
# Expected: 5-15 candidates
"""

# ============================================================================
# 📋 FILE STRUCTURE
# ============================================================================

FILE_STRUCTURE = """
pharmarep-master/
│
├── README.md                          # Overview
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment template
│
├── backend/
│   ├── main.py                        # FastAPI app + endpoints
│   ├── db.py                          # SQLite schema & ops
│   ├── orchestrator.py                # Master agent logic
│   ├── aggregator.py                  # Scoring formula
│   ├── ranking.py                     # LLM re-ranking
│   ├── pdf_gen.py                     # Report generation
│   ├── prompts.py                     # ALL LLM prompts
│   │
│   └── workers/
│       ├── __init__.py
│       ├── base.py                    # Abstract worker
│       ├── papers.py                  # Europe PMC + PubMed
│       ├── trials.py                  # ClinicalTrials.gov
│       ├── patents.py                 # PatentsView (mocked)
│       └── market.py                  # Market data (mocked)
│
├── frontend/
│   ├── app.py                         # Streamlit dashboard
│   ├── components.py                  # Reusable UI components
│   │
│   └── assets/
│       └── style.css                  # Custom styling
│
├── tests/
│   ├── test_aggregator.py
│   ├── test_orchestrator.py
│   ├── test_workers.py
│   └── test_e2e.py
│
└── reports/                           # Generated PDFs (auto-created)
    └── {query_id}.pdf
"""

# ============================================================================
# 🎯 SUCCESS CRITERIA
# ============================================================================

SUCCESS_CRITERIA = """
✅ SYSTEM IS WORKING IF:

1. Backend starts without errors
   → python backend/main.py
   → Uvicorn running on 0.0.0.0:8000
   → FastAPI docs at http://localhost:8000/docs

2. Frontend starts without errors
   → streamlit run frontend/app.py
   → http://localhost:8501 loads

3. Can submit a query
   → Enter "Alzheimer's disease"
   → Click "Start Research"
   → See "Research started (ID: ...)" message

4. Status updates show progress
   → Progress bar moves 0% → 100%
   → Worker status changes: pending → running → done

5. Results appear after completion
   → Candidates displayed with scores
   → Evidence snippets shown
   → Download PDF button works

6. PDF report is generated
   → Professional looking document
   → Title, executive summary, top candidates table
   → Evidence references
   → Methodology & disclaimer
"""

print(ARCHITECTURE_ASCII)
print(QUICK_START)
print(SCORING_FORMULA)
print(API_CHEAT_SHEET)
print(TESTING_EXAMPLES)
print(FILE_STRUCTURE)
print(SUCCESS_CRITERIA)
