"""
LOCKMATE — Phase 8: Unified Benchmark Runner

Executes comprehensive evaluation:
1. Internal unit tests
2. Integration tests
3. Synthetic adversarial tests
4. Output validator
5. Practice self-check
6. Performance benchmark
7. Determinism checks

Generates machine-readable summary.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from ..utils.logging import get_logger

logger = get_logger("evaluation.benchmark")


class TestPhase(Enum):
    """Phases of the benchmark."""
    UNIT = "unit"
    INTEGRATION = "integration"
    ADVERSARIAL = "adversarial"
    VALIDATION = "validation"
    PRACTICE = "practice"
    PERFORMANCE = "performance"
    DETERMINISM = "determinism"


@dataclass
class BenchmarkResult:
    """Result of a single benchmark phase."""
    phase: TestPhase
    name: str
    passed: bool
    exit_code: int
    duration_ms: float
    output: str
    error: str
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSummary:
    """Complete benchmark summary."""
    timestamp: str
    toolkit_commit: str
    total_phases: int
    passed_phases: int
    failed_phases: int
    total_duration_ms: float
    phases: List[BenchmarkResult]
    machine_readable: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "toolkit_commit": self.toolkit_commit,
            "total_phases": self.total_phases,
            "passed_phases": self.passed_phases,
            "failed_phases": self.failed_phases,
            "total_duration_ms": self.total_duration_ms,
            "phases": [
                {
                    "phase": r.phase.value,
                    "name": r.name,
                    "passed": r.passed,
                    "exit_code": r.exit_code,
                    "duration_ms": r.duration_ms,
                    "metrics": r.metrics
                }
                for r in self.phases
            ],
            "machine_readable": self.machine_readable
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class BenchmarkRunner:
    """
    Unified benchmark runner for LOCKMATE evaluation.
    
    Runs all test phases and generates a comprehensive report.
    """
    
    def __init__(
        self,
        project_root: Path,
        secret: bytes,
        config_path: Optional[Path] = None,
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None
    ):
        self.project_root = project_root
        self.secret = secret
        self.config_path = config_path or project_root / "config" / "policy.yaml"
        self.input_dir = input_dir
        self.output_dir = output_dir or project_root / "benchmark_output"
        self.results: List[BenchmarkResult] = []
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_all(self) -> BenchmarkSummary:
        """Run all benchmark phases."""
        start_time = time.time()
        
        # Get toolkit commit
        commit = self._get_git_commit()
        
        # Run each phase
        self._run_unit_tests()
        self._run_integration_tests()
        self._run_adversarial_tests()
        self._run_output_validation()
        self._run_practice_check()
        self._run_performance_benchmark()
        self._run_determinism_check()
        
        total_duration = (time.time() - start_time) * 1000
        
        # Create summary
        summary = BenchmarkSummary(
            timestamp=datetime.utcnow().isoformat() + "Z",
            toolkit_commit=commit,
            total_phases=len(self.results),
            passed_phases=sum(1 for r in self.results if r.passed),
            failed_phases=sum(1 for r in self.results if not r.passed),
            total_duration_ms=total_duration,
            phases=self.results,
            machine_readable=self._create_machine_readable()
        )
        
        # Save summary
        summary_path = self.output_dir / "benchmark_summary.json"
        summary_path.write_text(summary.to_json())
        
        logger.info("benchmark_complete",
                   total=len(self.results),
                   passed=summary.passed_phases,
                   failed=summary.failed_phases,
                   duration_ms=total_duration)
        
        return summary
    
    def _get_git_commit(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()[:12]
        except Exception:
            pass
        return "unknown"
    
    def _run_command(
        self, 
        cmd: List[str], 
        phase: TestPhase,
        name: str,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 300
    ) -> BenchmarkResult:
        """Run a command and capture result."""
        start = time.time()
        
        # Prepare environment
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        
        # Always set RAKSHA_SECRET
        import base64
        run_env["RAKSHA_SECRET"] = base64.b64encode(self.secret).decode()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=run_env
            )
            
            duration = (time.time() - start) * 1000
            
            passed = result.returncode == 0
            
            return BenchmarkResult(
                phase=phase,
                name=name,
                passed=passed,
                exit_code=result.returncode,
                duration_ms=duration,
                output=result.stdout[-5000:] if result.stdout else "",
                error=result.stderr[-5000:] if result.stderr else "",
                metrics={}
            )
            
        except subprocess.TimeoutExpired:
            duration = (time.time() - start) * 1000
            return BenchmarkResult(
                phase=phase,
                name=name,
                passed=False,
                exit_code=-1,
                duration_ms=duration,
                output="",
                error=f"Timeout after {timeout}s",
                metrics={}
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return BenchmarkResult(
                phase=phase,
                name=name,
                passed=False,
                exit_code=-1,
                duration_ms=duration,
                output="",
                error=str(e),
                metrics={}
            )
    
    def _run_unit_tests(self):
        """Run internal unit tests."""
        logger.info("running_unit_tests")
        
        # Run pytest on unit tests
        result = self._run_command(
            [sys.executable, "-m", "pytest", "tests/unit", "-v", "--tb=short"],
            TestPhase.UNIT,
            "unit_tests",
            timeout=120
        )
        self.results.append(result)
    
    def _run_integration_tests(self):
        """Run integration tests."""
        logger.info("running_integration_tests")
        
        # Run integration tests if they exist
        integration_tests = list(self.project_root.glob("tests/integration/**/*.py"))
        if integration_tests:
            result = self._run_command(
                [sys.executable, "-m", "pytest", "tests/integration", "-v", "--tb=short"],
                TestPhase.INTEGRATION,
                "integration_tests",
                timeout=180
            )
        else:
            # Create a dummy pass result
            result = BenchmarkResult(
                phase=TestPhase.INTEGRATION,
                name="integration_tests",
                passed=True,
                exit_code=0,
                duration_ms=0,
                output="No integration tests found",
                error="",
                metrics={"skipped": True}
            )
        self.results.append(result)
    
    def _run_adversarial_tests(self):
        """Run synthetic adversarial tests."""
        logger.info("running_adversarial_tests")
        
        # This would use the adversarial test suite
        # For now, create a placeholder that can be extended
        from .adversarial_tests import AdversarialTestSuite
        from ..pipeline.full import run_pipeline
        
        try:
            from .synthetic_generator import SyntheticDataGenerator
            
            # Generate test data
            generator = SyntheticDataGenerator()
            test_records = generator.generate_dataset(50)
            
            # Write test files
            test_input = self.output_dir / "adversarial_input"
            test_input.mkdir(exist_ok=True)
            
            generator.write_csv(test_records, test_input / "test.csv")
            generator.write_json(test_records, test_input / "test.json")
            generator.write_jsonl(test_records, test_input / "test.jsonl")
            
            # Run adversarial tests
            adversarial_output = self.output_dir / "adversarial_output"
            
            suite = AdversarialTestSuite(run_pipeline, self.secret)
            suite.run_all(adversarial_output)
            
            summary = suite.get_summary()
            
            result = BenchmarkResult(
                phase=TestPhase.ADVERSARIAL,
                name="adversarial_tests",
                passed=summary["failed"] == 0 and summary["errors"] == 0,
                exit_code=0 if summary["failed"] == 0 else 1,
                duration_ms=0,  # Would be measured in suite
                output=json.dumps(summary),
                error="",
                metrics=summary
            )
        except Exception as e:
            result = BenchmarkResult(
                phase=TestPhase.ADVERSARIAL,
                name="adversarial_tests",
                passed=False,
                exit_code=-1,
                duration_ms=0,
                output="",
                error=str(e),
                metrics={}
            )
        
        self.results.append(result)
    
    def _run_output_validation(self):
        """Run output validator on generated outputs."""
        logger.info("running_output_validation")
        
        # Check if validator script exists
        validator = self.project_root / "scripts" / "validate_output.py"
        if validator.exists():
            result = self._run_command(
                [sys.executable, str(validator), "--output", str(self.output_dir)],
                TestPhase.VALIDATION,
                "output_validation",
                timeout=60
            )
        else:
            # Basic validation: check required files exist
            required = ["report.json", "records.jsonl"]
            missing = []
            for req in required:
                if not (self.output_dir / req).exists():
                    missing.append(req)
            
            result = BenchmarkResult(
                phase=TestPhase.VALIDATION,
                name="output_validation",
                passed=len(missing) == 0,
                exit_code=0 if len(missing) == 0 else 1,
                duration_ms=0,
                output=f"Missing files: {missing}" if missing else "All required files present",
                error="",
                metrics={"missing_files": missing}
            )
        
        self.results.append(result)
    
    def _run_practice_check(self):
        """Run practice self-check if practice data available."""
        logger.info("running_practice_check")
        
        # Check for practice data
        practice_dir = self.project_root / "data" / "practice"
        if practice_dir.exists() and any(practice_dir.iterdir()):
            # Run pipeline on practice data
            practice_output = self.output_dir / "practice_check"
            practice_output.mkdir(exist_ok=True)
            
            from ..pipeline.full import run_pipeline
            from ..utils.metrics import ProcessingMetricsCollector
            
            start = time.time()
            try:
                metrics = ProcessingMetricsCollector()
                run_pipeline(
                    input_dir=practice_dir,
                    output_dir=practice_output,
                    secret=self.secret,
                    config_path=self.config_path,
                    metrics_collector=metrics
                )
                duration = (time.time() - start) * 1000
                
                # Check output
                report_path = practice_output / "report.json"
                if report_path.exists():
                    with open(report_path) as f:
                        report = json.load(f)
                    
                    passed = report.get("counts", {}).get("files_quarantined", 0) == 0
                    
                    result = BenchmarkResult(
                        phase=TestPhase.PRACTICE,
                        name="practice_self_check",
                        passed=passed,
                        exit_code=0 if passed else 1,
                        duration_ms=duration,
                        output=json.dumps(report.get("counts", {})),
                        error="",
                        metrics=report.get("counts", {})
                    )
                else:
                    result = BenchmarkResult(
                        phase=TestPhase.PRACTICE,
                        name="practice_self_check",
                        passed=False,
                        exit_code=1,
                        duration_ms=duration,
                        output="No report generated",
                        error="Report missing",
                        metrics={}
                    )
            except Exception as e:
                duration = (time.time() - start) * 1000
                result = BenchmarkResult(
                    phase=TestPhase.PRACTICE,
                    name="practice_self_check",
                    passed=False,
                    exit_code=-1,
                    duration_ms=duration,
                    output="",
                    error=str(e),
                    metrics={}
                )
        else:
            result = BenchmarkResult(
                phase=TestPhase.PRACTICE,
                name="practice_self_check",
                passed=True,
                exit_code=0,
                duration_ms=0,
                output="No practice data available - skipped",
                error="",
                metrics={"skipped": True}
            )
        
        self.results.append(result)
    
    def _run_performance_benchmark(self):
        """Run performance benchmark."""
        logger.info("running_performance_benchmark")
        
        # Generate synthetic dataset for performance testing
        try:
            from .synthetic_generator import SyntheticDataGenerator
            
            generator = SyntheticDataGenerator()
            test_records = generator.generate_dataset(1000)
            
            perf_input = self.output_dir / "perf_input"
            perf_input.mkdir(exist_ok=True)
            
            generator.write_csv(test_records, perf_input / "perf.csv")
            generator.write_json(test_records, perf_input / "perf.json")
            
            perf_output = self.output_dir / "perf_output"
            perf_output.mkdir(exist_ok=True)
            
            from ..pipeline.full import run_pipeline
            from ..utils.metrics import ProcessingMetricsCollector
            
            start = time.time()
            metrics = ProcessingMetricsCollector()
            run_pipeline(
                input_dir=perf_input,
                output_dir=perf_output,
                secret=self.secret,
                config_path=self.config_path,
                metrics_collector=metrics
            )
            duration = (time.time() - start) * 1000
            
            totals = metrics.get_totals()
            
            result = BenchmarkResult(
                phase=TestPhase.PERFORMANCE,
                name="performance_benchmark",
                passed=True,  # Performance benchmarks don't pass/fail
                exit_code=0,
                duration_ms=duration,
                output=f"Processed {totals.get('records_processed', 0)} records in {duration:.0f}ms",
                error="",
                metrics={
                    "duration_ms": duration,
                    "records_processed": totals.get("records_processed", 0),
                    "peak_memory_mb": totals.get("peak_memory_mb", 0),
                    "files_processed": totals.get("files_total", 0),
                    "throughput_records_per_sec": totals.get("records_processed", 0) / (duration / 1000) if duration > 0 else 0
                }
            )
        except Exception as e:
            result = BenchmarkResult(
                phase=TestPhase.PERFORMANCE,
                name="performance_benchmark",
                passed=False,
                exit_code=-1,
                duration_ms=0,
                output="",
                error=str(e),
                metrics={}
            )
        
        self.results.append(result)
    
    def _run_determinism_check(self):
        """Run determinism verification."""
        logger.info("running_determinism_check")
        
        try:
            from .synthetic_generator import SyntheticDataGenerator
            from ..pipeline.full import run_pipeline
            from ..utils.metrics import ProcessingMetricsCollector
            
            # Generate test data
            generator = SyntheticDataGenerator(seed=42)
            test_records = generator.generate_dataset(100)
            
            det_input = self.output_dir / "det_input"
            det_input.mkdir(exist_ok=True)
            generator.write_json(test_records, det_input / "det.json")
            
            # Run twice with same secret
            output1 = self.output_dir / "det_output1"
            output2 = self.output_dir / "det_output2"
            
            for out in [output1, output2]:
                out.mkdir(exist_ok=True)
                metrics = ProcessingMetricsCollector()
                run_pipeline(
                    input_dir=det_input,
                    output_dir=out,
                    secret=self.secret,
                    config_path=self.config_path,
                    metrics_collector=metrics
                )
            
            # Compare outputs
            report1 = output1 / "report.json"
            report2 = output2 / "report.json"
            
            if report1.exists() and report2.exists():
                with open(report1) as f:
                    r1 = json.load(f)
                with open(report2) as f:
                    r2 = json.load(f)
                
                # Remove timestamps for comparison
                for r in [r1, r2]:
                    r.pop("timing", None)
                
                deterministic = r1 == r2
                
                result = BenchmarkResult(
                    phase=TestPhase.DETERMINISM,
                    name="determinism_check",
                    passed=deterministic,
                    exit_code=0 if deterministic else 1,
                    duration_ms=0,
                    output="Outputs identical" if deterministic else "Outputs differ",
                    error="",
                    metrics={"deterministic": deterministic}
                )
            else:
                result = BenchmarkResult(
                    phase=TestPhase.DETERMINISM,
                    name="determinism_check",
                    passed=False,
                    exit_code=1,
                    duration_ms=0,
                    output="Missing report files",
                    error="Reports not generated",
                    metrics={}
                )
        except Exception as e:
            result = BenchmarkResult(
                phase=TestPhase.DETERMINISM,
                name="determinism_check",
                passed=False,
                exit_code=-1,
                duration_ms=0,
                output="",
                error=str(e),
                metrics={}
            )
        
        self.results.append(result)
    
    def _create_machine_readable(self) -> Dict[str, Any]:
        """Create machine-readable summary for CI/CD."""
        return {
            "status": "pass" if all(r.passed for r in self.results) else "fail",
            "phases": {
                r.phase.value: {
                    "name": r.name,
                    "passed": r.passed,
                    "exit_code": r.exit_code,
                    "duration_ms": r.duration_ms
                }
                for r in self.results
            },
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed)
            }
        }


def run_full_evaluation(
    project_root: Path,
    secret: bytes,
    config_path: Optional[Path] = None,
    input_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None
) -> BenchmarkSummary:
    """
    Convenience function to run full evaluation.
    
    Can be called as: python scripts/run_full_evaluation.py
    """
    runner = BenchmarkRunner(project_root, secret, config_path, input_dir, output_dir)
    return runner.run_all()