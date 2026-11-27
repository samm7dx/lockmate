# LOCKMATE Frontend Inspection Report

**Repository:** `C:\Users\samri\lockmate`  
**Date:** 2026-11-27  
**Inspector:** Senior Full-Stack Engineer / Frontend Architect

---

## 1. Existing Frontend Status

**NONE.** The repository contains zero frontend code:

- No `package.json`, `vite.config.*`, `frontend/`, `ui/`, or `*.html` files
- No React, Vue, Svelte, Streamlit, Gradio, or any UI framework present
- No CSS, assets, components, or pages
- Frontend is explicitly marked **optional** in `context.md` §23

**Verdict:** Greenfield frontend implementation required.

---

## 2. Relevant Repository Structure (Inspected)

```
lockmate/
├── main.py                          # CLI entry point (run_pipeline)
├── pyproject.toml                   # Python package config, pinned deps
├── raksha.toml                      # Submission config (name, setup, run)
├── requirements.txt                 # Pinned dependencies
├── config/policy.yaml               # Pipeline configuration
├── src/secret_wards/
│   ├── contracts.py                 # 12 frozen dataclasses (THE integration contract)
│   ├── pipeline/
│   │   ├── full.py                  # Full pipeline orchestration (run_pipeline)
│   │   └── basic.py                 # Basic pipeline (Phase 3 scaffold)
│   ├── intake/
│   │   ├── pipeline.py              # File discovery, classification, parsing
│   │   ├── discovery.py             # File walking, size/nesting limits
│   │   ├── classifier.py            # Format detection (CSV/TSV/JSON/FHIR/TEXT)
│   │   ├── encoding.py              # charset-normalizer detection
│   │   └── quarantine.py            # Quarantine handling
│   ├── parsers/
│   │   ├── csv_parser.py            # CSV/TSV → URM
│   │   ├── json_parser.py           # JSON (streaming) → URM
│   │   ├── text_parser.py           # Text → URM
│   │   └── fhir_parser.py           # FHIR R4 validation → URM
│   ├── detection/                   # PII detection (names, IDs, structured)
│   ├── clinical/                    # Medical preservation (drugs, labs, diagnoses, doctors)
│   ├── transform/
│   │   └── structured.py            # Text replacement + field sanitization
│   ├── output/
│   │   ├── pipeline.py              # OutputPipeline: serialize, report, records
│   │   ├── writer.py                # Atomic writes (temp + rename)
│   │   ├── security_gate.py         # Residual PII gate (pre/post write)
│   │   ├── serializer.py            # URM → original format
│   │   └── namer.py                 # Filename sanitization
│   ├── linkage/
│   │   ├── clustering.py            # Conservative patient clustering
│   │   ├── pseudonym.py             # HMAC-SHA256 pseudonym service
│   │   ├── matching.py              # Pairwise scoring
│   │   └── identity_candidates.py   # Blocking key generation
│   ├── privacy/
│   │   ├── date_shift.py            # Patient-consistent date shifting
│   │   ├── age_generalizer.py       # Age bands (0-4, 5-9, ..., 90+)
│   │   ├── location_generalizer.py  # Village→district, PIN→prefix
│   │   ├── rare_value_suppressor.py # k-anonymity suppression
│   │   └── privacy_metrics.py       # Privacy-utility metrics collector
│   ├── evaluation/
│   │   ├── evaluation_report.py     # Engineering quality report generator
│   │   ├── attack_simulator.py      # Privacy attack simulation
│   │   ├── benchmark.py             # Performance benchmarking
│   │   └── synthetic_generator.py   # Synthetic test data
│   ├── utils/
│   │   ├── metrics.py               # ProcessingMetricsCollector, StageMetrics
│   │   ├── logging.py               # Structured JSON logging
│   │   └── temp.py                  # Encrypted temp file manager
│   └── exceptions.py                # LockmateError, QuarantineAllError, etc.
├── test_output*/                    # Sample pipeline outputs
│   ├── sanitized/                   # Sanitized files (CSV, JSON)
│   ├── report.json                  # Processing report
│   └── records.jsonl                # Patient linkage records
└── data/gazetteers/                 # Offline name/medical/location lists
```

