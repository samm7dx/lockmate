"""
LOCKMATE — Phase 6: Deterministic Per-Patient Date Shifting

Implements deterministic date shifting using RAKSHA_SECRET as cryptographic key material.
Same patient receives the same shift across all hospitals and files.
Different secrets produce different shifts.
Preserves exact length of stay and intervals between dates.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Union, Tuple
import re

from cryptography.hazmat.primitives import hmac, hashes

from ..contracts import derive_date_shift as _derive_date_shift_contract
from ..utils.logging import get_logger

logger = get_logger("privacy.date_shift")


@dataclass(frozen=True)
class DateShiftConfig:
    """Configuration for date shifting."""
    max_shift_days: int = 365  # ±365 days
    domain_separator: bytes = b"lockmate.date_shift.v1"


class DateShifter:
    """
    Deterministic per-patient date shifter.
    
    Uses HMAC-SHA256 with domain separation to derive a patient-specific
    date shift from the RAKSHA_SECRET and patient pseudonym.
    
    Properties:
    - Same patient + same secret = same shift (deterministic)
    - Same patient + different secret = different shift
    - Different patients = independently derived shifts
    - Preserves intervals between dates for the same patient
    - Preserves length of stay
    """
    
    def __init__(self, secret: bytes, config: Optional[DateShiftConfig] = None):
        """
        Initialize the date shifter.
        
        Args:
            secret: RAKSHA_SECRET bytes (>=32 bytes)
            config: Optional configuration
        """
        if len(secret) < 32:
            raise ValueError("Secret must be at least 32 bytes")
        
        self.secret = secret
        self.config = config or DateShiftConfig()
        self._shift_cache: Dict[str, int] = {}
        
    def get_shift(self, patient_pseudonym: str) -> int:
        """
        Get the date shift for a patient.
        
        Uses caching for performance - same patient always gets same shift.
        
        Args:
            patient_pseudonym: Patient pseudonym (e.g., "PSN-abc12345")
            
        Returns:
            Shift in days (negative or positive)
        """
        if patient_pseudonym not in self._shift_cache:
            self._shift_cache[patient_pseudonym] = self._derive_shift(patient_pseudonym)
        return self._shift_cache[patient_pseudonym]
    
    def _derive_shift(self, patient_pseudonym: str) -> int:
        """
        Derive date shift using HMAC with domain separation.
        
        This is the core cryptographic operation. It uses the same algorithm
        as the contract function but with explicit domain separation.
        """
        h = hmac.HMAC(self.secret, hashes.SHA256())
        h.update(self.config.domain_separator)
        h.update(patient_pseudonym.encode("utf-8"))
        digest = h.finalize()
        
        # Map to [-max_shift_days, +max_shift_days]
        max_shift = self.config.max_shift_days
        range_size = max_shift * 2 + 1
        offset = int.from_bytes(digest[:4], "big") % range_size - max_shift
        
        logger.debug("date_shift_derived", 
                    patient_pseudonym=patient_pseudonym[:16], 
                    shift_days=offset)
        return offset
    
    def shift_date(self, dt: Union[datetime, date, str], patient_pseudonym: str) -> Union[datetime, date, str]:
        """
        Shift a single date by the patient's shift value.
        
        Args:
            dt: Date/datetime/string to shift
            patient_pseudonym: Patient pseudonym
            
        Returns:
            Shifted date of the same type as input
        """
        shift_days = self.get_shift(patient_pseudonym)
        
        if isinstance(dt, str):
            # Try to parse common date formats
            parsed = self._parse_date_string(dt)
            if parsed is None:
                # Can't parse, return original
                logger.warning("date_shift_parse_failed", original=dt[:50])
                return dt
            shifted = self._apply_shift(parsed, shift_days)
            return self._format_date_string(shifted, dt)
        elif isinstance(dt, datetime):
            return self._apply_shift(dt, shift_days)
        elif isinstance(dt, date):
            return self._apply_shift(dt, shift_days)
        else:
            return dt
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse common date string formats."""
        # Common FHIR and healthcare date formats
        formats = [
            "%Y-%m-%d",           # 2024-01-15
            "%Y-%m-%dT%H:%M:%S",  # 2024-01-15T10:30:00
            "%Y-%m-%dT%H:%M:%S.%f",  # 2024-01-15T10:30:00.123
            "%Y-%m-%dT%H:%M:%S%z",   # 2024-01-15T10:30:00+05:30
            "%d/%m/%Y",           # 15/01/2024
            "%d-%m-%Y",           # 15-01-2024
            "%m/%d/%Y",           # 01/15/2024
            "%Y%m%d",             # 20240115
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        # Try ISO format with timezone
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            pass
        
        return None
    
    def _format_date_string(self, dt: datetime, original: str) -> str:
        """Format shifted date preserving original format as much as possible."""
        # Detect original format and preserve it
        if re.match(r"^\d{4}-\d{2}-\d{2}$", original):
            return dt.strftime("%Y-%m-%d")
        elif re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+", original):
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]  # millisecond precision
        elif re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", original):
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        elif re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$", original):
            return dt.strftime("%Y-%m-%dT%H:%M:%S%z")
        elif re.match(r"^\d{2}/\d{2}/\d{4}$", original):
            return dt.strftime("%d/%m/%Y")
        elif re.match(r"^\d{2}-\d{2}-\d{4}$", original):
            return dt.strftime("%d-%m-%Y")
        elif re.match(r"^\d{2}/\d{2}/\d{4}$", original):  # mm/dd/yyyy
            return dt.strftime("%m/%d/%Y")
        elif re.match(r"^\d{8}$", original):
            return dt.strftime("%Y%m%d")
        else:
            # Default to ISO format
            return dt.isoformat()
    
    def _apply_shift(self, dt: Union[datetime, date], shift_days: int) -> Union[datetime, date]:
        """Apply shift to date/datetime."""
        if isinstance(dt, datetime):
            return dt + timedelta(days=shift_days)
        else:
            return dt + timedelta(days=shift_days)
    
    def shift_record_dates(self, record_dates: Dict[str, Union[datetime, date, str]], patient_pseudonym: str) -> Dict[str, Union[datetime, date, str]]:
        """
        Shift all dates in a record by the same patient shift.
        
        This preserves intervals between dates for the same patient.
        
        Args:
            record_dates: Dictionary of field_path -> date value
            patient_pseudonym: Patient pseudonym
            
        Returns:
            Dictionary with shifted dates
        """
        shifted = {}
        for field_path, date_value in record_dates.items():
            shifted[field_path] = self.shift_date(date_value, patient_pseudonym)
        return shifted
    
    def verify_interval_preservation(
        self, 
        original_dates: Dict[str, Union[datetime, date]], 
        shifted_dates: Dict[str, Union[datetime, date]]
    ) -> bool:
        """
        Verify that intervals between dates are preserved.
        
        Args:
            original_dates: Original dates by field path
            shifted_dates: Shifted dates by field path
            
        Returns:
            True if all intervals are preserved
        """
        fields = list(original_dates.keys())
        for i, f1 in enumerate(fields):
            for f2 in fields[i+1:]:
                if f1 in shifted_dates and f2 in shifted_dates:
                    orig_diff = (original_dates[f1] - original_dates[f2]).days
                    shifted_diff = (shifted_dates[f1] - shifted_dates[f2]).days
                    if orig_diff != shifted_diff:
                        logger.warning("interval_not_preserved", 
                                     field1=f1, field2=f2, 
                                     orig_diff=orig_diff, shifted_diff=shifted_diff)
                        return False
        return True


