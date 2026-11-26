"""Integration tests for the contracts adapter."""

import pytest
from pathlib import Path
import tempfile
import json
import orjson
import shutil

from lockmate.ingestion.secure_ingest import SecureIngestionPipeline, IngestionConfig
from lockmate.ingestion.adapters import (
    ContractsAdapter,
    parse_to_unified_records,
    build_parsed_document,
    build_full_report,
    build_records_entries,
    FormatType,
    RecordStatus,
    FieldType,
    RecordLocation,
    UnifiedRecord,
    FullReport,
    RecordsEntry,
    compute_sha256,
)
from lockmate.ingestion.validation import FileValidator, ValidationConfig
from lockmate.ingestion.parsers import CSVParser, JSONParser, TextParser, FHIRParser


class TestContractsAdapter:
    """Tests for the contracts adapter layer."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.input_dir = self.temp_dir / "input"
        self.output_dir = self.temp_dir / "output"
        self.quarantine_dir = self.temp_dir / "quarantine"
        
        self.input_dir.mkdir()
        self.output_dir.mkdir()
        self.quarantine_dir.mkdir()

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_compute_sha256(self):
        """Test SHA-256 computation."""
        test_file = self.input_dir / "test.txt"
        test_file.write_text("hello world")
        
        sha256 = compute_sha256(test_file)
        assert len(sha256) == 64  # 256 bits = 64 hex chars
        assert sha256 == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

    def test_format_type_enum(self):
        """Test FormatType enum values."""
        assert FormatType.CSV.value == "csv"
        assert FormatType.TSV.value == "tsv"
        assert FormatType.JSON.value == "json"
        assert FormatType.TEXT.value == "text"
        assert FormatType.FHIR.value == "fhir"
        assert FormatType.UNKNOWN.value == "unknown"

    def test_record_location(self):
        """Test RecordLocation factory methods."""
        # Row location - canonical format is "row:row:N"
        row_loc = RecordLocation.from_row(5)
        assert row_loc.location_type.value == "row"
        assert row_loc.value == "row:5"
        assert str(row_loc) == "row:row:5"
        
        # JSON pointer location - canonical format is "json_pointer:path"
        json_loc = RecordLocation.from_json_pointer("/entry/0/resource")
        assert json_loc.location_type.value == "json_pointer"
        assert json_loc.value == "/entry/0/resource"
        assert str(json_loc) == "json_pointer:/entry/0/resource"
        
        # Document location - canonical format is "doc:doc"
        doc_loc = RecordLocation.from_doc()
        assert doc_loc.location_type.value == "doc"
        assert doc_loc.value == "doc"
        assert str(doc_loc) == "doc:doc"

    def test_field_type_inference(self):
        """Test field type inference."""
        from lockmate.ingestion.adapters.contracts_adapter import _infer_field_type
        
        assert _infer_field_type("hello") == FieldType.STRING
        assert _infer_field_type(42) == FieldType.NUMBER
        assert _infer_field_type(3.14) == FieldType.NUMBER
        assert _infer_field_type(True) == FieldType.BOOLEAN
        assert _infer_field_type([1, 2, 3]) == FieldType.ARRAY
        assert _infer_field_type({"a": 1}) == FieldType.OBJECT
        assert _infer_field_type("2024-01-15") == FieldType.DATE

    def test_parse_csv_to_unified_records(self):
        """Test parsing CSV to UnifiedRecords."""
        # Create test CSV
        csv_file = self.input_dir / "patients.csv"
        csv_file.write_text("id,name,age,diagnosis\n1,John Doe,45,Diabetes\n2,Jane Smith,32,Hypertension")
        
        # Validate
        validator = FileValidator(config=ValidationConfig())
        validation_result = validator.validate(csv_file)
        
        # Parse
        parser = CSVParser()
        records = list(parser.parse(csv_file, encoding=validation_result.encoding))
        
        # Convert to unified records
        unified_records = parse_to_unified_records(csv_file, validation_result, iter(records))
        
        assert len(unified_records) == 2
        
        # Check first record
        ur1 = unified_records[0]
        assert len(ur1.record_id) > 10
        assert ur1.location.location_type.value == "row"
        assert ur1.location.value == "row:0"  # canonical format
        assert ur1.status == RecordStatus.PENDING
        assert "id" in ur1.fields
        assert "name" in ur1.fields
        assert "age" in ur1.fields
        assert "diagnosis" in ur1.fields
        
        # Check field types (CSV parser returns all as strings)
        assert ur1.fields["id"].field_type == FieldType.STRING
        assert ur1.fields["name"].field_type == FieldType.STRING
        assert ur1.fields["age"].field_type == FieldType.STRING
        assert ur1.fields["diagnosis"].field_type == FieldType.STRING
        
        # Check raw text
        assert "id: 1" in ur1.raw_text
        assert "name: John Doe" in ur1.raw_text

    def test_parse_json_to_unified_records(self):
        """Test parsing JSON to UnifiedRecords."""
        # Create test JSON
        json_file = self.input_dir / "data.json"
        json_file.write_text('[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]')
        
        validator = FileValidator(config=ValidationConfig())
        validation_result = validator.validate(json_file)
        
        parser = JSONParser()
        records = list(parser.parse(json_file, encoding=validation_result.encoding))
        
        unified_records = parse_to_unified_records(json_file, validation_result, iter(records))
        
        assert len(unified_records) == 2
        assert unified_records[0].location.location_type.value == "json_pointer"
        assert unified_records[0].fields["id"].field_type == FieldType.NUMBER

    def test_parse_text_to_unified_records(self):
        """Test parsing text to UnifiedRecords."""
        text_file = self.input_dir / "notes.txt"
        text_file.write_text("Line 1\nLine 2\nLine 3")
        
        validator = FileValidator(config=ValidationConfig())
        validation_result = validator.validate(text_file)
        
        parser = TextParser()
        records = list(parser.parse(text_file, encoding=validation_result.encoding))
        
        unified_records = parse_to_unified_records(text_file, validation_result, iter(records))
        
        assert len(unified_records) == 3
        # Text parser uses line_number by default, which maps to row location
        assert unified_records[0].location.value == "row:0"

    def test_build_parsed_document(self):
        """Test building ParsedDocument from parser output."""
        csv_file = self.input_dir / "data.csv"
        csv_file.write_text("id,value\n1,test\n2,demo")
        
        validator = FileValidator(config=ValidationConfig())
        validation_result = validator.validate(csv_file)
        
        parser = CSVParser()
        records = list(parser.parse(csv_file, encoding=validation_result.encoding))
        
        parsed_doc = build_parsed_document(csv_file, validation_result, iter(records))
        
        assert parsed_doc.source_file.sha256 == compute_sha256(csv_file)
        assert parsed_doc.source_file.format == FormatType.CSV
        assert parsed_doc.source_file.encoding == validation_result.encoding
        assert len(parsed_doc.records) == 2
        assert all(isinstance(r, UnifiedRecord) for r in parsed_doc.records)

    def test_build_full_report(self):
        """Test building FullReport."""
        from lockmate.ingestion.adapters.contracts_adapter import ReportData
        from datetime import datetime, timedelta
        
        start = datetime.utcnow()
        end = start + timedelta(seconds=5)
        
        report_data = ReportData(
            processed_files=[
                {
                    "sha256": "abc123",
                    "output_path": "sanitized/file1.jsonl",
                    "duration_ms": 100,
                    "peak_memory_mb": 50,
                    "record_count": 10,
                    "identifiers_detected": 2,
                    "records_linked": 8,
                    "records_generalized": 5,
                    "records_suppressed": 1,
                    "records_quarantined": 0,
                }
            ],
            quarantined_files=[
                {
                    "sha256": "def456",
                    "reason": "Invalid format",
                }
            ],
            failed_files=[],
            start_time=start,
            end_time=end,
            peak_memory_mb=100,
        )
        
        report = build_full_report(report_data)
        
        assert isinstance(report, FullReport)
        assert report.counts.files_total == 2
        assert report.counts.files_sanitized == 1
        assert report.counts.files_quarantined == 1
        assert report.counts.records_processed == 10
        assert report.timing.seconds == 5.0
        assert report.resources.peak_rss_mb == 100
        
        # Check file entries
        assert "abc123" in report.files
        assert report.files["abc123"].status == "sanitized"
        assert "def456" in report.files
        assert report.files["def456"].status == "quarantined"
        assert report.files["def456"].quarantine_reason == "Invalid format"

    def test_build_records_entries(self):
        """Test building RecordsEntry list from UnifiedRecords."""
        # Create mock unified records
        records = []
        for i in range(3):
            loc = RecordLocation.from_row(i)
            ur = UnifiedRecord(
                record_id=f"sha256:{loc}",
                location=loc,
                fields={},
                raw_text=f"record {i}",
                normalized_text=f"record {i}",
                offset_map=[(0, 0)],
                status=RecordStatus.PROCESSED,
                pseudonym=f"PATIENT_{i:04d}" if i < 2 else None,
                metadata={"output_file": f"sanitized/patient_{i}.jsonl"},
            )
            records.append(ur)
        
        entries = build_records_entries(records)
        
        assert len(entries) == 3
        assert entries[0].file == "sanitized/patient_0.jsonl"
        # Canonical location format is "row:row:0"
        assert entries[0].loc == "row:row:0"
        assert entries[0].patient == "PATIENT_0000"
        assert entries[1].patient == "PATIENT_0001"
        assert entries[2].patient is None

    def test_full_report_to_json(self):
        """Test FullReport.to_json() output."""
        from lockmate.ingestion.adapters.contracts_adapter import ReportData
        from datetime import datetime
        
        report_data = ReportData(
            processed_files=[],
            quarantined_files=[],
            failed_files=[],
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
        )
        
        report = build_full_report(report_data)
        json_str = report.to_json()
        
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert "files" in parsed
        assert "counts" in parsed
        assert "timing" in parsed
        assert "resources" in parsed

    def test_records_entry_to_jsonl(self):
        """Test RecordsEntry.to_jsonl() output."""
        entry = RecordsEntry(
            file="sanitized/data.jsonl",
            loc="row:0",
            patient="PATIENT_0001"
        )
        
        jsonl_str = entry.to_jsonl()
        parsed = json.loads(jsonl_str)
        
        assert parsed["file"] == "sanitized/data.jsonl"
        assert parsed["loc"] == "row:0"
        assert parsed["patient"] == "PATIENT_0001"

    def test_pipeline_with_contracts_output(self):
        """Test full pipeline with contracts adapter enabled."""
        # Create test files
        csv_file = self.input_dir / "patients.csv"
        csv_file.write_text("id,name,age\n1,Alice,30\n2,Bob,25")
        
        json_file = self.input_dir / "data.json"
        json_file.write_text('[{"id": 1, "value": "test"}]')
        
        config = IngestionConfig(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            quarantine_dir=self.quarantine_dir,
            use_contracts_adapter=True,
        )
        
        pipeline = SecureIngestionPipeline(config)
        result = pipeline.run()
        
        assert result.success
        assert result.total_records == 3
        
        # Check contracts outputs exist
        report_path = self.output_dir / "report.json"
        records_path = self.output_dir / "records.jsonl"
        
        assert report_path.exists()
        assert records_path.exists()
        
        # Verify report.json format
        report_json = json.loads(report_path.read_text())
        assert "files" in report_json
        assert "counts" in report_json
        assert "timing" in report_json
        assert "resources" in report_json
        assert report_json["counts"]["files_total"] == 2
        assert report_json["counts"]["files_sanitized"] == 2
        
        # Verify records.jsonl format
        records_lines = records_path.read_text().strip().split("\n")
        assert len(records_lines) == 3
        for line in records_lines:
            parsed = json.loads(line)
            assert "file" in parsed
            assert "loc" in parsed
            assert "patient" in parsed

    def test_pipeline_without_contracts_output(self):
        """Test pipeline with contracts adapter disabled."""
        csv_file = self.input_dir / "patients.csv"
        csv_file.write_text("id,name\n1,Alice")
        
        config = IngestionConfig(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            quarantine_dir=self.quarantine_dir,
            use_contracts_adapter=False,
        )
        
        pipeline = SecureIngestionPipeline(config)
        result = pipeline.run()
        
        assert result.success
        
        # Contracts outputs should NOT exist
        report_path = self.output_dir / "report.json"
        records_path = self.output_dir / "records.jsonl"
        
        # Legacy report.json from ReportGenerator should still exist
        # (it writes to output/report.json by default)
        # But contracts-specific report.json and records.jsonl should not
        # Actually the legacy ReportGenerator also writes report.json
        # The contracts adapter writes to the same location, so we check for records.jsonl
        assert not records_path.exists() or records_path.stat().st_size == 0

    def test_contracts_adapter_class(self):
        """Test ContractsAdapter class methods."""
        adapter = ContractsAdapter()
        
        # Create test data
        csv_file = self.input_dir / "data.csv"
        csv_file.write_text("id,value\n1,test")
        
        validator = FileValidator(config=ValidationConfig())
        validation_result = validator.validate(csv_file)
        
        parser = CSVParser()
        records = list(parser.parse(csv_file, encoding=validation_result.encoding))
        
        # Parse file
        parsed_doc = adapter.parse_file(csv_file, validation_result, iter(records))
        assert isinstance(parsed_doc.records[0], UnifiedRecord)
        
        # Add processed file
        adapter.add_processed_file({
            "sha256": "abc123",
            "output_path": "sanitized/data.jsonl",
            "duration_ms": 50,
            "peak_memory_mb": 10,
            "record_count": 1,
            "identifiers_detected": 0,
            "records_linked": 0,
            "records_generalized": 0,
            "records_suppressed": 0,
            "records_quarantined": 0,
        })
        
        # Finalize report
        report = adapter.finalize_report()
        assert isinstance(report, FullReport)
        assert report.counts.files_sanitized == 1
        
        # Build records entries
        entries = adapter.build_records_entries(parsed_doc.records)
        assert len(entries) == 1
        assert isinstance(entries[0], RecordsEntry)

    def test_fhir_parsed_document(self):
        """Test building ParsedDocument from FHIR parser output."""
        fhir_file = self.input_dir / "bundle.json"
        fhir_file.write_text('''
        {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "patient-1",
                        "name": [{"given": ["John"], "family": "Doe"}]
                    }
                }
            ]
        }
        ''')
        
        validator = FileValidator(config=ValidationConfig())
        validation_result = validator.validate(fhir_file)
        
        parser = FHIRParser()
        records = list(parser.parse(fhir_file, encoding=validation_result.encoding))
        
        parsed_doc = build_parsed_document(fhir_file, validation_result, iter(records))
        
        assert len(parsed_doc.records) == 1
        # File validator uses extension-based detection, returns JSON for .json files
        # FHIR parser handles FHIR content regardless of detected format
        assert parsed_doc.source_file.format == FormatType.JSON
        assert "_fhir_id" in parsed_doc.records[0].metadata.get("parser_metadata", {}) or \
               parsed_doc.records[0].location.location_type.value == "json_pointer"


class TestSecretWardsFormatCompatibility:
    """Tests to verify output format matches Secret-Wards-ToolKit expectations."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.input_dir = self.temp_dir / "input"
        self.output_dir = self.temp_dir / "output"
        self.quarantine_dir = self.temp_dir / "quarantine"
        
        self.input_dir.mkdir()
        self.output_dir.mkdir()
        self.quarantine_dir.mkdir()

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_report_json_structure(self):
        """Test report.json matches expected Secret-Wards-ToolKit structure."""
        csv_file = self.input_dir / "data.csv"
        csv_file.write_text("id,name\n1,Test")
        
        config = IngestionConfig(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            quarantine_dir=self.quarantine_dir,
            use_contracts_adapter=True,
        )
        
        pipeline = SecureIngestionPipeline(config)
        pipeline.run()
        
        report_path = self.output_dir / "report.json"
        report = json.loads(report_path.read_text())
        
        # Check required top-level keys
        required_keys = ["files", "counts", "timing", "resources"]
        for key in required_keys:
            assert key in report, f"Missing required key: {key}"
        
        # Check counts structure
        counts = report["counts"]
        required_counts = [
            "files_total", "files_sanitized", "files_quarantined",
            "records_processed", "identifiers_detected", "records_linked",
            "records_generalized", "records_suppressed", "records_quarantined",
            "total_processing_duration_ms", "peak_memory_mb"
        ]
        for key in required_counts:
            assert key in counts, f"Missing required count: {key}"
        
        # Check timing structure
        assert "seconds" in report["timing"]
        
        # Check resources structure
        assert "peak_rss_mb" in report["resources"]
        
        # Check file entries structure
        for sha256, file_entry in report["files"].items():
            assert "input_sha256" in file_entry
            assert "status" in file_entry
            assert file_entry["status"] in ["sanitized", "quarantined", "failed"]

    def test_records_jsonl_structure(self):
        """Test records.jsonl matches expected Secret-Wards-ToolKit structure."""
        csv_file = self.input_dir / "data.csv"
        csv_file.write_text("id,name\n1,Alice\n2,Bob")
        
        config = IngestionConfig(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            quarantine_dir=self.quarantine_dir,
            use_contracts_adapter=True,
        )
        
        pipeline = SecureIngestionPipeline(config)
        pipeline.run()
        
        records_path = self.output_dir / "records.jsonl"
        lines = records_path.read_text().strip().split("\n")
        
        assert len(lines) == 2
        
        for line in lines:
            record = json.loads(line)
            # Required fields per RecordsEntry
            assert "file" in record
            assert "loc" in record
            assert "patient" in record
            # patient can be null/None
            assert record["patient"] is None or isinstance(record["patient"], str)
            # loc should be a string in canonical format like "row:row:0" or "json_pointer:/0"
            assert isinstance(record["loc"], str)
            assert len(record["loc"]) > 0
            assert ":" in record["loc"]  # format: type:value

    def test_output_directory_structure(self):
        """Test output directory matches expected structure: sanitized/, report.json, records.jsonl"""
        csv_file = self.input_dir / "data.csv"
        csv_file.write_text("id,value\n1,test")
        
        config = IngestionConfig(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            quarantine_dir=self.quarantine_dir,
            use_contracts_adapter=True,
        )
        
        pipeline = SecureIngestionPipeline(config)
        pipeline.run()
        
        # Check output directory structure
        assert (self.output_dir / "report.json").exists()
        assert (self.output_dir / "records.jsonl").exists()
        # Note: The actual sanitized/ folder would be created by the serializer
        # when writing individual record files. For now we check the contracts outputs.


if __name__ == "__main__":
    pytest.main([__file__, "-v"])