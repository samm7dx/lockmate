"""
LOCKMATE — Phase 8: Engineering Quality Report

Generates a PII-free report containing:
- Build/test timestamp
- Toolkit commit
- Test counts
- Passed/failed tests
- Contract validation
- PII leakage metrics
- Medical preservation
- Canary results
- Linkage metrics (when Phase 5 exists)
- Privacy metrics (when Phase 6 is integrated)
- Runtime
- Peak memory
- Known limitations
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..utils.logging import get_logger

logger = get_logger("evaluation.report")


@dataclass
class EvaluationReport:
    """Complete engineering quality report."""
    # Metadata
    timestamp: str
    toolkit_commit: str
    toolkit_version: str
    lockmate_version: str
    
    # Test results
    test_summary: Dict[str, Any] = field(default_factory=dict)
    unit_tests: Dict[str, Any] = field(default_factory=dict)
    integration_tests: Dict[str, Any] = field(default_factory=dict)
    adversarial_tests: Dict[str, Any] = field(default_factory=dict)
    validation_tests: Dict[str, Any] = field(default_factory=dict)
    practice_check: Dict[str, Any] = field(default_factory=dict)
    performance_benchmark: Dict[str, Any] = field(default_factory=dict)
    determinism_check: Dict[str, Any] = field(default_factory=dict)
    
    # Contract validation
    contract_validation: Dict[str, Any] = field(default_factory=dict)
    
    # PII leakage metrics
    pii_leakage: Dict[str, Any] = field(default_factory=dict)
    
    # Medical preservation
    medical_preservation: Dict[str, Any] = field(default_factory=dict)
    
    # Canary results
    canary_results: Dict[str, Any] = field(default_factory=dict)
    
    # Linkage metrics (Phase 5)
    linkage_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Privacy metrics (Phase 6)
    privacy_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Security metrics (Phase 7)
    security_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Resource usage
    runtime_seconds: float = 0.0
    peak_memory_mb: int = 0
    
    # Known limitations
    limitations: List[str] = field(default_factory=list)
    
    # Overall status
    overall_status: str = "unknown"  # pass, fail, partial
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    def save(self, path: Path):
        """Save report to file."""
        path.write_text(self.to_json())
        logger.info("evaluation_report_saved", path=str(path))


class EvaluationReportGenerator:
    """
    Generates comprehensive engineering quality report.
    
    Aggregates results from all evaluation phases into a single
    PII-free report.
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def generate(
        self,
        benchmark_summary: Optional[Dict] = None,
        contract_validation: Optional[Dict] = None,
        pii_leakage: Optional[Dict] = None,
        medical_preservation: Optional[Dict] = None,
        canary_results: Optional[Dict] = None,
        linkage_metrics: Optional[Dict] = None,
        privacy_metrics: Optional[Dict] = None,
        security_metrics: Optional[Dict] = None,
        runtime_seconds: float = 0.0,
        peak_memory_mb: int = 0,
        limitations: Optional[List[str]] = None
    ) -> EvaluationReport:
        """
        Generate evaluation report from collected metrics.
        
        All inputs are optional - missing sections will be marked as not executed.
        """
        commit = self._get_git_commit()
        
        report = EvaluationReport(
            timestamp=datetime.utcnow().isoformat() + "Z",
            toolkit_commit=commit,
            toolkit_version=self._get_toolkit_version(),
            lockmate_version="1.0.0",
            runtime_seconds=runtime_seconds,
            peak_memory_mb=peak_memory_mb,
            limitations=limitations or self._get_default_limitations()
        )
        
        # Populate from benchmark summary
        if benchmark_summary:
            report.test_summary = benchmark_summary.get("machine_readable", {})
            for phase_result in benchmark_summary.get("phases", []):
                phase = phase_result.get("phase")
                if phase == "unit":
                    report.unit_tests = phase_result
                elif phase == "integration":
                    report.integration_tests = phase_result
                elif phase == "adversarial":
                    report.adversarial_tests = phase_result
                elif phase == "validation":
                    report.validation_tests = phase_result
                elif phase == "practice":
                    report.practice_check = phase_result
                elif phase == "performance":
                    report.performance_benchmark = phase_result
                elif phase == "determinism":
                    report.determinism_check = phase_result
        
        # Populate other sections
        if contract_validation:
            report.contract_validation = contract_validation
        else:
            report.contract_validation = {"executed": False, "reason": "Not provided"}
        
        if pii_leakage:
            report.pii_leakage = pii_leakage
        else:
            report.pii_leakage = {"executed": False, "reason": "Not provided"}
        
        if medical_preservation:
            report.medical_preservation = medical_preservation
        else:
            report.medical_preservation = {"executed": False, "reason": "Not provided"}
        
        if canary_results:
            report.canary_results = canary_results
        else:
            report.canary_results = {"executed": False, "reason": "Not provided"}
        
        if linkage_metrics:
            report.linkage_metrics = linkage_metrics
        else:
            report.linkage_metrics = {"executed": False, "reason": "Phase 5 not integrated"}
        
        if privacy_metrics:
            report.privacy_metrics = privacy_metrics
        else:
            report.privacy_metrics = {"executed": False, "reason": "Phase 6 not integrated"}
        
        if security_metrics:
            report.security_metrics = security_metrics
        else:
            report.security_metrics = {"executed": False, "reason": "Phase 7 not integrated"}
        
        # Determine overall status
        report.overall_status = self._determine_status(report)
        
        return report
    
    def _get_git_commit(self) -> str:
        """Get current git commit."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "unknown"
    
    def _get_toolkit_version(self) -> str:
        """Get toolkit version from pyproject.toml or similar."""
        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomli
                with open(pyproject, "rb") as f:
                    data = tomli.load(f)
                return data.get("project", {}).get("version", "unknown")
            except Exception:
                pass
        return "unknown"
    
    def _get_default_limitations(self) -> List[str]:
        """Get default list of known limitations."""
        return [
            "Phase 5 (cross-hospital identity linkage) not yet integrated",
            "Phase 6 (quasi-identifier privacy) components implemented but not integrated into main pipeline",
            "Phase 7 (security hardening) components implemented but not integrated into main pipeline",
            "Phase 8 (adversarial evaluation) framework created but requires integration testing",
            "Synthetic testing only - no validation on organizer's hidden test set",
            "Gazetteer data for location generalization is minimal (placeholder)",
            "Rare disease suppression uses keyword matching, not clinical ontology",
            "Date shifting preserves intervals but not seasonal patterns",
            "Age bands are fixed 5-year; wider bands for high-risk not yet configurable per-field",
            "Cross-release linkage attack not simulated (requires multiple releases)",
            "Pseudonym inversion assumes HMAC-SHA256 security; no side-channel analysis",
            "Performance benchmarks use synthetic data; real-world performance may vary",
            "Offline execution verified but not tested in fully air-gapped environment",
            "Memory profiling uses basic RSS; detailed allocation tracking not implemented",
            "Determinism verified for same secret; different secret behavior not fully tested"
        ]
    
    def _determine_status(self, report: EvaluationReport) -> str:
        """Determine overall status from report."""
        # Check if critical tests passed
        critical_phases = ["unit", "validation"]
        
        for phase in critical_phases:
            phase_data = getattr(report, f"{phase}_tests", {})
            if phase_data and not phase_data.get("passed", False):
                return "fail"
        
        # Check if any executed tests failed
        all_phases = [
            report.unit_tests,
            report.integration_tests,
            report.adversarial_tests,
            report.validation_tests,
            report.practice_check,
            report.determinism_check
        ]
        
        executed_phases = [p for p in all_phases if p and not p.get("metrics", {}).get("skipped")]
        if executed_phases:
            failed = [p for p in executed_phases if not p.get("passed", True)]
            if failed:
                return "partial"
        
        return "pass"


def generate_evaluation_report(
    project_root: Path,
    output_path: Path,
    **kwargs
) -> EvaluationReport:
    """
    Convenience function to generate and save evaluation report.
    
    Args:
        project_root: Project root directory
        output_path: Path to save report
        **kwargs: All metrics dictionaries
        
    Returns:
        Generated EvaluationReport
    """
    generator = EvaluationReportGenerator(project_root)
    report = generator.generate(**kwargs)
    report.save(output_path)
    return report


def collect_pii_leakage_metrics(output_dir: Path) -> Dict[str, Any]:
    """
    Scan output directory for PII leakage.
    
    Returns metrics on any detected PII in sanitized output.
    """
    import re
    
    pii_patterns = {
        "aadhaar": re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
        "pan": re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b'),
        "phone": re.compile(r'(?:\+91[\s-]?)?[6-9]\d{9}\b'),
        "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        "abha": re.compile(r'\b\d{14}\b'),
    }
    
    results = {pii_type: 0 for pii_type in pii_patterns}
    results["files_scanned"] = 0
    results["files_with_leaks"] = 0
    results["leak_details"] = []
    
    sanitized_dir = output_dir / "sanitized"
    if sanitized_dir.exists():
        for file_path in sanitized_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in [".json", ".jsonl", ".csv", ".txt", ".xml"]:
                try:
                    content = file_path.read_text(errors="ignore")
                    results["files_scanned"] += 1
                    
                    file_leaks = {}
                    for pii_type, pattern in pii_patterns.items():
                        matches = pattern.findall(content)
                        if matches:
                            results[pii_type] += len(matches)
                            file_leaks[pii_type] = len(matches)
                    
                    if file_leaks:
                        results["files_with_leaks"] += 1
                        results["leak_details"].append({
                            "file": str(file_path.relative_to(output_dir)),
                            "leaks": file_leaks
                        })
                except Exception as e:
                    results["leak_details"].append({
                        "file": str(file_path.relative_to(output_dir)),
                        "error": str(e)
                    })
    
    return results


def collect_medical_preservation_metrics(
    input_dir: Path,
    output_dir: Path
) -> Dict[str, Any]:
    """
    Measure clinical/medical information preservation.
    
    Compares medical entities in input vs output.
    """
    # This would require parsing both input and output
    # For now, return placeholder structure
    return {
        "executed": False,
        "reason": "Requires input/output comparison implementation",
        "metrics": {
            "drugs_preserved": 0,
            "drugs_total": 0,
            "diagnoses_preserved": 0,
            "diagnoses_total": 0,
            "labs_preserved": 0,
            "labs_total": 0,
            "procedures_preserved": 0,
            "procedures_total": 0,
            "dosages_preserved": 0,
            "dosages_total": 0
        }
    }


def collect_canary_results(output_dir: Path, expected_canaries: Dict[str, str]) -> Dict[str, Any]:
    """
    Verify canary values in output.
    """
    results = {
        "total_expected": len(expected_canaries),
        "found": 0,
        "missing": [],
        "tampered": []
    }
    
    for context, expected_canary in expected_canaries.items():
        found = False
        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                try:
                    content = file_path.read_text(errors="ignore")
                    if expected_canary in content:
                        found = True
                        break
                except Exception:
                    pass
        
        if found:
            results["found"] += 1
        else:
            results["missing"].append(context)
    
    results["all_present"] = results["found"] == results["total_expected"]
    return results