**Key files for frontend integration:**
- `src/secret_wards/pipeline/full.py:run_pipeline()` — Main entry point
- `src/secret_wards/contracts.py` — All data schemas (FullReport, RecordsEntry, etc.)
- `src/secret_wards/output/pipeline.py:OutputPipeline` — Report/records generation
- `src/secret_wards/utils/metrics.py:ProcessingMetricsCollector` — Real-time metrics

---

## 3. Backend Execution & Integration Method

### Current Execution (CLI Only)
```bash
# Required env var
export RAKSHA_SECRET="base64_or_hex_32+_bytes"

# Run
python main.py --input /path/to/input --output /path/to/output
```

### Integration Options for Frontend

| Approach | Pros | Cons | Effort |
|----------|------|------|--------|
| **Subprocess CLI** | Zero backend changes, isolates secrets | No streaming progress, blocking | Low |
| **FastAPI wrapper** | Streaming progress, async, RESTful | New service, secret handling | Medium |
| **Direct Python import** | Fastest, shared process | Secret in same process, blocks UI | Low-Medium |

### Recommended: **FastAPI Wrapper** (Minimal)
- New file: `src/secret_wards/api/server.py`
- Exposes: `POST /api/process`, `GET /api/status/{job_id}`, `GET /api/report/{job_id}`, `GET /api/download/{job_id}/{file_type}`
- Runs `run_pipeline()` in background thread/process
- Keeps `RAKSHA_SECRET` in backend process only (never exposed to frontend)
- Frontend polls status or uses SSE/WebSocket for progress

**Why not subprocess?** Need real-time progress (stage metrics, file counts) for honest UX.
**Why not direct import?** Secret isolation + non-blocking UI.

---

## 4. Actual Available Data, Output Schemas & Metrics

### 4.1 `report.json` Schema (from `contracts.py:FullReport` + `SPEC.md`)
```json
{
  "schema": "raksha-report/1",
  "files": [
    {
      "input_sha256": "64-char-hex",
      "output": "sanitized/relative/path.csv",
      "status": "sanitized|quarantined|suppressed",
      "quarantine_reason": "unsupported_format|parse_error|residual_pii|...",
      "processing_duration_ms": 123,
      "peak_memory_mb": 45,
      "records_processed": 100,
      "identifiers_detected": 250,
      "records_linked": 95,
      "records_generalized": 100,
      "records_suppressed": 3,
      "records_quarantined": 0
    }
  ],
  "counts": {
    "files_total": 817,
    "files_sanitized": 809,
    "files_quarantined": 8,
    "records_processed": 5756,
    "identifiers_detected": 21950,
    "records_linked": 5690,
    "records_generalized": 2100,
    "records_suppressed": 3,
    "records_quarantined": 0,
    "total_processing_duration_ms": 41200,
    "peak_memory_mb": 380
  },
  "entities": {"PATIENT_NAME": 6600, "PHONE": 1540, ...},
  "timing": {"seconds": 41.2},
  "resources": {"peak_rss_mb": 380.5}
}
```

### 4.2 `records.jsonl` Schema (from `contracts.py:RecordsEntry` + `SPEC.md`)
```jsonl
{"file": "sanitized/registration/sanjeevani_registration.csv", "loc": "row:12", "patient": "PSN-7Q2K9D"}
{"file": "sanitized/opd/sanjeevani_opd_2026_10.json", "loc": "/visits/3", "patient": "PSN-7Q2K9D"}
{"file": "sanitized/discharge/doc_0007.txt", "loc": "doc", "patient": "PSN-7Q2K9D"}
{"file": "sanitized/registration/arogya_legacy_export.csv", "loc": "row:40", "out": "row:39", "patient": "PSN-11XQ0A", "status": "generalized"}
```

### 4.3 Sanitized Files
- **Location:** `output/sanitized/` (mirrors input structure, filenames sanitized)
- **Formats:** CSV→CSV, TSV→TSV, JSON→JSON, FHIR→valid FHIR R4, Text→Text
- **Encoding:** UTF-8 only
- **Pseudonyms injected** into records (e.g., `patient_ref` column, `Patient.id`)

### 4.4 Quarantine Results
- **Location:** `output/sanitized/quarantined/` (NOT part of release per SPEC)
- **Original files copied** with SHA-256 names
- **Reported in** `report.json` with `status: "quarantined"` and `reason`

