"""
LOCKMATE — Processing Metrics Collection
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional
from contextlib import contextmanager

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class StageMetrics:
    """Metrics for a single pipeline stage."""
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    peak_memory_mb: float = 0.0
    records_processed: int = 0
    identifiers_detected: int = 0
    records_linked: int = 0
    records_generalized: int = 0
    records_suppressed: int = 0
    records_quarantined: int = 0
    
    @property
    def duration_ms(self) -> int:
        return int((self.end_time - self.start_time) * 1000)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "peak_memory_mb": self.peak_memory_mb,
            "records_processed": self.records_processed,
            "identifiers_detected": self.identifiers_detected,
            "records_linked": self.records_linked,
            "records_generalized": self.records_generalized,
            "records_suppressed": self.records_suppressed,
            "records_quarantined": self.records_quarantined
        }


class ProcessingMetricsCollector:
    """
    Collects and aggregates processing metrics across pipeline stages.
    
    Thread-safe for concurrent stage execution.
    """
    
    def __init__(self):
        self._stages: Dict[str, StageMetrics] = {}
        self._lock = threading.Lock()
        self._process = None
        if HAS_PSUTIL:
            self._process = psutil.Process()
    
    @contextmanager
    def stage(self, name: str):
        """Context manager for timing a pipeline stage."""
        metrics = StageMetrics(name=name)
        metrics.start_time = time.perf_counter()
        peak_mem = 0.0
        
        try:
            yield metrics
        finally:
            metrics.end_time = time.perf_counter()
            # Update peak memory
            if HAS_PSUTIL and self._process:
                try:
                    current_mem = self._process.memory_info().rss / (1024 * 1024)
                    peak_mem = max(peak_mem, current_mem)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            metrics.peak_memory_mb = peak_mem
            
            with self._lock:
                self._stages[name] = metrics
    
    def record_identifiers(self, count: int) -> None:
        """Record detected identifiers (thread-safe)."""
        with self._lock:
            # Add to the most recent stage
            if self._stages:
                latest = max(self._stages.values(), key=lambda s: s.end_time)
                latest.identifiers_detected += count
    
    def record_linked(self, count: int) -> None:
        """Record linked records."""
        with self._lock:
            if self._stages:
                latest = max(self._stages.values(), key=lambda s: s.end_time)
                latest.records_linked += count
    
    def record_generalized(self, count: int) -> None:
        """Record generalized records."""
        with self._lock:
            if self._stages:
                latest = max(self._stages.values(), key=lambda s: s.end_time)
                latest.records_generalized += count
    
    def record_suppressed(self, count: int) -> None:
        """Record suppressed records."""
        with self._lock:
            if self._stages:
                latest = max(self._stages.values(), key=lambda s: s.end_time)
                latest.records_suppressed += count
    
    def record_quarantined(self, count: int) -> None:
        """Record quarantined records."""
        with self._lock:
            if self._stages:
                latest = max(self._stages.values(), key=lambda s: s.end_time)
                latest.records_quarantined += count
    
    def get_stage(self, name: str) -> Optional[StageMetrics]:
        """Get metrics for a specific stage."""
        with self._lock:
            return self._stages.get(name)
    
    def get_all_stages(self) -> Dict[str, StageMetrics]:
        """Get all stage metrics."""
        with self._lock:
            return dict(self._stages)
    
    def get_totals(self) -> dict:
        """Get aggregated totals across all stages."""
        with self._lock:
            total_duration = sum(s.duration_ms for s in self._stages.values())
            peak_memory = max((s.peak_memory_mb for s in self._stages.values()), default=0.0)
            return {
                "total_duration_ms": total_duration,
                "peak_memory_mb": peak_memory,
                "records_processed": sum(s.records_processed for s in self._stages.values()),
                "identifiers_detected": sum(s.identifiers_detected for s in self._stages.values()),
                "records_linked": sum(s.records_linked for s in self._stages.values()),
                "records_generalized": sum(s.records_generalized for s in self._stages.values()),
                "records_suppressed": sum(s.records_suppressed for s in self._stages.values()),
                "records_quarantined": sum(s.records_quarantined for s in self._stages.values()),
            }
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._stages.clear()


class FileMetrics:
    """Metrics for a single file processing."""
    
    def __init__(self, file_sha256: str):
        self.file_sha256 = file_sha256
        self.start_time = time.perf_counter()
        self.peak_memory_mb = 0.0
        self.records_processed = 0
        self.identifiers_detected = 0
        self.records_linked = 0
        self.records_generalized = 0
        self.records_suppressed = 0
        self.records_quarantined = 0
        self.status = "processing"
        self._process = None
        if HAS_PSUTIL:
            self._process = psutil.Process()
    
    def update_peak_memory(self) -> None:
        """Update peak memory if current is higher."""
        if HAS_PSUTIL and self._process:
            try:
                current = self._process.memory_info().rss / (1024 * 1024)
                self.peak_memory_mb = max(self.peak_memory_mb, current)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    def finalize(self, status: str = "processed") -> dict:
        """Finalize and return metrics dict."""
        self.update_peak_memory()
        duration_ms = int((time.perf_counter() - self.start_time) * 1000)
        self.status = status
        return {
            "file_sha256": self.file_sha256,
            "duration_ms": duration_ms,
            "peak_memory_mb": int(self.peak_memory_mb),
            "records_processed": self.records_processed,
            "identifiers_detected": self.identifiers_detected,
            "records_linked": self.records_linked,
            "records_generalized": self.records_generalized,
            "records_suppressed": self.records_suppressed,
            "records_quarantined": self.records_quarantined,
            "status": self.status
        }