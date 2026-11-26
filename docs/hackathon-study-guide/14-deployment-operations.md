# LOCKMATE Hackathon Study Guide — Document 14
## Deployment & Operations — Production Considerations, Monitoring, Runbooks

---

### 14.1 Deployment Overview

| Aspect | Current State | Production Target |
|--------|---------------|-------------------|
| **Packaging** | `pip install -e .` (editable) | Wheel + Docker image |
| **Configuration** | Python `IngestionConfig` objects | YAML/JSON + env vars |
| **Runtime** | Single Python process | Container / systemd service |
| **Orchestration** | Manual / cron | Airflow / Prefect / Kubernetes CronJob |
| **Monitoring** | Structured logs (stdout) | Prometheus + Grafana + AlertManager |
| **Secrets** | None in code | Vault / SealedSecrets / AWS Secrets Manager |

---

### 14.2 Deployment Models

#### 14.2.1 Model A: Batch Cron Job (Simplest)

```bash
# /etc/cron.d/lockmate-ingestion
# Run every 15 minutes
*/15 * * * * lockmate /opt/lockmate/venv/bin/python -m lockmate.ingestion.cli \
    --input-dir /data/incoming \
    --output-dir /data/processed \
    --quarantine-dir /data/quarantine \
    --allowed-roots /data/incoming \
    --max-file-size 104857600 \
    --log-level INFO \
    --log-format json
```

**Pros**: Simple, no orchestrator dependency  
**Cons**: No retry, no visibility, manual scaling

---

#### 14.2.2 Model B: Airflow DAG (Recommended)

```python
# dags/lockmate_ingestion.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def run_ingestion(**context):
    from lockmate.ingestion import SecureIngestionPipeline, IngestionConfig
    from pathlib import Path
    
    config = IngestionConfig(
        input_dir=Path("/data/incoming/{{ ds }}"),
        output_dir=Path("/data/processed/{{ ds }}"),
        quarantine_dir=Path("/data/quarantine/{{ ds }}"),
        allowed_roots=[Path("/data/incoming")],
        max_file_size=100_000_000,
        fail_fast=False,
    )
    pipeline = SecureIngestionPipeline(config)
    result = pipeline.run()
    
    if not result.success:
        raise Exception(f"Ingestion failed: {result.errors}")
    
    # Push metrics to XCom for downstream tasks
    context['ti'].xcom_push(key='records_processed', value=result.total_records)
    context['ti'].xcom_push(key='files_quarantined', value=len(result.quarantined_files))

with DAG(
    'lockmate_ingestion',
    schedule_interval='@daily',
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={'retries': 2, 'retry_delay': timedelta(minutes=5)},
) as dag:
    
    ingest = PythonOperator(
        task_id='run_ingestion',
        python_callable=run_ingestion,
        provide_context=True,
    )
    
    # Downstream: trigger Detection module
    trigger_detection = PythonOperator(
        task_id='trigger_detection',
        python_callable=lambda **ctx: print(f"Trigger detection for {ctx['ti'].xcom_pull(key='records_processed')} records"),
    )
    
    ingest >> trigger_detection
```

---

#### 14.2.3 Model C: Kubernetes CronJob

```yaml
# k8s/lockmate-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: lockmate-ingestion
  namespace: data-processing
spec:
  schedule: "*/15 * * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: lockmate-sa
          containers:
          - name: lockmate
            image: lockmate:latest
            imagePullPolicy: Always
            env:
            - name: LOCKMATE_INPUT_DIR
              value: "/data/incoming"
            - name: LOCKMATE_OUTPUT_DIR
              value: "/data/processed"
            - name: LOCKMATE_QUARANTINE_DIR
              value: "/data/quarantine"
            - name: LOCKMATE_ALLOWED_ROOTS
              value: "/data/incoming"
            - name: LOCKMATE_MAX_FILE_SIZE
              value: "104857600"
            - name: LOCKMATE_LOG_LEVEL
              value: "INFO"
            - name: LOCKMATE_LOG_FORMAT
              value: "json"
            volumeMounts:
            - name: data
              mountPath: /data
            - name: config
              mountPath: /config
            resources:
              requests:
                memory: "2Gi"
                cpu: "1000m"
              limits:
                memory: "4Gi"
                cpu: "2000m"
          volumes:
          - name: data
            persistentVolumeClaim:
              claimName: lockmate-data-pvc
          - name: config
            configMap:
              name: lockmate-config
          restartPolicy: OnFailure
```

