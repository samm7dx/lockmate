"""
LOCKMATE — Devanagari to Latin Transliteration

Provides Devanagari to Latin (IAST) transliteration with Double Metaphone
phonetic encoding for cross-script name matching.
"""

from __future__ import annotations

from typing import List, Tuple, Optional
from functools import lru_cache

# Try to import indic-transliteration
try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    INDIC_TRANSLITERATION_AVAILABLE = True
except ImportError:
    INDIC_TRANSLITERATION_AVAILABLE = False

try:
    from metaphone import doublemetaphone
    DOUBLE_METAPHONE_AVAILABLE = True
except ImportError:
    DOUBLE_METAPHONE_AVAILABLE = False

from ..utils.logging import get_logger_adapter

logger = get_logger_adapter("detection.transliterate")

# Manual Devanagari to IAST mapping (fallback if indic-transliteration unavailable)
DEVANAGARI_TO_IAST = {
    # Vowels
    'अ': 'a', 'आ': 'ā', 'इ': 'i', 'ई': 'ī', 'उ': 'u', 'ऊ': 'ū',
    'ऋ': 'ṛ', 'ॠ': 'ṝ', 'ऌ': 'ḷ', 'ॡ': 'ḹ', 'ए': 'e', 'ऐ': 'ai',
    'ओ': 'o', 'औ': 'au', 'अं': 'ṃ', 'अः': 'ḥ',
    # Consonants
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ṅ',
    'च': 'c', 'छ': 'ch', 'ज': 'j', 'झ': 'jh', 'ञ': 'ñ',
    'ट': 'ṭ', 'ठ': 'ṭh', 'ड': 'ḍ', 'ढ': 'ḍh', 'ण': 'ṇ',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'ś',
    'ष': 'ṣ', 'स': 's', 'ह': 'h',
    # Diacritics (matras)
    'ा': 'ā', 'ि': 'i', 'ी': 'ī', 'ु': 'u', 'ू': 'ū',
    'ृ': 'ṛ', 'ॄ': 'ṝ', 'ॢ': 'ḷ', 'ॣ': 'ḹ',
    'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au',
    'ं': 'ṃ', 'ः': 'ḥ', '्': '',  # virama
    # Digits
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
    # Punctuation
    '।': '.', '॥': '..',
}

# Consonants that need implicit 'a' when not followed by matra
CONSONANTS = set('कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह')

# Virama (halant)
VIRAMA = '्'

# Devanagari range
DEVANAGARI_START = 0x0900
DEVANAGARI_END = 0x097F


def is_devanagari(char: str) -> bool:
    """Check if character is in Devanagari range."""
    return DEVANAGARI_START <= ord(char) <= DEVANAGARI_END


def is_devanagari_text(text: str) -> bool:
    """Check if text contains Devanagari characters."""
    return any(is_devanagari(c) for c in text)


@lru_cache(maxsize=1024)
def _devanagari_to_latin_cached(text: str) -> str:
    """
    Transliterate Devanagari text to Latin (IAST) script (cached).
    
    Uses indic-transliteration library if available, otherwise falls back
    to manual mapping.
    """
    if not text:
        return ""
    
    # Try library first
    if INDIC_TRANSLITERATION_AVAILABLE:
        try:
            result = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
            # Convert ITRANS to IAST-like representation
            return _itrans_to_iast(result)
        except Exception as e:
            logger.debug("transliteration_library_failed", error=str(e))
    
    # Fallback to manual mapping
    return _manual_devanagari_to_latin(text)


def _itrans_to_iast(text: str) -> str:
    """Convert ITRANS to IAST-like Latin."""
    mapping = {
        'aa': 'ā', 'ii': 'ī', 'uu': 'ū', 'RRi': 'ṛ', 'RRI': 'ṝ',
        'LLi': 'ḷ', 'LLI': 'ḹ', 'ee': 'ē', 'ai': 'ai', 'oo': 'ō', 'au': 'au',
        'M': 'ṃ', 'H': 'ḥ', '~': 'ṃ', '.h': 'ḥ',
        'k': 'k', 'kh': 'kh', 'g': 'g', 'gh': 'gh', 'G': 'ṅ',
        'c': 'c', 'ch': 'ch', 'j': 'j', 'jh': 'jh', 'J': 'ñ',
        'T': 'ṭ', 'Th': 'ṭh', 'D': 'ḍ', 'Dh': 'ḍh', 'N': 'ṇ',
        't': 't', 'th': 'th', 'd': 'd', 'dh': 'dh', 'n': 'n',
        'p': 'p', 'ph': 'ph', 'b': 'b', 'bh': 'bh', 'm': 'm',
        'y': 'y', 'r': 'r', 'l': 'l', 'v': 'v', 'w': 'v',
        'S': 'ś', 'sh': 'ṣ', 's': 's', 'h': 'h',
        'a': 'a', 'i': 'i', 'u': 'u', 'e': 'e', 'o': 'o',
    }
    
    result = text
    # Sort by length descending to handle multi-char sequences first
    for k, v in sorted(mapping.items(), key=lambda x: -len(x[0])):
        result = result.replace(k, v)
    return result


