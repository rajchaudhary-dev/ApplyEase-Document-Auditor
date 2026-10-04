import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
from src.config import (
    DB_PATH,
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_DOSSIERS_TABLE,
    SUPABASE_VACANCIES_TABLE
)

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

    # Gazette Rules Cache Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gazette_rules (
            gazette_id TEXT PRIMARY KEY,
            sha256_hash TEXT UNIQUE NOT NULL,
            file_name TEXT NOT NULL,
            parsed_json TEXT NOT NULL,
            post_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    logger.info("Candidate dossier saved to SQLite for candidate_id: %s", candidate_id)

    # Automatically sync dossier to Supabase Cloud DB if configured
    sync_dossier_to_supabase(dossier_data)


def sync_dossier_to_supabase(dossier_data: Dict[str, Any]):
    """Sync candidate dossier JSON payload to Supabase candidate_dossiers table."""
    if not (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
        return

    cid = dossier_data.get("candidate_id")
    payload = {
        "candidate_id": cid,
        "primary_name": dossier_data.get("primary_name"),
        "primary_dob": dossier_data.get("primary_dob"),
        "primary_category": dossier_data.get("primary_category"),
        "primary_father_name": dossier_data.get("primary_father_name"),
        "audit_passed": dossier_data.get("audit_passed", True),
        "critical_discrepancy_count": dossier_data.get("critical_discrepancy_count", 0),
        "warning_count": dossier_data.get("warning_count", 0),
        "summary_report": dossier_data.get("summary_report", ""),
        "extracted_documents": dossier_data.get("extracted_documents", []),
        "discrepancies": dossier_data.get("discrepancies", []),
        "transformed_assets": dossier_data.get("transformed_assets", [])
    }

    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_DOSSIERS_TABLE}"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code in [200, 201]:
            logger.info("Successfully synced candidate dossier to Supabase (%s)", cid)
        else:
            logger.warning("Supabase dossier sync returned HTTP %s (Table may need creation): %s", 
                           resp.status_code, resp.text[:120])
    except Exception as e:
        logger.warning("Could not sync dossier to Supabase: %s", str(e))


def fetch_vacancies_from_supabase(limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve active live government recruitment vacancies from Supabase."""
    if not (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
        return []

    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_VACANCIES_TABLE}?select=*&limit={limit}&order=created_at.desc"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        logger.warning("Failed to fetch vacancies from Supabase (HTTP %s): %s", resp.status_code, resp.text[:100])
        return []
    except Exception as e:
        logger.warning("Error querying vacancies from Supabase: %s", str(e))
        return []

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


def save_gazette_rule(gazette_id: str, sha256_hash: str, file_name: str, parsed_json_str: str, post_code: Optional[str] = None):
    """Save or update parsed gazette rules JSON indexed by SHA-256 hash."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO gazette_rules (gazette_id, sha256_hash, file_name, parsed_json, post_code)
        VALUES (?, ?, ?, ?, ?)
    """, (gazette_id, sha256_hash, file_name, parsed_json_str, post_code))

    conn.commit()
    conn.close()
    logger.info("Gazette rules saved to DB [ID: %s, Hash: %s]", gazette_id, sha256_hash[:10])

def get_gazette_rule_by_hash(sha256_hash: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached gazette rules by SHA-256 hash."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM gazette_rules WHERE sha256_hash = ?", (sha256_hash,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    data = json.loads(row["parsed_json"])
    data["gazette_id"] = row["gazette_id"]
    data["sha256_hash"] = row["sha256_hash"]
    return data

def get_gazette_rule_by_id(gazette_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached gazette rules by Gazette ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM gazette_rules WHERE gazette_id = ?", (gazette_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    data = json.loads(row["parsed_json"])
    data["gazette_id"] = row["gazette_id"]
    data["sha256_hash"] = row["sha256_hash"]
    return data

def list_all_gazettes() -> List[Dict[str, Any]]:
    """List summary of all cached recruitment gazettes."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT gazette_id, sha256_hash, file_name, post_code, created_at FROM gazette_rules ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]