---

#### 14.2.4 Model D: Library Integration (Embedded)

```python
# In your application
from lockmate.ingestion import SecureIngestionPipeline, IngestionConfig
from pathlib import Path

def process_uploaded_file(upload_path: Path) -> dict:
    """Process a single uploaded file synchronously."""
    with tempfile.TemporaryDirectory() as tmp:
        config = IngestionConfig(
            input_dir=upload_path.parent,
            output_dir=Path(tmp) / "out",
            quarantine_dir=Path(tmp) / "quar",
            allowed_roots=[upload_path.parent],
            max_file_size=50_000_000,
        )
        pipeline = SecureIngestionPipeline(config)
        result = pipeline.ingest_file(upload_path)  # Single file
        
        records = list(result)
        return {
            "success": True,
            "record_count": len(records),
            "records": records[:100],  # Return preview
        }
```

---

### 14.3 Configuration Management

#### 14.3.1 Configuration Sources (Priority Order)

1. **Defaults** (in `IngestionConfig` dataclass)
2. **Config file** (YAML/JSON via `LOCKMATE_CONFIG_FILE`)
3. **Environment variables** (prefix `LOCKMATE_`)
4. **CLI arguments** (highest priority)

#### 14.3.2 Example Config File

```yaml
# config/production.yaml
input_dir: "/data/incoming"
output_dir: "/data/processed"
quarantine_dir: "/data/quarantine"
allowed_roots:
  - "/data/incoming"
  - "/data/trusted_sources"

max_file_size: 104857600        # 100MB
max_total_size: 1073741824      # 1GB
follow_symlinks: false

csv_parser:
  chunksize: 50000
  encoding: "utf-8"
  has_header: true

json_parser:
  use_orjson: true
  array_mode: "auto"

text_parser:
  encoding: "utf-8"

fhir_parser:
  validate_resources: false

validation:
  allowed_mime_types:
    - "text/csv"
    - "application/json"
    - "text/plain"
    - "application/fhir+json"
  allowed_encodings:
    - "utf-8"
    - "utf-16"
    - "latin-1"

quarantine:
  max_size: 10737418240         # 10GB
  compress: true
  retention_days: 30

output:
  format: "jsonl"
  max_records_per_file: 100000
  include_metadata: true
  atomic_writes: true

pipeline:
  fail_fast: false
  log_level: "INFO"
  log_format: "json"
```

#### 14.3.3 Loading Config

