"""
LOCKMATE — Contract Tests

Tests for the shared data contracts (contracts.py).
"""

import pytest
from pathlib import Path
from datetime import datetime

from secret_wards.contracts import (
    # Enums
    FormatType,
    RecordStatus,
    FieldType,
    PIIType,
    MedicalType,
    QuarantineReason,
    RecordLocationType,
    # Data Classes
    InputFile,
    ParsedDocument,
    RecordLocation,
    FieldValue,
    UnifiedRecord,
    PIISpan,
    MedicalSpan,
    IdentityCandidate,
    PatientCluster,
    PrivacyTransformation,
    SanitizedRecord,
    QuarantineResult,
    ProcessingMetrics,
    # Report Structures
    FileReportEntry,
    ReportTotals,
    ReportTiming,
    ReportResources,
    FullReport,
    RecordsEntry,
    # Utility Functions
    compute_sha256,
    generate_pseudonym_format,
    derive_date_shift,
)


class TestEnums:
    """Test enum definitions."""
    
    def test_format_type_values(self):
        assert FormatType.CSV.value == "csv"
        assert FormatType.TSV.value == "tsv"
        assert FormatType.JSON.value == "json"
        assert FormatType.TEXT.value == "text"
        assert FormatType.FHIR.value == "fhir"
        assert FormatType.UNKNOWN.value == "unknown"
    
    def test_record_status_values(self):
        assert RecordStatus.PENDING.value == "pending"
        assert RecordStatus.PROCESSED.value == "processed"
        assert RecordStatus.QUARANTINED.value == "quarantined"
    
    def test_pii_type_completeness(self):
        # All required PII types from context.md §9.3
        required = {
            "NAME", "PHONE", "AADHAAR", "ABHA", "PAN",
            "EMAIL", "ADDRESS", "DATE", "UHID", "RELATIVE",
            "DOCTOR", "URL", "PIN"
        }
        actual = {t.name for t in PIIType}
        assert required.issubset(actual), f"Missing PII types: {required - actual}"
    
    def test_medical_type_completeness(self):
        required = {
            "DRUG", "DOSAGE", "FREQUENCY", "DURATION",
            "DIAGNOSIS", "PROCEDURE", "LAB", "VITAL", "UNIT"
        }
        actual = {t.name for t in MedicalType}
        assert required.issubset(actual), f"Missing Medical types: {required - actual}"


class TestInputFile:
    """Test InputFile dataclass."""
    
    def test_creation(self):
        file = InputFile(
            path=Path("/test/file.csv"),
            sha256="a" * 64,
            size_bytes=1024,
            format=FormatType.CSV,
            encoding="utf-8"
        )
        assert file.path == Path("/test/file.csv")
        assert file.sha256 == "a" * 64
        assert file.format == FormatType.CSV
    
    def test_serialization_roundtrip(self):
        file = InputFile(
            path=Path("/test/file.csv"),
            sha256="a" * 64,
            size_bytes=1024,
            format=FormatType.CSV,
            encoding="utf-8"
        )
        data = file.to_dict()
        restored = InputFile.from_dict(data)
        assert restored.path == file.path
        assert restored.sha256 == file.sha256
        assert restored.format == file.format


class TestRecordLocation:
    """Test RecordLocation dataclass."""
    
    def test_row_location(self):
        loc = RecordLocation.from_row(5)
        assert loc.location_type == RecordLocationType.ROW
        assert loc.value == "row:5"
        assert str(loc) == "row:row:5"
    
    def test_json_pointer_location(self):
        loc = RecordLocation.from_json_pointer("/visits/3")
        assert loc.location_type == RecordLocationType.JSON_POINTER
        assert loc.value == "/visits/3"
    
    def test_doc_location(self):
        loc = RecordLocation.from_doc()
        assert loc.location_type == RecordLocationType.DOC
        assert loc.value == "doc"
    
    def test_serialization_roundtrip(self):
        loc = RecordLocation.from_row(10)
        data = loc.to_dict()
        restored = RecordLocation.from_dict(data)
        assert restored.location_type == loc.location_type
        assert restored.value == loc.value


class TestFieldValue:
    """Test FieldValue dataclass."""
    
    def test_creation(self):
        fv = FieldValue(
            value="John Doe",
            field_type=FieldType.STRING,
            path="patient.name",
            is_identifier_field=True
        )
        assert fv.value == "John Doe"
        assert fv.field_type == FieldType.STRING
        assert fv.path == "patient.name"
        assert fv.is_identifier_field is True
    
    def test_serialization_roundtrip(self):
        fv = FieldValue(
            value=42,
            field_type=FieldType.NUMBER,
            path="patient.age",
            is_identifier_field=False
        )
        data = fv.to_dict()
        restored = FieldValue.from_dict(data)
        assert restored.value == fv.value
        assert restored.field_type == fv.field_type


