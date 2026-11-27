"""
LOCKMATE — Phase 8: Hidden-Format Robustness Tests

Tests LOCKMATE on formats and labels not explicitly used during tuning:
- Changed CSV column names
- New JSON nesting structures
- New metadata locations
- Unusual field labels
- Different transliteration variants
- Unexpected separators
- New document naming conventions
- Mixed-script sentences

Files that cannot be processed safely are quarantined.
"""

from __future__ import annotations

import logging
import tempfile
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from ..utils.logging import get_logger

logger = get_logger("evaluation.adversarial_tests")


class TestResult(Enum):
    """Result of an adversarial test."""
    PASS = "pass"
    FAIL = "fail"
    QUARANTINE = "quarantine"
    ERROR = "error"


@dataclass
class AdversarialTestCase:
    """A single adversarial test case."""
    name: str
    description: str
    generator: Callable[[], bytes]  # Returns file content
    expected_behavior: str  # "process", "quarantine", "fail_gracefully"
    file_extension: str = ".txt"
    mime_type: str = "text/plain"


@dataclass
class AdversarialTestResult:
    """Result of running an adversarial test."""
    test_name: str
    result: TestResult
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    output_files: List[str] = field(default_factory=list)
    quarantine_files: List[str] = field(default_factory=list)


class AdversarialTestSuite:
    """
    Suite of adversarial format robustness tests.
    
    Generates challenging inputs and verifies LOCKMATE handles them
    safely (processes correctly or quarantines gracefully).
    """
    
    def __init__(self, pipeline_func: Callable[[Path, Path, bytes], Any], secret: bytes):
        """
        Initialize test suite.
        
        Args:
            pipeline_func: Function(input_dir, output_dir, secret) -> result
            secret: RAKSHA_SECRET for testing
        """
        self.pipeline_func = pipeline_func
        self.secret = secret
        self.test_cases: List[AdversarialTestCase] = []
        self.results: List[AdversarialTestResult] = []
        self._register_default_tests()
    
    def _register_default_tests(self):
        """Register default adversarial test cases."""
        
        # Test 1: CSV with renamed columns
        self.test_cases.append(AdversarialTestCase(
            name="csv_renamed_columns",
            description="CSV with non-standard column names",
            generator=self._gen_csv_renamed_columns,
            expected_behavior="process",
            file_extension=".csv"
        ))
        
        # Test 2: JSON with deep nesting
        self.test_cases.append(AdversarialTestCase(
            name="json_deep_nesting",
            description="JSON with deeply nested PII",
            generator=self._gen_json_deep_nesting,
            expected_behavior="process",
            file_extension=".json"
        ))
        
        # Test 3: JSON with PII in unusual keys
        self.test_cases.append(AdversarialTestCase(
            name="json_unusual_keys",
            description="JSON with PII in non-standard keys",
            generator=self._gen_json_unusual_keys,
            expected_behavior="process",
            file_extension=".json"
        ))
        
        # Test 4: Mixed script content
        self.test_cases.append(AdversarialTestCase(
            name="mixed_script",
            description="Text with mixed English/Hindi/transliterated content",
            generator=self._gen_mixed_script,
            expected_behavior="process",
            file_extension=".txt"
        ))
        
        # Test 5: Unusual date formats
        self.test_cases.append(AdversarialTestCase(
            name="unusual_dates",
            description="Various non-standard date formats",
            generator=self._gen_unusual_dates,
            expected_behavior="process",
            file_extension=".txt"
        ))
        
        # Test 6: CSV with unexpected separators
        self.test_cases.append(AdversarialTestCase(
            name="csv_pipe_separated",
            description="Pipe-separated values instead of comma",
            generator=self._gen_csv_pipe_separated,
            expected_behavior="process",
            file_extension=".csv"
        ))
        
        # Test 7: Malformed JSON
        self.test_cases.append(AdversarialTestCase(
            name="malformed_json",
            description="JSON with syntax errors",
            generator=self._gen_malformed_json,
            expected_behavior="quarantine",
            file_extension=".json"
        ))
        
        # Test 8: Very large record
        self.test_cases.append(AdversarialTestCase(
            name="large_record",
            description="Record with extremely long text fields",
            generator=self._gen_large_record,
            expected_behavior="process",
            file_extension=".json"
        ))
        
        # Test 9: Binary content in text file
        self.test_cases.append(AdversarialTestCase(
            name="binary_in_text",
            description="Text file with embedded binary data",
            generator=self._gen_binary_in_text,
            expected_behavior="quarantine",
            file_extension=".txt"
        ))
        
        # Test 10: FHIR with non-standard extensions
        self.test_cases.append(AdversarialTestCase(
            name="fhir_custom_extensions",
            description="FHIR bundle with custom extensions containing PII",
            generator=self._gen_fhir_custom_extensions,
            expected_behavior="process",
            file_extension=".json"
        ))
        
        # Test 11: CSV with quoted newlines
        self.test_cases.append(AdversarialTestCase(
            name="csv_quoted_newlines",
            description="CSV with newlines inside quoted fields",
            generator=self._gen_csv_quoted_newlines,
            expected_behavior="process",
            file_extension=".csv"
        ))
        
        # Test 12: Transliteration variants
        self.test_cases.append(AdversarialTestCase(
            name="transliteration_variants",
            description="Multiple transliteration schemes for same names",
            generator=self._gen_transliteration_variants,
            expected_behavior="process",
            file_extension=".txt"
        ))
        
        # Test 13: Empty/null values
        self.test_cases.append(AdversarialTestCase(
            name="empty_null_values",
            description="Records with many empty or null fields",
            generator=self._gen_empty_null_values,
            expected_behavior="process",
            file_extension=".csv"
        ))
        
        # Test 14: Unicode edge cases
        self.test_cases.append(AdversarialTestCase(
            name="unicode_edge_cases",
            description="Unicode normalization edge cases (ZWJ, RTL, etc.)",
            generator=self._gen_unicode_edge_cases,
            expected_behavior="process",
            file_extension=".txt"
        ))
        
        # Test 15: Multiple encodings
        self.test_cases.append(AdversarialTestCase(
            name="multiple_encodings",
            description="File with mixed UTF-8 and Latin-1 content",
            generator=self._gen_multiple_encodings,
            expected_behavior="process",
            file_extension=".txt"
        ))
    
    def add_test_case(self, test_case: AdversarialTestCase):
        """Add a custom test case."""
        self.test_cases.append(test_case)
    
    def run_all(self, output_base: Path) -> List[AdversarialTestResult]:
        """
        Run all adversarial tests.
        
        Args:
            output_base: Base directory for test outputs
            
        Returns:
            List of test results
        """
        self.results = []
        
        for test_case in self.test_cases:
            logger.info("running_adversarial_test", test=test_case.name)
            result = self._run_single_test(test_case, output_base)
            self.results.append(result)
            
            logger.info("adversarial_test_complete",
                       test=test_case.name,
                       result=result.result.value,
                       message=result.message)
        
        return self.results
    
    def _run_single_test(
        self, 
        test_case: AdversarialTestCase, 
        output_base: Path
    ) -> AdversarialTestResult:
        """Run a single adversarial test case."""
        import time
        import shutil
        
        start_time = time.time()
        
        # Create temporary input directory
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            input_dir.mkdir()
            
            output_dir = output_base / f"adversarial_{test_case.name}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                # Generate test file
                content = test_case.generator()
                test_file = input_dir / f"test{test_case.file_extension}"
                test_file.write_bytes(content)
                
                # Run pipeline
                self.pipeline_func(input_dir, output_dir, self.secret)
                
                processing_time = (time.time() - start_time) * 1000
                
                # Analyze results
                return self._analyze_result(test_case, output_dir, processing_time)
                
            except Exception as e:
                processing_time = (time.time() - start_time) * 1000
                
                if test_case.expected_behavior == "quarantine":
                    # Expected to fail/quarantine
                    return AdversarialTestResult(
                        test_name=test_case.name,
                        result=TestResult.PASS,
                        message=f"Correctly failed/quarantined: {type(e).__name__}",
                        details={"exception": type(e).__name__},
                        processing_time_ms=processing_time
                    )
                else:
                    return AdversarialTestResult(
                        test_name=test_case.name,
                        result=TestResult.ERROR,
                        message=f"Unexpected error: {e}",
                        details={"exception": type(e).__name__, "error": str(e)[:200]},
                        processing_time_ms=processing_time
                    )
    
    def _analyze_result(
        self, 
        test_case: AdversarialTestCase, 
        output_dir: Path,
        processing_time: float
    ) -> AdversarialTestResult:
        """Analyze test output."""
        sanitized_dir = output_dir / "sanitized"
        quarantined_dir = output_dir / "quarantined"
        
        sanitized_files = list(sanitized_dir.rglob("*")) if sanitized_dir.exists() else []
        quarantined_files = list(quarantined_dir.rglob("*")) if quarantined_dir.exists() else []
        
        sanitized_files = [f for f in sanitized_files if f.is_file()]
        quarantined_files = [f for f in quarantined_files if f.is_file()]
        
        if test_case.expected_behavior == "process":
            if sanitized_files:
                return AdversarialTestResult(
                    test_name=test_case.name,
                    result=TestResult.PASS,
                    message="Successfully processed",
                    processing_time_ms=processing_time,
                    output_files=[str(f) for f in sanitized_files],
                    quarantine_files=[str(f) for f in quarantined_files]
                )
            elif quarantined_files:
                return AdversarialTestResult(
                    test_name=test_case.name,
                    result=TestResult.QUARANTINE,
                    message="Unexpectedly quarantined",
                    processing_time_ms=processing_time,
                    output_files=[str(f) for f in sanitized_files],
                    quarantine_files=[str(f) for f in quarantined_files]
                )
            else:
                return AdversarialTestResult(
                    test_name=test_case.name,
                    result=TestResult.FAIL,
                    message="No output produced",
                    processing_time_ms=processing_time
                )
        
        elif test_case.expected_behavior == "quarantine":
            if quarantined_files:
                return AdversarialTestResult(
                    test_name=test_case.name,
                    result=TestResult.PASS,
                    message="Correctly quarantined",
                    processing_time_ms=processing_time,
                    output_files=[str(f) for f in sanitized_files],
                    quarantine_files=[str(f) for f in quarantined_files]
                )
            else:
                return AdversarialTestResult(
                    test_name=test_case.name,
                    result=TestResult.FAIL,
                    message="Should have been quarantined but wasn't",
                    processing_time_ms=processing_time,
                    output_files=[str(f) for f in sanitized_files]
                )
        
        return AdversarialTestResult(
            test_name=test_case.name,
            result=TestResult.FAIL,
            message="Unknown expected behavior",
            processing_time_ms=processing_time
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test suite summary."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.result == TestResult.PASS)
        failed = sum(1 for r in self.results if r.result == TestResult.FAIL)
        quarantined = sum(1 for r in self.results if r.result == TestResult.QUARANTINE)
        errors = sum(1 for r in self.results if r.result == TestResult.ERROR)
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "quarantined": quarantined,
            "errors": errors,
            "pass_rate": passed / total if total > 0 else 0,
            "results": [
                {
                    "test": r.test_name,
                    "result": r.result.value,
                    "message": r.message,
                    "time_ms": r.processing_time_ms
                }
                for r in self.results
            ]
        }
    
    # ==================== Test Generators ====================
    
    def _gen_csv_renamed_columns(self) -> bytes:
        """CSV with non-standard column names."""
        return b"""patient_full_name,contact_number,aadhaar_number,patient_age,home_address,admission_dt,discharge_dt,primary_diagnosis
"Rajesh Sharma","9876543210","1234 5678 9012","45","123 MG Road, Mumbai","2024-01-15","2024-01-20","Hypertension"
"Priya Verma","8765432109","2345 6789 0123","32","456 Gandhi Street, Delhi","2024-02-10","2024-02-15","Diabetes"
"""
    
    def _gen_json_deep_nesting(self) -> bytes:
        """JSON with deeply nested PII."""
        return b'''{
  "patient": {
    "personal": {
      "identity": {
        "name": "Amit Kumar",
        "identifiers": {
          "aadhaar": "3456 7890 1234",
          "pan": "ABCDE1234F"
        }
      }
    },
    "clinical": {
      "visits": [
        {
          "encounter": {
            "details": {
              "admission": "2024-03-01",
              "discharge": "2024-03-05",
              "diagnosis": "Bronchitis"
            }
          }
        }
      ]
    }
  }
}'''
    
    def _gen_json_unusual_keys(self) -> bytes:
        """JSON with PII in non-standard keys."""
        return b'''{
  "user_data": {
    "full_name": "Sunita Singh",
    "mobile_no": "7654321098",
    "uid_aadhaar": "4567 8901 2345",
    "email_addr": "sunita@example.com",
    "residential_address": "789 Park Avenue, Bangalore",
    "dob": "1980-05-15"
  },
  "medical_record": {
    "admit_date": "2024-04-10",
    "release_date": "2024-04-18",
    "condition": "Viral Fever"
  }
}'''
    
    def _gen_mixed_script(self) -> bytes:
        """Mixed script content."""
        text = """Patient: Rajesh Sharma (राजेश शर्मा)
Phone: 9876543210
Aadhaar: 1234 5678 9012
Address: 123 MG Road, Mumbai, Maharashtra
Diagnosis: Hypertension (उच्च रक्तचाप)
Doctor: Dr. Amit Kumar (डॉ. अमित कुमार)
Relative: Priya Sharma (प्रिया शर्मा)
Admission: 2024-01-15
Discharge: 2024-01-20
"""
        return text.encode('utf-8')
    
    def _gen_unusual_dates(self) -> bytes:
        """Various non-standard date formats."""
        return b"""Patient: Test Patient
Dates:
- 15/01/2024 (DD/MM/YYYY)
- 01-15-2024 (MM-DD-YYYY)
- 20240115 (YYYYMMDD)
- 15-Jan-2024 (DD-Mon-YYYY)
- Jan 15, 2024 (Mon DD, YYYY)
- 2024-01-15T10:30:00 (ISO with time)
- 2024-01-15T10:30:00+05:30 (ISO with timezone)
- 15/01/24 (DD/MM/YY)
- 01.15.2024 (MM.DD.YYYY)
"""
    
    def _gen_csv_pipe_separated(self) -> bytes:
        """Pipe-separated values."""
        return b"""name|phone|aadhaar|age|address|admission|discharge|diagnosis
Rajesh Sharma|9876543210|1234 5678 9012|45|123 MG Road, Mumbai|2024-01-15|2024-01-20|Hypertension
Priya Verma|8765432109|2345 6789 0123|32|456 Gandhi Street, Delhi|2024-02-10|2024-02-15|Diabetes
"""
    
    def _gen_malformed_json(self) -> bytes:
        """JSON with syntax errors."""
        return b'''{
  "patient": {
    "name": "Test Patient",
    "aadhaar": "1234 5678 9012",
    "visits": [
      {"date": "2024-01-15", "diagnosis": "Flu"}
    ]  // Missing closing brace
}'''
    
    def _gen_large_record(self) -> bytes:
        """Record with extremely long text fields."""
        long_text = "x" * 100000  # 100KB text field
        return f'''{{
  "patient": {{
    "name": "Test Patient",
    "notes": "{long_text}",
    "aadhaar": "1234 5678 9012"
  }}
}}'''.encode()
    
    def _gen_binary_in_text(self) -> bytes:
        """Text file with embedded binary data."""
        text = b"Patient: Test Patient\nAadhaar: 1234 5678 9012\n"
        binary = bytes(range(256)) * 10  # Binary data
        return text + b"\nAttachment: " + binary + b"\nEnd of record"
    
    def _gen_fhir_custom_extensions(self) -> bytes:
        """FHIR with custom extensions containing PII."""
        return b'''{
  "resourceType": "Bundle",
  "type": "collection",
  "entry": [
    {
      "resource": {
        "resourceType": "Patient",
        "id": "patient-1",
        "extension": [
          {
            "url": "http://hospital.org/extensions/aadhaar",
            "valueString": "1234 5678 9012"
          },
          {
            "url": "http://hospital.org/extensions/phone",
            "valueString": "9876543210"
          }
        ],
        "name": [{"text": "Test Patient"}]
      }
    }
  ]
}'''
    
    def _gen_csv_quoted_newlines(self) -> bytes:
        """CSV with newlines inside quoted fields."""
        return b'''name,address,notes
"Rajesh Sharma","123 MG Road\nMumbai\nMaharashtra","Admitted for\nHypertension\nTreatment"
"Priya Verma","456 Gandhi Street\nDelhi","Diabetes\nFollow-up"
'''
    
    def _gen_transliteration_variants(self) -> bytes:
        """Multiple transliteration schemes."""
        text = """Names:
- Rajesh Sharma (standard)
- Raajesh Sharma (double vowel)
- Rajes Sharma (dropped vowel)
- Rajesh Sharmah (added h)
- Rajesh Kumar Sharma (added middle)
- Sharma Rajesh (reversed order)
- RAJESH SHARMA (uppercase)
- rajesh sharma (lowercase)
- राज़ेश शर्मा (Devanagari)
"""
        return text.encode('utf-8')
    
    def _gen_empty_null_values(self) -> bytes:
        """Records with many empty/null fields."""
        return b'''name,phone,aadhaar,age,address,admission,discharge,diagnosis
"Test Patient",,,,"",,,
"Another Patient",9876543210,,30,,2024-01-15,,
"Third Patient",,,,"123 Street",,,Flu
,,,40,,2024-02-01,2024-02-05,
'''
    
    def _gen_unicode_edge_cases(self) -> bytes:
        """Unicode normalization edge cases."""
        # Zero-width joiner, RTL marks, etc.
        zwj = "\u200d"
        rlm = "\u200f"
        lrm = "\u200e"
        
        text = f"""Patient: Raj{zwj}esh Sharma{rlm}
Phone: 9876543210
Aadhaar: 1234 5678 9012
Address: 123 MG Road{lrm} Mumbai
Diagnosis: Hypertension
"""
        return text.encode('utf-8')
    
    def _gen_multiple_encodings(self) -> bytes:
        """File with mixed UTF-8 and Latin-1 content."""
        # Start with UTF-8
        utf8_part = "Patient: Rajesh Sharma\nAadhaar: 1234 5678 9012\n".encode('utf-8')
        # Add Latin-1 encoded Hindi (will be mojibake but tests encoding detection)
        latin1_part = "रोगी: राजेश शर्मा\n".encode('latin-1', errors='replace')
        return utf8_part + latin1_part + b"\nEnd of record"


def run_adversarial_tests(
    pipeline_func: Callable[[Path, Path, bytes], Any],
    secret: bytes,
    output_base: Path
) -> Dict[str, Any]:
    """
    Convenience function to run all adversarial tests.
    
    Args:
        pipeline_func: Pipeline function to test
        secret: RAKSHA_SECRET
        output_base: Base output directory
        
    Returns:
        Test summary dictionary
    """
    suite = AdversarialTestSuite(pipeline_func, secret)
    suite.run_all(output_base)
    return suite.get_summary()