```python
# lockmate/ingestion/config_loader.py
import yaml
import os
from pathlib import Path
from dataclasses import fields
from lockmate.ingestion.config import IngestionConfig, CSVParserConfig, ...

def load_config(config_path: str | None = None) -> IngestionConfig:
    # 1. Start with defaults
    config_dict = {}
    
    # 2. Load from file
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            file_config = yaml.safe_load(f)
            config_dict.update(file_config)
    
    # 3. Override from env vars
    env_mapping = {
        'LOCKMATE_INPUT_DIR': 'input_dir',
        'LOCKMATE_OUTPUT_DIR': 'output_dir',
        'LOCKMATE_QUARANTINE_DIR': 'quarantine_dir',
        'LOCKMATE_MAX_FILE_SIZE': ('max_file_size', int),
        'LOCKMATE_MAX_TOTAL_SIZE': ('max_total_size', int),
        'LOCKMATE_FOLLOW_SYMLINKS': ('follow_symlinks', lambda x: x.lower() == 'true'),
        'LOCKMATE_LOG_LEVEL': 'log_level',
        'LOCKMATE_LOG_FORMAT': 'log_format',
    }
    
    for env_var, config_key in env_mapping.items():
        value = os.environ.get(env_var)
        if value is not None:
            if isinstance(config_key, tuple):
                key, converter = config_key
                config_dict[key] = converter(value)
            else:
                config_dict[config_key] = value
    
    # 4. Convert nested dicts to config objects
    for nested_key in ['csv_parser', 'json_parser', 'text_parser', 'fhir_parser', 
                       'validation', 'quarantine', 'output']:
        if nested_key in config_dict:
            config_class = {
                'csv_parser': CSVParserConfig,
                'json_parser': JSONParserConfig,
                'text_parser': TextParserConfig,
                'fhir_parser': FHIRParserConfig,
                'validation': ValidationConfig,
                'quarantine': QuarantineConfig,
                'output': OutputConfig,
            }[nested_key]
            config_dict[nested_key] = config_class(**config_dict[nested_key])
    
    # 5. Handle allowed_roots (Path objects)
    if 'allowed_roots' in config_dict:
        config_dict['allowed_roots'] = [Path(p) for p in config_dict['allowed_roots']]
    if 'input_dir' in config_dict:
        config_dict['input_dir'] = Path(config_dict['input_dir'])
    # ... same for output_dir, quarantine_dir
    
    return IngestionConfig(**config_dict)
```

---

### 14.4 Monitoring & Observability

#### 14.4.1 Key Metrics to Emit

```python
# lockmate/ingestion/metrics.py (to implement)
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

# Create registry (or use default)
registry = CollectorRegistry()

INGESTION_RUNS_TOTAL = Counter(
    'lockmate_ingestion_runs_total',
    'Total ingestion runs',
    ['status'],  # success, failed
    registry=registry
)

INGESTION_FILES_TOTAL = Counter(
    'lockmate_ingestion_files_total',
    'Total files processed',
    ['status'],  # processed, quarantined, failed
    registry=registry
)

INGESTION_RECORDS_TOTAL = Counter(
    'lockmate_ingestion_records_total',
    'Total records output',
    ['format'],  # csv, json, text, fhir
    registry=registry
)

INGESTION_DURATION = Histogram(
    'lockmate_ingestion_duration_seconds',
    'Ingestion pipeline duration',
    buckets=[1, 5, 10, 30, 60, 300, 600, 1800],
    registry=registry
)

VALIDATION_DURATION = Histogram(
    'lockmate_validation_duration_seconds',
    'Validation layer duration',
    ['layer'],  # path_guard, symlink_guard, size_limits, file_validator
    registry=registry
)

PARSER_DURATION = Histogram(
    'lockmate_parser_duration_seconds',
    'Parser duration',
    ['parser'],  # csv, json, text, fhir
    registry=registry
)

QUARANTINE_SIZE = Gauge(
    'lockmate_quarantine_size_bytes',
    'Current quarantine directory size',
    registry=registry
)

ACTIVE_PIPELINES = Gauge(
    'lockmate_active_pipelines',
    'Number of currently running pipelines',
    registry=registry
)
```

#### 14.4.2 Instrumented Pipeline

