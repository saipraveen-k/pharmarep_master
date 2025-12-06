import os
import time

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="PharmaRep Master",
    page_icon="💊",
    layout="wide",
)

st.title("💊 PharmaRep Master — Rapid Drug Repurposing")
st.write(
    "Type a research query (e.g., 'repurpose for Alzheimer's') and click Start. "
    "Results are research leads only — not clinical advice."
)

query = st.text_input("Research query", placeholder="e.g., repurpose for Alzheimer's disease")
max_results = st.number_input("Max results per worker", 5, 50, 10)

col1, col2 = st.columns([2, 1])
with col1:
    start_btn = st.button("🚀 Start Research", use_container_width=True)
with col2:
    clear_btn = st.button("Clear", use_container_width=True)

if clear_btn:
    st.session_state.clear()
    st.experimental_rerun()

if start_btn:
    if not query.strip():
        st.error("Please enter a query.")
    else:
        try:
            r = requests.post(
                f"{API_BASE_URL}/api/start_query",
                json={"query": query, "max_results": int(max_results), "include_internal_docs": False},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            st.session_state["query_id"] = data["query_id"]
            st.session_state["status"] = "running"
            st.success(f"Started query: {data['query_id']}")
        except Exception as e:
            st.error(f"Error starting query: {e}")

qid = st.session_state.get("query_id")
if qid:
    st.markdown("---")
    st.subheader("Pipeline Progress")
    prog_ph = st.empty()
    info_ph = st.empty()

    while True:
        try:
            s = requests.get(f"{API_BASE_URL}/api/status/{qid}", timeout=10)
            if s.status_code != 200:
                st.error("Status check failed.")
                break
            sj = s.json()
            pct = sj["progress_percent"]
            status = sj["status"]

            with prog_ph.container():
                st.progress(pct / 100)
                st.caption(f"Progress: {pct}%")

            with info_ph.container():
                if status == "running":
                    st.info("Pipeline running...")
                elif status == "completed":
                    st.success("Pipeline completed.")
                elif status == "failed":
                    st.error(f"Pipeline failed: {sj.get('error_message')}")
                    break

            if status != "running":
                break
            time.sleep(2)
        except Exception as e:
            st.error(f"Error polling status: {e}")
            break

    if st.session_state.get("status") == "running":
        st.session_state["status"] = status

    if st.session_state.get("status") == "completed":
        st.markdown("---")
        st.subheader("Top Candidates")
        try:
            r = requests.get(f"{API_BASE_URL}/api/candidates/{qid}", timeout=15)
            r.raise_for_status()
            data = r.json()
            cands = data.get("candidates", [])
            if not cands:
                st.info("No candidates found.")
            else:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total candidates", len(cands))
                with col2:
                    st.metric("Top score", f"{cands[0].get('final_score', 0.0):.3f}")
                with col3:
                    multi = sum(1 for c in cands if c.get("sources_count", 0) >= 2)
                    st.metric("Multi-source", multi)
                with col4:
                    avg = sum(c.get("final_score", 0.0) for c in cands) / len(cands)
                    st.metric("Average score", f"{avg:.3f}")

                for i, c in enumerate(cands[:10], 1):
                    with st.expander(
                        f"{i}. {c.get('drug','Unknown')} — Score {c.get('final_score',0.0):.3f} "
                        f"(sources: {c.get('sources_count',0)})"
                    ):
                        st.write(f"**Mechanism:** {c.get('mechanism') or 'N/A'}")
                        st.write(f"**Diseases:** {', '.join(c.get('diseases', [])) or 'N/A'}")
                        st.write(f"**Evidence count:** {len(c.get('evidence', []))}")
                        for ev in c.get("evidence", [])[:5]:
                            line = f"- [{ev.get('source')}] {ev.get('snippet','')[:200]}"
                            if ev.get("source_url"):
                                line += f"  \n  [{ev.get('source_url')}]({ev.get('source_url')})"
                            st.markdown(line)
                st.markdown("---")
                if st.button("📥 Download full PDF report"):
                    pr = requests.get(f"{API_BASE_URL}/api/report/{qid}", timeout=30)
                    if pr.status_code == 200:
                        st.download_button(
                            "Download PDF",
                            pr.content,
                            file_name=f"pharmarep_{qid}.pdf",
                            mime="application/pdf",
                        )
                    else:
                        st.error("Report not available yet.")
        except Exception as e:
            st.error(f"Error fetching candidates: {e}")
