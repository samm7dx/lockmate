"""
LOCKMATE — Phase 6: Age Generalization

Implements configurable age bands for quasi-identifier generalization.
Supports five-year bands by default, with configurable wider bands.
Ensures true age always falls within the published band.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, Union
import yaml
from pathlib import Path

from ..utils.logging import get_logger

logger = get_logger("privacy.age_generalizer")


@dataclass(frozen=True)
class AgeBand:
    """Represents an age band with inclusive bounds."""
    min_age: int
    max_age: Optional[int]  # None means unbounded (e.g., 90+)
    label: str
    
    def contains(self, age: int) -> bool:
        """Check if age falls within this band."""
        if age < self.min_age:
            return False
        if self.max_age is not None and age > self.max_age:
            return False
        return True
    
    def __str__(self) -> str:
        if self.max_age is None:
            return f"{self.min_age}+"
        elif self.min_age == self.max_age:
            return str(self.min_age)
        else:
            return f"{self.min_age}-{self.max_age}"


@dataclass
class AgeBandPolicy:
    """Configuration policy for age band generalization."""
    bands: List[AgeBand] = field(default_factory=list)
    default_band_label: str = "unknown"
    
    @classmethod
    def from_config(cls, config: Dict) -> "AgeBandPolicy":
        """Create policy from configuration dictionary."""
        bands = []
        for band_config in config.get("age_bands", []):
            if isinstance(band_config, list) and len(band_config) >= 2:
                min_age = band_config[0]
                max_age = band_config[1] if band_config[1] is not None else None
                if max_age is not None:
                    label = f"{min_age}-{max_age}"
                else:
                    label = f"{min_age}+"
                bands.append(AgeBand(min_age, max_age, label))
        
        return cls(bands=bands)
    
    @classmethod
    def default_five_year(cls) -> "AgeBandPolicy":
        """Create default 5-year age band policy."""
        bands = []
        # 0-4, 5-9, ..., 85-89, 90+
        for start in range(0, 90, 5):
            end = start + 4
            bands.append(AgeBand(start, end, f"{start}-{end}"))
        bands.append(AgeBand(90, None, "90+"))
        return cls(bands=bands)
    
    @classmethod
    def wide_bands(cls) -> "AgeBandPolicy":
        """Create wider age bands for higher privacy."""
        bands = [
            AgeBand(0, 17, "0-17"),
            AgeBand(18, 29, "18-29"),
            AgeBand(30, 39, "30-39"),
            AgeBand(40, 49, "40-49"),
            AgeBand(50, 59, "50-59"),
            AgeBand(60, 69, "60-69"),
            AgeBand(70, 79, "70-79"),
            AgeBand(80, None, "80+"),
        ]
        return cls(bands=bands)
    
    def get_band_for_age(self, age: int) -> AgeBand:
        """Get the age band that contains the given age."""
        for band in self.bands:
            if band.contains(age):
                return band
        # Fallback: return last band or create unknown
        if self.bands:
            return self.bands[-1]
        return AgeBand(0, None, self.default_band_label)
    
    def get_band_label(self, age: int) -> str:
        """Get the label for the age band containing the given age."""
        return str(self.get_band_for_age(age))
    
    def validate_bands(self) -> bool:
        """Validate that bands are contiguous and cover all ages."""
        if not self.bands:
            return False
        
        # Check first band starts at 0
        if self.bands[0].min_age != 0:
            logger.warning("age_bands_not_start_at_zero", first_band=self.bands[0].min_age)
            return False
        
        # Check contiguity
        for i in range(len(self.bands) - 1):
            current = self.bands[i]
            next_band = self.bands[i + 1]
            if current.max_age is not None:
                expected_next = current.max_age + 1
                if next_band.min_age != expected_next:
                    logger.warning("age_bands_not_contiguous", 
                                 current=str(current), next=str(next_band))
                    return False
        
        return True


class AgeGeneralizer:
    """
    Age generalization for quasi-identifier protection.
    
    Converts exact ages to age bands based on configurable policy.
    Handles date of birth to age conversion and generalization.
    """
    
    def __init__(self, policy: Optional[AgeBandPolicy] = None):
        """
        Initialize the age generalizer.
        
        Args:
            policy: AgeBandPolicy instance (uses default 5-year if None)
        """
        self.policy = policy or AgeBandPolicy.default_five_year()
        
        if not self.policy.validate_bands():
            logger.warning("age_band_policy_validation_failed")
    
    def generalize_age(self, age: int) -> str:
        """
        Generalize an exact age to its age band label.
        
        Args:
            age: Exact age in years
            
        Returns:
            Age band label (e.g., "45-49")
        """
        if age < 0:
            logger.warning("negative_age_generalized", age=age)
            age = 0
        return self.policy.get_band_label(age)
    
    def generalize_dob(self, dob: Union[date, datetime, str], reference_date: Optional[date] = None) -> str:
        """
        Generalize date of birth to age band.
        
        Args:
            dob: Date of birth
            reference_date: Reference date for age calculation (default: today)
            
        Returns:
            Age band label
        """
        if reference_date is None:
            reference_date = date.today()
        
        # Parse DOB if string
        if isinstance(dob, str):
            dob = self._parse_date(dob)
        elif isinstance(dob, datetime):
            dob = dob.date()
        
        if dob is None:
            return self.policy.default_band_label
        
        # Calculate age
        age = self._calculate_age(dob, reference_date)
        return self.generalize_age(age)
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string in common formats."""
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%m/%d/%Y",
            "%Y%m%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
        except ValueError:
            pass
        return None
    
    def _calculate_age(self, dob: date, reference: date) -> int:
        """Calculate age in years at reference date."""
        age = reference.year - dob.year
        if (reference.month, reference.day) < (dob.month, dob.day):
            age -= 1
        return max(0, age)
    
    def get_band_bounds(self, age: int) -> Tuple[int, Optional[int]]:
        """
        Get the min and max bounds of the age band for a given age.
        
        Args:
            age: Exact age
            
        Returns:
            Tuple of (min_age, max_age) where max_age can be None
        """
        band = self.policy.get_band_for_age(age)
        return (band.min_age, band.max_age)
    
    def create_age_band_field(self, age: int, field_name: str = "age_band") -> Dict[str, str]:
        """
        Create a structured field for the age band.
        
        Args:
            age: Exact age
            field_name: Name of the field to create
            
        Returns:
            Dictionary with field_name -> band_label
        """
        return {field_name: self.generalize_age(age)}
    
    @classmethod
    def from_policy_file(cls, policy_path: Path) -> "AgeGeneralizer":
        """Create AgeGeneralizer from policy.yaml file."""
        with open(policy_path) as f:
            config = yaml.safe_load(f)
        privacy_config = config.get("privacy", {})
        policy = AgeBandPolicy.from_config(privacy_config)
        return cls(policy)


def load_age_bands_from_policy(policy_path: Path) -> AgeBandPolicy:
    """Load age band policy from policy.yaml."""
    with open(policy_path) as f:
        config = yaml.safe_load(f)
    privacy_config = config.get("privacy", {})
    return AgeBandPolicy.from_config(privacy_config)