```python
# In secure_ingest.py
from lockmate.ingestion.metrics import *

class SecureIngestionPipeline:
    def run(self) -> IngestionResult:
        ACTIVE_PIPELINES.inc()
        start_time = time.perf_counter()
        
        try:
            result = self._run_internal()
            INGESTION_RUNS_TOTAL.labels(status='success').inc()
            return result
        except Exception as e:
            INGESTION_RUNS_TOTAL.labels(status='failed').inc()
            raise
        finally:
            ACTIVE_PIPELINES.dec()
            INGESTION_DURATION.observe(time.perf_counter() - start_time)
    
    def _process_file(self, file_path: Path, result: IngestionResult) -> None:
        # Validation metrics
        for layer_name, validator in [
            ('path_guard', self.path_guard),
            ('symlink_guard', self.symlink_guard),
            ('size_limits', self.size_limiter),
            ('file_validator', self.validator),
        ]:
            layer_start = time.perf_counter()
            try:
                # ... validation call ...
                VALIDATION_DURATION.labels(layer=layer_name).observe(
                    time.perf_counter() - layer_start
                )
            except Exception:
                VALIDATION_DURATION.labels(layer=layer_name).observe(
                    time.perf_counter() - layer_start
                )
                raise
        
        # Parser metrics
        parser_name = self._get_parser_name(validation_result.mime_type)
        parser_start = time.perf_counter()
        records = list(parser.parse(...))
        PARSER_DURATION.labels(parser=parser_name).observe(
            time.perf_counter() - parser_start
        )
        
        # File status metrics
        if validation_result.is_valid:
            INGESTION_FILES_TOTAL.labels(status='processed').inc()
            INGESTION_RECORDS_TOTAL.labels(format=parser_name).inc(len(records))
        else:
            INGESTION_FILES_TOTAL.labels(status='quarantined').inc()
```

#### 14.4.3 Grafana Dashboard Panels

| Panel | Query | Purpose |
|-------|-------|---------|
| Runs Success Rate | `sum(rate(lockmate_ingestion_runs_total{status="success"}[5m])) / sum(rate(lockmate_ingestion_runs_total[5m]))` | Health |
| Files Processed/sec | `sum(rate(lockmate_ingestion_files_total{status="processed"}[5m]))` | Throughput |
| Quarantine Rate | `sum(rate(lockmate_ingestion_files_total{status="quarantined"}[5m])) / sum(rate(lockmate_ingestion_files_total[5m]))` | Anomaly detection |
| Records/sec by Format | `sum by (format) (rate(lockmate_ingestion_records_total[5m]))` | Format mix |
| Pipeline Duration p95 | `histogram_quantile(0.95, rate(lockmate_ingestion_duration_seconds_bucket[5m]))` | Latency |
| Validation Layer Latency | `sum by (layer) (rate(lockmate_validation_duration_seconds_sum[5m])) / sum by (layer) (rate(lockmate_validation_duration_seconds_count[5m]))` | Bottleneck ID |
| Quarantine Size | `lockmate_quarantine_size_bytes` | Capacity planning |

---

#### 14.4.4 Alert Rules (PrometheusRule)

```yaml
# k8s/alerts.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: lockmate-alerts
spec:
  groups:
  - name: lockmate
    rules:
    - alert: LockmateIngestionFailureRate
      expr: |
        sum(rate(lockmate_ingestion_runs_total{status="failed"}[15m])) 
        / sum(rate(lockmate_ingestion_runs_total[15m])) > 0.1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "LOCKMATE ingestion failure rate > 10%"
        description: "{{ $value | humanizePercentage }} of runs failed in last 15m"
    
    - alert: LockmateHighQuarantineRate
      expr: |
        sum(rate(lockmate_ingestion_files_total{status="quarantined"}[15m]))
        / sum(rate(lockmate_ingestion_files_total[15m])) > 0.2
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "High quarantine rate: {{ $value | humanizePercentage }}"
        description: "Many files being quarantined - check input source"
    
    - alert: LockmateQuarantineDiskFull
      expr: lockmate_quarantine_size_bytes > 8000000000  # 8GB of 10GB limit
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Quarantine directory at {{ $value | humanizeBytes }}"
        description: "Approaching 10GB limit, check retention policy"
    
    - alert: LockmatePipelineDurationHigh
      expr: |
        histogram_quantile(0.95, rate(lockmate_ingestion_duration_seconds_bucket[15m])) > 300
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "Pipeline p95 duration > 5 minutes"
        description: "Check for large files or validation bottlenecks"
```