### 4.5 Real-Time Metrics (from `ProcessingMetricsCollector`)
Available per-stage during pipeline execution:
```python
{
  "stage_name": "intake_and_parse",
  "duration_ms": 15000,
  "peak_memory_mb": 512,
  "records_processed": 0,
  "identifiers_detected": 0,
  "records_linked": 0,
  "records_generalized": 0,
  "records_suppressed": 0,
  "records_quarantined": 2
}
```
Stages: `intake_and_parse`, `sanitize_{sha8}`, `patient_linkage`, `output_and_reports`

### 4.6 Privacy & Evaluation Metrics (from `privacy_metrics.py` + `evaluation_report.py`)
```json
{
  "privacy_metrics": {
    "total_records": 5756,
    "records_with_date_shift": 5756,
    "records_age_generalized": 5756,
    "records_location_generalized": 5756,
    "records_suppressed": 3,
    "age_band_distribution": {"25-29": 800, "30-34": 750, ...},
    "location_level_distribution": {"district": 4000, "state": 1756},
    "date_shift_distribution": {"1-30": 1200, "31-90": 2000, ...},
    "interval_preservation_rate": 1.0,
    "los_preservation_rate": 1.0,
    "rare_combinations_detected": 15,
    "combinations_generalized": 10,
    "combinations_suppressed": 3,
    "k_anonymity_threshold": 5,
    "clinical_preservation_rate": 0.987
  },
  "linkage_metrics": {
    "clusters_formed": 4200,
    "singletons": 1500,
    "records_linked": 5690,
    "precision": 0.99,
    "recall": 0.95,
    "f05": 0.98
  },
  "attack_simulation": {
    "direct_identifier": {"success_rate": 0.0, "protected": 5756},
    "voter_list_linkage": {"success_rate": 0.02, "protected": 5600},
    "quasi_identifier": {"success_rate": 0.05, "protected": 5400},
    "rare_disease": {"success_rate": 0.10, "protected": 5100},
    "known_visit_date": {"success_rate": 0.0, "protected": 5756},
    "length_of_stay": {"success_rate": 0.03, "protected": 5500},
    "pseudonym_inversion": {"success_rate": 0.0, "protected": 5756},
    "cross_release": {"success_rate": 0.0, "protected": 5756}
  }
}
```

---

## 5. Recommended Frontend Technology Stack

### Decision: **React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui + FastAPI**

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Framework** | React 18 + TypeScript | Industry standard, great DX, type-safe contracts |
| **Build** | Vite 5 | Instant HMR, optimized builds, zero config |
| **Styling** | Tailwind CSS + shadcn/ui | Professional healthcare look, accessible components, dark mode |
| **State** | TanStack Query (React Query) | Server state, polling, caching, mutations |
| **Charts** | Recharts | Lightweight, composable, SSR-safe |
| **API** | FastAPI (Python) | Native async, auto OpenAPI, Pydantic matches contracts |
| **Process** | Background thread + SSE | Real-time progress without separate worker infra |

### Project Structure (Frontend)
```
lockmate-frontend/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/
│   │   ├── client.ts          # TanStack Query hooks
│   │   └── types.ts           # TypeScript interfaces from contracts.py
│   ├── components/
│   │   ├── ui/                # shadcn/ui components
│   │   ├── dashboard/         # Dashboard widgets
│   │   ├── upload/            # Dropzone, file list, progress
│   │   ├── results/           # Report tables, download buttons
│   │   ├── privacy/           # Attack simulation charts, metrics
│   │   └── demo/              # Before/after viewer, linkage explorer
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Upload.tsx
│   │   ├── Results.tsx
│   │   ├── Privacy.tsx
│   │   └── Demo.tsx
│   ├── hooks/
│   │   ├── usePipeline.ts     # SSE connection, polling
│   │   └── useReport.ts       # Report data fetching
│   └── utils/
│       ├── formatters.ts      # Bytes, duration, percentages
│       └── constants.ts       # PII types, quarantine reasons
└── public/
```

---

## 6. Proposed Screen Layout & Navigation

