# LOCKMATE Hackathon Study Guide — Document 4
## Format Parsers — CSV, JSON, Text, FHIR

---

### 4.1 Parser Architecture Overview

All parsers implement a common iterator interface:

```python
class BaseParser(Protocol):
    def parse(
        self,
        file_path: Union[str, Path],
        encoding: Optional[str] = None
    ) -> Iterator[dict[str, Any]]: ...
```

Each parser yields **one dictionary per record** (row, object, line, resource).

---

### 4.2 CSV/TSV Parser (`csv_parser.py` — 144 lines)

**Classes**: `CSVParser`, `TSVParser` (subclass), `CSVParserConfig`

```python
class CSVParserConfig(BaseModel):
    delimiter: str = ","
    has_header: bool = True
    encoding: str = "utf-8"
    skip_blank_lines: bool = True
    max_rows: int | None = None
    quote_char: str = '"'
    escape_char: str = "\\"
    # Pandas-specific
    dtype: dict | None = None
    na_values: list[str] | None = None
    keep_default_na: bool = True
```

**TSVParser** overrides: `delimiter = "\t"`, `has_header = True`

**Parsing Flow**:
```python
def parse(self, file_path, encoding=None) -> Iterator[dict]:
    # 1. Read with pandas (streaming via chunksize for large files)
    # 2. Validate column names (no duplicates after sanitization)
    # 3. Yield each row as dict with sanitized keys
    # 4. Handle NaN/None values per config
```

**Key Features**:
| Feature | Implementation |
|---------|----------------|
| Streaming | `pd.read_csv(chunksize=10000)` for large files |
| Column Sanitization | `[^a-zA-Z0-9_]` → `_`, dedup with `_1`, `_2` |
| Type Inference | Pandas default + `dtype` override |
| Missing Values | Configurable `na_values`, `keep_default_na` |
| Encoding | UTF-8 default, configurable |

**Test Coverage** (`test_csv_parser.py`):
- ✅ Basic CSV with header
- ✅ CSV without header (auto columns)
- ✅ TSV parsing
- ✅ Custom delimiter
- ✅ Skip blank lines
- ✅ Max rows limit
- ✅ Encoding (UTF-8, Latin-1)
- ✅ NaN handling
- ✅ Column name sanitization
- ✅ Large file streaming (mocked)

---

### 4.3 JSON Parser (`json_parser.py` — 191 lines)

**Classes**: `JSONParser`, `NestedJSONParser`, `JSONParserConfig`

```python
class JSONParserConfig(BaseModel):
    use_orjson: bool = True           # orjson for speed
    max_depth: int = 100              # Prevent stack overflow
    max_file_size: int = 100 * 1024 * 1024
    array_mode: str = "items"         # "items" or "whole"
    encoding: str = "utf-8"
```

**Modes**:
| `array_mode` | Behavior |
|--------------|----------|
| `"items"` (default) | JSON array → yield each element as record |
| `"whole"` | Entire file → single record with `data` key |

**NestedJSONParser** — Flattens nested objects:
```python
# Input: {"patient": {"name": "John", "address": {"city": "Boston"}}}
# Output: {"patient.name": "John", "patient.address.city": "Boston"}
```

**Parsing Flow**:
```python
def parse(self, file_path, encoding=None) -> Iterator[dict]:
    # 1. Check file size
    # 2. Read entire file (JSON requires full parse)
    # 3. Parse with orjson (fast) or stdlib json
    # 4. If dict → yield as single record
    # 5. If list → iterate based on array_mode
    # 6. Track depth to prevent DoS
```

**Test Coverage** (`test_json_parser.py`):
- ✅ Simple JSON object
- ✅ JSON array (items mode)
- ✅ JSON array (whole mode)
- ✅ Nested JSON flattening
- ✅ Empty array
- ✅ Invalid JSON → exception
- ✅ Large file size limit
- ✅ Max depth exceeded
- ✅ orjson vs json parity

---

### 4.4 Text Parser (`text_parser.py` — 161 lines)

**Classes**: `TextParser`, `TextParserConfig`

```python
class TextParserConfig(BaseModel):
    encoding: str = "utf-8"
    max_line_length: int = 1_000_000
    skip_empty_lines: bool = True
    strip_whitespace: bool = True
    line_mode: str = "lines"  # "lines" or "whole"
```

**Modes**:
| `line_mode` | Behavior |
|-------------|----------|
| `"lines"` (default) | Each line → separate record with `line_number`, `content` |
| `"whole"` | Entire file → single record with `content` |

**Parsing Flow**:
```python
def parse(self, file_path, encoding=None) -> Iterator[dict]:
    # 1. Open with encoding
    # 2. Iterate lines with enumerate
    # 3. Apply skip_empty, strip_whitespace
    # 4. Check max_line_length
    # 5. Yield {"line_number": n, "content": line}
```

**Test Coverage** (`test_text_parser.py`):
- ✅ Basic line-by-line
- ✅ Skip empty lines
- ✅ Strip whitespace
- ✅ Whole file mode
- ✅ Max line length enforcement
- ✅ Encoding handling (UTF-8, Latin-1)
- ✅ Unicode content
- ✅ Large file streaming

