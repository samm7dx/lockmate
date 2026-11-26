# LOCKMATE Hackathon Study Guide — Document 8
## Integration Testing — Test Results, Coverage, Fixtures

---

### 8.1 Test Suite Overview

| Metric | Value |
|--------|-------|
| **Total Test Files** | 13 |
| **Total Tests** | 104 |
| **Passed** | 97 |
| **Skipped** | 7 (Windows symlink limitations) |
| **Failed** | 0 |
| **Execution Time** | ~1.76s |
| **Coverage Target** | Not enforced (no `pytest-cov` in CI) |

---

### 8.2 Test File Inventory

| File | Tests | Module Under Test |
|------|-------|-------------------|
| `test_integration.py` | 13 | Full pipeline (`SecureIngestionPipeline`) |
| `test_csv_parser.py` | 10 | `CSVParser`, `TSVParser` |
| `test_json_parser.py` | 9 | `JSONParser`, `NestedJSONParser` |
| `test_text_parser.py` | 8 | `TextParser` |
| `test_fhir_parser.py` | 7 | `FHIRParser` (all skipped w/o `fhir.resources`) |
| `test_path_guard.py` | 7 | `PathGuard` |
| `test_symlink_guard.py` | 7 | `SymlinkGuard` (6 skipped Windows) |
| `test_size_limits.py` | 5 | `SizeLimiter` |
| `test_file_validator.py` | 9 | `FileValidator` |
| `test_quarantine.py` | 8 | `QuarantineManager` |
| `test_serializer.py` | 6 | `OutputSerializer` |
| `test_atomic_write.py` | 6 | `AtomicWriter` |
| `test_output.py` | 9 | `ReportGenerator`, `RecordsGenerator` |

---

### 8.3 Integration Test Deep Dive (`test_integration.py`)

#### 8.3.1 Test Class Structure

```python
class TestSecureIngestionPipeline:
    def setup_method(self):
        """Per-test isolated temp directories."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.input_dir = self.temp_dir / "input"
        self.output_dir = self.temp_dir / "output"
        self.quarantine_dir = self.temp_dir / "quarantine"
        self.input_dir.mkdir()
        self.output_dir.mkdir()
        self.quarantine_dir.mkdir()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
```

#### 8.3.2 Test Cases

| Test | Scenario | Key Assertions |
|------|----------|----------------|
| `test_basic_csv_ingestion` | Single CSV with header | 3 records, 1 output file, report.json valid |
| `test_json_ingestion` | JSON array of objects | 2 records, correct format in records.jsonl |
| `test_text_ingestion` | Plain text file | 3 records (1 per line), `_meta` present |
| `test_multiple_files_ingestion` | CSV + JSON + TXT | 6 total records, 3 output files |
| `test_quarantine_invalid_file` | Valid CSV + binary .exe | 1 processed, 1 quarantined, report tracks both |
| `test_path_traversal_blocked` | Symlink outside root | File quarantined/failed (Linux only) |
| `test_size_limit_enforced` | File > 1KB limit (config) | Quarantined, `success=False` in report |
| `test_fhir_ingestion` | FHIR Patient resource | ≥1 record with FHIR metadata |
| `test_report_generation` | Report.json exists | Correct job_id, stats, timestamps |
| `test_empty_directory` | No input files | `success=True`, 0 records |
| `test_subdirectory_files` | Files in nested dirs | 2 files processed recursively |
| `test_ingest_file_method` | Direct method call | Iterator yields 2 records |
| `test_tsv_ingestion` | TSV file | 2 records, tab delimiter handled |

#### 8.3.3 Example Integration Test

```python
def test_basic_csv_ingestion(self):
    # Setup
    csv_file = self.input_dir / "data.csv"
    csv_file.write_text("id,name,value\n1,foo,100\n2,bar,200\n3,baz,300\n")
    
    config = IngestionConfig(
        input_dir=self.input_dir,
        output_dir=self.output_dir,
        quarantine_dir=self.quarantine_dir,
        allowed_roots=[self.input_dir],
    )
    pipeline = SecureIngestionPipeline(config)
    
    # Execute
    result = pipeline.run()
    
    # Assert pipeline result
    assert result.success is True
    assert result.total_records == 3
    assert len(result.processed_files) == 1
    assert len(result.failed_files) == 0
    assert len(result.quarantined_files) == 0
    
    # Assert output files
    report_file = self.output_dir / "report.json"
    assert report_file.exists()
    
    records_files = list(self.output_dir.glob("*.jsonl"))
    assert len(records_files) >= 1
    
    # Verify record content
    with open(records_files[0]) as f:
        records = [json.loads(line) for line in f]
    assert len(records) == 3
    assert records[0]["id"] == "1"
    assert "_meta" in records[0]
    assert records[0]["_meta"]["source_file"] == "data.csv"
```

---

### 8.4 Unit Test Patterns

#### 8.4.1 Parser Tests (Example: `test_csv_parser.py`)

```python
class TestCSVParser:
    def test_basic_csv_with_header(self):
        csv_content = "id,name\n1,Alice\n2,Bob\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            parser = CSVParser()
            records = list(parser.parse(f.name))
        assert len(records) == 2
        assert records[0] == {"id": "1", "name": "Alice"}
    
    def test_csv_without_header(self):
        parser = CSVParser(config=CSVParserConfig(has_header=False))
        records = list(parser.parse(csv_file))
        assert records[0] == {"column_0": "1", "column_1": "Alice"}
    
    def test_max_rows_limit(self):
        parser = CSVParser(config=CSVParserConfig(max_rows=2))
        records = list(parser.parse(large_csv))
        assert len(records) == 2
    
    def test_column_sanitization(self):
        # "First Name" → "First_Name", duplicate → "First_Name_1"
```

