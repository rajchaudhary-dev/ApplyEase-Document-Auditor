import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Union, Optional

from src.db.database import init_db, save_candidate_dossier
from src.schemas.document_schema import ExtractedDocumentField, DocumentType
from src.schemas.dossier_schema import CandidateDossier, SeverityLevel
from src.services.gemini_vision import MultimodalDocumentExtractor
from src.services.discrepancy_engine import CrossDocumentDiscrepancyEngine
from src.services.asset_transformer import AssetTransformerEngine
from src.services.storage_bucket import StorageBucketService

logger = logging.getLogger("ApplyEase.AuditorAgent")

class DocumentAuditorPipeline:
    """Autonomous Multimodal Document Auditor Agent for ApplyEase Feature 1."""

    def __init__(self, api_key: Optional[str] = None):
        init_db()
        self.extractor = MultimodalDocumentExtractor(api_key=api_key)
        self.discrepancy_engine = CrossDocumentDiscrepancyEngine()
        self.bucket_service = StorageBucketService()
        self.asset_transformer = AssetTransformerEngine(bucket_service=self.bucket_service)

    def process_candidate_documents(
        self, 
        document_paths: List[Union[str, Path]], 
        candidate_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        End-to-end agentic workflow:
        1. Ingest mass documents
        2. Execute Gemini Vision multimodal OCR & field extraction
        3. Cross-audit documents for discrepancies (Name variance, DOB, Category validity)
        4. Compress & transform photos, signatures, and document scans using OpenCV/Pillow
        5. Persist to SQLite DB & Object Storage Bucket
        6. Emit candidate audit report
        """
        cid = candidate_id or f"CAND-{uuid.uuid4().hex[:8].upper()}"
        logger.info("Starting Multimodal Document Audit Agent for Candidate ID: %s", cid)

        extracted_docs: List[ExtractedDocumentField] = []
        raw_doc_dict_list: List[Dict[str, Any]] = []
        transformed_assets_list: List[Dict[str, Any]] = []

        # Step 1 & 2: Multimodal Extraction & Asset Compression
        for doc_path in document_paths:
            path = Path(doc_path)
            if not path.exists():
                logger.warning("Skipping missing file: %s", path)
                continue

            # Vision Field Extraction via Gemini Flash Vision
            extracted_field = self.extractor.extract_document(path)
            extracted_docs.append(extracted_field)

            doc_dict = extracted_field.model_dump()
            doc_dict["file_name"] = path.name
            raw_doc_dict_list.append(doc_dict)

            # Asset Processing with OpenCV / Pillow based on detected document type
            try:
                if extracted_field.document_type == DocumentType.PASSPORT_PHOTO:
                    asset_meta = self.asset_transformer.process_and_bucket_photo(cid, path)
                    transformed_assets_list.append(asset_meta)
                elif extracted_field.document_type == DocumentType.SIGNATURE:
                    asset_meta = self.asset_transformer.process_and_bucket_signature(cid, path)
                    transformed_assets_list.append(asset_meta)
                else:
                    doc_type_str = extracted_field.document_type.value if hasattr(extracted_field.document_type, "value") else str(extracted_field.document_type)
                    asset_meta = self.asset_transformer.process_and_bucket_document(cid, path, doc_type_str)
                    transformed_assets_list.append(asset_meta)
            except Exception as e:
                logger.error("Failed to process asset transformation for %s: %s", path.name, str(e))

        # Step 3: Cross-Document Discrepancy & Anomaly Audit
        discrepancy_items, primary_info = self.discrepancy_engine.analyze_dossier(extracted_docs)
        discrepancy_dict_list = [d.model_dump() for d in discrepancy_items]

        critical_count = sum(1 for d in discrepancy_items if d.severity == SeverityLevel.CRITICAL)
        warning_count = sum(1 for d in discrepancy_items if d.severity == SeverityLevel.WARNING)
        audit_passed = (critical_count == 0)

        # Build Summary Report text
        summary_report = self._build_summary_report(
            cid=cid,
            primary_info=primary_info,
            doc_count=len(extracted_docs),
            critical_count=critical_count,
            warning_count=warning_count,
            discrepancies=discrepancy_items,
            assets=transformed_assets_list
        )

        dossier_data = {
            "candidate_id": cid,
            "primary_name": primary_info.get("primary_name"),
            "primary_dob": primary_info.get("primary_dob"),
            "primary_category": primary_info.get("primary_category"),
            "primary_father_name": primary_info.get("primary_father"),
            "extracted_documents": raw_doc_dict_list,
            "discrepancies": discrepancy_dict_list,
            "transformed_assets": transformed_assets_list,
            "audit_passed": audit_passed,
            "critical_discrepancy_count": critical_count,
            "warning_count": warning_count,
            "summary_report": summary_report
        }

        # Step 4: Save to Database & Bucket Storage
        save_candidate_dossier(dossier_data)
        logger.info("Audit complete for %s. Passed: %s, Critical Discrepancies: %d", cid, audit_passed, critical_count)

        return dossier_data

    def _build_summary_report(
        self, 
        cid: str, 
        primary_info: Dict[str, Any], 
        doc_count: int, 
        critical_count: int, 
        warning_count: int,
        discrepancies: List[Any],
        assets: List[Dict[str, Any]]
    ) -> str:
        lines = [
            f"=== ApplyEase Candidate Dossier Audit Report ===",
            f"Candidate ID: {cid}",
            f"Primary Name: {primary_info.get('primary_name') or 'N/A'}",
            f"Primary DOB: {primary_info.get('primary_dob') or 'N/A'}",
            f"Primary Category: {primary_info.get('primary_category') or 'UR'}",
            f"Total Documents Audited: {doc_count}",
            f"Audit Status: {'PASSED' if critical_count == 0 else 'ACTION REQUIRED (DISCREPANCIES DETECTED)'}",
            f"Critical Risk Flags: {critical_count} | Warnings: {warning_count}",
            ""
        ]

        if discrepancies:
            lines.append("--- Discrepancy & Anomaly Audit Trail ---")
            for idx, d in enumerate(discrepancies, 1):
                sev = d.severity.value if hasattr(d.severity, "value") else str(d.severity)
                lines.append(f"[{idx}] [{sev}] Field: '{d.field_name}'")
                lines.append(f"    Source 1 ({d.source_document_1}): {d.value_1}")
                lines.append(f"    Source 2 ({d.source_document_2}): {d.value_2}")
                lines.append(f"    Details: {d.description}")
                lines.append(f"    Action Required: {d.recommendation}")
                lines.append("")
        else:
            lines.append("[OK] No administrative discrepancies found across documents.")

        lines.append(f"--- Transformed & Compressed Bucket Assets ({len(assets)} items) ---")
        for a in assets:
            lines.append(f" - [{a.get('asset_type')}] {a.get('stored_filename')} ({a.get('file_size_kb')} KB, {a.get('width')}x{a.get('height')} px)")

        return "\n".join(lines)
