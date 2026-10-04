import shutil
import tempfile
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from src.services.gazette_evaluator import GazetteRuleEvaluator
from src.db.database import get_gazette_rule_by_hash, get_gazette_rule_by_id, list_all_gazettes
from src.schemas.gazette_schema import GazetteRulesSchema

router = APIRouter(prefix="/api/v1/gazette", tags=["Gazette Intelligence"])

@router.post("/parse", summary="Ingest recruitment gazette PDF, extract eligibility matrix & rules using Gemini Large-Context Engine")
async def parse_gazette_notification(
    file: UploadFile = File(...),
    post_code: Optional[str] = Form(None),
    gemini_api_key: Optional[str] = Form(None),
    force_reparse: bool = Form(False)
):
    """
    Ingest multi-page PDF gazette (up to 50MB), run Gemini Large-Context Engine, 
    cache JSON result by SHA-256 hash, and clean up remote GenAI files.
    """
    if not file.filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Only PDF or image gazette files are supported.")

    temp_dir = Path(tempfile.mkdtemp(prefix="gazette_upload_"))
    temp_file_path = temp_dir / file.filename

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        evaluator = GazetteRuleEvaluator(api_key=gemini_api_key)
        gazette_schema = evaluator.evaluate_gazette(
            file_path=temp_file_path,
            post_code=post_code,
            force_reparse=force_reparse
        )

        return JSONResponse(status_code=200, content=gazette_schema.model_dump())

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gazette Rule Evaluator failed: {str(e)}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@router.get("/{gazette_id_or_hash}", summary="Retrieve cached gazette eligibility rules by ID or SHA-256 hash")
def get_gazette(gazette_id_or_hash: str):
    # Try ID lookup first
    data = get_gazette_rule_by_id(gazette_id_or_hash)
    if not data:
        # Try Hash lookup
        data = get_gazette_rule_by_hash(gazette_id_or_hash)

    if not data:
        raise HTTPException(status_code=404, detail=f"Gazette rules not found for ID or Hash: {gazette_id_or_hash}")
    return data

@router.get("", summary="List all cached recruitment gazette notifications")
def list_gazettes():
    return list_all_gazettes()