---

### 14.5 Logging in Production

#### 14.5.1 Structured JSON Logging

```python
# lockmate/ingestion/logging_config.py
import structlog
import logging
import sys

def configure_production_logging(log_level: str = "INFO", log_format: str = "json"):
    """Configure structlog for production JSON output."""
    
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if log_format == "json" 
            else structlog.dev.ConsoleRenderer(colors=False),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure stdlib logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
```

#### 14.5.2 Log Fields Reference

| Field | Description | Example |
|-------|-------------|---------|
| `timestamp` | ISO8601 UTC | `2026-01-15T10:00:01.123Z` |
| `level` | Log level | `info`, `warning`, `error` |
| `logger` | Module name | `lockmate.ingestion.secure_ingest` |
| `event` | Human-readable message | `File processed` |
| `job_id` | Pipeline run ID | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| `file_path` | File being processed | `/data/incoming/patients.csv` |
| `status` | Outcome | `processed`, `quarantined`, `failed` |
| `records` | Record count | `150` |
| `mime_type` | Detected MIME | `text/csv` |
| `duration_ms` | Processing time | `45.2` |
| `error_type` | Exception class | `PathTraversalError` |
| `error_code` | Standardized code | `SEC-001` |

---

### 14.6 Runbooks

#### 14.6.1 Runbook: High Quarantine Rate

```
Title: LOCKMATE High Quarantine Rate
Severity: Warning
Owner: Data Engineering

Symptoms:
- Alert: LockmateHighQuarantineRate firing
- Quarantine rate > 20% for 10+ minutes
- Quarantine directory growing rapidly

Diagnosis:
1. Check recent quarantine entries:
   cat /data/quarantine/metadata.jsonl | tail -20 | jq '.reason'
   
2. Common reasons:
   - "Disallowed MIME type" → New file format from source
   - "Path traversal" → Malformed input paths
   - "Size limit exceeded" → Source sending larger files
   - "Encoding detection failed" → Corrupted/mixed encoding files

3. Verify source system hasn't changed format

Resolution:
- If new legitimate format: Add MIME type to ValidationConfig.allowed_mime_types
- If source error: Contact upstream, quarantine is working correctly
- If config issue: Deploy config fix, reprocess quarantined files

Verification:
- Quarantine rate returns to < 5%
- Processed files count returns to baseline
```

#### 14.6.2 Runbook: Pipeline Failures

```
Title: LOCKMATE Pipeline Failures
Severity: Critical
Owner: Data Engineering

Symptoms:
- Alert: LockmateIngestionFailureRate firing
- Pipeline runs failing consistently
- No output files generated

Diagnosis:
1. Check logs for error pattern:
   kubectl logs -l app=lockmate --tail=100 | jq 'select(.level=="error")'
   
2. Common failures:
   - Permission denied on input/output dirs
   - Disk full on output/quarantine
   - OOM on large JSON/FHIR files
   - Config validation error (invalid paths)

3. Check resource usage:
   kubectl top pod -l app=lockmate

Resolution:
- Permissions: Fix volume mounts / RBAC
- Disk: Clean up, increase PVC size
- OOM: Increase memory limit, reduce max_file_size
- Config: Fix and redeploy

Verification:
- Next scheduled run succeeds
- Metrics show success rate = 100%
```

#### 14.6.3 Runbook: Reprocess Quarantined Files

