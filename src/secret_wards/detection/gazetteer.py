"""
LOCKMATE — Gazetteer Loader

Loads and manages gazetteers for multilingual name detection.
Supports Indian first names, surnames, honorifics, and relationship markers
in both Latin and Devanagari scripts.
"""

from __future__ import annotations

import os
import csv
from pathlib import Path
from typing import Dict, List, Set, Optional, FrozenSet
from functools import lru_cache

from ..utils.logging import get_logger_adapter

logger = get_logger_adapter("detection.gazetteer")

# Default gazetteer paths (relative to project root)
DEFAULT_GAZETTEER_DIR = Path(__file__).parent.parent.parent / "data" / "gazetteers"

# Gazetteer file names
GAZETTEER_FILES = {
    "first_names_latin": "indian_first_names_latin.txt",
    "first_names_devanagari": "indian_first_names_devanagari.txt",
    "surnames_latin": "indian_surnames_latin.txt",
    "surnames_devanagari": "indian_surnames_devanagari.txt",
    "honorifics_latin": "honorifics_latin.txt",
    "honorifics_devanagari": "honorifics_devanagari.txt",
    "relationship_markers": "relationship_markers.txt",
    "medical_drugs": "medical_drugs.txt",
    "medical_diagnoses": "medical_diagnoses.txt",
    "medical_labs": "medical_labs.txt",
    "clinical_units": "clinical_units.txt",
    "districts_latin": "indian_districts_latin.txt",
}

# In-memory caches (lazy loaded)
_gazetteer_cache: Dict[str, FrozenSet[str]] = {}


class Gazetteer:
    """
    Manages gazetteer loading and lookup for name detection.
    
    Gazetteers are loaded once and cached as frozensets for fast O(1) lookup.
    Supports both Latin and Devanagari scripts.
    """
    
    def __init__(self, gazetteer_dir: Optional[Path] = None):
        self.gazetteer_dir = gazetteer_dir or DEFAULT_GAZETTEER_DIR
        self._loaded = False
        self._data: Dict[str, FrozenSet[str]] = {}
    
    def load_all(self) -> None:
        """Load all gazetteer files."""
        if self._loaded:
            return
        
        for name, filename in GAZETTEER_FILES.items():
            path = self.gazetteer_dir / filename
            if path.exists():
                self._data[name] = self._load_gazetteer(path)
                logger.debug("gazetteer_loaded", name=name, count=len(self._data[name]))
            else:
                logger.warning("gazetteer_missing", name=name, path=str(path))
                self._data[name] = frozenset()
        
        self._loaded = True
    
    def _load_gazetteer(self, path: Path) -> FrozenSet[str]:
        """Load a gazetteer file into a frozenset."""
        entries = set()
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    entries.add(line.strip().lower())
        return frozenset(entries)
    
    def get(self, name: str) -> FrozenSet[str]:
        """Get a gazetteer by name."""
        if not self._loaded:
            self.load_all()
        return self._data.get(name, frozenset())
    
    def contains(self, name: str, token: str) -> bool:
        """Check if token exists in gazetteer."""
        if not self._loaded:
            self.load_all()
        return token.lower() in self._data.get(name, frozenset())
    
    def get_all_names(self) -> FrozenSet[str]:
        """Get all names from all name gazetteers combined."""
        if not self._loaded:
            self.load_all()
        all_names = set()
        for key in ["first_names_latin", "first_names_devanagari", 
                      "surnames_latin", "surnames_devanagari"]:
            all_names.update(self._data.get(key, frozenset()))
        return frozenset(all_names)
    
    def get_honorifics(self) -> FrozenSet[str]:
        """Get all honorifics."""
        if not self._loaded:
            self.load_all()
        honorifics = set()
        honorifics.update(self._data.get("honorifics_latin", frozenset()))
        honorifics.update(self._data.get("honorifics_devanagari", frozenset()))
        return frozenset(honorifics)
    
    def get_relationship_markers(self) -> FrozenSet[str]:
        """Get relationship markers (S/o, D/o, etc.)."""
        if not self._loaded:
            self.load_all()
        return self._data.get("relationship_markers", frozenset())
    
    def get_medical_terms(self) -> FrozenSet[str]:
        """Get all medical terms (drugs, diagnoses, labs, units)."""
        if not self._loaded:
            self.load_all()
        medical = set()
        for key in ["medical_drugs", "medical_diagnoses", "medical_labs", "clinical_units"]:
            medical.update(self._data.get(key, frozenset()))
        return frozenset(medical)


# Global singleton instance
_global_gazetteer: Optional[Gazetteer] = None


def get_gazetteer() -> Gazetteer:
    """Get global gazetteer singleton."""
    global _global_gazetteer
    if _global_gazetteer is None:
        _global_gazetteer = Gazetteer()
    return _global_gazetteer


def ensure_gazetteers_exist() -> bool:
    """Check if gazetteer files exist, create minimal ones if missing."""
    gazetteer = get_gazetteer()
    gazetteer.load_all()
    
    missing = []
    for name in ["first_names_latin", "first_names_devanagari", 
                  "surnames_latin", "surnames_devanagari"]:
        if not gazetteer._data.get(name):
            missing.append(name)
    
    if missing:
        logger.warning("gazetteers_missing", missing=missing)
        _create_minimal_gazetteers()
        return False
    return True


