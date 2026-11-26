#!/usr/bin/env python3
"""
PharmaRep Master - Streamlit Frontend
Provides interactive UI for drug repurposing queries.
Run: streamlit run app.py
"""

import streamlit as st
import requests
import time
import json
from typing import Dict, List
import os

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
POLLING_INTERVAL = 1  # seconds

# Page config
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
        background-color: #0F1419;
        color: #E8E8E8;
    }
    .candidate-card {
        background-color: #1A1F2E;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #2196F3;
        margin-bottom: 15px;
        margin-top: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("💊 PharmaRep Master")
st.markdown("**AI-Powered Drug Repurposing Research Platform**")
st.divider()

# Initialize session state
if "query_id" not in st.session_state:
    st.session_state.query_id = None
if "candidates" not in st.session_state:
    st.session_state.candidates = []
if "query_text" not in st.session_state:
    st.session_state.query_text = ""

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    max_results = st.slider("Max Results", 1, 20, 5, help="Maximum candidates to return")
    api_url = st.text_input("API Base URL", value=API_BASE_URL)

# Main interface - Two columns
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🔍 Query")
    query_text = st.text_area(
        "Enter medical condition or drug:",
        placeholder="e.g., Alzheimer's disease, Parkinson's, Cancer",
        height=100,
        key="query_input"
    )
    
    if st.button("🚀 Search", use_container_width=True, type="primary"):
        if not query_text.strip():
            st.error("Please enter a query")
        else:
            st.session_state.query_text = query_text
            st.session_state.candidates = []
            
            # Send query to API
            try:
                response = requests.post(
                    f"{api_url}/api/query",
                    json={
                        "query_text": query_text,
                        "max_results": max_results
                    },
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                st.session_state.query_id = data["query_id"]
                st.success(f"✅ Query started: {data['query_id'][:8]}")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ API Error: {str(e)}")
                st.info("Make sure backend is running: `cd backend && python main.py`")

with col2:
    st.subheader("📊 Pipeline Progress")
    
    if st.session_state.query_id:
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        # Poll for status
        max_attempts = 120  # 2 minutes with 1-second intervals
        attempt = 0
        completed = False
        
        while attempt < max_attempts and not completed:
            try:
                # Get status
                status_response = requests.get(
                    f"{api_url}/api/status/{st.session_state.query_id}",
                    timeout=5
                )
                status_response.raise_for_status()
                status_data = status_response.json()
                
                progress = status_data["progress"]
                is_completed = status_data["completed"]
                status_dict = status_data["status"]
                
                # Update progress bar
                with progress_placeholder.container():
                    st.progress(progress / 100, text=f"Progress: {progress}%")
                
                # Update status
                with status_placeholder.container():
                    if progress >= 100:
                        st.success("✅ Pipeline completed.", icon="✅")
                    else:
                        status_text = ", ".join([f"{k}: {v}" for k, v in status_dict.items()])
                        st.info(status_text, icon="⏳")
                
                # Get candidates if completed
                if is_completed or progress >= 100:
                    try:
                        candidates_response = requests.get(
                            f"{api_url}/api/candidates/{st.session_state.query_id}",
                            timeout=5
                        )
                        candidates_response.raise_for_status()
                        candidates_data = candidates_response.json()
                        st.session_state.candidates = candidates_data.get("candidates", [])
                        completed = True
                        break
                    except requests.exceptions.RequestException:
                        pass
                
                # Sleep before next poll
                time.sleep(POLLING_INTERVAL)
                attempt += 1
                
            except requests.exceptions.RequestException as e:
                st.error(f"Status error: {str(e)}")
                break

# Display candidates
st.divider()
st.subheader("🏆 Top Candidates")

if st.session_state.candidates:
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Candidates", len(st.session_state.candidates))
    with col2:
        avg_score = sum(c.get("final_score", 0) for c in st.session_state.candidates) / len(st.session_state.candidates)
        st.metric("Average Score", f"{avg_score:.3f}")
    with col3:
        st.metric("Top Score", f"{st.session_state.candidates[0].get('final_score', 0):.3f}")
    with col4:
        st.metric("Query", st.session_state.query_text[:20] + "..." if len(st.session_state.query_text) > 20 else st.session_state.query_text)
    
    st.divider()
    
    # Display each candidate
    for idx, candidate in enumerate(st.session_state.candidates, 1):
        # Use markdown to create card effect
        st.markdown(f"""
        <div class="candidate-card">
            <h3>{idx}. {candidate.get('drug', 'Unknown')}</h3>
            <p><strong>Mechanism:</strong> {candidate.get('mechanism', 'N/A')}</p>
            <p><strong>Diseases:</strong> {', '.join(candidate.get('diseases', []))}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Metrics in columns
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Final Score", f"{candidate.get('final_score', 0):.3f}")
        with col2:
            st.metric("Det. Score", f"{candidate.get('deterministic_score', 0):.3f}")
        with col3:
            st.metric("LLM Score", f"{candidate.get('llm_score', 0):.3f}")
        
        # Evidence section
        if candidate.get("evidence"):
            with st.expander(f"📋 Evidence ({len(candidate.get('evidence', []))})"):
                for i, evidence in enumerate(candidate.get("evidence", [])[:3], 1):
                    st.write(f"**{i}. {evidence.get('source', 'Unknown')}**")
                    st.caption(evidence.get('snippet', 'N/A'))
                    if evidence.get('source_id'):
                        st.caption(f"ID: {evidence.get('source_id')}")
        
        st.write("---")
    
    # Download results
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export as JSON
        json_data = json.dumps(st.session_state.candidates, indent=2)
        st.download_button(
            label="📥 Download Results (JSON)",
            data=json_data,
            file_name=f"pharmarep_results_{st.session_state.query_id[:8]}.json",
            mime="application/json"
        )
    
    with col2:
        # Download PDF Report
        try:
            pdf_response = requests.get(
                f"{api_url}/api/report/{st.session_state.query_id}",
                timeout=5
            )
            if pdf_response.status_code == 200:
                st.download_button(
                    label="📄 Download PDF Report",
                    data=pdf_response.content,
                    file_name=f"pharmarep_report_{st.session_state.query_id[:8]}.pdf",
                    mime="application/pdf"
                )
        except:
            st.info("📄 PDF generating...")
    
    with col3:
        st.metric("Query ID", st.session_state.query_id[:8])

else:
    if st.session_state.query_id:
        st.info("⏳ Waiting for candidates...")
    else:
        st.info("👈 Enter a query and click Search to get started")

# Footer
st.divider()
st.markdown("""
---
**PharmaRep Master v1.0** | AI-Powered Drug Repurposing
- 📚 Search: Papers, Clinical Trials, Patents, Market Data
- 🤖 Score: Deterministic + LLM Ranking
- 📄 Export: JSON, PDF Reports
""")