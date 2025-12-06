# backend/db.py
import sqlite3
import json
import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)
DB_PATH = os.getenv("DB_PATH", "./pharmarep.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            query_id TEXT PRIMARY KEY,
            query_text TEXT NOT NULL,
            max_results INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS hits (
            hit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id TEXT NOT NULL,
            source TEXT NOT NULL,
            drug TEXT NOT NULL,
            disease TEXT,
            mechanism TEXT,
            evidence_snippet TEXT,
            confidence REAL,
            source_url TEXT,
            source_id TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id TEXT NOT NULL,
            drug TEXT NOT NULL,
            deterministic_score REAL,
            llm_score REAL,
            final_score REAL,
            sources_count INTEGER,
            mechanism TEXT,
            evidence_json TEXT,
            aggregated_meta_json TEXT,
            human_review_flag INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id TEXT NOT NULL UNIQUE,
            result_json TEXT NOT NULL,
            pdf_path TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    logger.info(f"DB initialized at {DB_PATH}")


def save_query(query_id: str, query_text: str, max_results: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO queries (query_id, query_text, max_results) VALUES (?, ?, ?)",
        (query_id, query_text, max_results),
    )
    conn.commit()
    conn.close()


def save_hits(query_id: str, hits: List[Dict]):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for h in hits:
        c.execute(
            """
            INSERT INTO hits
            (query_id, source, drug, disease, mechanism, evidence_snippet,
             confidence, source_url, source_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                query_id,
                h.get("source", ""),
                h.get("drug", ""),
                h.get("disease", ""),
                h.get("mechanism", ""),
                h.get("evidence_snippet", ""),
                h.get("confidence", 0.5),
                h.get("source_url"),
                h.get("source_id", ""),
                h.get("notes", ""),
            ),
        )
    conn.commit()
    conn.close()


def save_candidates(query_id: str, cands: List[Dict]):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for cand in cands:
        c.execute(
            """
            INSERT INTO candidates
            (query_id, drug, deterministic_score, llm_score, final_score,
             sources_count, mechanism, evidence_json, aggregated_meta_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                query_id,
                cand["drug"],
                cand["deterministic_score"],
                cand.get("llm_score"),
                cand["final_score"],
                cand["sources_count"],
                cand.get("mechanism", ""),
                json.dumps(cand.get("evidence", [])),
                json.dumps(cand.get("aggregated_meta", {})),
            ),
        )
    conn.commit()
    conn.close()


def save_result(query_id: str, result: Dict):
    all_hits = []
    for src, hits in result.get("worker_results", {}).items():
        for h in hits:
            all_hits.append(h)
    save_hits(query_id, all_hits)
    save_candidates(query_id, result.get("candidates", []))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO results (query_id, result_json, pdf_path) VALUES (?, ?, ?)",
        (query_id, json.dumps(result), ""),
    )
    conn.commit()
    conn.close()


def get_candidates_by_query_id(query_id: str) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT * FROM candidates WHERE query_id = ? ORDER BY final_score DESC",
        (query_id,),
    )
    rows = c.fetchall()
    conn.close()
    out: List[Dict] = []
    for r in rows:
        d = dict(r)
        d["evidence"] = json.loads(d.get("evidence_json", "[]"))
        d["aggregated_meta"] = json.loads(d.get("aggregated_meta_json", "{}"))
        out.append(d)
    return out