---

### 4.5 FHIR Parser (`fhir_parser.py` — 207 lines)

**Classes**: `FHIRParser`, `FHIRParserConfig`

```python
class FHIRParserConfig(BaseModel):
    encoding: str = "utf-8"
    validate_resources: bool = True
    extract_references: bool = True
    flatten: bool = False
    bundle_mode: str = "entries"  # "entries" or "bundle"
```

**Requires**: `fhir.resources` package (optional dependency)

```python
# Only available if installed:
# pip install "lockmate[fhir]"  # or: pip install fhir.resources
```

**Bundle Handling**:
| `bundle_mode` | Behavior |
|---------------|----------|
| `"entries"` (default) | `Bundle.entry[].resource` → each resource as record |
| `"bundle"` | Entire Bundle as single record |

**Reference Extraction** (when `extract_references=True`):
```python
# Input: Patient with reference to Organization
# Output includes: "organization_reference": "Organization/123"
```

**Parsing Flow**:
```python
def parse(self, file_path, encoding=None) -> Iterator[dict]:
    # 1. Check fhir.resources available
    # 2. Parse JSON
    # 3. If Bundle → iterate entries
    # 4. If single resource → yield directly
    # 5. Validate with fhir.resources models (optional)
    # 6. Extract references (optional)
    # 7. Flatten (optional)
    # 8. Yield with metadata: resource_type, id, fhir_version
```

**Test Coverage** (`test_fhir_parser.py`):
- ✅ Single Patient resource
- ✅ Bundle with multiple entries
- ✅ Bundle mode variations
- ✅ Reference extraction
- ✅ Validation enabled/disabled
- ⏭️ Skipped if `fhir.resources` not installed (7 tests)

---

### 4.6 Parser Comparison Matrix

| Feature | CSV/TSV | JSON | Text | FHIR |
|---------|---------|------|------|------|
| **Streaming** | ✅ (pandas chunks) | ❌ (full parse) | ✅ (line iter) | ❌ (full parse) |
| **Max File Size** | Configurable | 100MB default | Configurable | 100MB default |
| **Schema Validation** | Column names | JSON syntax | Line length | FHIR spec (optional) |
| **Nested Data** | Flat only | ✅ NestedJSONParser | N/A | ✅ flatten option |
| **Dependencies** | pandas | orjson (optional) | stdlib | fhir.resources (optional) |
| **Records per File** | 1 per row | 1 per array item / object | 1 per line | 1 per resource |
| **Typical Use** | Tabular exports | API dumps, logs | Logs, notes | Healthcare interop |

---

### 4.7 Parser Selection in Pipeline

```python
# In secure_ingest.py:_get_parser()
def _get_parser(self, mime_type: str) -> BaseParser:
    if "csv" in mime_type or "tab-separated" in mime_type:
        return CSVParser() if "csv" in mime_type else TSVParser()
    elif "json" in mime_type:
        if "fhir" in mime_type:
            return FHIRParser()
        return JSONParser()
    else:
        return TextParser()  # Default fallback
```

**MIME Types Mapped** (from `file_validator.py`):
| Extension | MIME Type | Parser |
|-----------|-----------|--------|
| `.csv` | `text/csv` | CSVParser |
| `.tsv` | `text/tab-separated-values` | TSVParser |
| `.json` | `application/json` | JSONParser |
| `.ndjson`, `.jsonl` | `application/x-ndjson` | JSONParser |
| `.fhir.json` | `application/fhir+json` | FHIRParser |
| `.txt`, `.log` | `text/plain` | TextParser |
| *unknown* | *extension fallback* | TextParser |

---

### 4.8 Adding a Custom Parser

1. **Create parser** in `parsers/custom_parser.py`:
```python
class CustomParser:
    def parse(self, file_path, encoding=None) -> Iterator[dict]:
        # Implementation
        yield {"field": "value"}
```

2. **Export** in `parsers/__init__.py`:
```python
from lockmate.ingestion.parsers.custom_parser import CustomParser
__all__ = [..., "CustomParser"]
```

3. **Register MIME type** in `file_validator.py`:
```python
_EXTENSION_MIME_TYPES[".custom"] = "application/custom"
```

4. **Add case** in `secure_ingest.py:_get_parser()`:
```python
elif "custom" in mime_type:
    return CustomParser()
```

5. **Write tests** in `tests/test_custom_parser.py`

---

### 4.9 Parser Test Results Summary

| Parser | Tests | Pass | Skip | Notes |
|--------|-------|------|------|-------|
| CSV | 10 | 10 | 0 | Includes TSV subclass |
| JSON | 9 | 9 | 0 | orjson + stdlib |
| Text | 8 | 8 | 0 | |
| FHIR | 7 | 0 | 7 | Requires `fhir.resources` |
| **Total** | **34** | **27** | **7** | |

> FHIR tests skipped when optional dependency not installed. Install with `pip install "lockmate[fhir]"` to run.