class TestUnifiedRecord:
    """Test UnifiedRecord dataclass."""
    
    def test_creation(self):
        record = UnifiedRecord(
            record_id="abc123:row:0",
            location=RecordLocation.from_row(0),
            fields={},
            raw_text="Patient John Doe",
            normalized_text="Patient John Doe",
            offset_map=[(0, 16)]
        )
        assert record.record_id == "abc123:row:0"
        assert record.status == RecordStatus.PENDING
        assert record.pseudonym is None
    
    def test_serialization_roundtrip(self):
        record = UnifiedRecord(
            record_id="abc123:row:0",
            location=RecordLocation.from_row(0),
            fields={
                "name": FieldValue("John", FieldType.STRING, "patient.name")
            },
            raw_text="Patient John",
            normalized_text="Patient John",
            offset_map=[(0, 12)]
        )
        data = record.to_dict()
        restored = UnifiedRecord.from_dict(data)
        assert restored.record_id == record.record_id
        assert "name" in restored.fields


class TestPIISpan:
    """Test PIISpan dataclass."""
    
    def test_creation(self):
        span = PIISpan(
            start=0,
            end=8,
            pii_type=PIIType.NAME,
            confidence=0.95,
            original_text="John Doe",
            context="Patient John Doe admitted",
            detector="name_detector"
        )
        assert span.start == 0
        assert span.end == 8
        assert span.pii_type == PIIType.NAME
        assert span.confidence == 0.95
    
    def test_overlaps(self):
        span1 = PIISpan(0, 8, PIIType.NAME, 0.9, "John Doe", "", "detector")
        span2 = PIISpan(5, 15, PIIType.PHONE, 0.8, "Doe 123", "", "detector")
        assert span1.overlaps(span2) is True
    
    def test_contains(self):
        span1 = PIISpan(0, 20, PIIType.NAME, 0.9, "John Doe Smith", "", "detector")
        span2 = PIISpan(5, 15, PIIType.NAME, 0.8, "Doe Smi", "", "detector")
        assert span1.contains(span2) is True
    
    def test_serialization_roundtrip(self):
        span = PIISpan(0, 8, PIIType.NAME, 0.9, "John Doe", "context", "detector")
        data = span.to_dict()
        restored = PIISpan.from_dict(data)
        assert restored.start == span.start
        assert restored.pii_type == span.pii_type


class TestMedicalSpan:
    """Test MedicalSpan dataclass."""
    
    def test_creation(self):
        span = MedicalSpan(
            start=10,
            end=18,
            medical_type=MedicalType.DOSAGE,
            confidence=0.95,
            original_text="500 mg"
        )
        assert span.medical_type == MedicalType.DOSAGE
        assert span.confidence == 0.95
    
    def test_overlaps(self):
        span1 = MedicalSpan(0, 10, MedicalType.DRUG, 0.9, "Paracetamol")
        span2 = MedicalSpan(5, 15, MedicalType.DOSAGE, 0.8, "cetamol 500")
        assert span1.overlaps(span2) is True


class TestPatientCluster:
    """Test PatientCluster dataclass."""
    
    def test_creation(self):
        cluster = PatientCluster(
            cluster_id="cluster_1",
            records=[],
            canonical_identity="aadhaar:123456789012|name:john_doe",
            pseudonym="PSN-a1b2c3d4",
            is_confident=True
        )
        assert cluster.cluster_id == "cluster_1"
        assert cluster.pseudonym == "PSN-a1b2c3d4"
        assert cluster.is_confident is True
    
    def test_add_record(self):
        cluster = PatientCluster(cluster_id="c1", records=[])
        record = UnifiedRecord(
            record_id="abc:row:0",
            location=RecordLocation.from_row(0),
            fields={},
            raw_text="test",
            normalized_text="test",
            offset_map=[]
        )
        cluster.add_record(record)
        assert len(cluster.records) == 1


class TestPrivacyTransformation:
    """Test PrivacyTransformation dataclass."""
    
    def test_creation(self):
        record = UnifiedRecord(
            record_id="abc:row:0",
            location=RecordLocation.from_row(0),
            fields={},
            raw_text="test",
            normalized_text="test",
            offset_map=[]
        )
        transform = PrivacyTransformation(
            record=record,
            date_shifts={"dob": -120},
            age_band="25-29",
            location_generalization={"village": "district"},
            suppressions=["rare_diagnosis"]
        )
        assert transform.date_shifts["dob"] == -120
        assert transform.age_band == "25-29"
    
    def test_serialization_roundtrip(self):
        record = UnifiedRecord(
            record_id="abc:row:0",
            location=RecordLocation.from_row(0),
            fields={},
            raw_text="test",
            normalized_text="test",
            offset_map=[]
        )
        transform = PrivacyTransformation(record=record, age_band="30-34")
        data = transform.to_dict()
        restored = PrivacyTransformation.from_dict(data, record)
        assert restored.age_band == "30-34"


