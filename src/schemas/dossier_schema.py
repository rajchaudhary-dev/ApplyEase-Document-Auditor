from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from src.schemas.document_schema import DocumentType, ExtractedDocumentField

class SeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"  # Likely to cause rejection in document verification (e.g. name mismatch, expired cert)
    WARNING = "WARNING"    # Minor variation (e.g. middle initial vs full name, format difference)
    INFO = "INFO"          # Informational note (e.g. verified financial year match)

class DiscrepancyItem(BaseModel):
    field_name: str = Field(description="Name of the field being cross-referenced (e.g., candidate_name, dob, category)")
    severity: SeverityLevel
    source_document_1: str
    value_1: Optional[str]
    source_document_2: str
    value_2: Optional[str]
    description: str = Field(description="Detailed explanation of discrepancy or anomaly")
    recommendation: str = Field(description="Actionable advice to avoid disqualification")

class TransformedAssetMetadata(BaseModel):
    asset_type: str  # photo, signature, document_scan
    original_filename: str
    stored_bucket_path: str
    file_size_kb: float
    width: int
    height: int
    format: str
    checksum_md5: str

class CandidateDossier(BaseModel):
    candidate_id: str
    primary_name: Optional[str] = None
    primary_dob: Optional[str] = None
    primary_category: Optional[str] = None
    primary_father_name: Optional[str] = None
    extracted_documents: List[ExtractedDocumentField] = []
    discrepancies: List[DiscrepancyItem] = []
    transformed_assets: List[TransformedAssetMetadata] = []
    audit_passed: bool = True
    critical_discrepancy_count: int = 0
    warning_count: int = 0
    summary_report: str = ""
