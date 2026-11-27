"""
LOCKMATE — FastAPI Backend for Frontend Integration

Provides REST API endpoints for file upload, pipeline processing,
job status, and result retrieval.
"""

from __future__ import annotations

import os
import sys
import uuid
import shutil
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure we can import secret_wards modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from secret_wards.pipeline.full import run_pipeline
from secret_wards.utils.metrics import ProcessingMetricsCollector
from secret_wards.utils.logging import setup_logging, get_logger_adapter
from secret_wards.exceptions import LockmateError

logger = get_logger_adapter("api.server")


# =============================================================================
# Job Management
# =============================================================================

@dataclass
class JobStatus:
    """Status of a processing job."""
    job_id: str
    status: str  # pending, running, completed, failed
    stage: str = "initializing"
    progress: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    input_files: List[Dict[str, Any]] = field(default_factory=list)
    output_dir: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# In-memory job store (for demo purposes)
jobs: Dict[str, JobStatus] = {}
jobs_lock = threading.Lock()


def get_job(job_id: str) -> Optional[JobStatus]:
    with jobs_lock:
        return jobs.get(job_id)


def set_job(job: JobStatus) -> None:
    with jobs_lock:
        jobs[job.job_id] = job


def list_jobs() -> List[JobStatus]:
    with jobs_lock:
        return list(jobs.values())


# =============================================================================
# Secret Validation (extracted from main.py)
# =============================================================================

def validate_environment() -> bytes:
    """
    Validate and return RAKSHA_SECRET from environment.
    
    Returns:
        Secret as bytes (validated >=32 bytes)
        
    Raises:
        LockmateError: If secret not set or invalid
    """
    secret_env = os.environ.get("RAKSHA_SECRET")
    if not secret_env:
        raise LockmateError(
            "RAKSHA_SECRET environment variable not set. "
            "Set it to a base64 or hex encoded secret (>=32 bytes)."
        )
    
    # Try to decode as base64 first, then hex
    secret_bytes = None
    for decoder in ("base64", "hex"):
        try:
            if decoder == "base64":
                import base64
                secret_bytes = base64.b64decode(secret_env)
            else:
                secret_bytes = bytes.fromhex(secret_env)
            break
        except Exception:
            continue
    
    if secret_bytes is None:
        raise LockmateError(
            "RAKSHA_SECRET must be valid base64 or hex encoded string"
        )
    
    if len(secret_bytes) < 32:
        raise LockmateError(
            f"RAKSHA_SECRET must be at least 32 bytes (got {len(secret_bytes)} bytes)"
        )
    
    return secret_bytes


# =============================================================================
# Pipeline Execution
# =============================================================================

def run_pipeline_job(job_id: str, input_dir: Path, config_path: Path) -> None:
    """
    Background task to run the LOCKMATE pipeline.
    """
    job = get_job(job_id)
    if not job:
        return
    
    # Update job status
    job.status = "running"
    job.stage = "starting"
    job.started_at = datetime.utcnow().isoformat()
    set_job(job)
    
    try:
        secret = validate_environment()
        
        # Create isolated output directory for this job
        output_dir = Path("frontend_runs") / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        job.output_dir = str(output_dir)
        set_job(job)
        
        metrics = ProcessingMetricsCollector()
        
        # Track stage changes for progress updates
        original_stage = metrics.stage
        
        def tracking_stage(name: str):
            ctx = original_stage(name)
            original_enter = ctx.__enter__
            
            def wrapped_enter():
                result = original_enter()
                job.stage = name
                job.progress = metrics.get_totals()
                set_job(job)
                return result
            
            ctx.__enter__ = wrapped_enter
            return ctx
        
        metrics.stage = tracking_stage
        
        # Run the pipeline
        run_pipeline(
            input_dir=input_dir,
            output_dir=output_dir,
            secret=secret,
            config_path=config_path,
            metrics_collector=metrics
        )
        
        # Job completed successfully
        job.status = "completed"
        job.stage = "completed"
        job.progress = metrics.get_totals()
        job.completed_at = datetime.utcnow().isoformat()
        set_job(job)
        logger.info("job_completed", job_id=job_id)
        
    except Exception as e:
        logger.error("job_failed", job_id=job_id, error=str(e))
        job.status = "failed"
        job.stage = "failed"
        job.error = str(e)
        job.completed_at = datetime.utcnow().isoformat()
        set_job(job)
    finally:
        # Clean up staged input files (keep output)
        try:
            if input_dir.exists() and input_dir != Path("frontend_runs") / job_id:
                shutil.rmtree(input_dir, ignore_errors=True)
        except Exception:
            pass


# =============================================================================
# Pydantic Models
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


class ProcessResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobListResponse(BaseModel):
    jobs: List[Dict[str, Any]]


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    stage: str
    progress: Dict[str, Any]
    error: Optional[str]
    input_files: List[Dict[str, Any]]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]


class ReportResponse(BaseModel):
    job_id: str
    report: Dict[str, Any]


# =============================================================================
# FastAPI Application
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info("api_started")
    yield
    # Shutdown
    logger.info("api_shutdown")


app = FastAPI(
    title="LOCKMATE API",
    description="Offline Healthcare Privacy Firewall - API for frontend integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supported file extensions
SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".json", ".txt", ".jsonl"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB


def validate_upload_files(files: List[UploadFile]) -> List[UploadFile]:
    """Validate uploaded files."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    total_size = 0
    validated = []
    
    for file in files:
        # Check extension
        ext = Path(file.filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
            )
        
        # Check file size (read to check)
        content = file.file.read()
        file_size = len(content)
        file.file.seek(0)  # Reset for later reading
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)} MB"
            )
        
        total_size += file_size
        if total_size > MAX_TOTAL_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Total upload size exceeds maximum of {MAX_TOTAL_SIZE // (1024*1024*1024)} GB"
            )
        
        validated.append(file)
    
    return validated


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/api/process", response_model=ProcessResponse)
async def process_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    config_path: str = Form(default="config/policy.yaml")
):
    """
    Upload files and start sanitization pipeline.
    """
    # Validate files
    validated_files = validate_upload_files(files)
    
    # Create job
    job_id = str(uuid.uuid4())[:8]
    job = JobStatus(
        job_id=job_id,
        status="pending",
        stage="uploading",
    )
    
    # Create isolated input directory for this job
    input_dir = Path("frontend_runs") / job_id / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded files
    input_files_info = []
    for file in validated_files:
        file_path = input_dir / file.filename
        content = await file.read()
        file_path.write_bytes(content)
        
        input_files_info.append({
            "filename": file.filename,
            "size": len(content),
            "format": Path(file.filename).suffix.lower().lstrip(".")
        })
    
    job.input_files = input_files_info
    set_job(job)
    
    # Start background processing
    background_tasks.add_task(run_pipeline_job, job_id, input_dir, Path(config_path))
    
    return ProcessResponse(
        job_id=job_id,
        status="pending",
        message=f"Uploaded {len(validated_files)} files. Processing started."
    )


@app.get("/api/runs", response_model=JobListResponse)
async def list_runs():
    """List all processing runs."""
    all_jobs = list_jobs()
    # Sort by created_at descending
    all_jobs.sort(key=lambda j: j.created_at, reverse=True)
    
    return JobListResponse(
        jobs=[{
            "job_id": j.job_id,
            "status": j.status,
            "stage": j.stage,
            "created_at": j.created_at,
            "started_at": j.started_at,
            "completed_at": j.completed_at,
            "file_count": len(j.input_files),
            "error": j.error
        } for j in all_jobs]
    )


@app.get("/api/runs/{job_id}", response_model=JobStatusResponse)
async def get_run_status(job_id: str):
    """Get status of a specific job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        stage=job.stage,
        progress=job.progress,
        error=job.error,
        input_files=job.input_files,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at
    )


@app.get("/api/runs/{job_id}/report", response_model=ReportResponse)
async def get_report(job_id: str):
    """Retrieve the sanitization report for a job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    if not job.output_dir:
        raise HTTPException(status_code=404, detail="Output directory not found")
    
    report_path = Path(job.output_dir) / "report.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    import json
    report = json.loads(report_path.read_text(encoding="utf-8"))
    
    return ReportResponse(job_id=job_id, report=report)


@app.get("/api/runs/{job_id}/records")
async def get_records(job_id: str):
    """Download records.jsonl for a job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    if not job.output_dir:
        raise HTTPException(status_code=404, detail="Output directory not found")
    
    records_path = Path(job.output_dir) / "records.jsonl"
    if not records_path.exists():
        raise HTTPException(status_code=404, detail="Records file not found")
    
    return FileResponse(
        records_path,
        media_type="application/jsonl",
        filename=f"records_{job_id}.jsonl"
    )


@app.get("/api/runs/{job_id}/download")
async def download_sanitized(job_id: str):
    """Download sanitized files as ZIP."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    if not job.output_dir:
        raise HTTPException(status_code=404, detail="Output directory not found")
    
    sanitized_dir = Path(job.output_dir) / "sanitized"
    if not sanitized_dir.exists():
        raise HTTPException(status_code=404, detail="Sanitized output not found")
    
    # Create ZIP in memory
    import zipfile
    import io
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sanitized_dir.rglob("*"):
            if file_path.is_file() and "quarantined" not in file_path.parts:
                arcname = file_path.relative_to(sanitized_dir)
                zf.write(file_path, arcname)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=sanitized_{job_id}.zip"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)