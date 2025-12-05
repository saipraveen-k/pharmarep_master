"""
frontend/app.py — Streamlit Dashboard for PharmaRep Master
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime
import os

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="PharmaRep Master",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: white;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #1a6c80;
    }
    .candidate-card {
        background-color: white;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        margin-bottom: 15px;
    }
    .score-excellent {
        color: #27ae60;
        font-weight: bold;
    }
    .score-good {
        color: #f39c12;
        font-weight: bold;
    }
    .score-fair {
        color: #e74c3c;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# Sidebar
# ============================================================================

st.sidebar.image("https://via.placeholder.com/200x60?text=PharmaRep+Master", use_column_width=True)
st.sidebar.markdown("---")

st.sidebar.header("🔬 About")
st.sidebar.info(
    """
    **PharmaRep Master** accelerates drug repurposing research using Agentic AI.
    
    Simultaneously searches:
    - 📄 Biomedical literature
    - 🏥 Clinical trials
    - 📋 Patents
    - 📊 Market data
    
    **Result:** 90 days → <7 days
    """
)

# ============================================================================
# Main Page
# ============================================================================

st.title("💊 PharmaRep Master")
st.markdown("**Rapid Drug Repurposing with Agentic AI** — Research lead time: 2-3 months → <1 week")

# ============================================================================
# Query Input Section
# ============================================================================

with st.container():
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input(
            "🔍 Enter Research Query",
            placeholder="e.g., 'Alzheimer's disease treatment', 'diabetes complications', 'cancer immunotherapy'",
            help="Describe the condition or therapeutic area you want to research"
        )
    
    with col2:
        max_results = st.number_input("Max Results", min_value=5, max_value=100, value=20)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        include_internal = st.checkbox("Include Internal Docs", value=False)
    
    if include_internal:
        with col2:
            uploaded_file = st.file_uploader("Upload PDF/DOCX", type=["pdf", "docx"])

st.markdown("---")

# ============================================================================
# Query Execution
# ============================================================================

query_id = st.session_state.get("query_id", None)
search_started = st.session_state.get("search_started", False)

if st.button("🚀 Start Research", key="start_button", use_container_width=True):
    if not query:
        st.error("Please enter a research query")
    else:
        # Start query via API
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/start_query",
                json={
                    "query": query,
                    "max_results": max_results,
                    "include_internal_docs": include_internal
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                st.session_state.query_id = data["query_id"]
                st.session_state.search_started = True
                st.success(f"✅ Research started (ID: {data['query_id'][:8]}...)")
                st.rerun()
            else:
                st.error(f"Error: {response.text}")
        except Exception as e:
            st.error(f"Connection error: {e}")

# ============================================================================
# Progress Tracking
# ============================================================================

if st.session_state.get("search_started", False) and st.session_state.get("query_id"):
    query_id = st.session_state.query_id
    
    with st.container():
        st.markdown("### 📊 Research Progress")
        
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        workers_placeholder = st.empty()
        
        # Poll status
        poll_interval = 2  # seconds
        max_polls = 300  # 10 minutes
        polls = 0
        
        while polls < max_polls:
            try:
                response = requests.get(f"{API_BASE_URL}/api/status/{query_id}", timeout=10)
                
                if response.status_code == 200:
                    status_data = response.json()
                    status = status_data["status"]
                    progress = status_data["progress_percent"]
                    workers = status_data.get("worker_status", {})
                    
                    # Update progress bar
                    with progress_placeholder.container():
                        st.progress(progress / 100)
                        st.caption(f"Progress: {progress}%")
                    
                    # Update status text
                    with status_placeholder.container():
                        if status == "running":
                            st.info(f"🔄 Research running... ({progress}% complete)")
                        elif status == "completed":
                            st.success("✅ Research completed!")
                            st.session_state.search_started = False
                            break
                        elif status == "failed":
                            st.error(f"❌ Research failed: {status_data.get('error_message', 'Unknown error')}")
                            st.session_state.search_started = False
                            break
                    
                    # Update worker status
                    with workers_placeholder.container():
                        worker_cols = st.columns(5)
                        worker_names = ["papers", "clinical_trials", "patents", "market", "internal_docs"]
                        
                        for i, worker_name in enumerate(worker_names):
                            worker_status = workers.get(worker_name, "pending")
                            icon = "✅" if worker_status == "done" else "⏳" if worker_status == "running" else "⏱️"
                            worker_cols[i].metric(worker_name, icon)
                    
                    if status != "running":
                        break
                    
                    time.sleep(poll_interval)
                    polls += 1
                else:
                    st.error(f"Status check failed: {response.status_code}")
                    break
                    
            except Exception as e:
                st.warning(f"Connection error: {e}")
                time.sleep(poll_interval)
                polls += 1

# ============================================================================
# Results Display
# ============================================================================

if st.session_state.get("query_id") and not st.session_state.get("search_started", False):
    query_id = st.session_state.query_id
    
    try:
        # Fetch candidates
        response = requests.get(f"{API_BASE_URL}/api/candidates/{query_id}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            candidates = data.get("candidates", [])
            
            if candidates:
                st.markdown("---")
                st.markdown("### 🎯 Top Drug Repurposing Candidates")
                
                # Metrics row
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Candidates", len(candidates))
                with col2:
                    top_score = candidates[0].get("final_score", 0) if candidates else 0
                    st.metric("Top Score", f"{top_score:.3f}")
                with col3:
                    multi_source = len([c for c in candidates if c.get("sources_count", 0) >= 2])
                    st.metric("Multi-Source", multi_source)
                with col4:
                    avg_score = sum(c.get("final_score", 0) for c in candidates) / len(candidates)
                    st.metric("Avg Score", f"{avg_score:.3f}")
                
                # Candidate cards
                for i, cand in enumerate(candidates[:10], 1):
                    drug = cand.get("drug", "Unknown")
                    score = cand.get("final_score", 0)
                    sources = cand.get("sources_count", 0)
                    mechanism = cand.get("mechanism", "N/A")
                    evidence = cand.get("evidence", [])
                    
                    # Score color
                    if score >= 0.8:
                        score_class = "score-excellent"
                    elif score >= 0.6:
                        score_class = "score-good"
                    else:
                        score_class = "score-fair"
                    
                    with st.expander(f"**{i}. {drug}** — Score: {score:.3f} | Sources: {sources}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"**Mechanism:** {mechanism}")
                            st.markdown(f"**Evidence Count:** {len(evidence)}")
                            
                            if evidence:
                                st.markdown("**Evidence Sources:**")
                                for ev in evidence[:3]:
                                    source = ev.get("source", "Unknown")
                                    snippet = ev.get("snippet", "No snippet")[:100]
                                    confidence = ev.get("confidence", 0)
                                    st.markdown(f"• [{source}] {snippet}... (confidence: {confidence:.2f})")
                        
                        with col2:
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button("🚩 Flag", key=f"flag_{i}"):
                                    st.info(f"Flagged {drug} for human review")
                            with col_b:
                                if st.button("📋 Details", key=f"details_{i}"):
                                    st.json(cand)
                
                # Download PDF
                st.markdown("---")
                col1, col2 = st.columns([2, 1])
                with col1:
                    if st.button("📥 Download Full PDF Report", use_container_width=True):
                        try:
                            response = requests.get(f"{API_BASE_URL}/api/report/{query_id}")
                            if response.status_code == 200:
                                st.download_button(
                                    label="Download PDF",
                                    data=response.content,
                                    file_name=f"pharmarep_{query_id[:8]}.pdf",
                                    mime="application/pdf"
                                )
                        except Exception as e:
                            st.error(f"Error downloading: {e}")
            else:
                st.info("No candidates found. Try a different query.")
        else:
            st.error("Error fetching results")
            
    except Exception as e:
        st.error(f"Error: {e}")

# ============================================================================
# Footer
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 12px;'>
    <p>PharmaRep Master v1.0 | Powered by Agentic AI</p>
    <p>Research lead: 2-3 months → <1 week | Candidates identified: 10x more viable options</p>
</div>
""", unsafe_allow_html=True)

---

requirements.txt — Python Dependencies
"""

# Core
fastapi==0.104.1
uvicorn==0.24.0
streamlit==1.28.1

# APIs & Data
aiohttp==3.9.1
requests==2.31.0

# OpenAI
openai==1.3.0

# Database
sqlite3

# PDF Generation
reportlab==4.0.7

# ML/Data
numpy==1.24.3
pandas==1.5.3

# Environment
python-dotenv==1.0.0
pydantic==2.4.2

# Async
asyncio

# Utilities
python-multipart==0.0.6
