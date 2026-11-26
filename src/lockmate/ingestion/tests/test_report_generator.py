"""Tests for report_generator module."""

import pytest
from pathlib import Path
import tempfile
import json

from lockmate.ingestion.output.report_generator import ReportGenerator, ReportConfig, IngestionReport


class TestReportGenerator:
    """Tests for ReportGenerator."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.temp_dir / "output"
        self.generator = ReportGenerator(ReportConfig(output_dir=self.output_dir))
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_write_report(self):
        """Test writing a basic report."""
        self.generator.start_job(metadata={"source": "test"})
        
        self.generator.add_file_processed("file1.csv", "csv", 100, 5000)
        self.generator.add_file_processed("file2.json", "json", 50, 3000)
        self.generator.add_file_failed("file3.txt", "Parse error")
        
        report_path = self.generator.write()
        
        assert report_path.exists()
        
        data = json.loads(report_path.read_text())
        
        # Verify structure
        assert "job_id" in data
        assert "timestamp" in data
        assert "ingestion" in data
        assert data["ingestion"]["total_files"] == 3
        assert data["ingestion"]["processed_files"] == 2
        assert data["ingestion"]["failed_files"] == 1
        assert data["ingestion"]["total_records"] == 150
        assert data["ingestion"]["total_size_bytes"] == 8000
        assert data["ingestion"]["formats"] == {"csv": 1, "json": 1}
        assert len(data["ingestion"]["errors"]) == 1
    
    def test_report_with_all_stats(self):
        """Test report with all module stats."""
        self.generator.start_job()
        
        self.generator.add_file_processed("file.csv", "csv", 10, 1000)
        
        self.generator.update_detection_stats(
            sensitive_records=5,
            total_findings=12,
            label_counts={"PII_NAME": 5, "PHI_DIAGNOSIS": 7},
            avg_confidence=0.85
        )
        
        self.generator.update_linkage_stats(
            total_groups=3,
            duplicate_records=2,
            unique_records=8,
            avg_group_size=3.3
        )
        
        self.generator.update_privacy_stats(
            redacted=3,
            masked=2,
            hashed=4,
            pseudonymized=1
        )
        
        report = self.generator.get_report()
        
        assert report.detection.sensitive_records == 5
        assert report.detection.total_findings == 12
        assert report.detection.avg_confidence == 0.85
        assert report.linkage.duplicate_records == 2
        assert report.privacy.redacted_fields == 3
        assert report.privacy.total_actions == 10
    
    def test_duration(self):
        """Test duration calculation."""
        self.generator.start_job()
        self.generator.end_job()
        
        report = self.generator.get_report()
        duration = report.ingestion.duration_seconds
        
        assert duration is not None
        assert duration >= 0
    
    def test_quarantine_counting(self):
        """Test quarantined file counting."""
        self.generator.start_job()
        self.generator.add_file_quarantined("suspicious.txt")
        
        report = self.generator.get_report()
        assert report.ingestion.quarantined_files == 1
    
    def test_report_to_dict(self):
        """Test report to_dict method."""
        report = IngestionReport()
        data = report.to_dict()
        
        assert "job_id" in data
        assert isinstance(data["job_id"], str)
        assert "timestamp" in data
        assert "ingestion" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])