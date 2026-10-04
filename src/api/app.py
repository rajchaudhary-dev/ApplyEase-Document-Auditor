import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from src.agent.auditor_agent import DocumentAuditorPipeline
from src.db.database import get_candidate_dossier_from_db, init_db
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
