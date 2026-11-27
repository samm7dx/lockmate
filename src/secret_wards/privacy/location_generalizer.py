"""
LOCKMATE — Phase 6: Location Generalization

Implements hierarchical location generalization for Indian addresses.
Hierarchy: House → Street/Locality → Village → Tehsil → District → State

Supports configurable privacy levels and gazetteer-based mapping.
Handles English, Hindi, and transliteration variants.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
import yaml

from ..utils.logging import get_logger

logger = get_logger("privacy.location_generalizer")


@dataclass(frozen=True)
class LocationLevel:
    """Represents a level in the location hierarchy."""
    name: str
    level: int  # 0 = most specific (house), higher = more general
    patterns: List[str] = field(default_factory=list)  # Regex patterns to identify this level
    keywords: List[str] = field(default_factory=list)  # Keywords that indicate this level


@dataclass
class LocationHierarchy:
    """Configurable location hierarchy for generalization."""
    levels: List[LocationLevel] = field(default_factory=list)
    gazetteer: Dict[str, Dict[str, str]] = field(default_factory=dict)  # location -> {level: parent}
    
    @classmethod
    def default_indian(cls) -> "LocationHierarchy":
        """Create default Indian address hierarchy."""
        levels = [
            LocationLevel(
                name="house",
                level=0,
                patterns=[
                    r"^\d+[A-Za-z]?$",  # House number
                    r"^(house|flat|apartment|apt)\s*\d+",  # House/flat/apartment
                ],
                keywords=["house", "flat", "apartment", "apt", "bungalow", "villa"]
            ),
            LocationLevel(
                name="street",
                level=1,
                patterns=[
                    r"(street|road|lane|avenue|marg|path|gali|nagar|colony)",
                ],
                keywords=["street", "road", "lane", "avenue", "marg", "path", "gali", "nagar", "colony", "chowk", "square"]
            ),
            LocationLevel(
                name="locality",
                level=2,
                patterns=[
                    r"(sector|block|phase|zone|area|layout|extension|enclave)",
                ],
                keywords=["sector", "block", "phase", "zone", "area", "layout", "extension", "enclave", "mohalla", "mohallah"]
            ),
            LocationLevel(
                name="village",
                level=3,
                patterns=[
                    r"(village|gram|gaon|village\s+\w+)",
                ],
                keywords=["village", "gram", "gaon", "pind", "gramin"]
            ),
            LocationLevel(
                name="tehsil",
                level=4,
                patterns=[
                    r"(tehsil|taluk|taluka|mandal|block\s+\w+)",
                ],
                keywords=["tehsil", "taluk", "taluka", "mandal", "block"]
            ),
            LocationLevel(
                name="district",
                level=5,
                patterns=[
                    r"(district|zila|zilla|dist\.)",
                ],
                keywords=["district", "zila", "zilla", "dist"]
            ),
            LocationLevel(
                name="state",
                level=6,
                patterns=[
                    r"(state|province)",
                ],
                keywords=["state", "province"]
            ),
        ]
        
        # Common Indian state mappings
        gazetteer = {
            "maharashtra": {"state": "maharashtra", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "delhi": {"state": "delhi", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "karnataka": {"state": "karnataka", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "tamil nadu": {"state": "tamil nadu", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "gujarat": {"state": "gujarat", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "rajasthan": {"state": "rajasthan", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "uttar pradesh": {"state": "uttar pradesh", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "west bengal": {"state": "west bengal", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "bihar": {"state": "bihar", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "madhya pradesh": {"state": "madhya pradesh", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "punjab": {"state": "punjab", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "haryana": {"state": "haryana", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "kerala": {"state": "kerala", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "odisha": {"state": "odisha", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "telangana": {"state": "telangana", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "andhra pradesh": {"state": "andhra pradesh", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "assam": {"state": "assam", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "jharkhand": {"state": "jharkhand", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "chhattisgarh": {"state": "chhattisgarh", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "uttarakhand": {"state": "uttarakhand", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "himachal pradesh": {"state": "himachal pradesh", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "goa": {"state": "goa", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "jammu and kashmir": {"state": "jammu and kashmir", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
            "ladakh": {"state": "ladakh", "district": "unknown", "tehsil": "unknown", "village": "unknown"},
        }
        
        return cls(levels=levels, gazetteer=gazetteer)
    
    def get_level_by_name(self, name: str) -> Optional[LocationLevel]:
        """Get level by name."""
        for level in self.levels:
            if level.name == name:
                return level
        return None
    
    def get_generalized(self, location: str, target_level: str) -> Optional[str]:
        """
        Get the generalized form of a location at the target level.
        
        Args:
            location: Specific location (e.g., village name)
            target_level: Target level name (e.g., "district")
            
        Returns:
            Generalized location or None if not found
        """
        loc_lower = location.lower().strip()
        if loc_lower in self.gazetteer:
            return self.gazetteer[loc_lower].get(target_level)
        return None


@dataclass
class ParsedAddress:
    """Parsed address components."""
    raw: str
    components: Dict[str, str] = field(default_factory=dict)  # level_name -> value
    detected_level: int = -1  # Most specific level detected
    confidence: float = 0.0


class LocationGeneralizer:
    """
    Location generalization for quasi-identifier protection.
    
    Parses addresses into hierarchical components and generalizes
    to the configured privacy level.
    """
    
    def __init__(
        self, 
        hierarchy: Optional[LocationHierarchy] = None,
        min_level: str = "district",  # Minimum level to retain (privacy setting)
        gazetteer_path: Optional[Path] = None
    ):
        """
        Initialize the location generalizer.
        
        Args:
            hierarchy: LocationHierarchy instance (uses default if None)
            min_level: Minimum level to retain (house, street, locality, village, tehsil, district, state)
            gazetteer_path: Path to external gazetteer CSV/JSON
        """
        self.hierarchy = hierarchy or LocationHierarchy.default_indian()
        self.min_level_name = min_level
        self.min_level_obj = self.hierarchy.get_level_by_name(min_level)
        
        if self.min_level_obj is None:
            raise ValueError(f"Unknown minimum level: {min_level}")
        
        # Load external gazetteer if provided
        if gazetteer_path and gazetteer_path.exists():
            self._load_gazetteer(gazetteer_path)
        
        # Build lookup for fast detection
        self._build_detectors()
    
    def _build_detectors(self):
        """Build regex detectors for each level."""
        self.detectors = {}
        for level in self.hierarchy.levels:
            combined_pattern = "|".join(level.patterns) if level.patterns else None
            if combined_pattern:
                self.detectors[level.name] = re.compile(combined_pattern, re.IGNORECASE)
    
    def _load_gazetteer(self, path: Path):
        """Load gazetteer from CSV or JSON."""
        try:
            if path.suffix == ".csv":
                import csv
                with open(path, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Expected columns: village, tehsil, district, state
                        village = row.get("village", "").lower().strip()
                        if village:
                            self.hierarchy.gazetteer[village] = {
                                "village": village,
                                "tehsil": row.get("tehsil", "").lower().strip() or "unknown",
                                "district": row.get("district", "").lower().strip() or "unknown",
                                "state": row.get("state", "").lower().strip() or "unknown",
                            }
            elif path.suffix == ".json":
                import json
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.hierarchy.gazetteer[k.lower().strip()] = v
            logger.info("gazetteer_loaded", entries=len(self.hierarchy.gazetteer))
        except Exception as e:
            logger.warning("gazetteer_load_failed", path=str(path), error=str(e))
    
    def parse_address(self, address: str) -> ParsedAddress:
        """
        Parse an address into hierarchical components.
        
        Args:
            address: Raw address string
            
        Returns:
            ParsedAddress with detected components
        """
        if not address:
            return ParsedAddress(raw=address)
        
        # Normalize
        normalized = self._normalize_address(address)
        tokens = self._tokenize(normalized)
        
        components = {}
        detected_level = -1
        
        # Try to match each level
        for level in self.hierarchy.levels:
            for token in tokens:
                if self._matches_level(token, level):
                    components[level.name] = token
                    if level.level > detected_level:
                        detected_level = level.level
                    break
        
        # If we have a village, try to look up higher levels from gazetteer
        if "village" in components:
            village = components["village"].lower()
            if village in self.hierarchy.gazetteer:
                gaz = self.hierarchy.gazetteer[village]
                for level_name in ["tehsil", "district", "state"]:
                    if level_name not in components and gaz.get(level_name) != "unknown":
                        components[level_name] = gaz[level_name]
                        level_obj = self.hierarchy.get_level_by_name(level_name)
                        if level_obj and level_obj.level > detected_level:
                            detected_level = level_obj.level
        
        return ParsedAddress(
            raw=address,
            components=components,
            detected_level=detected_level,
            confidence=0.8 if components else 0.1
        )
    
    def _normalize_address(self, address: str) -> str:
        """Normalize address for parsing."""
        # Handle Hindi/Devanagari
        address = address.strip()
        # Replace common separators
        address = re.sub(r"[,\;\|]", " ", address)
        # Collapse whitespace
        address = re.sub(r"\s+", " ", address)
        return address
    
    def _tokenize(self, address: str) -> List[str]:
        """Tokenize address into meaningful chunks."""
        # Split by common delimiters
        tokens = re.split(r"\s+", address)
        # Also try comma-separated
        if "," in address:
            tokens.extend([t.strip() for t in address.split(",")])
        return [t for t in tokens if t]
    
    def _matches_level(self, token: str, level: LocationLevel) -> bool:
        """Check if token matches a level."""
        if level.name in self.detectors:
            return bool(self.detectors[level.name].search(token))
        
        # Check keywords
        token_lower = token.lower()
        for keyword in level.keywords:
            if keyword in token_lower:
                return True
        return False
    
    def generalize(self, address: str) -> str:
        """
        Generalize an address to the minimum privacy level.
        
        Args:
            address: Raw address string
            
        Returns:
            Generalized address string
        """
        parsed = self.parse_address(address)
        
        # If we couldn't parse anything, return a safe default
        if not parsed.components:
            return self._get_default_for_min_level()
        
        # Find the most specific component at or above min_level
        result_components = []
        for level in self.hierarchy.levels:
            if level.level >= self.min_level_obj.level and level.name in parsed.components:
                result_components.append(parsed.components[level.name])
        
        if not result_components:
            # No component at required level, use the highest available
            available_levels = [l for l in self.hierarchy.levels if l.name in parsed.components]
            if available_levels:
                highest = max(available_levels, key=lambda x: x.level)
                result_components.append(parsed.components[highest.name])
            else:
                return self._get_default_for_min_level()
        
        return ", ".join(result_components)
    
    def _get_default_for_min_level(self) -> str:
        """Get a default value for the minimum level."""
        defaults = {
            "house": "unknown house",
            "street": "unknown street",
            "locality": "unknown locality",
            "village": "unknown village",
            "tehsil": "unknown tehsil",
            "district": "unknown district",
            "state": "unknown state",
        }
        return defaults.get(self.min_level_name, "unknown location")
    
    def generalize_structured(self, address_fields: Dict[str, str]) -> Dict[str, str]:
        """
        Generalize structured address fields (e.g., from CSV/JSON).
        
        Args:
            address_fields: Dictionary of field_name -> value
            
        Returns:
            Dictionary with generalized fields
        """
        # Combine all address fields into one string for parsing
        combined = " ".join(str(v) for v in address_fields.values() if v)
        parsed = self.parse_address(combined)
        
        result = {}
        for level in self.hierarchy.levels:
            if level.level >= self.min_level_obj.level:
                if level.name in parsed.components:
                    result[level.name] = parsed.components[level.name]
                else:
                    result[level.name] = self._get_default_for_min_level()
        
        return result
    
    def get_generalization_level(self, address: str) -> str:
        """
        Get the level to which an address was generalized.
        
        Args:
            address: Raw address
            
        Returns:
            Level name (e.g., "district")
        """
        parsed = self.parse_address(address)
        if parsed.detected_level >= self.min_level_obj.level:
            # Find the level name for detected_level
            for level in self.hierarchy.levels:
                if level.level == parsed.detected_level:
                    return level.name
        return self.min_level_name


def load_gazetteer_from_census(census_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Load gazetteer from Census 2011 CSV.
    
    Expected columns: village, tehsil, district, state
    """
    import csv
    gazetteer = {}
    with open(census_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            village = row.get("village", "").lower().strip()
            if village:
                gazetteer[village] = {
                    "village": village,
                    "tehsil": row.get("tehsil", "").lower().strip() or "unknown",
                    "district": row.get("district", "").lower().strip() or "unknown",
                    "state": row.get("state", "").lower().strip() or "unknown",
                }
    return gazetteer


def create_hierarchy_from_config(config: Dict) -> LocationHierarchy:
    """Create LocationHierarchy from policy configuration."""
    hierarchy = LocationHierarchy.default_indian()
    
    # Override gazetteer if provided
    if "gazetteer" in config:
        hierarchy.gazetteer.update(config["gazetteer"])
    
    return hierarchy