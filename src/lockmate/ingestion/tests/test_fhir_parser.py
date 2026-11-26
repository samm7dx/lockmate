"""Tests for fhir_parser module."""

import pytest
from pathlib import Path
import tempfile
import json

# Check if fhir.resources is available
try:
    from lockmate.ingestion.parsers.fhir_parser import FHIRParser, FHIRParserConfig, parse_fhir_ndjson
    FHIR_AVAILABLE = True
except ImportError:
    FHIR_AVAILABLE = False


@pytest.mark.skipif(not FHIR_AVAILABLE, reason="fhir.resources not installed")
class TestFHIRParser:
    """Tests for FHIRParser."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parse_single_resource(self):
        """Test parsing a single FHIR resource."""
        fhir_file = self.temp_dir / "patient.json"
        patient = {
            "resourceType": "Patient",
            "id": "patient-1",
            "name": [{"family": "Doe", "given": ["John"]}],
            "birthDate": "1990-01-01",
            "gender": "male"
        }
        fhir_file.write_text(json.dumps(patient), encoding="utf-8")
        
        parser = FHIRParser()
        records = list(parser.parse(fhir_file))
        
        assert len(records) == 1
        assert records[0]["resourceType"] == "Patient"
        assert records[0]["id"] == "patient-1"
        assert records[0]["_resource_type"] == "Patient"
        assert records[0]["name"][0]["family"] == "Doe"
    
    def test_parse_bundle(self):
        """Test parsing a FHIR Bundle."""
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "id": "bundle-1",
            "entry": [
                {"resource": {"resourceType": "Patient", "id": "p1", "gender": "male"}},
                {"resource": {"resourceType": "Observation", "id": "o1", "status": "final"}},
            ]
        }
        fhir_file = self.temp_dir / "bundle.json"
        fhir_file.write_text(json.dumps(bundle), encoding="utf-8")
        
        parser = FHIRParser()
        records = list(parser.parse(fhir_file))
        
        assert len(records) == 2
        assert records[0]["resourceType"] == "Patient"
        assert records[0]["_bundle_id"] == "bundle-1"
        assert records[0]["_bundle_entry"] == 1
        assert records[1]["resourceType"] == "Observation"
        assert records[1]["_bundle_entry"] == 2
    
    def test_bundle_whole_mode(self):
        """Test bundle mode as whole."""
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {"resource": {"resourceType": "Patient", "id": "p1"}},
            ]
        }
        fhir_file = self.temp_dir / "bundle.json"
        fhir_file.write_text(json.dumps(bundle), encoding="utf-8")
        
        config = FHIRParserConfig(bundle_mode="whole")
        parser = FHIRParser(config)
        records = list(parser.parse(fhir_file))
        
        assert len(records) == 1
        assert records[0]["resourceType"] == "Bundle"
        assert "_bundle_id" in records[0]
    
    def test_resource_type_filter(self):
        """Test filtering by resource type."""
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {"resource": {"resourceType": "Patient", "id": "p1"}},
                {"resource": {"resourceType": "Observation", "id": "o1"}},
            ]
        }
        fhir_file = self.temp_dir / "bundle.json"
        fhir_file.write_text(json.dumps(bundle), encoding="utf-8")
        
        config = FHIRParserConfig(resource_types=["Patient"])
        parser = FHIRParser(config)
        records = list(parser.parse(fhir_file))
        
        assert len(records) == 1
        assert records[0]["resourceType"] == "Patient"
    
    def test_parse_ndjson(self):
        """Test parsing FHIR NDJSON."""
        fhir_file = self.temp_dir / "bundle.ndjson"
        lines = [
            {"resourceType": "Patient", "id": "p1"},
            {"resourceType": "Observation", "id": "o1"},
            {"resourceType": "Condition", "id": "c1"},
        ]
        fhir_file.write_text(
            "\n".join(json.dumps(l) for l in lines),
            encoding="utf-8"
        )
        
        records = list(parse_fhir_ndjson(fhir_file))
        
        assert len(records) == 3
        assert records[0]["resourceType"] == "Patient"
        assert records[0]["_line_number"] == 1
        assert records[2]["resourceType"] == "Condition"
        assert records[2]["_line_number"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])