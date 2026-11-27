# LOCKMATE Frontend Setup Guide

## Quick Start

### Option 1: Automated (Windows)
```cmd
run_lockmate.bat
```
This starts both backend and frontend in separate terminal windows.

### Option 2: Manual

#### Backend
```bash
cd C:\Users\samri\lockmate
set RAKSHA_SECRET=cHJhY3RpY2U=  # base64 for "practice"
python -m uvicorn secret_wards.api.server:app --host 127.0.0.1 --port 8000 --reload
```

#### Frontend
```bash
cd C:\Users\samri\lockmate\lockmate-frontend
npm run dev
```

Then open http://127.0.0.1:5173

---

## Requirements

### Backend
- Python 3.10+
- Dependencies: `pip install -e .` (from repository root)

### Frontend
- Node.js 18+
- Dependencies: `npm install` (in `lockmate-frontend/`)

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `RAKSHA_SECRET` | Yes | Base64 or hex encoded secret (≥32 bytes). Used for pseudonymization and date shifting. |
| `VITE_API_BASE` | No | Backend API URL (default: `http://127.0.0.1:8000`) |

**Generate a secret:**
```bash
# Base64 (recommended)
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"

# Or use practice secret for demo
export RAKSHA_SECRET=cHJhY3RpY2U=
```

---

## Testing with Practice Data

The repository includes practice data in the official toolkit:

```bash
# Using the official toolkit data
cd C:\Users\samri\lockmate

# Set secret
set RAKSHA_SECRET=cHJhY3RpY2U=

# Run pipeline directly (for comparison)
python main.py --input "C:\Users\samri\Secret-Wards-ToolKit\dev\input" --output test_output

# Or use the frontend:
# 1. Start backend and frontend (run_lockmate.bat)
# 2. Open http://127.0.0.1:5173
# 3. Go to Upload page
# 4. Drag files from C:\Users\samri\Secret-Wards-ToolKit\dev\input\
# 5. Click "Start Sanitization"
# 6. View results when complete
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/process` | Upload files & start processing |
| GET | `/api/runs` | List all processing runs |
| GET | `/api/runs/{job_id}` | Get job status |
| GET | `/api/runs/{job_id}/report` | Get sanitization report |
| GET | `/api/runs/{job_id}/records` | Download records.jsonl |
| GET | `/api/runs/{job_id}/download` | Download sanitized files (ZIP) |

---

## Frontend Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Overview, metrics, recent runs |
| `/upload` | Upload & Sanitize | Drag-drop upload, processing monitor |
| `/results/:jobId` | Results | Sanitized files, downloads, report summary |
| `/evaluation/:jobId` | Privacy & Evaluation | PII detection, linkage, attack simulation |

---

## Supported File Formats

- **CSV** (`.csv`) — Comma-separated values
- **TSV** (`.tsv`) — Tab-separated values  
- **JSON** (`.json`) — Nested objects, arrays
- **Text** (`.txt`) — Plain text notes
- **FHIR R4** (`.json`) — FHIR Bundles/Resources

Limits: 100 MB/file, 2 GB total per upload.

---

## Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version  # Must be 3.10+

# Reinstall dependencies
pip install -e . --force-reinstall --no-deps
pip install fastapi==0.110.0 uvicorn[standard]==0.29.0 python-multipart==0.0.9

# Check RAKSHA_SECRET
echo %RAKSHA_SECRET%
```

### Frontend won't start
```bash
cd lockmate-frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### API connection failed
- Verify backend is running on port 8000
- Check CORS: backend allows `http://localhost:5173` and `http://127.0.0.1:5173`
- Check browser console for errors

### Processing fails
- Check file formats (must be supported extensions)
- Check file sizes (≤100 MB each, ≤2 GB total)
- Check backend logs for detailed errors
- Ensure `RAKSHA_SECRET` is set correctly

### No results after processing
- Wait for job status to show "Completed"
- Check job status: `GET /api/runs/{job_id}`
- If failed, check error message in job status

---

## Project Structure

```
lockmate/
├── run_lockmate.bat           # Windows launcher
├── src/secret_wards/api/      # FastAPI backend
│   ├── __init__.py
│   └── server.py              # API endpoints
├── lockmate-frontend/         # React + Vite frontend
│   ├── src/
│   │   ├── api/client.ts      # API client & types
│   │   ├── components/        # Reusable UI components
│   │   ├── pages/             # Page components
│   │   ├── App.tsx            # Routing & layout
│   │   └── main.tsx           # Entry point
│   ├── package.json
│   └── vite.config.ts
└── docs/FRONTEND-SETUP.md     # This file
```

---

## Security Notes

- **Never commit `RAKSHA_SECRET`** to version control
- Backend binds to `127.0.0.1` only (not exposed to network)
- CORS restricted to local frontend origins
- Uploaded files stored in isolated per-job directories (`frontend_runs/{job_id}/`)
- Raw input files cleaned up after processing
- Quarantined files never exposed via API downloads
- No PII in browser storage or logs

---

## Development

### Backend Development
```bash
# Run with auto-reload
python -m uvicorn secret_wards.api.server:app --reload --port 8000
```

### Frontend Development
```bash
cd lockmate-frontend
npm run dev        # Dev server with HMR
npm run build      # Production build
npm run preview    # Preview production build
```

### Run Tests
```bash
# Backend tests
cd C:\Users\samri\lockmate
python -m pytest tests/ -v

# Frontend tests
cd lockmate-frontend
npm run test
```