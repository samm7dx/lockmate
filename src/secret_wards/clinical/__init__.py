"""
LOCKMATE — Clinical Preservation Module

Contextual medical entity preservation and doctor/patient disambiguation.
"""

from __future__ import annotations

from .drugs import detect_drugs
from .labs import detect_labs
from .diagnoses import detect_diagnoses
from .doctors import detect_doctors
from .veto import merge_spans_with_veto

__all__ = [
    "detect_drugs",
    "detect_labs",
    "detect_diagnoses",
    "detect_doctors",
    "merge_spans_with_veto",
]