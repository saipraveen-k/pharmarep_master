import streamlit as st
from typing import List, Dict

def render_candidate_card(index: int, cand: Dict):
    drug = cand.get("drug", "Unknown")
    score = cand.get("final_score", 0.0)
    sources = cand.get("sources_count", 0)
    mechanism = cand.get("mechanism", "N/A")
    evidence: List[Dict] = cand.get("evidence", [])

    with st.expander(f"{index}. {drug} — Score: {score:.3f} | Sources: {sources}"):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"**Mechanism:** {mechanism}")
            st.markdown(f"**Evidence Count:** {len(evidence)}")
            if evidence:
                st.markdown("**Evidence:**")
                for ev in evidence[:3]:
                    src = ev.get("source", "src")
                    snippet = ev.get("snippet", "")[:160]
                    conf = ev.get("confidence", 0.0)
                    url = ev.get("source_url")
                    line = f"- [{src}] {snippet} (confidence: {conf:.2f})"
                    if url:
                        line += f"  \n  [{url}]({url})"
                    st.markdown(line)
        with col2:
            st.button("🚩 Flag for review", key=f"flag_{index}")
            with st.popover("Raw JSON"):
                st.json(cand)