def _create_minimal_gazetteers() -> None:
    """Create minimal gazetteer files for testing/development."""
    gazetteer_dir = DEFAULT_GAZETTEER_DIR
    gazetteer_dir.mkdir(parents=True, exist_ok=True)
    
    # Minimal first names (Latin)
    first_names_latin = {
        "rahul", "priya", "amit", "priyanka", "rajesh", "sunita",
        "anil", "meena", "vikas", "pooja", "arun", "seema",
        "mohammad", "mohammed", "mohd", "ahmed", "ali", "fatima",
        "raj", "kumar", "singh", "sharma", "patel", "gupta",
    }
    
    # Minimal first names (Devanagari)
    first_names_devanagari = {
        "राहुल", "प्रिया", "अमित", "प्रियंका", "राजेश", "सुनीता",
        "अनिल", "मीना", "विकास", "पूजा", "अरुण", "सीमा",
        "मोहम्मद", "अहमद", "अली", "फातिमा", "राज", "कुमार",
        "सिंह", "शर्मा", "पटेल", "गुप्ता",
    }
    
    # Minimal surnames (Latin)
    surnames_latin = {
        "sharma", "singh", "kumar", "patel", "gupta", "verma",
        "agarwal", "jain", "shah", "reddy", "rao", "iyer",
    }
    
    # Minimal surnames (Devanagari)
    surnames_devanagari = {
        "शर्मा", "सिंह", "कुमार", "पटेल", "गुप्ता", "वर्मा",
        "अग्रवाल", "जैन", "शाह", "रेड्डी", "राव", "अय्यर",
    }
    
    # Honorifics
    honorifics_latin = {"mr", "mrs", "ms", "dr", "prof", "shri", "smt"}
    honorifics_devanagari = {"श्री", "श्रीमती", "डॉ", "प्रोफेसर"}
    
    # Relationship markers
    relationship_markers = {
        "s/o", "d/o", "w/o", "c/o", "son of", "daughter of", "wife of",
        "पुत्र", "पुत्री", "पत्नी", "पति", "पिता", "माता",
        "के/की देखभाल में", "देखभाल में",
        "s/o", "d/o", "w/o", "c/o",  # lowercase variants
    }
    
    # Write files
    files = {
        "indian_first_names_latin.txt": first_names_latin,
        "indian_first_names_devanagari.txt": first_names_devanagari,
        "indian_surnames_latin.txt": surnames_latin,
        "indian_surnames_devanagari.txt": surnames_devanagari,
        "honorifics_latin.txt": honorifics_latin,
        "honorifics_devanagari.txt": honorifics_devanagari,
        "relationship_markers.txt": relationship_markers,
    }
    
    for filename, entries in files.items():
        path = DEFAULT_GAZETTEER_DIR / filename
        if not path.exists():
            with open(path, 'w', encoding='utf-8') as f:
                for entry in sorted(entries):
                    f.write(entry + '\n')


# Medical gazetteers (minimal)
def _create_medical_gazetteers() -> None:
    """Create minimal medical gazetteer files."""
    medical_dir = DEFAULT_GAZETTEER_DIR / "medical"
    medical_dir.mkdir(parents=True, exist_ok=True)
    
    medical_files = {
        "medical_drugs.txt": {
            "paracetamol", "dolo", "crocin", "calpol", "metformin", "aspirin",
            "ibuprofen", "diclofenac", "amoxicillin", "azithromycin",
            "ciprofloxacin", "metronidazole", "omeprazole", "ranitidine",
            "pantoprazole", "atorvastatin", "amlodipine", "losartan",
            "metoprolol", "insulin", "glimepiride", "gliclazide",
            "pioglitazone", "sitagliptin", "linagliptin", "empagliflozin",
            "dapagliflozin", "canagliflozin", "ramipril", "enalapril",
            "lisinopril", "telmisartan", "valsartan", "hydrochlorothiazide",
            "furosemide", "spironolactone", "warfarin", "aspirin",
            "clopidogrel", "atorvastatin", "simvastatin", "rosuvastatin",
        },
        "medical_diagnoses.txt": {
            "diabetes", "hypertension", "tb", "hiv", "aids", "cancer",
            "asthma", "arthritis", "osteoporosis", "anemia", "leukemia",
            "lymphoma", "melanoma", "carcinoma", "sarcoma",
            "parkinson's", "alzheimer's", "crohn's", "diabetes",
            "hypertension", "tb", "hiv", "aids", "cancer",
        },
        "medical_labs.txt": {
            "hba1c", "cbc", "lft", "kft", "tsh", "hb", "wbc", "rbc",
            "platelet", "creatinine", "urea", "glucose", "cholesterol",
            "hdl", "ldl", "triglycerides", "bilirubin", "alt", "ast",
            "alp", "ggt", "protein", "albumin", "sodium", "potassium",
            "chloride", "calcium", "magnesium", "phosphate", "uric",
        },
        "clinical_units.txt": {
            "mg", "g", "ml", "mcg", "iu", "u", "mg/dl", "mmol/l",
            "°c", "bpm", "mmhg", "cm", "kg", "years", "months", "days",
        },
    }
    
    for filename, entries in medical_files.items():
        path = DEFAULT_GAZETTEER_DIR / "medical" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with open(path, 'w', encoding='utf-8') as f:
                for entry in sorted(entries):
                    f.write(entry + '\n')


# Initialize on import
_create_minimal_gazetteers()
ensure_gazetteers_exist()