def _manual_devanagari_to_latin(text: str) -> str:
    """
    Manual Devanagari to Latin transliteration using IAST mapping.
    Handles conjunct consonants and matras properly.
    """
    if not text:
        return ""
    
    result = []
    i = 0
    n = len(text)
    
    while i < n:
        char = text[i]
        
        if not is_devanagari(char):
            result.append(char)
            i += 1
            continue
        
        # Handle virama (halant) - conjunct consonants
        if char == VIRAMA:
            # Virama removes inherent 'a' from previous consonant
            # For simplicity, we just skip it (the previous consonant was already written without 'a')
            i += 1
            continue
        
        # Check for matra (vowel sign) after consonant
        if char in CONSONANTS:
            # Look ahead for matra
            matra = ''
            if i + 1 < n and text[i + 1] in DEVANAGARI_TO_IAST:
                next_char = text[i + 1]
                if next_char in DEVANAGARI_TO_IAST and next_char not in CONSONANTS and next_char != VIRAMA:
                    matra = DEVANAGARI_TO_IAST[next_char]
                    i += 1
            
            base = DEVANAGARI_TO_IAST.get(char, char)
            result.append(base + matra)
            i += 1
        elif char in DEVANAGARI_TO_IAST:
            # Vowel or other mapped char
            result.append(DEVANAGARI_TO_IAST[char])
            i += 1
        else:
            # Unknown Devanagari char
            result.append(char)
            i += 1
    
    return ''.join(result)


def devanagari_to_latin(text: str) -> str:
    """
    Main entry point for Devanagari to Latin transliteration.
    
    Args:
        text: Input text (may contain mixed scripts)
    
    Returns:
        Latin transliteration
    """
    if not text:
        return ""
    
    # If no Devanagari, return as-is
    if not is_devanagari_text(text):
        return text
    
    # Check if mostly Devanagari
    devanagari_chars = sum(1 for c in text if is_devanagari(c))
    total_chars = sum(1 for c in text if not c.isspace())
    
    if devanagari_chars / max(total_chars, 1) > 0.5:
        # Mostly Devanagari - transliterate whole string using cached function
        return _devanagari_to_latin_cached(text)
    else:
        # Mixed script - transliterate only Devanagari portions
        return _transliterate_mixed(text)


def _transliterate_mixed(text: str) -> str:
    """Transliterate only Devanagari portions in mixed-script text."""
    result = []
    i = 0
    n = len(text)
    
    while i < n:
        char = text[i]
        if is_devanagari(char):
            # Collect consecutive Devanagari chars
            devanagari_seq = []
            while i < n and is_devanagari(text[i]):
                devanagari_seq.append(text[i])
                i += 1
            result.append(devanagari_to_latin(''.join(devanagari_seq)))
        else:
            result.append(char)
            i += 1
    
    return ''.join(result)


def is_devanagari(char: str) -> bool:
    """Check if character is in Devanagari range."""
    return DEVANAGARI_START <= ord(char) <= DEVANAGARI_END


def is_devanagari_text(text: str) -> bool:
    """Check if text contains Devanagari characters."""
    return any(is_devanagari(c) for c in text)


@lru_cache(maxsize=1024)
def double_metaphone(text: str) -> Tuple[str, Optional[str]]:
    """
    Compute Double Metaphone codes for text.
    
    Returns:
        Tuple of (primary_code, secondary_code_or_None)
    """
    if not text:
        return ("", None)
    
    if DOUBLE_METAPHONE_AVAILABLE:
        try:
            primary, secondary = doublemetaphone(text)
            return (primary, secondary if secondary else None)
        except Exception:
            pass
    
    # Fallback: simple metaphone-like encoding
    return (_simple_metaphone(text), None)