### Navigation (Left Sidebar - Persistent)
```
LOCKMATE 🛡️
├── Dashboard          ← Landing, overview, recent runs
├── Upload & Sanitize  ← Drag-drop, batch, start, live progress
├── Results            ← Sanitized files, report.json, records.jsonl
├── Privacy & Eval     ← PII leaks, linkage, clinical, attacks, runtime
└── Demo View          ← Judge presentation mode (full-screen)
```

### Screen Details

#### 1. Dashboard (`/`)
- **Header:** LOCKMATE — Offline Healthcare Privacy Firewall
- **Stats Cards (4):** Files Processed, PII Detected, Patients Linked, Quarantined
- **Recent Runs Table:** Timestamp, Input Path, Status, Duration, Files, Records
- **Quick Actions:** "New Run" button → navigates to Upload

#### 2. Upload & Sanitize (`/upload`)
- **Dropzone:** Multi-file/folder (webkitdirectory), shows detected formats
- **File List:** Name, Size, Format, SHA-256 (truncated), Status (pending/processing/done/error)
- **Batch Controls:** Select all, Clear, "Start Sanitization" (disabled until files added)
- **Live Progress Panel (SSE):**
  - Stage pills: Intake → Detection → Linkage → Privacy → Output
  - Per-file progress bars
  - Real-time metrics: files/sec, records/sec, memory, PII count
  - Error toast with quarantine reason

#### 3. Results (`/results/{run_id}`)
- **Tabs:** Sanitized Files | Report.json | Records.jsonl | Quarantine
- **Sanitized Files:** Tree view, download buttons (per-file + bulk ZIP), search
- **Report.json:** Rendered JSON with collapsible sections, copy button
- **Records.jsonl:** Virtualized table (file, loc, patient, status), filter by patient
- **Quarantine:** Table (file, reason, details), download original for inspection

#### 4. Privacy & Evaluation (`/privacy/{run_id}`)
- **Tabs:** PII Detection | Patient Linkage | Clinical Preservation | Privacy Attacks | Runtime
- **PII Detection:** Bar chart by type (NAME, PHONE, AADHAAR, ...), by script (Latin/Devanagari/Hinglish), by channel (text, JSON key, filename)
- **Patient Linkage:** Clusters table, precision/recall/F0.5, false merge count
- **Clinical Preservation:** Preservation rate per category (drugs, labs, diagnoses, dosages, vitals)
- **Privacy Attacks:** Radar chart of 8 attack success rates, target: all < 5%
- **Runtime:** Stage timing waterfall, memory timeline, determinism badge

#### 5. Demo View (`/demo/{run_id}`)
- **Full-screen presentation mode** (no sidebar, no chrome)
- **Sections (auto-advance or manual):**
  1. Problem: Raw input with PII highlighted
  2. Pipeline: Animated stage flow with sample record
  3. Identity: Cross-hospital patient → stable pseudonym
  4. Clinical: Before/After diff — identity gone, medicine preserved
  5. Privacy: Attack simulation results → measured failure
  6. Verification: Sanitized output tree, report.json, records.jsonl, `CONTRACT OK`
- **Keyboard navigation:** Space/Arrow keys, `F` fullscreen, `Esc` exit

---

## 7. Exact Backend Integration Requirements

