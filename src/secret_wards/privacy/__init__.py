"""
LOCKMATE — Phase 6: Quasi-Identifier Privacy & Re-identification Protection

This module implements the privacy layer for reducing patient re-identification risk
while retaining medically useful information.

Components:
- date_shift: Deterministic per-patient date shifting
- age_generalizer: Configurable age band generalization
- location_generalizer: Hierarchical location generalization
- rare_value_suppressor: Risk-based rare combination suppression
- privacy_metrics: Privacy-utility reporting
"""

from .date_shift import DateShifter, derive_patient_date_shift
from .age_generalizer import AgeGeneralizer, AgeBandPolicy
from .location_generalizer import LocationGeneralizer, LocationHierarchy
from .rare_value_suppressor import RareValueSuppressor, SuppressionPolicy
from .privacy_metrics import PrivacyMetricsCollector, PrivacyMetrics

__all__ = [
    "DateShifter",
    "derive_patient_date_shift",
    "AgeGeneralizer",
    "AgeBandPolicy",
    "LocationGeneralizer",
    "LocationHierarchy",
    "RareValueSuppressor",
    "SuppressionPolicy",
    "PrivacyMetricsCollector",
    "PrivacyMetrics",
]