def derive_patient_date_shift(patient_pseudonym: str, secret: bytes, max_days: int = 365) -> int:
    """
    Derive a deterministic date shift for a patient.
    
    This is a standalone function that can be used without the DateShifter class.
    Uses the same algorithm as the contract function.
    
    Args:
        patient_pseudonym: Patient pseudonym (e.g., "PSN-abc12345")
        secret: RAKSHA_SECRET bytes
        max_days: Maximum shift in days (default 365 for ±365)
        
    Returns:
        Shift offset in days [-max_days, +max_days]
    """
    h = hmac.HMAC(secret, hashes.SHA256())
    h.update(b"lockmate.date_shift.v1")
    h.update(patient_pseudonym.encode("utf-8"))
    digest = h.finalize()
    
    range_size = max_days * 2 + 1
    offset = int.from_bytes(digest[:4], "big") % range_size - max_days
    return offset


def shift_fhir_date(date_str: str, shift_days: int) -> str:
    """
    Shift a FHIR date string preserving FHIR validity.
    
    FHIR dates can be:
    - YYYY
    - YYYY-MM
    - YYYY-MM-DD
    - YYYY-MM-DDThh:mm:ss+zz:zz
    
    Args:
        date_str: FHIR date string
        shift_days: Days to shift (can be negative)
        
    Returns:
        Shifted FHIR date string
    """
    # Parse based on format
    if re.match(r"^\d{4}$", date_str):
        # Year only - can't shift meaningfully without month/day
        return date_str
    elif re.match(r"^\d{4}-\d{2}$", date_str):
        # Year-month - shift by approximate month
        year, month = map(int, date_str.split('-'))
        # Approximate: shift by days/30 months
        month_shift = shift_days // 30
        new_month = month + month_shift
        new_year = year + (new_month - 1) // 12
        new_month = ((new_month - 1) % 12) + 1
        return f"{new_year:04d}-{new_month:02d}"
    else:
        # Full date or datetime - use datetime parsing directly
        # Reuse the parsing/formatting logic without DateShifter
        parsed = _parse_fhir_date(date_str)
        if parsed is None:
            return date_str
        shifted = parsed + timedelta(days=shift_days)
        return _format_fhir_date(shifted, date_str)