### 7.1 New FastAPI Server (`src/secret_wards/api/server.py`)
```python
from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import uuid
import threading
import json
import os

app = FastAPI(title="LOCKMATE API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# In-memory job store (replace with Redis for production)
jobs: dict[str, dict] = {}

class ProcessRequest(BaseModel):
    input_dir: str
    config_path: str = "config/policy.yaml"

class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, running, completed, failed
    stage: str
    progress: dict  # ProcessingMetricsCollector.get_totals()
    error: str | None = None

@app.post("/api/process")
async def start_processing(request: ProcessRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "pending", "stage": "initializing", "progress": {}, "error": None, "output_dir": None}
    background_tasks.add_task(run_pipeline_job, job_id, request.input_dir, request.config_path)
    return {"job_id": job_id}

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    return jobs[job_id]

@app.get("/api/status/{job_id}/stream")
async def stream_status(job_id: str):
    # SSE endpoint for real-time updates
    async def event_generator():
        last_progress = {}
        while True:
            job = jobs.get(job_id)
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break
            if job["progress"] != last_progress:
                yield f"data: {json.dumps(job['progress'])}\n\n"
                last_progress = job["progress"]
            if job["status"] in ("completed", "failed"):
                yield f"data: {json.dumps({'status': job['status'], 'final': True})}\n\n"
                break
            await asyncio.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/report/{job_id}")
async def get_report(job_id: str):
    job = jobs.get(job_id)
    if not job or job["status"] != "completed":
        raise HTTPException(404, "Report not ready")
    report_path = Path(job["output_dir"]) / "report.json"
    return FileResponse(report_path, media_type="application/json")

@app.get("/api/records/{job_id}")
async def get_records(job_id: str):
    job = jobs.get(job_id)
    if not job or job["status"] != "completed":
        raise HTTPException(404, "Records not ready")
    records_path = Path(job["output_dir"]) / "records.jsonl"
    return FileResponse(records_path, media_type="application/json")

@app.get("/api/download/{job_id}/{file_type}")
async def download_output(job_id: str, file_type: str):
    job = jobs.get(job_id)
    if not job or job["status"] != "completed":
        raise HTTPException(404, "Output not ready")
    
    output_dir = Path(job["output_dir"])
    if file_type == "sanitized":
        # Create ZIP of sanitized/
        import zipfile, io
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in (output_dir / "sanitized").rglob("*"):
                if file_path.is_file() and "quarantined" not in file_path.parts:
                    zf.write(file_path, file_path.relative_to(output_dir))
        zip_buffer.seek(0)
        return StreamingResponse(zip_buffer, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=sanitized.zip"})
    elif file_type == "quarantined":
        # Similar for quarantined
        ...
    raise HTTPException(400, "Invalid file_type")

def run_pipeline_job(job_id: str, input_dir: str, config_path: str):
    from secret_wards.pipeline.full import run_pipeline
    from secret_wards.utils.metrics import ProcessingMetricsCollector
    
    jobs[job_id]["status"] = "running"
    jobs[job_id]["stage"] = "starting"
    
    secret = validate_environment()  # From main.py
    output_dir = Path(f"frontend_runs/{job_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    jobs[job_id]["output_dir"] = str(output_dir)
    
    metrics = ProcessingMetricsCollector()
    
    # Monkey-patch to capture stage metrics for SSE
    original_stage = metrics.stage
    def tracking_stage(name):
        ctx = original_stage(name)
        original_enter = ctx.__enter__
        def wrapped_enter():
            result = original_enter()
            jobs[job_id]["stage"] = name
            jobs[job_id]["progress"] = metrics.get_totals()
            return result
        ctx.__enter__ = wrapped_enter
        return ctx
    metrics.stage = tracking_stage
    
    try:
        run_pipeline(
            input_dir=Path(input_dir),
            output_dir=output_dir,
            secret=secret,
            config_path=Path(config_path),
            metrics_collector=metrics
        )
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = metrics.get_totals()
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

def validate_environment() -> bytes:
    # Copy from main.py:106-137
    ...
```

### 7.2 Required Backend Changes (Minimal)

| File | Change | Lines |
|------|--------|-------|
| `src/secret_wards/api/server.py` | **NEW** FastAPI server | ~150 |
| `src/secret_wards/api/__init__.py` | **NEW** package init | 1 |
| `pyproject.toml` | Add `fastapi`, `uvicorn`, `python-multipart` | +3 deps |
| `main.py` | Extract `validate_environment()` to shared module | Refactor |

### 7.3 Missing API Functionality (Frontend Needs)
1. **SSE streaming** for real-time stage metrics (implemented above)
2. **File upload endpoint** (multipart) → frontend sends files to backend temp dir
3. **Run listing** → `GET /api/runs` for Dashboard recent runs
4. **Cancel endpoint** → `POST /api/cancel/{job_id}` for long runs
5. **Config validation** → `GET /api/config/schema` for UI form generation

---

## 8. Security Considerations

### 8.1 What Must NEVER Reach Frontend
| Secret/Data | Risk | Mitigation |
|-------------|------|------------|
| `RAKSHA_SECRET` | Pseudonym/date-shift inversion | **Backend-only env var**, never in API response, never logged |
| Pseudonym mappings | Re-identification | Only in `records.jsonl` (sanitized output), never raw map |
| Patient PII (names, IDs) | Direct leakage | Output security gate validates; frontend only sees sanitized |
| Canary values | Pipeline bypass detection | Only in logs/temp (scanned), never in API |
| Raw input files | PII exposure | Frontend uploads → backend temp → processed → deleted |