```
Title: Reprocess Quarantined Files After Config Fix
Severity: Operational
Owner: Data Engineering

Procedure:
1. Identify files to reprocess:
   cat /data/quarantine/metadata.jsonl | jq 'select(.reason=="Disallowed MIME type: application/x-newformat") | .original_path'
   
2. Copy back to input (or new input directory):
   mkdir -p /data/reprocess
   # Use jq to extract paths and copy
   
3. Update config to allow new format:
   # Edit ValidationConfig.allowed_mime_types
   
4. Run ingestion on reprocess directory:
   python -m lockmate.ingestion.cli --input-dir /data/reprocess --output-dir /data/processed --config production.yaml
   
5. Verify output:
   Check report.json, records.jsonl
   
6. Clean up quarantine entries (optional):
   # Use QuarantineManager API or delete specific metadata lines
```

---

### 14.7 Security Hardening for Production

| Control | Implementation |
|---------|----------------|
| **Least Privilege** | Run as non-root user (UID 1000), read-only root fs |
| **Network** | Egress only to allowed registries/monitoring; no ingress |
| **Secrets** | No secrets in config; use Vault/SealedSecrets for any API keys |
| **Image** | Distroless/base image, signed, scanned (Trivy/Snyk) |
| **Runtime** | `securityContext: {readOnlyRootFilesystem: true, runAsNonRoot: true, allowPrivilegeEscalation: false}` |
| **Audit** | All config changes via GitOps; immutable deployments |
| **Quarantine** | Separate PVC, encrypted at rest, access logging |

---

### 14.8 Disaster Recovery

| Scenario | RTO | RPO | Recovery Procedure |
|----------|-----|-----|-------------------|
| **Pipeline pod crashes** | <5 min | 0 | Kubernetes restarts; idempotent re-run |
| **Output PVC corruption** | <30 min | 15 min | Restore from snapshot; re-run last batch |
| **Quarantine PVC full** | <10 min | 0 | Scale PVC; clean old entries via retention |
| **Config deployed broken** | <15 min | 0 | Rollback via ArgoCD/Flux; re-run |
| **Upstream data format change** | <1 hour | 0 | Update config; reprocess affected files |

---

### 14.9 CI/CD Pipeline

```yaml
# .github/workflows/ci.yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install -e ".[dev]"
      - run: pip install fhir.resources
      - run: pytest -v --cov=lockmate --cov-report=xml
      - uses: codecov/codecov-action@v3

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run bandit
        run: pip install bandit && bandit -r src/
      - name: Run pip-audit
        run: pip install pip-audit && pip-audit
      - name: Check for secrets
        run: pip install trufflehog && trufflehog filesystem .

  build:
    needs: [test, security]
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: docker build -t lockmate:${{ github.sha }} .
      - name: Scan image
        run: docker run --rm aquasec/trivy image lockmate:${{ github.sha }}
      - name: Push to registry
        run: |
          echo ${{ secrets.REGISTRY_PASSWORD }} | docker login -u ${{ secrets.REGISTRY_USER }} --password-stdin
          docker tag lockmate:${{ github.sha }} ${{ secrets.REGISTRY }}/lockmate:${{ github.sha }}
          docker push ${{ secrets.REGISTRY }}/lockmate:${{ github.sha }}
```

---

### 14.10 Operations Checklist

#### Pre-Deploy
- [ ] All tests pass (including FHIR with `fhir.resources`)
- [ ] Security scan clean (bandit, pip-audit, trufflehog)
- [ ] Docker image builds and scans clean
- [ ] Config validated against schema
- [ ] Quarantine retention policy configured
- [ ] Monitoring dashboards imported
- [ ] Alert rules deployed
- [ ] Runbooks reviewed and accessible

#### Post-Deploy
- [ ] Smoke test: run on sample data
- [ ] Verify metrics appearing in Prometheus
- [ ] Verify logs in aggregation (Loki/Elastic)
- [ ] Check quarantine directory writable
- [ ] Verify output directory permissions
- [ ] Test alert firing (simulate failure)

#### Ongoing
- [ ] Weekly: Review quarantine trends
- [ ] Monthly: Capacity review (disk, memory)
- [ ] Quarterly: Dependency updates, security patches
- [ ] Per-incident: Update runbooks