def _parse_fhir_date(date_str: str):
    """Parse FHIR date string - extracted from DateShifter for reuse."""
    # Common FHIR and healthcare date formats
    formats = [
        "%Y-%m-%d",           # 2024-01-15
        "%Y-%m-%dT%H:%M:%S",  # 2024-01-15T10:30:00
        "%Y-%m-%dT%H:%M:%S.%f",  # 2024-01-15T10:30:00.123
        "%Y-%m-%dT%H:%M:%S%z",   # 2024-01-15T10:30:00+05:30
        "%d/%m/%Y",           # 15/01/2024
        "%d-%m-%Y",           # 15-01-2024
        "%m/%d/%Y",           # 01/15/2024
        "%Y%m%d",             # 20240115
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    # Try ISO format with timezone
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        pass
    
    return None


def _format_fhir_date(dt: datetime, original: str) -> str:
    """Format FHIR date - extracted from DateShifter for reuse."""
    # Detect original format and preserve it
    if re.match(r"^\d{4}-\d{2}-\d{2}$", original):
        return dt.strftime("%Y-%m-%d")
    elif re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+", original):
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]  # millisecond precision
    elif re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", original):
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    elif re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$", original):
        return dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    elif re.match(r"^\d{2}/\d{2}/\d{4}$", original):
        return dt.strftime("%d/%m/%Y")
    elif re.match(r"^\d{2}-\d{2}-\d{4}$", original):
        return dt.strftime("%d-%m-%Y")
    elif re.match(r"^\d{2}/\d{2}/\d{4}$", original):  # mm/dd/yyyy
        return dt.strftime("%m/%d/%Y")
    elif re.match(r"^\d{8}$", original):
        return dt.strftime("%Y%m%d")
    else:
        # Default to ISO format
        return dt.isoformat()


# Re-export the contract function for compatibility
derive_date_shift = _derive_date_shift_contract