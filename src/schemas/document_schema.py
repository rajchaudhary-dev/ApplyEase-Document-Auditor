from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class DocumentType(str, Enum):
    CLASS_10_MARKSHEET = "class_10_marksheet"
    CLASS_12_MARKSHEET = "class_12_marksheet"
    DEGREE_CERTIFICATE = "degree_certificate"
    AADHAAR_CARD = "aadhaar_card"
    PASSPORT = "passport"
    OBC_NCL_CERTIFICATE = "obc_ncl_certificate"
    EWS_CERTIFICATE = "ews_certificate"
    SC_ST_CERTIFICATE = "sc_st_certificate"
    DOMICILE_CERTIFICATE = "domicile_certificate"
    PASSPORT_PHOTO = "passport_photo"
    SIGNATURE = "signature"
    UNKNOWN = "unknown"

class ExtractedDocumentField(BaseModel):
    document_type: DocumentType = Field(description="Detected type of document")
    full_name: Optional[str] = Field(default=None, description="Full candidate name as written on document")
    father_name: Optional[str] = Field(default=None, description="Father or parent/guardian name")
    mother_name: Optional[str] = Field(default=None, description="Mother name if present")
    dob: Optional[str] = Field(default=None, description="Date of birth in YYYY-MM-DD or DD/MM/YYYY format")
    gender: Optional[str] = Field(default=None, description="Gender (Male/Female/Other)")
    category: Optional[str] = Field(default=None, description="Reservation Category (UR, OBC-NCL, EWS, SC, ST)")
    certificate_number: Optional[str] = Field(default=None, description="Registration, Roll No, or Certificate ID")
    issue_date: Optional[str] = Field(default=None, description="Document issue date")
    financial_year: Optional[str] = Field(default=None, description="Financial year for OBC-NCL / EWS certificates (e.g. 2023-2024)")
    issuing_authority: Optional[str] = Field(default=None, description="Issuing authority (e.g., Tehsildar, CBSE, SDO)")
    state: Optional[str] = Field(default=None, description="State of issuance")
    percentage_or_cgpa: Optional[str] = Field(default=None, description="Aggregate marks/percentage/CGPA if academic doc")
    extraction_confidence: float = Field(default=0.9, description="Confidence score of OCR extraction (0.0 to 1.0)")
    raw_ocr_text: Optional[str] = Field(default=None, description="Full transcribed raw text snippet")
