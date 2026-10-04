from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class NotificationMetadata(BaseModel):
    post_name: str = Field(description="Name of the position(s) / post(s) advertised")
    advertisement_number: Optional[str] = Field(default=None, description="Official Advt / Gazette Notification Number")
    organization: Optional[str] = Field(default=None, description="Issuing department or recruitment board (e.g., UPSC, SSC, IBPS)")
    issue_date: Optional[str] = Field(default=None, description="Date when notification was published (YYYY-MM-DD or DD/MM/YYYY)")
    total_vacancies: Optional[int] = Field(default=None, description="Total number of seats/vacancies announced")

class KeyDates(BaseModel):
    registration_start_date: Optional[str] = Field(default=None, description="Online application opening date")
    registration_deadline: Optional[str] = Field(default=None, description="Last date for application submission")
    cutoff_date: Optional[str] = Field(default=None, description="Crucial date for determining age & educational eligibility")
    fee_payment_deadline: Optional[str] = Field(default=None, description="Last date to deposit examination fee")
    exam_dates: Optional[str] = Field(default=None, description="Scheduled exam or interview dates if declared")

class ApplicationFeeMatrix(BaseModel):
    general: float = Field(default=0.0, description="Fee for Unreserved / General category candidates")
    obc: float = Field(default=0.0, description="Fee for OBC category candidates")
    ews: float = Field(default=0.0, description="Fee for EWS category candidates")
    sc: float = Field(default=0.0, description="Fee for SC category candidates")
    st: float = Field(default=0.0, description="Fee for ST category candidates")
    pwbd: float = Field(default=0.0, description="Fee for PwBD / Disabled candidates")
    female: float = Field(default=0.0, description="Fee for Female candidates")
    payment_modes: List[str] = Field(default_factory=list, description="Accepted payment methods (Net Banking, UPI, Challan)")

class AgeCriteria(BaseModel):
    cutoff_date: Optional[str] = Field(default=None, description="Reference date as on which age is calculated")
    min_age_general: int = Field(default=18, description="Minimum age limit for Unreserved category")
    max_age_general: int = Field(default=30, description="Maximum upper age limit for Unreserved category")
    age_relaxations: Dict[str, int] = Field(
        default_factory=lambda: {"OBC": 3, "SC": 5, "ST": 5, "PwBD": 10, "ExServicemen": 5},
        description="Category-wise upper age relaxation in years (e.g. OBC: 3, SC/ST: 5)"
    )

class EducationalQualifications(BaseModel):
    minimum_degree: str = Field(description="Minimum required qualification (e.g., Bachelor's Degree, Class 10, B.Tech)")
    required_disciplines: List[str] = Field(default_factory=list, description="Mandatory subjects or degree streams")
    min_percentage_or_cgpa: Optional[str] = Field(default=None, description="Minimum passing percentage or CGPA cutoff if specified")
    mandatory_experience_months: int = Field(default=0, description="Required work experience duration in months")
    experience_details: Optional[str] = Field(default=None, description="Specific field or nature of required work experience")

class ReservationRules(BaseModel):
    obc_ncl_cutoff_window: Optional[str] = Field(default=None, description="Valid issue date window for OBC Non-Creamy Layer certificates")
    ews_valid_financial_year: Optional[str] = Field(default=None, description="Mandatory Financial Year for EWS Income & Asset certificates")
    domicile_requirements: Optional[str] = Field(default=None, description="State domicile or citizenship criteria")
    other_clauses: List[str] = Field(default_factory=list, description="Additional reservation & equivalence clauses")

class AssetUploadGuidelines(BaseModel):
    photo_width_px: int = Field(default=200, description="Required photo width in pixels")
    photo_height_px: int = Field(default=230, description="Required photo height in pixels")
    photo_min_kb: int = Field(default=20, description="Minimum photo file size in KB")
    photo_max_kb: int = Field(default=50, description="Maximum photo file size in KB")
    photo_format: str = Field(default="JPEG", description="Accepted image format for photo")
    
    signature_width_px: int = Field(default=140, description="Required signature width in pixels")
    signature_height_px: int = Field(default=60, description="Required signature height in pixels")
    signature_min_kb: int = Field(default=10, description="Minimum signature file size in KB")
    signature_max_kb: int = Field(default=20, description="Maximum signature file size in KB")
    signature_format: str = Field(default="JPEG", description="Accepted image format for signature")
    
    document_max_kb: int = Field(default=300, description="Maximum file size for uploaded certificates/documents in KB")

class GazetteRulesSchema(BaseModel):
    gazette_id: Optional[str] = Field(default=None, description="Unique identifier for parsed gazette notification")
    sha256_hash: Optional[str] = Field(default=None, description="SHA-256 hash of the gazette PDF file")
    metadata: NotificationMetadata
    key_dates: KeyDates
    application_fee: ApplicationFeeMatrix
    age_criteria: AgeCriteria
    educational_qualifications: EducationalQualifications
    reservation_rules: ReservationRules
    asset_upload_guidelines: AssetUploadGuidelines
    important_clauses: List[str] = Field(default_factory=list, description="Citations and critical eligibility clauses extracted from gazette")