### 8.2 Frontend Security Practices
- **No localStorage/sessionStorage** for any pipeline data
- **HTTPS in production** (dev: localhost only)
- **CSP headers** on FastAPI responses
- **Input validation** on upload (size, type, filename sanitization)
- **No PII in URLs** — use job IDs, not filenames
- **Auto-cleanup** — frontend runs auto-expire after 24h (configurable)

### 8.3 Backend Security (Already Implemented)
- `TempFileManager` encrypts temp files with AES-GCM (key from `RAKSHA_SECRET`)
- Structured JSON logging — **no raw text** (see `utils/logging.py`)
- `ResidualPIIGate` scans output pre/post write
- Canary injection + verification
- Atomic writes prevent partial exposure

---

## 9. Existing Components & Code Reusable

### Backend (Directly Usable)
| Module | Exports | Frontend Use |
|--------|---------|--------------|
| `contracts.py` | All dataclasses + `to_dict()` | TypeScript interfaces (auto-generate) |
| `utils/metrics.py` | `ProcessingMetricsCollector`, `StageMetrics` | Real-time progress SSE |
| `output/pipeline.py` | `OutputPipeline` | Report/records generation |
| `evaluation/attack_simulator.py` | `PrivacyAttackSimulator` | Privacy attack dashboard data |
| `privacy/privacy_metrics.py` | `PrivacyMetricsCollector` | Privacy metrics panel |
| `pipeline/full.py` | `run_pipeline()` | Core processing function |

### TypeScript Interface Generation
```bash
# Option 1: Manual (recommended for control)
# Copy contracts.py schemas → src/api/types.ts

# Option 2: Automated (datamodel-code-generator)
pip install datamodel-code-generator
datamodel-codegen --input src/secret_wards/contracts.py --output src/api/types.ts --input-file-type python
```

### No Existing Frontend Code to Reuse
- Zero components, styles, or utilities exist
- All UI built from shadcn/ui primitives

---

## 10. Most Efficient Implementation Approach

### Phase 1: Backend API (Day 1, 2-3 hrs)
1. Create `src/secret_wards/api/server.py` with FastAPI + SSE
2. Add `fastapi`, `uvicorn[standard]`, `python-multipart` to `pyproject.toml`
3. Extract `validate_environment()` from `main.py` to `src/secret_wards/utils/secrets.py`
4. Test: `uvicorn secret_wards.api.server:app --reload` → `POST /api/process`

### Phase 2: Frontend Scaffold (Day 1, 1-2 hrs)
1. `npm create vite@latest lockmate-frontend -- --template react-ts`
2. `cd lockmate-frontend && npm install`
3. `npx shadcn-ui@latest init` (Tailwind, neutral slate, CSS variables)
4. Add TanStack Query: `npm install @tanstack/react-query`
5. Configure API client with base URL `http://localhost:8000`

### Phase 3: Core Screens (Day 2, 4-5 hrs)
| Screen | Components | API Calls |
|--------|------------|-----------|
| Upload | Dropzone, FileTable, ProgressPanel (SSE) | `POST /api/process`, `GET /api/status/{id}/stream` |
| Results | TabView, FileTree, ReportViewer, RecordsTable | `GET /api/report/{id}`, `GET /api/records/{id}`, `GET /api/download/{id}/sanitized` |
| Privacy | MetricCards, BarCharts, RadarChart, DataTables | Embedded in report.json + separate `/api/privacy/{id}` |

### Phase 4: Dashboard & Demo (Day 2, 2-3 hrs)
- Dashboard: Recent runs from `GET /api/runs` (new endpoint)
- Demo: Full-screen presentation component, keyboard nav

### Phase 5: Polish & Security (Day 3, 2 hrs)
- Dark mode, responsive breakpoints
- Error boundaries, loading skeletons
- Security audit: no secrets in bundle, CSP, no localStorage
- Run `validate_output.py` on test output → verify `CONTRACT OK`

---