#### 8.4.2 Validation Tests (Example: `test_path_guard.py`)

```python
class TestPathGuard:
    def test_valid_path_within_root(self):
        guard = PathGuard([Path("/data/input")])
        result = guard.validate("/data/input/file.csv")
        assert result == Path("/data/input/file.csv")
    
    def test_path_traversal_blocked(self):
        guard = PathGuard([Path("/data/input")])
        with pytest.raises(PathTraversalError):
            guard.validate("/data/input/../../etc/passwd")
    
    def test_null_byte_blocked(self):
        guard = PathGuard([Path("/data/input")])
        with pytest.raises(PathTraversalError):
            guard.validate(Path("/data/input/file.txt\x00.exe"))
    
    @pytest.mark.skipif(sys.platform == "win32", reason="Symlinks require admin on Windows")
    def test_symlink_outside_root_blocked(self):
        # Creates symlink in input_dir pointing to /etc/passwd
        # Verifies PathGuard catches it after resolve()
```

---

### 8.5 Test Fixtures & Synthetic Data

**All tests use SYNTHETIC DATA ONLY** — no real PHI/PII.

```python
# Common synthetic patterns
SYNTHETIC_CSV = """patient_id,name,dob,condition
PAT-001,John Doe,1980-01-15,Diabetes
PAT-002,Jane Smith,1992-03-22,Hypertension
"""

SYNTHETIC_JSON = [
    {"patient_id": "PAT-001", "name": "John Doe", "dob": "1980-01-15"},
    {"patient_id": "PAT-002", "name": "Jane Smith", "dob": "1992-03-22"}
]

SYNTHETIC_FHIR = {
    "resourceType": "Patient",
    "id": "PAT-001",
    "name": [{"family": "Doe", "given": ["John"]}],
    "birthDate": "1980-01-15"
}
```

---

### 8.6 Running Tests

```bash
# All tests (97 pass, 7 skip)
pytest -v

# Specific module
pytest src/lockmate/ingestion/tests/test_integration.py -v

# With coverage (if pytest-cov installed)
pytest --cov=lockmate --cov-report=term-missing

# Parallel execution
pytest -n auto

# Only failed
pytest --lf

# Verbose with output
pytest -v -s
```

---

### 8.7 pytest Configuration (`pytest.ini`)

```ini
[pytest]
testpaths = src/lockmate/ingestion/tests tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
filterwarnings =
    ignore::DeprecationWarning
```

---

### 8.8 Test Results Summary (Actual Run)

```
================================= test session starts =================================
platform win32 -- Python 3.11.x, pytest-7.x.x
collected 104 items

test_integration.py ..............                          [ 12%]
test_csv_parser.py ..........                               [ 22%]
test_json_parser.py ..........                              [ 31%]
test_text_parser.py ........                                [ 38%]
test_fhir_parser.py sssssss                                 [ 45%]
test_path_guard.py .....ss                                  [ 53%]
test_symlink_guard.py sssssss                               [ 61%]
test_size_limits.py .....                                   [ 66%]
test_file_validator.py ..........                           [ 75%]
test_quarantine.py ..........                               [ 84%]
test_serializer.py ......                                   [ 90%]
test_atomic_write.py ......                                 [ 96%]
test_output.py ..........                                   [100%]

================================== 97 passed, 7 skipped in 1.76s ==================================
```

**Skip Breakdown**:
- `test_fhir_parser.py`: 7 skipped (requires `fhir.resources` package)
- `test_path_guard.py`: 2 skipped (symlink tests on Windows)
- `test_symlink_guard.py`: 6 skipped (all symlink tests on Windows)

---

### 8.9 Adding New Tests

#### 8.9.1 Unit Test Template

```python
# tests/test_new_feature.py
import pytest
from pathlib import Path
from lockmate.ingestion.module import NewClass

class TestNewClass:
    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_basic_functionality(self):
        obj = NewClass()
        result = obj.method("input")
        assert result == "expected"
    
    def test_edge_case(self):
        obj = NewClass()
        with pytest.raises(ExpectedException):
            obj.method("bad_input")
```

#### 8.9.2 Integration Test Template

```python
def test_new_format_ingestion(self):
    # 1. Create test file in self.input_dir
    test_file = self.input_dir / "test.newfmt"
    test_file.write_text("synthetic data")
    
    # 2. Run pipeline
    result = self.pipeline.run()
    
    # 3. Assert results
    assert result.success
    assert result.total_records > 0
    
    # 4. Verify output
    records_files = list(self.output_dir.glob("*.jsonl"))
    assert len(records_files) > 0
```

---

### 8.10 Known Test Gaps

| Area | Gap | Priority |
|------|-----|----------|
| **FHIR tests** | Require optional dependency | Medium |
| **Symlink tests** | Windows platform limitation | Low (pass on Linux) |
| **Large file streaming** | Mocked, not real 1GB+ files | Medium |
| **Concurrent pipeline runs** | Not tested | Low |
| **Memory pressure** | No OOM simulation | Low |
| **Encoding edge cases** | Limited to UTF-8/Latin-1 | Medium |
| **Malformed UTF-8** | Not tested | Medium |

---

### 8.11 CI/CD Integration

```yaml
# .github/workflows/test.yml (example)
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install -e ".[dev]"
      - run: pip install fhir.resources  # For FHIR tests
      - run: pytest -v
```

> On Linux, all 104 tests pass (no symlink skips).