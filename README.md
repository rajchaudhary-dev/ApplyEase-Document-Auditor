# ApplyEase — Multimodal Document Auditor (Feature 1 Agentic Pipeline)

This repository contains the standalone implementation of **Feature 1: Multimodal Document Auditor (Gemini Flash Vision)** for **ApplyEase**.

---

## 🎯 Scope & Capabilities

1. **Mass Document Ingestion:**
   - Ingests candidate document dumps (Class 10, Class 12, Degree marksheets, Aadhaar ID, OBC-NCL / EWS / SC / ST caste certificates, Passport Photo, Signature).

2. **Multimodal Extraction & Schema Normalization (Gemini Flash Vision):**
   - Uses `google-genai` SDK with `gemini-3.8-flash` vision capabilities to extract structured candidate details (`full_name`, `father_name`, `dob`, `category`, `certificate_number`, `issue_date`, `financial_year`, `issuing_authority`, `marks_percentage`).

3. **Cross-Document Discrepancy & Anomaly Audit Engine:**
   - Establishes Class 10 Marksheet as the gold standard baseline for Indian recruitment compliance.
   - Audits name expansion vs abbreviation variances (e.g. `Rohan Kumar Sharma` vs `Rohan K. Sharma`).
   - Audits Date of Birth (DOB) discrepancies across documents.
   - Verifies OBC-NCL / EWS reservation certificate issue dates and financial year validity windows.

4. **OpenCV & Pillow Asset Transformation Engine:**
   - Auto-crops passport photo & signature contours using OpenCV.
   - Resizes, pads, and dynamically compresses assets to government portal constraints:
     - **Passport Photo:** 200x230 px, JPEG, compressed to 20KB–50KB limit.
     - **Signature:** 140x60 px, JPEG, compressed to 10KB–20KB limit.
     - **Document Scans:** Compressed under 300KB limit.

5. **Storage Bucket & Database Persistence:**
   - Dumps processed assets into a local/S3-compatible bucket folder (`storage_bucket/{candidate_id}/...`) with MD5 checksums and file metadata.
   - Persists candidate profiles, document extractions, flagged discrepancies, and asset URIs in SQLite (`applyease_dossier.db`).

6. **FastAPI REST Service & Integration API:**
   - Complete REST endpoints for document mass upload, dossier retrieval, discrepancy reporting, and asset downloading.

---

## 📁 Folder Structure

```
ApplyEase/
├── setup_env.ps1                   # Environment & dependency setup script
├── requirements.txt                # Python dependencies (google-genai, opencv, pillow, pydantic, fastapi)
├── .env.example                    # Environment settings template
├── README.md                       # Comprehensive documentation
├── src/
│   ├── config.py                   # Global configuration & portal image constraints
│   ├── schemas/
│   │   ├── document_schema.py      # Pydantic schemas for extracted fields
│   │   └── dossier_schema.py       # Candidate Dossier & Discrepancy report schemas
│   ├── db/
│   │   ├── database.py             # SQLite database initialization & CRUD operations
│   ├── services/
│   │   ├── gemini_vision.py        # Gemini Flash Vision OCR extraction service
│   │   ├── discrepancy_engine.py   # Cross-document anomaly audit engine
│   │   ├── asset_transformer.py    # OpenCV / Pillow cropping & compression pipeline
│   │   └── storage_bucket.py       # Object storage bucket manager
│   ├── agent/
│   │   └── auditor_agent.py        # Autonomous Document Auditor Agent pipeline
│   └── api/
│       └── app.py                  # FastAPI REST endpoints
└── tests/
    ├── generate_mock_docs.py       # Synthetic candidate test document generator
    └── test_pipeline.py            # End-to-end integration test runner
```

---

## 🚀 How to Run & Test

### 1. Environment Setup
```powershell
powershell -ExecutionPolicy Bypass -File .\setup_env.ps1
```

### 2. Set API Key (Optional for Live Gemini Vision)
Create a `.env` file or export your Gemini API Key:
```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```
*(Note: If no API key is provided, the system automatically runs with offline mock vision extractions for instant unit testing).*

### 3. Run End-to-End Integration Test
```powershell
python tests\test_pipeline.py
```

### 4. Start FastAPI REST Server
```powershell
python -m uvicorn src.api.app:app --reload --port 8000
```
Open interactive API docs at: `http://localhost:8000/docs`

---

## 📡 API Endpoints Summary

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/dossier/upload` | Upload candidate documents, run vision extractions, execute discrepancy audit, compress assets into bucket, and save to DB |
| `GET` | `/api/v1/dossier/{candidate_id}` | Retrieve candidate profile, extracted documents, audit flags, and asset metadata |
| `GET` | `/api/v1/dossier/{candidate_id}/discrepancies` | Get list of critical & warning administrative discrepancies |
| `GET` | `/api/v1/dossier/{candidate_id}/asset/{filename}` | Download compressed photo, signature, or document scan from storage bucket |

---

## 💡 Team Integration Notes
- Module output returns a clean JSON `CandidateDossier` containing `primary_name`, `primary_dob`, `primary_category`, `extracted_documents`, `discrepancies`, and `transformed_assets`.
- `Feature 2 (Gazette Intelligence Engine)` can directly consume `dossier["primary_dob"]`, `dossier["primary_category"]`, and `dossier["extracted_documents"]`.
- `Feature 3 & 4 (Portal Pilot Agent)` can consume the compressed asset paths in `dossier["transformed_assets"]` for direct portal upload.
