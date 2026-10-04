import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.config import DB_PATH

logger = logging.getLogger("ApplyEase.DB")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite database tables for ApplyEase Multimodal Auditor."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Candidate Profile Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            candidate_id TEXT PRIMARY KEY,
            full_name TEXT,
            dob TEXT,
            category TEXT,
            father_name TEXT,
            audit_passed INTEGER DEFAULT 1,
            critical_count INTEGER DEFAULT 0,
            warning_count INTEGER DEFAULT 0,
            summary_report TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Extracted Documents Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS extracted_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT NOT NULL,
            document_type TEXT NOT NULL,
            file_name TEXT,
            extracted_json TEXT NOT NULL,
            confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates (candidate_id)
        );
    """)

    # Discrepancies Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS discrepancies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            severity TEXT NOT NULL,
            source_doc_1 TEXT,
            value_1 TEXT,
            source_doc_2 TEXT,
            value_2 TEXT,
            description TEXT,
            recommendation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates (candidate_id)
        );
    """)

    # Transformed Assets Storage Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transformed_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            original_filename TEXT,
            stored_bucket_path TEXT NOT NULL,
            file_size_kb REAL,
            width INTEGER,
            height INTEGER,
            format TEXT,
            checksum_md5 TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates (candidate_id)
        );
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully at %s", DB_PATH)

def save_candidate_dossier(dossier_data: Dict[str, Any]):
    """Persist candidate profile, document extractions, discrepancies, and asset logs into SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()

    candidate_id = dossier_data["candidate_id"]

    # Upsert Candidate
    cursor.execute("""
        INSERT OR REPLACE INTO candidates 
        (candidate_id, full_name, dob, category, father_name, audit_passed, critical_count, warning_count, summary_report)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        candidate_id,
        dossier_data.get("primary_name"),
        dossier_data.get("primary_dob"),
        dossier_data.get("primary_category"),
        dossier_data.get("primary_father_name"),
        1 if dossier_data.get("audit_passed", True) else 0,
        dossier_data.get("critical_discrepancy_count", 0),
        dossier_data.get("warning_count", 0),
        dossier_data.get("summary_report", "")
    ))

    # Clear old entries for clean re-audit if exists
    cursor.execute("DELETE FROM extracted_documents WHERE candidate_id = ?", (candidate_id,))
    cursor.execute("DELETE FROM discrepancies WHERE candidate_id = ?", (candidate_id,))
    cursor.execute("DELETE FROM transformed_assets WHERE candidate_id = ?", (candidate_id,))

    # Insert Extracted Documents
    for doc in dossier_data.get("extracted_documents", []):
        cursor.execute("""
            INSERT INTO extracted_documents (candidate_id, document_type, file_name, extracted_json, confidence)
            VALUES (?, ?, ?, ?, ?)
        """, (
            candidate_id,
            doc.get("document_type", "unknown"),
            doc.get("file_name", "unknown"),
            json.dumps(doc),
            doc.get("extraction_confidence", 0.9)
        ))

    # Insert Discrepancies
    for disc in dossier_data.get("discrepancies", []):
        cursor.execute("""
            INSERT INTO discrepancies 
            (candidate_id, field_name, severity, source_doc_1, value_1, source_doc_2, value_2, description, recommendation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            candidate_id,
            disc.get("field_name"),
            disc.get("severity"),
            disc.get("source_document_1"),
            disc.get("value_1"),
            disc.get("source_document_2"),
            disc.get("value_2"),
            disc.get("description"),
            disc.get("recommendation")
        ))

    # Insert Assets
    for asset in dossier_data.get("transformed_assets", []):
        cursor.execute("""
            INSERT INTO transformed_assets 
            (candidate_id, asset_type, original_filename, stored_bucket_path, file_size_kb, width, height, format, checksum_md5)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            candidate_id,
            asset.get("asset_type"),
            asset.get("original_filename"),
            asset.get("stored_bucket_path"),
            asset.get("file_size_kb"),
            asset.get("width"),
            asset.get("height"),
            asset.get("format"),
            asset.get("checksum_md5")
        ))

    conn.commit()
    conn.close()
    logger.info("Candidate dossier saved to DB for candidate_id: %s", candidate_id)

def get_candidate_dossier_from_db(candidate_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full candidate dossier and audit history from SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,))
    cand = cursor.fetchone()
    if not cand:
        conn.close()
        return None

    # Fetch Documents
    cursor.execute("SELECT * FROM extracted_documents WHERE candidate_id = ?", (candidate_id,))
    docs = [json.loads(row["extracted_json"]) for row in cursor.fetchall()]

    # Fetch Discrepancies
    cursor.execute("SELECT * FROM discrepancies WHERE candidate_id = ?", (candidate_id,))
    discs = [dict(row) for row in cursor.fetchall()]

    # Fetch Assets
    cursor.execute("SELECT * FROM transformed_assets WHERE candidate_id = ?", (candidate_id,))
    assets = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "candidate_id": cand["candidate_id"],
        "primary_name": cand["full_name"],
        "primary_dob": cand["dob"],
        "primary_category": cand["category"],
        "primary_father_name": cand["father_name"],
        "audit_passed": bool(cand["audit_passed"]),
        "critical_discrepancy_count": cand["critical_count"],
        "warning_count": cand["warning_count"],
        "summary_report": cand["summary_report"],
        "extracted_documents": docs,
        "discrepancies": discs,
        "transformed_assets": assets
    }