## Summary: Current Frontend Readiness

| Aspect | Status | Notes |
|--------|--------|-------|
| Frontend code | **0%** | Greenfield |
| Backend API | **0%** | Needs FastAPI wrapper |
| Data schemas | **100%** | `contracts.py` complete |
| Output formats | **100%** | `report.json`, `records.jsonl` validated |
| Real-time metrics | **90%** | `ProcessingMetricsCollector` exists, needs SSE exposure |
| Privacy metrics | **80%** | Modules exist, need API endpoint |
| Security model | **95%** | Backend solid, frontend must not leak |

---

## Exact Technology Stack to Use

```
Frontend:
  React 18 + TypeScript + Vite 5
  Tailwind CSS 3.4 + shadcn/ui (latest)
  TanStack Query 5 (server state)
  Recharts 2 (charts)
  Lucide React (icons)
  date-fns (date formatting)
  clsx + tailwind-merge (class utilities)

Backend API:
  FastAPI 0.110 + Uvicorn
  Pydantic 2 (validation)
  SSE via StreamingResponse
  python-multipart (file upload)

Dev Tools:
  ESLint + Prettier + TypeScript strict
  Vitest (unit tests)
  Playwright (e2e)
```

---

## Recommended Application Structure

```
lockmate/
├── src/secret_wards/api/          # NEW: FastAPI backend
│   ├── __init__.py
│   └── server.py
├── lockmate-frontend/             # NEW: React app
│   ├── src/
│   │   ├── api/                   # TanStack Query hooks + types
│   │   ├── components/            # Reusable UI components
│   │   ├── pages/                 # 5 route pages
│   │   ├── hooks/                 # Custom hooks (SSE, polling)
│   │   └── utils/                 # Formatters, constants
│   └── public/
├── frontend_runs/                 # Auto-created per-job output (gitignored)
├── docs/frontend-inspection.md    # THIS FILE
└── pyproject.toml                 # Updated with FastAPI deps
```

---

## Minimum Backend Changes Required

1. **`src/secret_wards/api/server.py`** — New FastAPI server (~150 lines)
2. **`src/secret_wards/api/__init__.py`** — Package init
3. **`src/secret_wards/utils/secrets.py`** — Extract `validate_environment()` from `main.py`
4. **`pyproject.toml`** — Add `fastapi==0.110.0`, `uvicorn[standard]==0.29.0`, `python-multipart==0.0.9`
5. **`main.py`** — Import `validate_environment` from shared module

---

## Most Important Implementation Tasks (Execution Order)

| # | Task | Effort | Dependencies |
|---|------|--------|--------------|
| 1 | Create FastAPI server with SSE streaming | 2-3 hrs | None |
| 2 | Scaffold React + Vite + Tailwind + shadcn/ui | 1-2 hrs | None |
| 3 | Implement Upload screen + SSE progress | 2-3 hrs | #1, #2 |
| 4 | Implement Results screen (report, records, downloads) | 2 hrs | #1, #2 |
| 5 | Implement Privacy & Evaluation screen | 2-3 hrs | #1, #2, #4 |
| 6 | Implement Dashboard (recent runs) | 1 hr | #1, #2 |
| 7 | Implement Demo View (presentation mode) | 1-2 hrs | #2, #4 |
| 8 | Security hardening + `validate_output.py` verification | 1-2 hrs | All |
| 9 | Polish: dark mode, responsive, error handling | 1-2 hrs | All |

**Total estimated: ~14-20 hours over 2-3 days.**

---

## Verification Checklist (Before Demo)

- [ ] `python main.py --input dev/input --output test_out` → works
- [ ] `python3 validate_output.py --input dev/input --output test_out` → `CONTRACT OK`
- [ ] `uvicorn secret_wards.api.server:app --reload` → API responds
- [ ] Frontend upload → backend processes → report.json generated
- [ ] SSE progress updates in real-time during processing
- [ ] Download sanitized.zip → extracts valid CSV/JSON
- [ ] Privacy attack dashboard shows <5% success rates
- [ ] Demo view runs full-screen, keyboard navigable
- [ ] No `RAKSHA_SECRET` in frontend bundle, network tab, or localStorage
- [ ] Dark mode + responsive (mobile breakpoint) works