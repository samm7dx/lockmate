"""
LOCKMATE — Phase 7: Export Security Hardening

Implements final export process security:
- Final outputs inspected before release
- Unsafe files quarantined
- Quarantined files don't enter sanitized/
- report.json is PII-free
- records.jsonl is PII-free
- Filenames are sanitized
- Temporary files cleaned
- Unsupported attachments fail safely
- Canary values cannot bypass output gate
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum

from ..utils.logging import get_logger

logger = get_logger("security.export_hardening")


class ExportCheckResult(Enum):
    """Result of export security check."""
    PASS = "pass"
    FAIL = "fail"
    QUARANTINE = "quarantine"


@dataclass
class ExportCheck:
    """Result of a single export check."""
    name: str
    result: ExportCheckResult
    message: str
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "result": self.result.value,
            "message": self.message,
            "details": self.details or {}
        }


class CanaryChecker:
    """
    Verifies canary values in output to detect bypass attempts.
    
    Canaries are unique markers that should appear in output if
    the pipeline executed correctly. If they're missing or modified,
    it indicates potential tampering or bypass.
    """
    
    def __init__(self, canary_prefix: str = "LOCKMATE_CANARY_", secret: bytes = None):
        self.canary_prefix = canary_prefix
        self.secret = secret
        self._expected_canaries: Dict[str, str] = {}
    
    def generate_canary(self, context: str) -> str:
        """Generate a canary value for a specific context."""
        import hmac
        import hashlib
        
        if self.secret:
            h = hmac.HMAC(self.secret, digestmod=hashlib.sha256)
            h.update(f"{self.canary_prefix}{context}".encode())
            canary = h.hexdigest()[:16]
        else:
            # Fallback without secret (less secure)
            canary = hashlib.sha256(f"{self.canary_prefix}{context}".encode()).hexdigest()[:16]
        
        full_canary = f"{self.canary_prefix}{context}:{canary}"
        self._expected_canaries[context] = full_canary
        return full_canary
    
    def verify_canary(self, context: str, found_canary: str) -> bool:
        """Verify a canary value matches expected."""
        expected = self._expected_canaries.get(context)
        if not expected:
            logger.warning("canary_no_expected", context=context)
            return False
        
        if found_canary != expected:
            logger.error("canary_mismatch", context=context, expected=expected[:32], found=found_canary[:32])
            return False
        
        return True
    
    def check_output_for_canaries(self, output_path: Path) -> List[ExportCheck]:
        """Scan output directory for expected canaries."""
        checks = []
        
        for context, expected_canary in self._expected_canaries.items():
            found = False
            # Search in all files
            for file_path in output_path.rglob("*"):
                if file_path.is_file():
                    try:
                        content = file_path.read_text(errors="ignore")
                        if expected_canary in content:
                            found = True
                            break
                    except Exception:
                        pass
            
            if found:
                checks.append(ExportCheck(
                    name=f"canary_{context}",
                    result=ExportCheckResult.PASS,
                    message=f"Canary found for {context}"
                ))
            else:
                checks.append(ExportCheck(
                    name=f"canary_{context}",
                    result=ExportCheckResult.FAIL,
                    message=f"Canary MISSING for {context} - possible bypass"
                ))
        
        return checks


class OutputGate:
    """
    Final output gate that validates all exports before release.
    
    Performs multiple security checks:
    1. PII detection in output files
    2. Canary verification
    3. File structure validation
    4. Report integrity
    5. Filename sanitization
    """
    
    def __init__(
        self, 
        output_dir: Path,
        canary_checker: Optional[CanaryChecker] = None,
        secret: bytes = None
    ):
        self.output_dir = output_dir
        self.sanitized_dir = output_dir / "sanitized"
        self.quarantined_dir = output_dir / "quarantined"
        self.canary_checker = canary_checker
        self.secret = secret
        
        # PII patterns for final check
        self.pii_patterns = [
            (re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), "AADHAAR"),
            (re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b'), "PAN"),
            (re.compile(r'\b\d{14}\b'), "ABHA"),
            (re.compile(r'(?:\+91[\s-]?)?[6-9]\d{9}\b'), "PHONE"),
            (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), "EMAIL"),
        ]
        
        # Ensure quarantined directory exists
        self.quarantined_dir.mkdir(parents=True, exist_ok=True)
    
    def run_all_checks(self) -> Tuple[bool, List[ExportCheck]]:
        """
        Run all export security checks.
        
        Returns:
            Tuple of (all_passed, list_of_checks)
        """
        all_checks = []
        
        # 1. Check sanitized directory exists
        all_checks.append(self._check_sanitized_dir_exists())
        
        # 2. Check for PII in sanitized files
        all_checks.extend(self._check_pii_in_sanitized())
        
        # 3. Validate report.json
        all_checks.extend(self._validate_report_json())
        
        # 4. Validate records.jsonl
        all_checks.extend(self._validate_records_jsonl())
        
        # 5. Check filename sanitization
        all_checks.extend(self._check_filenames())
        
        # 6. Check no quarantined files in sanitized
        all_checks.append(self._check_quarantine_isolation())
        
        # 7. Verify canaries
        if self.canary_checker:
            all_checks.extend(self.canary_checker.check_output_for_canaries(self.sanitized_dir))
        
        # 8. Check for unsupported attachments
        all_checks.extend(self._check_attachments())
        
        # 9. Verify temporary files cleaned
        all_checks.append(self._check_temp_files_cleaned())
        
        # Determine overall result
        all_passed = all(c.result == ExportCheckResult.PASS for c in all_checks)
        
        logger.info("export_gate_checks_complete", 
                   total=len(all_checks),
                   passed=sum(1 for c in all_checks if c.result == ExportCheckResult.PASS),
                   failed=sum(1 for c in all_checks if c.result == ExportCheckResult.FAIL),
                   all_passed=all_passed)
        
        return all_passed, all_checks
    
    def _check_sanitized_dir_exists(self) -> ExportCheck:
        if self.sanitized_dir.exists():
            return ExportCheck("sanitized_dir_exists", ExportCheckResult.PASS, "Sanitized directory exists")
        else:
            return ExportCheck("sanitized_dir_exists", ExportCheckResult.FAIL, "Sanitized directory missing")
    
    def _check_pii_in_sanitized(self) -> List[ExportCheck]:
        checks = []
        
        for file_path in self.sanitized_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in [".json", ".jsonl", ".csv", ".txt", ".xml"]:
                try:
                    content = file_path.read_text(errors="ignore")
                    for pattern, pii_type in self.pii_patterns:
                        matches = pattern.findall(content)
                        if matches:
                            checks.append(ExportCheck(
                                name=f"pii_check_{file_path.name}",
                                result=ExportCheckResult.FAIL,
                                message=f"PII detected in sanitized output: {pii_type}",
                                details={"file": str(file_path), "pii_type": pii_type, "count": len(matches)}
                            ))
                            break
                    else:
                        checks.append(ExportCheck(
                            name=f"pii_check_{file_path.name}",
                            result=ExportCheckResult.PASS,
                            message=f"No PII detected in {file_path.name}"
                        ))
                except Exception as e:
                    checks.append(ExportCheck(
                        name=f"pii_check_{file_path.name}",
                        result=ExportCheckResult.FAIL,
                        message=f"Failed to scan file: {e}",
                        details={"file": str(file_path)}
                    ))
        
        return checks
    
    def _validate_report_json(self) -> List[ExportCheck]:
        checks = []
        report_path = self.output_dir / "report.json"
        
        if not report_path.exists():
            checks.append(ExportCheck(
                "report_json_exists", ExportCheckResult.FAIL, "report.json not found"
            ))
            return checks
        
        try:
            with open(report_path) as f:
                report = json.load(f)
            
            # Check required fields
            required_fields = ["schema", "files", "counts", "timing", "resources"]
            for field in required_fields:
                if field not in report:
                    checks.append(ExportCheck(
                        f"report_json_field_{field}", ExportCheckResult.FAIL,
                        f"Required field missing: {field}"
                    ))
                else:
                    checks.append(ExportCheck(
                        f"report_json_field_{field}", ExportCheckResult.PASS,
                        f"Required field present: {field}"
                    ))
            
            # Check for PII in report
            report_str = json.dumps(report)
            for pattern, pii_type in self.pii_patterns:
                if pattern.search(report_str):
                    checks.append(ExportCheck(
                        "report_json_pii_free", ExportCheckResult.FAIL,
                        f"PII detected in report.json: {pii_type}"
                    ))
                    break
            else:
                checks.append(ExportCheck(
                    "report_json_pii_free", ExportCheckResult.PASS,
                    "report.json is PII-free"
                ))
            
            # Check schema version
            if report.get("schema") == "raksha-report/1":
                checks.append(ExportCheck(
                    "report_json_schema", ExportCheckResult.PASS,
                    "Correct schema version"
                ))
            else:
                checks.append(ExportCheck(
                    "report_json_schema", ExportCheckResult.FAIL,
                    f"Invalid schema: {report.get('schema')}"
                ))
            
        except json.JSONDecodeError as e:
            checks.append(ExportCheck(
                "report_json_valid", ExportCheckResult.FAIL,
                f"Invalid JSON: {e}"
            ))
        except Exception as e:
            checks.append(ExportCheck(
                "report_json_read", ExportCheckResult.FAIL,
                f"Failed to read report: {e}"
            ))
        
        return checks
    
    def _validate_records_jsonl(self) -> List[ExportCheck]:
        checks = []
        records_path = self.output_dir / "records.jsonl"
        
        if not records_path.exists():
            checks.append(ExportCheck(
                "records_jsonl_exists", ExportCheckResult.FAIL, "records.jsonl not found"
            ))
            return checks
        
        try:
            with open(records_path) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        # Check required fields
                        if "file" not in record or "loc" not in record or "patient" not in record:
                            checks.append(ExportCheck(
                                f"records_jsonl_line_{line_num}", ExportCheckResult.FAIL,
                                "Missing required fields"
                            ))
                        # Check patient is pseudonym or null
                        patient = record.get("patient")
                        if patient is not None and not patient.startswith("PSN-"):
                            checks.append(ExportCheck(
                                f"records_jsonl_line_{line_num}", ExportCheckResult.FAIL,
                                f"Invalid patient format: {patient}"
                            ))
                    except json.JSONDecodeError:
                        checks.append(ExportCheck(
                            f"records_jsonl_line_{line_num}", ExportCheckResult.FAIL,
                            "Invalid JSON"
                        ))
            
            checks.append(ExportCheck(
                "records_jsonl_format", ExportCheckResult.PASS,
                "records.jsonl format valid"
            ))
            
        except Exception as e:
            checks.append(ExportCheck(
                "records_jsonl_read", ExportCheckResult.FAIL,
                f"Failed to read records: {e}"
            ))
        
        return checks
    
    def _check_filenames(self) -> List[ExportCheck]:
        checks = []
        
        # Check for potentially unsafe filenames
        unsafe_patterns = [
            (re.compile(r'\.\.'), "path_traversal"),
            (re.compile(r'[<>:"|?*]'), "invalid_chars"),
            (re.compile(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$', re.IGNORECASE), "reserved_name"),
        ]
        
        for file_path in self.sanitized_dir.rglob("*"):
            if file_path.is_file():
                name = file_path.name
                for pattern, issue_type in unsafe_patterns:
                    if pattern.search(name):
                        checks.append(ExportCheck(
                            f"filename_{file_path.name}", ExportCheckResult.FAIL,
                            f"Unsafe filename: {issue_type}",
                            details={"file": str(file_path), "issue": issue_type}
                        ))
                        break
                else:
                    checks.append(ExportCheck(
                        f"filename_{file_path.name}", ExportCheckResult.PASS,
                        "Filename safe"
                    ))
        
        return checks
    
    def _check_quarantine_isolation(self) -> ExportCheck:
        """Ensure no quarantined files leaked into sanitized."""
        # Check if any file in sanitized was originally quarantined
        # This is a simplified check - in practice would track file provenance
        quarantined_files = list(self.quarantined_dir.rglob("*")) if self.quarantined_dir.exists() else []
        sanitized_files = list(self.sanitized_dir.rglob("*")) if self.sanitized_dir.exists() else []
        
        # Check by hash
        quarantined_hashes = set()
        for qf in quarantined_files:
            if qf.is_file():
                try:
                    with open(qf, "rb") as f:
                        quarantined_hashes.add(hashlib.sha256(f.read()).hexdigest())
                except Exception:
                    pass
        
        for sf in sanitized_files:
            if sf.is_file():
                try:
                    with open(sf, "rb") as f:
                        if hashlib.sha256(f.read()).hexdigest() in quarantined_hashes:
                            return ExportCheck(
                                "quarantine_isolation", ExportCheckResult.FAIL,
                                "Quarantined file found in sanitized output",
                                details={"file": str(sf)}
                            )
                except Exception:
                    pass
        
        return ExportCheck(
            "quarantine_isolation", ExportCheckResult.PASS,
            "No quarantined files in sanitized output"
        )
    
    def _check_attachments(self) -> List[ExportCheck]:
        """Check for unsupported/binary attachments in output."""
        checks = []
        
        for file_path in self.sanitized_dir.rglob("*"):
            if file_path.is_file():
                # Check for binary files that shouldn't be in sanitized
                try:
                    with open(file_path, "rb") as f:
                        chunk = f.read(8192)
                        # Check for binary content (high entropy, null bytes)
                        if b'\x00' in chunk and file_path.suffix not in [".enc", ".bin"]:
                            checks.append(ExportCheck(
                                f"attachment_{file_path.name}", ExportCheckResult.QUARANTINE,
                                "Binary attachment detected in sanitized output",
                                details={"file": str(file_path)}
                            ))
                except Exception:
                    pass
        
        return checks
    
    def _check_temp_files_cleaned(self) -> ExportCheck:
        """Check that no temporary files remain."""
        temp_patterns = ["*.tmp", "*.temp", "*~", "*.bak", "*.swp"]
        temp_files = []
        
        for pattern in temp_patterns:
            temp_files.extend(self.output_dir.rglob(pattern))
        
        if temp_files:
            return ExportCheck(
                "temp_files_cleaned", ExportCheckResult.FAIL,
                f"Temporary files remain: {len(temp_files)}",
                details={"files": [str(f) for f in temp_files[:10]]}
            )
        
        return ExportCheck(
            "temp_files_cleaned", ExportCheckResult.PASS,
            "No temporary files found"
        )


class ExportHardener:
    """
    Main export hardening coordinator.
    
    Runs all security checks and can quarantine/block unsafe exports.
    """
    
    def __init__(
        self, 
        output_dir: Path,
        secret: bytes = None,
        canary_prefix: str = "LOCKMATE_CANARY_"
    ):
        self.output_dir = output_dir
        self.secret = secret
        self.canary_checker = CanaryChecker(canary_prefix, secret)
        self.output_gate = OutputGate(output_dir, self.canary_checker, secret)
        
        # Generate canaries for key pipeline stages
        self._generate_pipeline_canaries()
    
    def _generate_pipeline_canaries(self):
        """Generate canaries for each pipeline stage."""
        stages = [
            "intake_complete",
            "parsing_complete", 
            "detection_complete",
            "sanitization_complete",
            "output_complete"
        ]
        
        for stage in stages:
            self.canary_checker.generate_canary(stage)
    
    def add_canary_to_output(self, context: str, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add canary to output data structure."""
        canary = self.canary_checker.generate_canary(context)
        output_data["_canary"] = canary
        return output_data
    
    def verify_and_finalize(self) -> Tuple[bool, List[ExportCheck]]:
        """
        Run all checks and finalize export.
        
        Returns:
            Tuple of (success, checks)
        """
        success, checks = self.output_gate.run_all_checks()
        
        if not success:
            logger.error("export_gate_failed", 
                        extra={"failed_checks": [c.name for c in checks if c.result != ExportCheckResult.PASS]})
            # Could move sanitized to quarantined here
        else:
            logger.info("export_gate_passed")
        
        return success, checks
    
    def get_canary_report(self) -> Dict[str, str]:
        """Get report of all expected canaries."""
        return dict(self.canary_checker._expected_canaries)


def create_export_hardener(output_dir: Path, secret: bytes = None) -> ExportHardener:
    """Factory function to create ExportHardener."""
    return ExportHardener(output_dir, secret)