def _simple_metaphone(text: str) -> str:
    """Simple Metaphone-like encoding for fallback."""
    if not text:
        return ""
    
    text = text.upper()
    # Very simplified metaphone
    result = []
    i = 0
    while i < len(text):
        c = text[i]
        if c in 'AEIOU':
            if i == 0:
                result.append(c)
        elif c == 'B':
            if i+1 < len(text) and text[i+1] != 'B':
                result.append('B')
        elif c == 'C':
            if i+1 < len(text) and text[i+1] in 'IEY':
                result.append('S')
            else:
                result.append('K')
        elif c == 'D':
            result.append('T')
        elif c == 'G':
            if i+1 < len(text) and text[i+1] in 'IEY':
                result.append('J')
            else:
                result.append('K')
        elif c == 'H':
            if i+1 < len(text) and text[i+1] not in 'AEIOU':
                result.append('H')
        elif c == 'K':
            result.append('K')
        elif c == 'P':
            result.append('P')
        elif c == 'T':
            result.append('T')
        elif c in 'AEIOU':
            pass  # Already handled
        else:
            result.append(c)
        i += 1
    
    return ''.join(result)


def get_phonetic_codes(text: str) -> Tuple[str, Optional[str]]:
    """
    Get phonetic codes for name matching.
    
    For Devanagari text, first transliterates to Latin, then applies Double Metaphone.
    
    Returns:
        Tuple of (primary_code, secondary_code_or_None)
    """
    if not text:
        return ("", None)
    
    # Transliterate if needed
    latin_text = devanagari_to_latin(text)
    return double_metaphone(latin_text)


def transliterate_name(name: str) -> str:
    """
    Transliterate a name from any supported script to Latin.
    
    Handles:
    - Devanagari (Hindi)
    - Mixed script (Hinglish)
    - Already Latin
    
    Returns:
        Latin transliteration
    """
    if not name:
        return ""
    
    # Check for Devanagari
    if is_devanagari_text(name):
        return devanagari_to_latin(name)
    
    # Check for mixed script
    if any(is_devanagari(c) for c in name):
        return _transliterate_mixed(name)
    
    # Already Latin
    return name


def generate_name_variants(name: str) -> List[str]:
    """
    Generate common transliteration variants for a name.
    
    Useful for matching and blocking.
    """
    variants = set()
    
    if not name:
        return []
    
    # Original
    variants.add(name)
    
    # Transliterated
    latin = transliterate_name(name)
    if latin != name:
        variants.add(latin)
    
    # Lowercase
    variants.add(name.lower())
    variants.add(latin.lower())
    
    # Remove diacritics
    def strip_accents(s):
        return ''.join(c for c in unicodedata.normalize('NFD', s) 
                       if unicodedata.category(c) != 'Mn')
    variants.add(strip_accents(latin))
    
    # Common Indian name variations
    # Mohammad variants
    mohammad_variants = ['mohammad', 'mohammed', 'mohd', 'muhammad', 'muhammed']
    for var in mohammad_variants:
        if var in name.lower() or var in latin.lower():
            variants.update(mohammad_variants)
            break
    
    # Common abbreviations
    abbrevs = {
        'mohd': 'mohammad',
        'md': 'mohammad',
        'dr': 'doctor',
        'mr': 'mister',
        'mrs': 'mistress',
        'ms': 'miss',
    }
    for abbr, full in abbrevs.items():
        if abbr in name.lower():
            variants.add(full)
    
    return list(variants)


# Backwards compatibility
DEVANAGARI_TO_IAST = DEVANAGARI_TO_IAST
DEVANAGARI_TO_IAST.update({
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ṅ',
    'च': 'c', 'छ': 'ch', 'ज': 'j', 'झ': 'jh', 'ञ': 'ñ',
    'ट': 'ṭ', 'ठ': 'ṭh', 'ड': 'ḍ', 'ढ': 'ḍh', 'ण': 'ṇ',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'ś',
    'ष': 'ṣ', 'स': 's', 'ह': 'h',
})


__all__ = [
    'devanagari_to_latin',
    'transliterate_name',
    'double_metaphone',
    'get_phonetic_codes',
    'transliterate_name',
    'generate_name_variants',
    'is_devanagari',
    'is_devanagari_text',
    'DEVANAGARI_TO_IAST',
]