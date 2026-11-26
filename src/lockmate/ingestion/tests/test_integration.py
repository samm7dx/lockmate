"""Integration tests for the secure ingestion pipeline."""

import pytest
from pathlib import Path
import tempfile
import json
import shutil

from lockmate.ingestion.secure_ingest import SecureIngestionPipeline, IngestionConfig


class TestSecureIngestionPipeline:
    """Integration tests for the full secure ingestion pipeline."""

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

    def _make_config(self):
        """Create a standard ingestion config."""
        return IngestionConfig(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            quarantine_dir=self.quarantine_dir,
            allowed_roots=[self.input_dir]
        )

    def _get_data_jsonl_files(self):
        """Get data output files (excluding contracts adapter records.jsonl)."""
        all_jsonl = list(self.output_dir.rglob("*.jsonl"))
        # Filter out contracts adapter records.jsonl
        data_files = [f for f in all_jsonl if f.name != "records.jsonl"]
        return data_files

    def test_basic_csv_ingestion(self):
        """Test basic CSV file ingestion."""
        # Create test CSV file
        csv_file = self.input_dir / "data.csv"
        csv_file.write_text("id,name,value\n1,Alice,100\n2,Bob,200\n3,Charlie,300\n")
        
        config = self._make_config()
        pipeline = SecureIngestionPipeline(config)
        result = pipeline.run()
        
        # Verify results
        assert result.success is True
        assert len(result.processed_files) == 1
        assert len(result.failed_files) == 0
        assert len(result.quarantined_files) == 0
        assert result.total_records == 3
        
        # Check output file exists (data file, not contracts records.jsonl)
        output_files = self._get_data_jsonl_files()
        assert len(output_files) == 1
        
        # Verify output content
        with open(output_files[0]) as f:
            lines = f.readlines()
            assert len(lines) == 3
            record = json.loads(lines[0])
            assert record["id"] == "1"
            assert record["name"] == "Alice"
            assert record["value"] == "100"

    def test_json_ingestion(self):
        """Test JSON file ingestion."""
        # Create test JSON file
        json_file = self.input_dir / "data.json"
        json_file.write_text('[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]')
        
        config = self._make_config()
        pipeline = SecureIngestionPipeline(config)
        result = pipeline.run()
        
        assert result.success is True
        assert result.total_records == 2
        
        output_files = self._get_data_jsonl_files()
        assert len(output_files) == 1
        
        with open(output_files[0]) as f:
            lines = f.readlines()
            assert len(lines) == 2

    def test_text_ingestion(self):
        """Test plain text file ingestion."""
        # Create test text file
        txt_file = self.input_dir / "data.txt"
        txt_file.write_text("Line 1\nLine 2\nLine 3\n")
        
        config = self._make_config()
        pipeline = SecureIngestionPipeline(config)
        result = pipeline.run()
        
        assert result.success is True
        assert result.total_records == 3  # Each line becomes a record
        
        output_files = self._get_data_jsonl_files()
        assert len(output_files) == 1
        
        with open(output_files[0]) as f:
            lines = f.readlines()
            assert len(lines) == 3

    def test_multiple_files_ingestion(self):
        """Test ingestion of multiple files."""
        # Create multiple test files
        (self.input_dir / "data1.csv").write_text("id,value\n1,100\n2,200\n")
        (self.input_dir / "data2.json").write_text('[{"id": 3}, {"id": 4}]')
        (self.input_dir / "data3.txt").write_text("line1\nline2\n")
        
        config = self._make_config()
        pipeline = SecureIngestionPipeline(config)
        result = pipeline.run()
        
        assert result.success is True
        assert len(result.processed_files) == 3
        assert result.total_records == 6  # 2 + 2 + 2
        
        output_files = self._get_data_jsonl_files()
        assert len(output_files) == 3

    def test_quarantine_invalid_file(self):
        """Test that invalid files are quarantined."""
        # Create a valid CSV file
        (self.input_dir / "valid.csv").write_text("id,value\n1,100\n")
        
        # Create an invalid file (binary content)
        invalid_file = self.input_dir / "invalid.bin"
        invalid_file.write_bytes(b"\x00\x01\x02\x03\x04\x05")
        
        config = self._make_config()
        pipeline = SecureIngestionPipeline(config)
        result = pipeline.run()
        
        # Valid file should be processed, invalid should be quarantined
        assert len(result.processed_files) == 1
        assert len(result.quarantined_files) == 1
        assert result.total_records == 1
        
        # Check quarantine directory has the file
        quarantine_files = list(self.quarantine_dir.rglob("*"))
        assert len(quarantine_files) >= 1

    def test_path_traversal_blocked(self):
        """Test that path traversal attempts are blocked."""
        # Create a file outside the allowed root
        outside_dir = self.temp_dir / "outside"
        outside_dir.mkdir()
        secret_file = outside_dir / "secret.txt"
        secret_file.write_text("secret")
        
        # Create a symlink inside input_dir pointing outside
        import sys
        if sys.platform != "win32":
            link_file = self.input_dir / "link.txt"
            link_file.symlink_to(secret_file)
            
            config = self._make_config()
            config.follow_symlinks = False
            pipeline = SecureIngestionPipeline(config)
            result = pipeline.run()
            
            # Symlink should be blocked/quarantined
            assert len(result.quarantined_files) >= 1 or len(result.failed_files) >= 1

    def test_size_limit_enforced(self):
        """Test that file size limits are enforced."""
        # Create a large file (over default 100MB limit)
        large_file = self.input_dir / "large.csv"
        # Write ~101MB of data
        large_content = "id,value\n" + "\n".join([f"{i},{i*100}" for i in range(100000)])
        large_file.write_text(large_content)
        
        config = self._make_config()
        config.max_file_size = 1024  # 1KB limit for testing
        pipeline = SecureIngestionPipeline(config)
        result = pipeline.run()
        
        # File should be quarantined due to size (check quarantine dir)
        quarantine_files = list(self.quarantine_dir.rglob("*"))
        quarantine_files = [f for f in quarantine_files if f.is_file() and f.name != "metadata.jsonl"]
        assert len(quarantine_files) >= 1
        assert len(result.processed_files) == 0
        assert result.success is False

    def test_fhir_ingestion(self):
        """Test FHIR resource ingestion."""
        # Create a simple FHIR Patient resource
        fhir_patient = {
            "resourceType": "Patient",
            "id": "example",
            "name": [{"family": "Smith", "given": ["John"]}],
            "gender": "male",
            "birthDate": "1990-01-01"
        }
        fhir_file = self.input_dir / "patient.json"
        fhir_file.write_text(json.dumps(fhir_patient))
        
        config = self._make_config()
        pipeline = SecureIngestionPipeline(config)
        result = pipeline.run()
        
        assert result.success is True
        assert result.total_records >= 1
        
        output_files = self._get_data_jsonl_files()
        assert len(output_files) >= 1

    def test_report_generation(self):
        """Test that ingestion report is generated."""
        (self.input_dir / "data.csv").write_text("id,value\n1,100\n")
        
        config = self._make_config()
        pipeline = SecureIngestionPipeline(config)
        result = pipeline.run()
        
        # Check report file exists (default filename is report.json)
        report_path = self.output_dir / "report.json"
        assert report_path.exists()
        
        # Verify report content (contracts adapter format)
        with open(report_path) as f:
            report = json.load(f)
            # Contracts adapter format has different structure
            assert "files" in report
            assert "counts" in report
            assert "timing" in report
            assert "resources" in report
            assert report["counts"]["files_total"] == 1
            assert report["counts"]["files_sanitized"] == 1
            assert report["counts"]["records_processed"] == 1

    def test_empty_directory(self):
        """Test ingestion with empty input directory."""
        config = self._make_config()
        pipeline = SecureIngestionPipeline(config)
        result = pipeline.run()
        
        assert result.success is True
        assert len(result.processed_files) == 0
        assert result.total_records == 0

    def test_subdirectory_files(self):
        """Test ingestion of files in subdirectories."""
        subdir = self.input_dir / "subdir"
        subdir.mkdir()
        (subdir / "data.csv").write_text("id,value\n1,100\n")
        (subdir / "data2.json").write_text('[{"id": 2}]')
        
        config = self._make_config()
        pipeline = SecureIngestionPipeline(config)
        result = pipeline.run()
        
        assert result.success is True
        assert len(result.processed_files) == 2
        assert result.total_records == 2
        
        output_files = self._get_data_jsonl_files()
        assert len(output_files) == 2

    def test_ingest_file_method(self):
        """Test the ingest_file method directly."""
        csv_file = self.input_dir / "data.csv"
        csv_file.write_text("id,name\n1,Alice\n2,Bob\n")
        
        config = self._make_config()
        pipeline = SecureIngestionPipeline(config)
        
        records = list(pipeline.ingest_file(csv_file))
        
        assert len(records) == 2
        assert records[0]["id"] == "1"
        assert records[0]["name"] == "Alice"
        assert records[1]["id"] == "2"
        assert records[1]["name"] == "Bob"

    def test_tsv_ingestion(self):
        """Test TSV file ingestion."""
        tsv_file = self.input_dir / "data.tsv"
        tsv_file.write_text("id\tname\tvalue\n1\tAlice\t100\n2\tBob\t200\n")
        
        config = self._make_config()
        pipeline = SecureIngestionPipeline(config)
        result = pipeline.run()
        
        assert result.success is True
        assert result.total_records == 2
        
        output_files = self._get_data_jsonl_files()
        assert len(output_files) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])