# PharmaRep Master — Setup & Implementation Guide

## 🚀 Quick Start (5 minutes)

### 1. Clone & Setup Environment
```bash
git clone <your-repo>
cd pharmarep-master
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Variables (.env)
```
OPENAI_API_KEY=sk-...
WORKER_TIMEOUT_SECONDS=25
MAX_RESULTS_PER_WORKER=20
REPORTS_DIR=./reports
DB_PATH=./pharmarep.db
STREAMLIT_THEME=dark
```

### 3. Initialize Database
```bash
python backend/db.py
# Creates tables: queries, hits, candidates, results
```

### 4. Run Backend
```bash
cd backend
python main.py
# FastAPI runs on http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 5. Run Streamlit Frontend (new terminal)
```bash
cd frontend
streamlit run app.py
# Streamlit runs on http://localhost:8501
```

---

## 📁 Project Structure

```
pharmarep-master/
├── backend/
│   ├── main.py                 # FastAPI app + endpoints
│   ├── db.py                   # SQLite schema + operations
│   ├── orchestrator.py         # Master planner & orchestration
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── base.py             # Worker base class
│   │   ├── papers.py           # Europe PMC + extraction
│   │   ├── trials.py           # ClinicalTrials.gov + extraction
│   │   ├── patents.py          # Patents API + extraction
│   │   ├── market.py           # Market data + extraction
│   │   └── internal_docs.py    # PDF/DOCX text extraction
│   ├── aggregator.py           # Deterministic scoring + grouping
│   ├── ranking.py              # LLM-assisted re-ranking
│   ├── pdf_gen.py              # PDF report generation
│   └── prompts.py              # All LLM prompts (centralized)
├── frontend/
│   ├── app.py                  # Streamlit UI
│   ├── components.py           # Reusable UI components
│   └── assets/
│       └── style.css           # Custom styling
├── tests/
│   ├── test_orchestrator.py
│   ├── test_aggregator.py
│   ├── test_workers.py
│   └── test_e2e.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔧 Implementation Roadmap

### Phase 1: Foundation (Complete first)
- [x] DB schema
- [x] FastAPI skeleton
- [x] Master planner LLM integration
- [x] Orchestrator with async workers
- [x] Mocked workers (for testing)

### Phase 2: Real Fetchers (Do next)
- [ ] Europe PMC fetcher + Worker extraction
- [ ] ClinicalTrials.gov fetcher + Worker extraction
- [ ] Patents API fetcher
- [ ] Market data fetcher
- [ ] Internal docs parser

### Phase 3: Intelligence Layer
- [ ] Aggregator + deterministic scoring
- [ ] LLM ranking (second pass)
- [ ] Score combination (final_score)

### Phase 4: UI & Output
- [ ] Streamlit candidate cards
- [ ] Progress tracking
- [ ] PDF generation + download
- [ ] Human review flagging

### Phase 5: Polish & Testing
- [ ] Unit tests (pytest)
- [ ] Integration tests
- [ ] Gold dataset evaluation
- [ ] Performance optimization

---

## 📋 Key Prompts (Reference)

All prompts are in `backend/prompts.py` and include:

1. **Master Planner** → decompose query into subtasks
2. **Worker Extraction** → extract drugs from raw text
3. **Aggregator** → deterministic scoring formula
4. **LLM Ranking** → re-rank with LLM
5. **PDF Summarizer** → generate report sections

---

## ✅ Testing the System

### Quick Test (Mocked)
```bash
python -m pytest tests/test_orchestrator.py -v
# Should pass with mocked workers
```

### End-to-End Test
```bash
curl -X POST http://localhost:8000/api/start_query \
  -H "Content-Type: application/json" \
  -d '{"query": "Alzheimer disease treatment repurposing", "max_results": 20}'
# Returns: {"query_id": "abc123", "status": "running"}

curl http://localhost:8000/api/status/abc123
# Returns: progress + worker status

curl http://localhost:8000/api/report/abc123
# Returns: PDF binary
```

---

## 🎯 Next Steps (Choose One)

1. **Get workers running** → I'll provide `workers/papers.py` with Europe PMC integration
2. **Build the Streamlit UI** → I'll create full candidate cards + progress UI
3. **Generate slides** → I'll create a professional pitch deck
4. **Run end-to-end test** → Full working demo with mocked data

Choose which you want to build next!
