# ApplyEase — Autonomous Recruitment Intelligence Pipeline

This repository contains the core pipeline microservices for **ApplyEase**, designed to eliminate administrative disqualification in government and institutional recruitment drives.

---

## 🎯 Features Implemented

### Feature 1: Multimodal Candidate Document Auditor (Gemini Flash Vision)
1. **Mass Document Ingestion:** Ingests candidate document dumps (Class 10, Class 12, Degree marksheets, Aadhaar ID, OBC-NCL / EWS / SC / ST caste certificates, Passport Photo, Signature).
2. **Multimodal Extraction & Schema Normalization:** Uses `google-genai` SDK with `gemini-3.8-flash` to extract structured candidate details (`full_name`, `father_name`, `dob`, `category`, `certificate_number`, `issue_date`, `financial_year`, `issuing_authority`, `marks_percentage`).
3. **Cross-Document Discrepancy & Anomaly Audit Engine:** Establishes Class 10 Marksheet as the gold standard baseline for Indian recruitment compliance. Detects name expansion vs abbreviation variances, DOB mismatches, and OBC-NCL / EWS certificate issue date validity windows.
4. **OpenCV & Pillow Asset Transformation Engine:** Auto-crops passport photo & signature contours, resizes, pads, and dynamically compresses assets to government portal constraints (Photo: 200x230px, 20-50KB; Signature: 140x60px, 10-20KB; Docs: <300KB).
5. **Storage Bucket & Database Persistence:** Dumps processed assets into a local/S3-compatible bucket folder (`storage_bucket/{candidate_id}/...`) with MD5 checksums and file metadata, persisting dossiers in SQLite (`applyease_dossier.db`).

### Feature 2: Gazette Rule Evaluator (Gemini Large-Context Engine)
1. **Multi-Page Brochure & Gazette Ingestion:** Accepts multi-page PDF notifications (30–120+ pages) via Google GenAI Files API (`client.files.upload()`).
2. **Structured Eligibility Rule Extraction:** Uses Gemini's large-context window with `GazetteRulesSchema` structured output (`response_mime_type="application/json"`) to extract:
   - **Notification Metadata:** Post name, advt number, organization, issue date, vacancy count.
   - **Key Dates:** Registration start/end dates, cutoff reference date, fee deadline, exam dates.
   - **Application Fee Matrix:** Category-wise fee breakdown (`GEN`, `OBC`, `EWS`, `SC`, `ST`, `PwBD`, `Female`) & payment modes.
   - **Age Criteria:** Reference cutoff date, min/max general age, category age relaxations (OBC +3, SC/ST +5, PwBD +10, Ex-Servicemen).
   - **Educational Qualifications:** Required degree, streams, min percentage/CGPA, mandatory experience.
   - **Reservation Rules:** OBC-NCL issue window, EWS financial year rules.
   - **Asset Upload Guidelines:** Exact photo/signature pixel dimensions, KB bounds, and file format specifications.
3. **Automatic Cleanup & SHA-256 Caching:** Deletes remote files from Google GenAI storage immediately after extraction (`client.files.delete()`) and caches parsed JSON rules in SQLite by file SHA-256 hash to eliminate duplicate API costs.

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
│   │   ├── document_schema.py      # Pydantic schemas for candidate document extractions
│   │   ├── dossier_schema.py       # Candidate Dossier & Discrepancy report schemas
│   │   └── gazette_schema.py       # Pydantic schema for Gazette Rules & Eligibility Matrices
│   ├── db/
│   │   ├── database.py             # SQLite database initialization & CRUD operations
│   ├── services/
│   │   ├── gemini_vision.py        # Gemini Flash Vision candidate document OCR extraction service
│   │   ├── gazette_evaluator.py    # Gazette Rule Evaluator service with Files API & SHA-256 caching
│   │   ├── discrepancy_engine.py   # Cross-document anomaly audit engine
│   │   ├── asset_transformer.py    # OpenCV / Pillow cropping & compression pipeline
│   │   └── storage_bucket.py       # Object storage bucket manager
│   ├── agent/
│   │   └── auditor_agent.py        # Autonomous Document Auditor Agent pipeline
│   └── api/
│       ├── app.py                  # Main FastAPI web server
│       └── gazette_router.py       # FastAPI router for Gazette Rule Evaluation
└── tests/
    ├── generate_mock_docs.py       # Synthetic candidate test document generator
    ├── generate_mock_gazette.py    # Synthetic recruitment gazette PDF generator
    ├── test_pipeline.py            # End-to-end integration test runner for Feature 1
    └── test_gazette_evaluator.py   # End-to-end integration test runner for Feature 2
```

---

## 🚀 How to Run & Test

### 1. Environment Setup
```powershell
powershell -ExecutionPolicy Bypass -File .\setup_env.ps1
```

### 2. Set API Key (Optional for Live Gemini API Calls)
```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```
*(Note: If no API key is provided, both modules automatically run with offline mock extractions for instant unit testing).*

### 3. Run Integration Test Suite
```powershell
# Feature 1 Document Auditor Test
python tests\test_pipeline.py

# Feature 2 Gazette Rule Evaluator Test
python tests\test_gazette_evaluator.py
```

### 4. Start FastAPI REST Server
```powershell
python -m uvicorn src.api.app:app --reload --port 8000
```
Open interactive OpenAPI documentation at: `http://localhost:8000/docs`

---

## 📡 API Endpoints Summary

| Module | Method | Endpoint | Description |
|---|---|---|---|
| **Dossier Auditor** | `POST` | `/api/v1/dossier/upload` | Upload candidate documents, run vision extractions, execute discrepancy audit, compress assets into bucket, and save to DB |
| **Dossier Auditor** | `GET` | `/api/v1/dossier/{candidate_id}` | Retrieve candidate profile, extracted documents, audit flags, and asset metadata |
| **Dossier Auditor** | `GET` | `/api/v1/dossier/{candidate_id}/discrepancies` | Get list of critical & warning administrative discrepancies |
| **Dossier Auditor** | `GET` | `/api/v1/dossier/{candidate_id}/asset/{filename}` | Download compressed photo, signature, or document scan from storage bucket |
| **Gazette Intelligence** | `POST` | `/api/v1/gazette/parse` | Upload recruitment PDF (up to 50MB), extract eligibility matrix with Gemini Files API, cache by SHA-256 hash, and return `GazetteRulesSchema` |
| **Gazette Intelligence** | `GET` | `/api/v1/gazette/{id_or_hash}` | Retrieve parsed gazette rules by Gazette ID or SHA-256 hash |
| **Gazette Intelligence** | `GET` | `/api/v1/gazette` | List all cached recruitment gazette notifications |
