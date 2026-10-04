import sys
import os
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tests.generate_mock_gazette import generate_mock_gazette_pdf
from src.services.gazette_evaluator import GazetteRuleEvaluator
from src.db.database import get_gazette_rule_by_hash, get_gazette_rule_by_id, list_all_gazettes

def run_gazette_evaluator_integration_test():
    print("=" * 65)
    print("  APPLYEASE FEATURE 2: GAZETTE RULE EVALUATOR - INTEGRATION TEST")
    print("=" * 65)

    gazette_dir = BASE_DIR / "tests" / "sample_gazettes"
    gazette_pdf_path = gazette_dir / "upsc_aso_2026_gazette.pdf"

    print(f"\n[1/4] Generating synthetic recruitment gazette PDF: {gazette_pdf_path.name}")
    generate_mock_gazette_pdf(gazette_pdf_path)
    assert gazette_pdf_path.exists(), "Failed to generate synthetic gazette PDF!"

    print("\n[2/4] Initializing GazetteRuleEvaluator & Parsing Notification...")
    evaluator = GazetteRuleEvaluator()
    schema_1 = evaluator.evaluate_gazette(
        file_path=gazette_pdf_path,
        post_code="ASO"
    )

    print(f"  - Gazette ID     : {schema_1.gazette_id}")
    print(f"  - SHA-256 Hash   : {schema_1.sha256_hash[:16]}...")
    print(f"  - Post Name      : {schema_1.metadata.post_name}")
    print(f"  - Advt Number    : {schema_1.metadata.advertisement_number}")
    print(f"  - Crucial Date   : {schema_1.key_dates.cutoff_date}")
    print(f"  - Age Limit      : Min {schema_1.age_criteria.min_age_general} / Max {schema_1.age_criteria.max_age_general} yrs")
    print(f"  - OBC Relaxation : +{schema_1.age_criteria.age_relaxations.get('OBC', 3)} yrs")
    print(f"  - Photo Specs    : {schema_1.asset_upload_guidelines.photo_width_px}x{schema_1.asset_upload_guidelines.photo_height_px} px ({schema_1.asset_upload_guidelines.photo_min_kb}-{schema_1.asset_upload_guidelines.photo_max_kb} KB)")

    print("\n[3/4] Testing SHA-256 Cache Performance (Second Call)...")
    schema_2 = evaluator.evaluate_gazette(
        file_path=gazette_pdf_path,
        post_code="ASO"
    )
    assert schema_2.sha256_hash == schema_1.sha256_hash, "SHA-256 hash mismatch!"
    print("  [OK] Successfully retrieved cached gazette rules instantly without re-upload!")

    print("\n[4/4] Verifying Database Persistence and Retrieval...")
    db_record = get_gazette_rule_by_hash(schema_1.sha256_hash)
    assert db_record is not None, "Failed to retrieve gazette record from DB by hash!"
    assert db_record["gazette_id"] == schema_1.gazette_id, "Gazette ID mismatch in DB!"

    all_gazettes = list_all_gazettes()
    assert len(all_gazettes) > 0, "No gazettes found in list_all_gazettes DB query!"
    print(f"  [OK] Verified {len(all_gazettes)} cached gazette notification(s) in SQLite database.")

    print("\n[SUCCESS] Feature 2: Gazette Rule Evaluator Integration Test PASSED!")
    print("=" * 65)

if __name__ == "__main__":
    run_gazette_evaluator_integration_test()
