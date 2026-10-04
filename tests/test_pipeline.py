import sys
import os
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tests.generate_mock_docs import generate_mock_documents
from src.agent.auditor_agent import DocumentAuditorPipeline
from src.db.database import get_candidate_dossier_from_db

def run_integration_test():
    print("=" * 60)
    print("  APPLYEASE MULTIMODAL DOCUMENT AUDITOR - INTEGRATION TEST")
    print("=" * 60)

    sample_dir = BASE_DIR / "tests" / "sample_documents"
    print(f"\n[1/4] Generating synthetic candidate test documents in: {sample_dir}")
    doc_paths = generate_mock_documents(sample_dir)
    for p in doc_paths:
        print(f"  - Generated: {p.name}")

    print("\n[2/4] Initializing Multimodal Document Auditor Agent...")
    pipeline = DocumentAuditorPipeline()

    print("\n[3/4] Running Agentic Processing Pipeline (Ingestion -> Gemini OCR -> Anomaly Audit -> OpenCV Bucket Compression -> DB Storage)...")
    candidate_id = "CAND-TEST-9901"
    dossier = pipeline.process_candidate_documents(
        document_paths=doc_paths,
        candidate_id=candidate_id
    )

    print("\n[4/4] Verifying Saved Candidate Dossier from Database...")
    db_dossier = get_candidate_dossier_from_db(candidate_id)

    assert db_dossier is not None, "Failed: Candidate dossier was not saved to DB!"
    assert db_dossier["candidate_id"] == candidate_id, "Failed: Candidate ID mismatch!"
    assert len(db_dossier["extracted_documents"]) > 0, "Failed: No extracted documents saved!"
    assert len(db_dossier["transformed_assets"]) > 0, "Failed: No bucket transformed assets saved!"

    print("\n" + db_dossier["summary_report"])

    print("\n[SUCCESS] Multimodal Document Auditor Agent Integration Test PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    run_integration_test()
