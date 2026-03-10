import sqlite3
import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)
DB_PATH = "./pharmarep.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            query_id TEXT PRIMARY KEY,
            query_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id TEXT NOT NULL,
            drug TEXT,
            disease TEXT,
            mechanism TEXT,
            evidence_snippet TEXT,
            confidence REAL,
            source TEXT,
            source_url TEXT,
            source_id TEXT,
            FOREIGN KEY (query_id) REFERENCES queries(query_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id TEXT NOT NULL,
            drug TEXT,
            deterministic_score REAL,
            llm_score REAL,
            final_score REAL,
            mechanism TEXT,
            diseases_json TEXT,
            sources_count INTEGER,
            evidence_count INTEGER,
            evidence_json TEXT,
            FOREIGN KEY (query_id) REFERENCES queries(query_id)
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info(f"DB initialized at {DB_PATH}")

def save_result(query_id: str, result: Dict):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT OR REPLACE INTO queries (query_id, query_text) VALUES (?, ?)",
            (query_id, result.get("query", ""))
        )
        
        worker_results = result.get("worker_results", {})
        for source, hits in worker_results.items():
            for hit in hits:
                cursor.execute("""
                    INSERT INTO hits (query_id, drug, disease, mechanism, evidence_snippet, 
                                     confidence, source, source_url, source_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    query_id,
                    hit.get("drug"),
                    hit.get("disease"),
                    hit.get("mechanism"),
                    hit.get("evidence_snippet"),
                    hit.get("confidence"),
                    hit.get("source"),
                    hit.get("source_url"),
                    hit.get("source_id")
                ))
        
        candidates = result.get("candidates", [])
        for c in candidates:
            cursor.execute("""
                INSERT INTO candidates (query_id, drug, deterministic_score, llm_score, 
                                       final_score, mechanism, diseases_json, sources_count, 
                                       evidence_count, evidence_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                query_id,
                c.get("drug"),
                c.get("deterministic_score"),
                c.get("llm_score"),
                c.get("final_score"),
                c.get("mechanism"),
                json.dumps(c.get("diseases", [])),
                c.get("sources_count"),
                len(c.get("evidence", [])),
                json.dumps(c.get("evidence", []))
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Saved result for query {query_id}")
    except Exception as e:
        logger.error(f"Error saving result: {e}")

def get_candidates(query_id: str) -> List[Dict]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT drug, deterministic_score, llm_score, final_score, mechanism, 
                   diseases_json, sources_count, evidence_json
            FROM candidates
            WHERE query_id = ?
            ORDER BY final_score DESC
        """, (query_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        candidates = []
        for row in rows:
            candidates.append({
                "drug": row[0],
                "deterministic_score": row[1],
                "llm_score": row[2],
                "final_score": row[3],
                "mechanism": row[4],
                "diseases": json.loads(row[5]) if row[5] else [],
                "sources_count": row[6],
                "evidence": json.loads(row[7]) if row[7] else [],
                "source_url": None
            })
        
        return candidates
    except Exception as e:
        logger.error(f"Error retrieving candidates: {e}")
        return []
