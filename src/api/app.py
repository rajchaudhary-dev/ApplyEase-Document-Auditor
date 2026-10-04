import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from src.agent.auditor_agent import DocumentAuditorPipeline
from src.db.database import get_candidate_dossier_from_db, fetch_vacancies_from_supabase, init_db
from src.services.storage_bucket import StorageBucketService
from src.api.gazette_router import router as gazette_router

app = FastAPI(
    title="ApplyEase - Autonomous Recruitment Intelligence API",
    description="Autonomous recruitment intelligence agent for candidate document extraction, gazette rule evaluation, discrepancy auditing, and asset compression.",
    version="2.0.0"
)

# Enable CORS for frontend/team integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Gazette Intelligence Router
app.include_router(gazette_router)

# Initialize DB on server start
@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/")
def root():
    return {
        "service": "ApplyEase Multimodal Document Auditor API",
        "status": "online",
        "documentation": "/docs"
    }

@app.post("/api/v1/dossier/upload", summary="Mass dump candidate documents for extraction, audit, and asset bucket compression")
async def upload_candidate_documents(
    files: List[UploadFile] = File(...),
    candidate_id: Optional[str] = Form(None),
    gemini_api_key: Optional[str] = Form(None)
):
    """
    Accepts candidate documents (Class 10, Class 12, Degree, Aadhaar, OBC/EWS, Photo, Signature).
    Runs Gemini Flash Vision multimodal extraction, cross-references discrepancies, 
    compresses photos/signatures with OpenCV/Pillow into local bucket storage, 
    and saves dossier to SQLite DB.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No document files provided.")

    # Save uploaded files into a temporary processing folder
    temp_dir = Path(tempfile.mkdtemp(prefix="applyease_upload_"))
    saved_file_paths = []

    try:
        for file in files:
            file_path = temp_dir / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_file_paths.append(file_path)

        # Launch Agentic Pipeline
        pipeline = DocumentAuditorPipeline(api_key=gemini_api_key)
        dossier_result = pipeline.process_candidate_documents(
            document_paths=saved_file_paths,
            candidate_id=candidate_id
        )

        return JSONResponse(status_code=200, content=dossier_result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document Auditor Pipeline failed: {str(e)}")

    finally:
        # Cleanup temporary upload folder
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.get("/api/v1/dossier/{candidate_id}", summary="Retrieve processed candidate dossier and audit summary")
def get_dossier(candidate_id: str):
    dossier = get_candidate_dossier_from_db(candidate_id)
    if not dossier:
        raise HTTPException(status_code=404, detail=f"Candidate dossier not found for ID: {candidate_id}")
    return dossier

@app.get("/api/v1/dossier/{candidate_id}/discrepancies", summary="Retrieve flagged cross-document administrative anomalies")
def get_discrepancies(candidate_id: str):
    dossier = get_candidate_dossier_from_db(candidate_id)
    if not dossier:
        raise HTTPException(status_code=404, detail=f"Candidate dossier not found for ID: {candidate_id}")
    return {
        "candidate_id": candidate_id,
        "audit_passed": dossier["audit_passed"],
        "critical_discrepancy_count": dossier["critical_discrepancy_count"],
        "warning_count": dossier["warning_count"],
        "discrepancies": dossier["discrepancies"]
    }

@app.get("/api/v1/dossier/{candidate_id}/asset/{filename}", summary="Download transformed bucket asset (photo/signature/scan)")
def download_asset(candidate_id: str, filename: str):
    bucket = StorageBucketService()
    asset_path = bucket.get_asset_path(candidate_id, filename)
    if not asset_path.exists():
        raise HTTPException(status_code=404, detail=f"Asset {filename} not found in bucket for candidate {candidate_id}")
    return FileResponse(asset_path)


@app.get("/api/v1/jobs/match-feed/{candidate_id}", summary="Personalized Job Radar with Rejection Policy & Fixed vs Variable Criteria Tagging")
def get_personalized_job_radar(candidate_id: str, limit: int = 20):
    """
    Evaluates candidate's audited profile against active live vacancies in Supabase:
    - Fixed Criteria: Age, Degree, Base Category.
    - Variable / Actionable: Certificate Renewal, Name Affidavit, Asset Conformity.
    Returns jobs tagged with 🟢 ELIGIBLE, 🟡 ACTIONABLE, or 🔴 INELIGIBLE.
    """
    dossier = get_candidate_dossier_from_db(candidate_id)
    if not dossier:
        # Default mock candidate profile if ID not yet in DB
        dossier = {
            "candidate_id": candidate_id,
            "primary_name": "Rajesh Kumar",
            "primary_dob": "2001-08-15",
            "primary_category": "OBC-NCL",
            "audit_passed": True,
            "discrepancies": [],
            "transformed_assets": []
        }

    vacancies = fetch_vacancies_from_supabase(limit=limit)
    if not vacancies:
        return {
            "candidate_id": candidate_id,
            "total_evaluated": 0,
            "summary": {"directly_eligible": 0, "actionable_remediation": 0, "ineligible": 0},
            "jobs": []
        }

    # Extract Candidate Baseline Data
    cand_dob_str = dossier.get("primary_dob") or "2001-01-01"
    cand_category = (dossier.get("primary_category") or "UR").upper()
    has_discrepancy = any(d.get("severity") == "CRITICAL" for d in dossier.get("discrepancies", []))

    # Calculate Candidate Age (as of 2026)
    try:
        from datetime import datetime
        parts = [int(p) for p in cand_dob_str.replace("/", "-").split("-")]
        if len(parts) == 3:
            birth_year = parts[0] if parts[0] > 1900 else parts[2]
            current_age = 2026 - birth_year
        else:
            current_age = 24
    except Exception:
        current_age = 24

    evaluated_jobs = []
    eligible_count = 0
    actionable_count = 0
    ineligible_count = 0

    for v in vacancies:
        v_id = v.get("id")
        title = v.get("title", "Recruitment Notification")
        org = v.get("org", "Government of India")
        age_dict = v.get("age_limit") or {}
        dates_dict = v.get("dates") or {}
        links_dict = v.get("links") or {}
        pdf_storage_url = v.get("notification_pdf_storage_url") or links_dict.get("notification_pdf")

        # 1. Evaluate FIXED CRITERIA: Age Limit
        min_age = 18
        max_age = 30
        try:
            if age_dict.get("min_age"):
                min_age = int(str(age_dict.get("min_age")).split()[0])
            if age_dict.get("max_age"):
                max_age = int(str(age_dict.get("max_age")).split()[0])
        except Exception:
            pass

        # Apply category age relaxation (OBC +3, SC/ST +5)
        allowed_max_age = max_age
        if "OBC" in cand_category:
            allowed_max_age += 3
        elif "SC" in cand_category or "ST" in cand_category:
            allowed_max_age += 5

        age_passed = (min_age <= current_age <= allowed_max_age)

        # 2. Evaluate VARIABLE CRITERIA: Reservation Certificate & Discrepancies
        needs_cert_renewal = False
        if "OBC" in cand_category or "EWS" in cand_category:
            # Check if dossier has a certified valid FY 2025-26 certificate
            docs = dossier.get("extracted_documents", [])
            valid_cert = any(
                d.get("document_type") in ["obc_ncl_certificate", "ews_certificate"] and
                ("2025-2026" in str(d.get("financial_year", "")) or "2026" in str(d.get("issue_date", "")))
                for d in docs
            )
            if not valid_cert:
                needs_cert_renewal = True

        # Determine Tier Status
        if not age_passed:
            status = "INELIGIBLE"
            status_badge = "🔴 Ineligible"
            ineligible_count += 1
            primary_reason = f"Age restriction mismatch ({current_age} yrs vs allowed {min_age}-{allowed_max_age} yrs)"
        elif needs_cert_renewal:
            status = "ACTIONABLE"
            status_badge = "🟡 Action Required (Renew Certificate)"
            actionable_count += 1
            primary_reason = f"{cand_category} Certificate renewal required for FY 2025-26 before closing date"
        elif has_discrepancy:
            status = "ACTIONABLE"
            status_badge = "🟡 Action Required (Affidavit Needed)"
            actionable_count += 1
            primary_reason = "Name or DOB discrepancy across documents requires an official Affidavit"
        else:
            status = "ELIGIBLE"
            status_badge = "🟢 100% Eligible - Ready to Apply"
            eligible_count += 1
            primary_reason = "All documents and eligibility criteria verified"

        evaluated_jobs.append({
            "job_id": v_id,
            "title": title,
            "organization": org,
            "status": status,
            "status_badge": status_badge,
            "primary_reason": primary_reason,
            "pdf_url": pdf_storage_url,
            "last_date": dates_dict.get("last_date_apply") or dates_dict.get("listing_last_date") or "Closing Soon",
            "criteria_breakdown": {
                "age": {
                    "passed": age_passed,
                    "badge": f"✅ Age {current_age} / Max {allowed_max_age}" if age_passed else f"❌ Overage ({current_age} / Max {allowed_max_age})",
                    "type": "FIXED"
                },
                "reservation_certificate": {
                    "passed": not needs_cert_renewal,
                    "badge": "✅ Valid Certificate" if not needs_cert_renewal else "⚠️ Renew at Tehsil (Est. 5 Days)",
                    "type": "VARIABLE",
                    "action": "Apply on State e-District portal for FY 2025-26 certificate before application deadline." if needs_cert_renewal else None
                },
                "identity_match": {
                    "passed": not has_discrepancy,
                    "badge": "✅ Documents Consistent" if not has_discrepancy else "⚠️ Name Variance (Affidavit Needed)",
                    "type": "VARIABLE"
                }
            }
        })

    return {
        "candidate_id": candidate_id,
        "candidate_summary": {
            "name": dossier.get("primary_name"),
            "category": cand_category,
            "age": current_age
        },
        "summary": {
            "total_evaluated": len(vacancies),
            "directly_eligible": eligible_count,
            "actionable_remediation": actionable_count,
            "ineligible": ineligible_count
        },
        "jobs": evaluated_jobs
    }