class TestQuarantineResult:
    """Test QuarantineResult dataclass."""
    
    def test_creation(self):
        input_file = InputFile(
            path=Path("/test/bad.pdf"),
            sha256="b" * 64,
            size_bytes=0,
            format=FormatType.UNKNOWN,
            encoding="binary"
        )
        result = QuarantineResult(
            input_file=input_file,
            reason=QuarantineReason.UNSUPPORTED_FORMAT,
            output_path=Path("/output/quarantined/b.pdf"),
            records_affected=0,
            details="PDF not supported"
        )
        assert result.reason == QuarantineReason.UNSUPPORTED_FORMAT
        assert result.records_affected == 0


class TestProcessingMetrics:
    """Test ProcessingMetrics dataclass."""
    
    def test_creation(self):
        metrics = ProcessingMetrics(
            file_sha256="a" * 64,
            duration_ms=1500,
            peak_memory_mb=256,
            records_processed=100,
            identifiers_detected=50,
            records_linked=80,
            records_generalized=100,
            records_suppressed=5,
            records_quarantined=0
        )
        assert metrics.duration_ms == 1500
        assert metrics.peak_memory_mb == 256


class TestReportStructures:
    """Test report.json structures."""
    
    def test_file_report_entry(self):
        entry = FileReportEntry(
            input_sha256="a" * 64,
            output_path="sanitized/file.csv",
            status="sanitized",
            processing_duration_ms=100,
            peak_memory_mb=50,
            records_processed=10,
            identifiers_detected=5
        )
        assert entry.status == "sanitized"
    
    def test_report_totals(self):
        totals = ReportTotals(
            files_total=10,
            files_sanitized=8,
            files_quarantined=2,
            records_processed=100,
            identifiers_detected=50,
            records_linked=80,
            records_generalized=90,
            records_suppressed=5,
            records_quarantined=3
        )
        assert totals.files_total == 10
    
    def test_full_report_serialization(self):
        report = FullReport()
        report.files["abc"] = FileReportEntry(
            input_sha256="abc",
            output_path="sanitized/file.csv",
            status="sanitized"
        )
        report.counts = ReportTotals(files_total=1, files_sanitized=1)
        
        json_str = report.to_json()
        assert "files" in json_str
        assert "counts" in json_str
        assert "timing" in json_str
        assert "resources" in json_str


class TestRecordsEntry:
    """Test records.jsonl entry."""
    
    def test_creation(self):
        entry = RecordsEntry(
            file="sanitized/hospital_a/patients.csv",
            loc="row:0",
            patient="PSN-a1b2c3d4"
        )
        assert entry.patient == "PSN-a1b2c3d4"
    
    def test_null_patient(self):
        entry = RecordsEntry(
            file="sanitized/notes.txt",
            loc="doc",
            patient=None
        )
        assert entry.patient is None
    
    def test_jsonl_output(self):
        entry = RecordsEntry(
            file="sanitized/file.csv",
            loc="row:0",
            patient="PSN-a1b2c3d4"
        )
        jsonl = entry.to_jsonl()
        assert '"patient":"PSN-a1b2c3d4"' in jsonl


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_compute_sha256(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        
        hash_val = compute_sha256(test_file)
        assert len(hash_val) == 64
        # Known hash for "Hello, World!"
        assert hash_val == "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
    
    def test_generate_pseudonym_format(self):
        secret = b"a" * 32
        canonical = "aadhaar:123456789012|name:john_doe"
        
        pseudonym = generate_pseudonym_format(canonical, secret)
        assert pseudonym.startswith("PSN-")
        assert len(pseudonym) == 12  # "PSN-" + 8 chars
        
        # Deterministic
        pseudonym2 = generate_pseudonym_format(canonical, secret)
        assert pseudonym == pseudonym2
        
        # Different secret = different pseudonym
        secret2 = b"b" * 32
        pseudonym3 = generate_pseudonym_format(canonical, secret2)
        assert pseudonym != pseudonym3
    
    def test_derive_date_shift(self):
        secret = b"a" * 32
        pseudonym = "PSN-a1b2c3d4"
        
        shift = derive_date_shift(pseudonym, secret)
        assert -365 <= shift <= 365
        
        # Deterministic
        shift2 = derive_date_shift(pseudonym, secret)
        assert shift == shift2
        
        # Different secret = different shift
        secret2 = b"b" * 32
        shift3 = derive_date_shift(pseudonym, secret2)
        assert shift != shift3
        
        # Different pseudonym = different shift
        pseudonym2 = "PSN-b2c3d4e5"
        shift4 = derive_date_shift(pseudonym2, secret)
        assert shift != shift4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])