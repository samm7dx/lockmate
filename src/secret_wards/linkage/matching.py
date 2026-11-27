"""
LOCKMATE — Identity Matching Functions

Implements core matching algorithms for cross-hospital patient linkage:
- Strong identifier exact matching (Aadhaar, ABHA, phone, email, PAN, insurance)
- Cross-script name matching with transliteration
- Phonetic comparison (Double Metaphone)
- Relative name matching
- Evidence-weighted scoring
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict
from functools import lru_cache

from ..contracts import UnifiedRecord, PIIType
from ..detection.transliterate import devanagari_to_latin
from ..detection.normalize import normalize_text
from ..utils.logging import get_logger_adapter

logger = get_logger_adapter("linkage.matching")


def _get_record_id(record: Any) -> str:
    """Extract record_id from a record (handles both UnifiedRecord and SanitizedRecord)."""
    if hasattr(record, 'record_id'):
        return record.record_id
    if hasattr(record, 'record') and hasattr(record.record, 'record_id'):
        return record.record.record_id
    if hasattr(record, 'record') and isinstance(record.record, dict):
        return record.record.get('record_id', '')
    raise AttributeError(f"Cannot extract record_id from {type(record)}")


@dataclass
class RecordFeatures:
    """Precomputed features for a record to avoid repeated extraction."""
    record_id: str
    # Strong identifiers (normalized)
    aadhaar: str = ""
    abha: str = ""
    pan: str = ""
    insurance_id: str = ""
    uhid: str = ""
    mrn: str = ""
    phone: str = ""
    email: str = ""
    # Names (normalized and variants)
    name: str = ""
    name_norm: str = ""
    name_latin: str = ""
    name_latin_norm: str = ""
    name_metaphone_primary: str = ""
    name_metaphone_secondary: str = ""
    name_tokens: frozenset = field(default_factory=frozenset)
    # Relative names
    relative_name: str = ""
    relative_name_norm: str = ""
    relative_name_latin: str = ""
    relative_name_latin_norm: str = ""
    relative_name_metaphone_primary: str = ""
    relative_name_metaphone_secondary: str = ""
    relative_name_tokens: frozenset = field(default_factory=frozenset)
    # Raw fields dict for any additional lookups
    raw_fields: Dict[str, str] = field(default_factory=dict)


# Feature cache: record_id -> RecordFeatures
_feature_cache: Dict[str, RecordFeatures] = {}


def _extract_features(record: Any) -> RecordFeatures:
    """Extract and precompute all features needed for matching from a record (cached by record_id)."""
    record_id = _get_record_id(record)
    
    # Check cache first
    if record_id in _feature_cache:
        return _feature_cache[record_id]
    
    fields = extract_identifier_fields(record)
    
    # Normalize strong identifiers
    aadhaar = normalize_identifier(fields.get('aadhaar', ''))
    abha = normalize_identifier(fields.get('abha', ''))
    pan = fields.get('pan', '').upper().strip()
    insurance_id = fields.get('insurance_id', '').upper().strip()
    uhid = normalize_identifier(fields.get('uhid', ''))
    mrn = normalize_identifier(fields.get('mrn', ''))
    phone = normalize_phone(fields.get('phone', '') or fields.get('mobile', '') or fields.get('mobile_no', ''))
    email = fields.get('email', '').lower().strip()
    
    # Extract and precompute name features
    name = extract_name(fields)
    name_norm = normalize_text(name) if name else ""
    
    # Transliteration
    name_latin = devanagari_to_latin(name) if name and any('\u0900' <= c <= '\u097F' for c in name) else name
    name_latin_norm = normalize_text(name_latin) if name_latin else ""
    
    # Phonetic
    name_metaphone_primary, name_metaphone_secondary = double_metaphone(name) if name else ("", "")
    
    # Tokens for fuzzy matching
    name_tokens = frozenset(re.findall(r'\b\w+\b', name.lower())) if name else frozenset()
    
    # Relative name features
    rel_name = extract_relative_name_field(record)
    rel_name_norm = normalize_text(rel_name) if rel_name else ""
    rel_name_latin = devanagari_to_latin(rel_name) if rel_name and any('\u0900' <= c <= '\u097F' for c in rel_name) else rel_name
    rel_name_latin_norm = normalize_text(rel_name_latin) if rel_name_latin else ""
    rel_name_metaphone_primary, rel_name_metaphone_secondary = double_metaphone(rel_name) if rel_name else ("", "")
    rel_name_tokens = frozenset(re.findall(r'\b\w+\b', rel_name.lower())) if rel_name else frozenset()
    
    features = RecordFeatures(
        record_id=record_id,
        aadhaar=aadhaar,
        abha=abha,
        pan=pan,
        insurance_id=insurance_id,
        uhid=uhid,
        mrn=mrn,
        phone=phone,
        email=email,
        name=name,
        name_norm=name_norm,
        name_latin=name_latin,
        name_latin_norm=name_latin_norm,
        name_metaphone_primary=name_metaphone_primary,
        name_metaphone_secondary=name_metaphone_secondary,
        name_tokens=name_tokens,
        relative_name=rel_name,
        relative_name_norm=rel_name_norm,
        relative_name_latin=rel_name_latin,
        relative_name_latin_norm=rel_name_latin_norm,
        relative_name_metaphone_primary=rel_name_metaphone_primary,
        relative_name_metaphone_secondary=rel_name_metaphone_secondary,
        relative_name_tokens=rel_name_tokens,
        raw_fields=fields,
    )
    
    # Cache the features
    _feature_cache[record_id] = features
    return features


def clear_feature_cache() -> None:
    """Clear the feature cache (useful between runs)."""
    _feature_cache.clear()

# Double Metaphone implementation (simplified)
def double_metaphone(text: str) -> Tuple[str, str]:
    """
    Simplified Double Metaphone implementation for English/Indian names.
    Returns (primary_code, secondary_code).
    """
    if not text:
        return ("", "")
    
    # Remove non-alphabetic characters
    text = re.sub(r'[^A-Za-z]', '', text.upper())
    if not text:
        return ("", "")
    
    # Simplified Metaphone rules for Indian names
    # This is a simplified version - in production, use a full implementation
    code = ""
    i = 0
    while i < len(text):
        char = text[i]
        
        # Handle special cases
        if char in 'AEIOU':
            if i == 0:
                code += char
        elif char == 'B':
            if i+1 < len(text) and text[i+1] != 'B':
                code += 'P'
        elif char == 'C':
            if i+1 < len(text) and text[i+1] in 'IEY':
                code += 'S'
            else:
                code += 'K'
        elif char == 'D':
            code += 'T'
        elif char == 'G':
            if i+1 < len(text) and text[i+1] in 'IEY':
                code += 'J'
            else:
                code += 'K'
        elif char == 'H':
            if i+1 < len(text) and text[i+1] not in 'AEIOU':
                code += ''
            else:
                code += 'H'
        elif char == 'K':
            code += 'K'
        elif char == 'L':
            code += 'L'
        elif char == 'M':
            code += 'M'
        elif char == 'N':
            code += 'N'
        elif char == 'P':
            code += 'P'
        elif char == 'Q':
            code += 'K'
        elif char == 'R':
            code += 'R'
        elif char == 'S':
            if i+1 < len(text) and text[i+1] == 'H':
                code += 'X'
            elif i+1 < len(text) and text[i+1] == 'C':
                code += 'S'
            else:
                code += 'S'
        elif char == 'T':
            if i+1 < len(text) and text[i+1] == 'H':
                code += '0'
            else:
                code += 'T'
        elif char == 'V':
            code += 'F'
        elif char == 'W':
            code += 'W'
        elif char == 'X':
            code += 'KS'
        elif char == 'Y':
            code += 'Y'
        elif char == 'Z':
            code += 'S'
        elif char in 'DFGJLPRTVWXY':
            code += char
        
        i += 1
    
    # For simplicity, return same primary and secondary
    return (code[:8], code[:8])


@dataclass
class MatchScore:
    """Result of a field match with evidence."""
    field: str
    score: float
    evidence: str
    match_type: str  # 'exact', 'fuzzy', 'phonetic', 'transliterated'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "score": self.score,
            "evidence": self.evidence,
            "match_type": self.match_type
        }


def normalize_identifier(value: str) -> str:
    """Normalize identifier for comparison (remove spaces, hyphens, case)."""
    if not value:
        return ""
    return re.sub(r'[\s\-\.]', '', value).lower()


def match_strong_identifiers(record_a: Any, record_b: Any) -> List[MatchScore]:
    """
    Match strong identifiers between two records using precomputed features.
    
    Strong identifiers (exact match required):
    - Aadhaar (12 digits)
    - ABHA (14 digits)
    - Phone (10 digits, various formats)
    - Email (exact)
    - PAN (exact)
    - Insurance ID (exact)
    
    Returns list of MatchScore objects.
    """
    scores = []
    
    # Extract features (cached)
    feat_a = _extract_features(record_a)
    feat_b = _extract_features(record_b)
    
    # Aadhaar matching
    if feat_a.aadhaar and feat_b.aadhaar and feat_a.aadhaar == feat_b.aadhaar:
        scores.append(MatchScore(
            field='aadhaar',
            score=1.0,
            evidence=f"exact match: {feat_a.aadhaar}",
            match_type='exact'
        ))
    
    # ABHA matching
    if feat_a.abha and feat_b.abha and feat_a.abha == feat_b.abha:
        scores.append(MatchScore(
            field='abha',
            score=1.0,
            evidence=f"exact match: {feat_a.abha}",
            match_type='exact'
        ))
    
    # Phone matching
    if feat_a.phone and feat_b.phone and feat_a.phone == feat_b.phone:
        scores.append(MatchScore(
            field='phone',
            score=1.0,
            evidence=f"exact match: {feat_a.phone}",
            match_type='exact'
        ))
    
    # Email matching
    if feat_a.email and feat_b.email and feat_a.email == feat_b.email:
        scores.append(MatchScore(
            field='email',
            score=1.0,
            evidence=f"exact match: {feat_a.email}",
            match_type='exact'
        ))
    
    # PAN matching
    if feat_a.pan and feat_b.pan and feat_a.pan == feat_b.pan:
        scores.append(MatchScore(
            field='pan',
            score=1.0,
            evidence=f"exact match: {feat_a.pan}",
            match_type='exact'
        ))
    
    # Insurance ID matching
    if feat_a.insurance_id and feat_b.insurance_id and feat_a.insurance_id == feat_b.insurance_id:
        scores.append(MatchScore(
            field='insurance_id',
            score=1.0,
            evidence=f"exact match: {feat_a.insurance_id}",
            match_type='exact'
        ))
    
    # UHID/MRN matching (hospital-specific)
    if feat_a.uhid and feat_b.uhid and feat_a.uhid == feat_b.uhid:
        scores.append(MatchScore(
            field='uhid',
            score=1.0,
            evidence=f"exact match: {feat_a.uhid}",
            match_type='exact'
        ))
    if feat_a.mrn and feat_b.mrn and feat_a.mrn == feat_b.mrn:
        scores.append(MatchScore(
            field='mrn',
            score=1.0,
            evidence=f"exact match: {feat_a.mrn}",
            match_type='exact'
        ))
    
    return scores


def normalize_phone(phone: str) -> str:
    """Normalize phone number to 10-digit format."""
    if not phone:
        return ""
    # Remove all non-digits
    digits = re.sub(r'\D', '', phone)
    # Handle Indian formats
    if digits.startswith('91') and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith('0') and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in '6789':
        return digits
    return ""


def extract_identifier_fields(record: Any) -> Dict[str, str]:
    """Extract identifier fields from a record (UnifiedRecord or SanitizedRecord)."""
    fields = {}
    
    # SanitizedRecord has transformed_fields
    if hasattr(record, 'transformed_fields'):
        for field_path, field_value in record.transformed_fields.items():
            if isinstance(field_value, str):
                fields[field_path.lower()] = field_value
            elif isinstance(field_value, dict):
                # For nested structures, flatten
                for k, v in field_value.items():
                    if isinstance(v, str):
                        fields[f"{field_path.lower()}.{k.lower()}"] = v
    
    # UnifiedRecord
    if hasattr(record, 'fields'):
        for field_path, field_value in record.fields.items():
            if isinstance(field_value.value, str):
                fields[field_path.lower()] = field_value.value
    elif isinstance(record, dict):
        for k, v in record.items():
            if isinstance(v, str):
                fields[k.lower()] = v
    
    return fields


def match_names_cross_script(name_a: str, name_b: str) -> List[MatchScore]:
    """
    Match names across scripts (Latin, Devanagari, Hinglish) using raw strings.
    
    Strategies:
    1. Direct exact match (after normalization)
    2. Transliteration: Devanagari → Latin + comparison
    3. Phonetic: Double Metaphone comparison
    4. Fuzzy match on tokens
    
    Returns list of MatchScore objects.
    """
    scores = []
    
    if not name_a or not name_b:
        return scores
    
    # Normalize both names
    norm_a = normalize_text(name_a)
    norm_b = normalize_text(name_b)
    
    # 1. Direct exact match
    if norm_a == norm_b:
        return [MatchScore(
            field='name',
            score=1.0,
            evidence=f"exact match: {norm_a}",
            match_type='exact'
        )]
    
    # 2. Try transliteration of Devanagari
    try:
        latin_a = devanagari_to_latin(name_a) if any('\u0900' <= c <= '\u097F' for c in name_a) else name_a
        latin_b = devanagari_to_latin(name_b) if any('\u0900' <= c <= '\u097F' for c in name_b) else name_b
        
        latin_a_norm = normalize_text(latin_a)
        latin_b_norm = normalize_text(latin_b)
        
        if latin_a_norm == latin_b_norm:
            scores.append(MatchScore(
                field='name',
                score=0.95,
                evidence=f"transliterated match: {latin_a_norm}",
                match_type='transliterated'
            ))
    except Exception:
        pass
    
    # 3. Phonetic matching (Double Metaphone)
    try:
        meta_a = double_metaphone(name_a)
        meta_b = double_metaphone(name_b)
        
        # Check primary codes
        if meta_a[0] and meta_b[0] and meta_a[0] == meta_b[0]:
            scores.append(MatchScore(
                field='name',
                score=0.85,
                evidence=f"phonetic match: {meta_a[0]}",
                match_type='phonetic'
            ))
        # Check cross codes
        elif meta_a[1] and meta_b[1] and meta_a[1] == meta_b[1]:
            scores.append(MatchScore(
                field='name',
                score=0.8,
                evidence=f"phonetic alt match: {meta_a[1]}",
                match_type='phonetic'
            ))
    except Exception:
        pass
    
    # 4. Token-based fuzzy match
    tokens_a = set(re.findall(r'\b\w+\b', name_a.lower()))
    tokens_b = set(re.findall(r'\b\w+\b', name_b.lower()))
    
    if tokens_a and tokens_b:
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        jaccard = len(intersection) / len(union) if union else 0
        
        if jaccard >= 0.5:
            scores.append(MatchScore(
                field='name',
                score=0.6 * jaccard,
                evidence=f"fuzzy token match: {intersection}",
                match_type='fuzzy'
            ))
    
    return scores


def match_names_cross_script_features(feat_a: RecordFeatures, feat_b: RecordFeatures) -> List[MatchScore]:
    """
    Match names using precomputed features (fast path).
    
    Uses pre-normalized, pre-transliterated, pre-phonetic features.
    """
    scores = []
    
    # 1. Direct exact match (normalized)
    if feat_a.name_norm and feat_b.name_norm and feat_a.name_norm == feat_b.name_norm:
        return [MatchScore(
            field='name',
            score=1.0,
            evidence=f"exact match: {feat_a.name_norm}",
            match_type='exact'
        )]
    
    # 2. Transliteration match (precomputed)
    if feat_a.name_latin_norm and feat_b.name_latin_norm and feat_a.name_latin_norm == feat_b.name_latin_norm:
        scores.append(MatchScore(
            field='name',
            score=0.95,
            evidence=f"transliterated match: {feat_a.name_latin_norm}",
            match_type='transliterated'
        ))
    
    # 3. Phonetic matching (precomputed)
    if feat_a.name_metaphone_primary and feat_b.name_metaphone_primary and feat_a.name_metaphone_primary == feat_b.name_metaphone_primary:
        scores.append(MatchScore(
            field='name',
            score=0.85,
            evidence=f"phonetic match: {feat_a.name_metaphone_primary}",
            match_type='phonetic'
        ))
    elif feat_a.name_metaphone_secondary and feat_b.name_metaphone_secondary and feat_a.name_metaphone_secondary == feat_b.name_metaphone_secondary:
        scores.append(MatchScore(
            field='name',
            score=0.8,
            evidence=f"phonetic alt match: {feat_a.name_metaphone_secondary}",
            match_type='phonetic'
        ))
    
    # 4. Token-based fuzzy match (precomputed)
    if feat_a.name_tokens and feat_b.name_tokens:
        intersection = feat_a.name_tokens & feat_b.name_tokens
        union = feat_a.name_tokens | feat_b.name_tokens
        jaccard = len(intersection) / len(union) if union else 0
        
        if jaccard >= 0.5:
            scores.append(MatchScore(
                field='name',
                score=0.6 * jaccard,
                evidence=f"fuzzy token match: {intersection}",
                match_type='fuzzy'
            ))
    
    return scores


def match_relative_names_features(feat_a: RecordFeatures, feat_b: RecordFeatures) -> List[MatchScore]:
    """Match relative names using precomputed features."""
    scores = []
    
    if not feat_a.relative_name or not feat_b.relative_name:
        return scores
    
    # 1. Direct exact match (normalized)
    if feat_a.relative_name_norm and feat_b.relative_name_norm and feat_a.relative_name_norm == feat_b.relative_name_norm:
        scores.append(MatchScore(
            field='relative_name',
            score=1.0,
            evidence=f"relative exact match: {feat_a.relative_name_norm}",
            match_type='exact'
        ))
    
    # 2. Transliteration match
    if feat_a.relative_name_latin_norm and feat_b.relative_name_latin_norm and feat_a.relative_name_latin_norm == feat_b.relative_name_latin_norm:
        scores.append(MatchScore(
            field='relative_name',
            score=0.95,
            evidence=f"relative transliterated match: {feat_a.relative_name_latin_norm}",
            match_type='transliterated'
        ))
    
    # 3. Phonetic matching
    if feat_a.relative_name_metaphone_primary and feat_b.relative_name_metaphone_primary and feat_a.relative_name_metaphone_primary == feat_b.relative_name_metaphone_primary:
        scores.append(MatchScore(
            field='relative_name',
            score=0.85,
            evidence=f"relative phonetic match: {feat_a.relative_name_metaphone_primary}",
            match_type='phonetic'
        ))
    elif feat_a.relative_name_metaphone_secondary and feat_b.relative_name_metaphone_secondary and feat_a.relative_name_metaphone_secondary == feat_b.relative_name_metaphone_secondary:
        scores.append(MatchScore(
            field='relative_name',
            score=0.8,
            evidence=f"relative phonetic alt match: {feat_a.relative_name_metaphone_secondary}",
            match_type='phonetic'
        ))
    
    # 4. Token-based fuzzy match
    if feat_a.relative_name_tokens and feat_b.relative_name_tokens:
        intersection = feat_a.relative_name_tokens & feat_b.relative_name_tokens
        union = feat_a.relative_name_tokens | feat_b.relative_name_tokens
        jaccard = len(intersection) / len(union) if union else 0
        
        if jaccard >= 0.5:
            scores.append(MatchScore(
                field='relative_name',
                score=0.6 * jaccard,
                evidence=f"relative fuzzy token match: {intersection}",
                match_type='fuzzy'
            ))
    
    return scores


def match_relative_names(rel_a: str, rel_b: str) -> List[MatchScore]:
    """
    Match relative names (father, mother, spouse names).
    
    Handles S/o, D/o, W/o prefixes and name matching.
    """
    scores = []
    
    if not rel_a or not rel_b:
        return scores
    
    # Extract names from relative strings (remove S/o, D/o, W/o, C/O)
    name_a = extract_relative_name(rel_a)
    name_b = extract_relative_name(rel_b)
    
    if name_a and name_b:
        name_scores = match_names_cross_script(name_a, name_b)
        for s in name_scores:
            s.field = 'relative_name'
            s.evidence = f"relative: {s.evidence}"
            scores.append(s)
    
    return scores


def extract_relative_name(text: str) -> str:
    """Extract person name from relative string (remove S/o, D/o, W/o, C/O)."""
    # Remove common prefixes
    text = re.sub(r'^\s*(?:S/o|D/o|W/o|C/O|S/O|D/O|W/O|C/O|Son\s+of|Daughter\s+of|Wife\s+of|Husband\s+of)\s+', '', text, flags=re.IGNORECASE)
    return text.strip()


def compute_match_score(
    record_a: Any,
    record_b: Any,
    weights: Optional[Dict[str, float]] = None
) -> Tuple[float, Dict[str, float]]:
    """
    Compute overall match score between two records using precomputed features.
    
    Combines strong identifier matches, name matches, and relative matches
    with configurable weights.
    
    Returns (total_score, breakdown_dict).
    """
    if weights is None:
        weights = {
            'aadhaar': 1.0,
            'abha': 1.0,
            'phone': 0.9,
            'email': 0.9,
            'pan': 0.8,
            'insurance_id': 0.8,
            'uhid': 0.9,
            'mrn': 0.9,
            'name': 0.7,
            'relative_name': 0.5,
        }
    
    # Extract precomputed features (cached)
    feat_a = _extract_features(record_a)
    feat_b = _extract_features(record_b)
    
    breakdown = {}
    total_score = 0.0
    total_weight = 0.0
    
    # Strong identifiers
    id_scores = match_strong_identifiers(record_a, record_b)
    for s in id_scores:
        weight = weights.get(s.field, 0.5)
        breakdown[s.field] = s.score * weight
        total_score += s.score * weight
        total_weight += weight
    
    # Name matching (fast path with precomputed features)
    if feat_a.name and feat_b.name:
        name_scores = match_names_cross_script_features(feat_a, feat_b)
        if name_scores:
            best_name_score = max(s.score for s in name_scores)
            weight = weights.get('name', 0.7)
            breakdown['name'] = best_name_score * weight
            total_score += best_name_score * weight
            total_weight += weight
    
    # Relative names (fast path with precomputed features)
    if feat_a.relative_name and feat_b.relative_name:
        rel_scores = match_relative_names_features(feat_a, feat_b)
        if rel_scores:
            best_rel_score = max(s.score for s in rel_scores)
            weight = weights.get('relative_name', 0.5)
            breakdown['relative_name'] = best_rel_score * weight
            total_score += best_rel_score * weight
            total_weight += weight
    
    # Normalize
    if total_weight > 0:
        total_score = total_score / total_weight
    
    return total_score, breakdown


def extract_name(record: Any) -> Optional[str]:
    """Extract patient name from record (UnifiedRecord or SanitizedRecord)."""
    # Check SanitizedRecord transformed_fields first
    if hasattr(record, 'transformed_fields'):
        for field_path, field_value in record.transformed_fields.items():
            field_lower = field_path.lower()
            if any(k in field_lower for k in ['patient_name', 'patient name', 'name', 'naam']):
                if isinstance(field_value, str):
                    return field_value.strip()
    
    # Check UnifiedRecord fields
    if hasattr(record, 'fields'):
        for field_path, field_value in record.fields.items():
            field_lower = field_path.lower()
            if any(k in field_lower for k in ['patient_name', 'patient name', 'name', 'naam']):
                if isinstance(field_value.value, str):
                    return field_value.value.strip()
    elif isinstance(record, dict):
        for k, v in record.items():
            if any(kw in k.lower() for kw in ['patient_name', 'patient name', 'name', 'naam']):
                if isinstance(v, str):
                    return v.strip()
    return None


def extract_relative_name_field(record: Any) -> Optional[str]:
    """Extract relative name from record (UnifiedRecord or SanitizedRecord)."""
    # Check SanitizedRecord transformed_fields first
    if hasattr(record, 'transformed_fields'):
        for field_path, field_value in record.transformed_fields.items():
            field_lower = field_path.lower()
            if any(k in field_lower for k in ['relative', 'relation', 'father', 'mother', 'husband', 'spouse', 's/o', 'd/o', 'w/o', 'c/o']):
                if isinstance(field_value, str):
                    return field_value.strip()
    
    # Check UnifiedRecord fields
    if hasattr(record, 'fields'):
        for field_path, field_value in record.fields.items():
            field_lower = field_path.lower()
            if any(k in field_lower for k in ['relative', 'relation', 'father', 'mother', 'husband', 'spouse', 's/o', 'd/o', 'w/o', 'c/o']):
                if isinstance(field_value.value, str):
                    return field_value.value.strip()
    elif isinstance(record, dict):
        for k, v in record.items():
            if any(kw in k.lower() for kw in ['relative', 'relation', 'father', 'mother', 'husband', 'spouse']):
                if isinstance(v, str):
                    return v.strip()
    return None