import re
import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, date

from src.schemas.document_schema import ExtractedDocumentField, DocumentType
from src.schemas.dossier_schema import DiscrepancyItem, SeverityLevel

logger = logging.getLogger("ApplyEase.DiscrepancyEngine")

class CrossDocumentDiscrepancyEngine:
    """Engine that cross-references candidate documents to detect administrative disqualification risks."""

    def analyze_dossier(self, documents: List[ExtractedDocumentField]) -> Tuple[List[DiscrepancyItem], Dict[str, Any]]:
        """Run comprehensive cross-document discrepancy and anomaly checks."""
        discrepancies: List[DiscrepancyItem] = []

        if not documents:
            return discrepancies, {"primary_name": None, "primary_dob": None, "primary_category": None, "primary_father": None}

        # 1. Establish Gold Standard Baseline (Class 10 is primary baseline in Indian Recruitment)
        class_10_doc = next((d for d in documents if d.document_type == DocumentType.CLASS_10_MARKSHEET), None)
        aadhaar_doc = next((d for d in documents if d.document_type == DocumentType.AADHAAR_CARD), None)
        caste_doc = next((d for d in documents if d.document_type in [
            DocumentType.OBC_NCL_CERTIFICATE, DocumentType.EWS_CERTIFICATE, DocumentType.SC_ST_CERTIFICATE
        ]), None)

        # Baseline resolution
        baseline_name = (class_10_doc.full_name if class_10_doc and class_10_doc.full_name 
                         else (aadhaar_doc.full_name if aadhaar_doc and aadhaar_doc.full_name else documents[0].full_name))
        
        baseline_dob = (class_10_doc.dob if class_10_doc and class_10_doc.dob 
                        else (aadhaar_doc.dob if aadhaar_doc and aadhaar_doc.dob else None))
        
        baseline_category = (caste_doc.category if caste_doc and caste_doc.category 
                             else next((d.category for d in documents if d.category), "UR"))
        
        baseline_father = (class_10_doc.father_name if class_10_doc and class_10_doc.father_name 
                           else (aadhaar_doc.father_name if aadhaar_doc and aadhaar_doc.father_name else None))

        # 2. Name Consistency Audit
        for doc in documents:
            if not doc.full_name or doc.document_type in [DocumentType.PASSPORT_PHOTO, DocumentType.SIGNATURE]:
                continue
            
            if doc == class_10_doc:
                continue

            # Compare name against baseline
            match_status, desc, severity = self._compare_names(baseline_name, doc.full_name)
            if not match_status:
                discrepancies.append(DiscrepancyItem(
                    field_name="full_name",
                    severity=severity,
                    source_document_1="Class 10 Marksheet (Gold Standard)" if class_10_doc else "Primary Document",
                    value_1=baseline_name,
                    source_document_2=doc.document_type.value,
                    value_2=doc.full_name,
                    description=f"Name mismatch detected: '{baseline_name}' vs '{doc.full_name}'. {desc}",
                    recommendation="Obtain an official Gazette notification or notarized affidavit explaining name variation prior to Document Verification (DV)."
                ))

        # 3. DOB Consistency Audit
        if baseline_dob:
            for doc in documents:
                if not doc.dob or doc == class_10_doc:
                    continue
                
                normalized_base_dob = self._normalize_date(baseline_dob)
                normalized_doc_dob = self._normalize_date(doc.dob)

                if normalized_base_dob and normalized_doc_dob and normalized_base_dob != normalized_doc_dob:
                    discrepancies.append(DiscrepancyItem(
                        field_name="dob",
                        severity=SeverityLevel.CRITICAL,
                        source_document_1="Class 10 Marksheet / Primary DOB",
                        value_1=baseline_dob,
                        source_document_2=doc.document_type.value,
                        value_2=doc.dob,
                        description=f"CRITICAL DOB mismatch: Class 10 DOB ({baseline_dob}) differs from {doc.document_type.value} DOB ({doc.dob}).",
                        recommendation="Correct Date of Birth on secondary ID proof immediately to match Class 10 Marksheet."
                    ))

        # 4. Father Name Consistency Audit
        if baseline_father:
            for doc in documents:
                if not doc.father_name or doc == class_10_doc:
                    continue

                match_status, desc, severity = self._compare_names(baseline_father, doc.father_name)
                if not match_status:
                    discrepancies.append(DiscrepancyItem(
                        field_name="father_name",
                        severity=severity,
                        source_document_1="Class 10 Marksheet",
                        value_1=baseline_father,
                        source_document_2=doc.document_type.value,
                        value_2=doc.father_name,
                        description=f"Father's name discrepancy: '{baseline_father}' vs '{doc.father_name}'. {desc}",
                        recommendation="Keep father's name affidavit handy during document verification."
                    ))

        # 5. Category & Financial Year Audit (OBC-NCL / EWS Certificate validity check)
        if caste_doc:
            fy_status, fy_desc, fy_severity = self._audit_reservation_certificate(caste_doc)
            if not fy_status:
                discrepancies.append(DiscrepancyItem(
                    field_name="financial_year_validity",
                    severity=fy_severity,
                    source_document_1=caste_doc.document_type.value,
                    value_1=f"Issue Date: {caste_doc.issue_date}, FY: {caste_doc.financial_year}",
                    source_document_2="Regulatory Recruitment Norms",
                    value_2="Valid Financial Year Window",
                    description=fy_desc,
                    recommendation="Obtain an updated non-creamy layer / income certificate for the current financial year before final submission."
                ))

        primary_summary = {
            "primary_name": baseline_name,
            "primary_dob": baseline_dob,
            "primary_category": baseline_category,
            "primary_father": baseline_father
        }

        return discrepancies, primary_summary

    def _compare_names(self, name1: str, name2: str) -> Tuple[bool, str, SeverityLevel]:
        """Compare two name strings handling spacing, middle initials, and expanded forms."""
        if not name1 or not name2:
            return True, "", SeverityLevel.INFO

        n1_clean = re.sub(r'[^a-zA-Z\s]', '', name1).strip().upper()
        n2_clean = re.sub(r'[^a-zA-Z\s]', '', name2).strip().upper()

        if n1_clean == n2_clean:
            return True, "Exact match", SeverityLevel.INFO

        tokens1 = n1_clean.split()
        tokens2 = n2_clean.split()

        # Check for initial abbreviation (e.g. Rohan K Sharma vs Rohan Kumar Sharma or Rohan Sharma)
        if len(tokens1) != len(tokens2):
            # Check if one is a subset with single letter initial
            if len(tokens1) == 2 and len(tokens2) == 3 and tokens1[0] == tokens2[0] and tokens1[1] == tokens2[2]:
                return False, "Middle name omitted in one document", SeverityLevel.WARNING
            if len(tokens1) == 3 and len(tokens2) == 3:
                if tokens1[0] == tokens2[0] and tokens1[2] == tokens2[2] and (tokens1[1][0] == tokens2[1][0]):
                    return False, "Middle initial abbreviated (e.g., K vs Kumar)", SeverityLevel.WARNING

            return False, f"Word count difference ({len(tokens1)} words vs {len(tokens2)} words)", SeverityLevel.WARNING

        # Equal length check
        mismatch_tokens = []
        for t1, t2 in zip(tokens1, tokens2):
            if t1 != t2:
                if len(t1) == 1 or len(t2) == 1:
                    if t1[0] == t2[0]:
                        continue  # e.g. K vs KUMAR
                mismatch_tokens.append((t1, t2))

        if not mismatch_tokens:
            return False, "Initial expansion variance detected", SeverityLevel.WARNING

        return False, f"Spelling variance in token(s): {mismatch_tokens}", SeverityLevel.CRITICAL

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize date strings into standard YYYY-MM-DD format."""
        if not date_str:
            return None
        date_str = date_str.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d %b %Y"):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
        return date_str

    def _audit_reservation_certificate(self, doc: ExtractedDocumentField) -> Tuple[bool, str, SeverityLevel]:
        """Audit OBC-NCL / EWS certificate issue date and financial year validity."""
        doc_type_val = doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type)

        if doc.document_type in [DocumentType.OBC_NCL_CERTIFICATE, DocumentType.EWS_CERTIFICATE]:
            if not doc.financial_year and not doc.issue_date:
                return False, f"{doc_type_val} missing issue date and financial year annotations.", SeverityLevel.WARNING
            
            # Check issue date age (typically valid for 1 financial year in government jobs)
            if doc.issue_date:
                norm_date = self._normalize_date(doc.issue_date)
                if norm_date:
                    try:
                        issue_dt = datetime.strptime(norm_date, "%Y-%m-%d").date()
                        today = date.today()
                        # If certificate is more than 3 years old, mark critical
                        days_old = (today - issue_dt).days
                        if days_old > 365 * 3:
                            return False, f"{doc_type_val} was issued on {doc.issue_date} (over 3 years old). Category certificate may be expired.", SeverityLevel.CRITICAL
                        elif days_old > 365:
                            return False, f"{doc_type_val} issue date ({doc.issue_date}) is older than 1 year. Ensure it covers the relevant Financial Year.", SeverityLevel.WARNING
                    except Exception:
                        pass

        return True, "Certificate validity verified.", SeverityLevel.INFO
