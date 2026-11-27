"""
LOCKMATE — Detection Module

All PII detection components.
"""

from __future__ import annotations

from .placeholder import detect_pii_placeholder
from .identifiers import detect_identifiers
from .names import detect_names
from .structured import scan_structured_fields, sanitize_json_keys, sanitize_csv_headers, sanitize_fhir_elements
from .normalize import normalize_text, apply_normalization, map_normalized_to_original
from .gazetteer import get_gazetteer, Gazetteer
from .transliterate import devanagari_to_latin, double_metaphone, is_devanagari_text
from .calibration import (
    ConfidenceCalibrator,
    MultiDetectorCalibrator,
    apply_default_calibration,
    compute_calibration_metrics
)

__all__ = [
    # Detection functions
    "detect_pii_placeholder",
    "detect_identifiers",
    "detect_names",
    "scan_structured_fields",
    "sanitize_json_keys",
    "sanitize_csv_headers",
    "sanitize_fhir_elements",
    # Normalization
    "normalize_text",
    "apply_normalization",
    "map_normalized_to_original",
    # Gazetteer
    "get_gazetteer",
    "Gazetteer",
    # Transliteration
    "devanagari_to_latin",
    "double_metaphone",
    "is_devanagari_text",
    # Calibration
    "ConfidenceCalibrator",
    "MultiDetectorCalibrator",
    "apply_default_calibration",
    "compute_calibration_metrics",
]