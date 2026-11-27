"""
LOCKMATE — Unicode Normalization Pipeline

Unicode normalization pipeline for multilingual PII detection.
Handles NFC normalization, Devanagari digit normalization, zero-width character handling,
Bidi/confusable character checks, and offset map maintenance.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Tuple, Optional

from ..contracts import UnifiedRecord
from ..utils.logging import get_logger_adapter

logger = get_logger_adapter("detection.normalize")

# Devanagari digit to ASCII mapping
DEVANAGARI_DIGITS = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}

# Zero-width characters to remove
ZERO_WIDTH_CHARS = {
    '\u200b',  # ZERO WIDTH SPACE
    '\u200c',  # ZERO WIDTH NON-JOINER
    '\u200d',  # ZERO WIDTH JOINER
    '\ufeff',  # ZERO WIDTH NO-BREAK SPACE (BOM)
}

# Bidi control characters
BIDI_CHARS = {
    '\u200e',  # LEFT-TO-RIGHT MARK
    '\u200f',  # RIGHT-TO-LEFT MARK
    '\u202a',  # LEFT-TO-RIGHT EMBEDDING
    '\u202b',  # RIGHT-TO-LEFT EMBEDDING
    '\u202c',  # POP DIRECTIONAL FORMATTING
    '\u202d',  # LEFT-TO-RIGHT OVERRIDE
    '\u202e',  # RIGHT-TO-LEFT OVERRIDE
}

# Confusable characters (common homographs)
CONFUSABLE_MAP = {
    # Cyrillic lookalikes
    'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'х': 'x', 'у': 'y',
    'А': 'A', 'Е': 'E', 'О': 'O', 'Р': 'P', 'С': 'C', 'Х': 'X', 'У': 'Y',
    # Greek lookalikes
    'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd', 'ε': 'e', 'ζ': 'z', 'η': 'h',
    'θ': 'q', 'ι': 'i', 'κ': 'k', 'λ': 'l', 'μ': 'm', 'ν': 'v', 'ξ': 'x',
    'ο': 'o', 'π': 'p', 'ρ': 'r', 'σ': 's', 'τ': 't', 'υ': 'u', 'φ': 'f',
    'χ': 'x', 'ψ': 'y', 'ω': 'w',
    # Full-width forms
    'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E', 'Ｆ': 'F',
    'Ｇ': 'G', 'Ｈ': 'H', 'Ｉ': 'I', 'Ｊ': 'J', 'Ｋ': 'K', 'Ｌ': 'L',
    'Ｍ': 'M', 'Ｎ': 'N', 'Ｏ': 'O', 'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R',
    'Ｓ': 'S', 'Ｔ': 'T', 'Ｕ': 'U', 'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X',
    'Ｙ': 'Y', 'Ｚ': 'Z',
    'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e', 'ｆ': 'f',
    'ｇ': 'g', 'ｈ': 'h', 'ｉ': 'i', 'ｊ': 'j', 'ｋ': 'k', 'ｌ': 'l',
    'ｍ': 'm', 'ｎ': 'n', 'ｏ': 'o', 'ｐ': 'p', 'ｑ': 'q', 'ｒ': 'r',
    'ｓ': 's', 'ｔ': 't', 'ｕ': 'u', 'ｖ': 'v', 'ｗ': 'w', 'ｘ': 'x',
    'ｙ': 'y', 'ｚ': 'z',
    '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
    '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
}


@dataclass
class NormalizationResult:
    """Result of Unicode normalization with offset mapping."""
    normalized_text: str
    offset_map: List[Tuple[int, int]]  # List of (orig_offset, norm_offset) for each normalized char
    had_changes: bool


def normalize_text(text: str) -> NormalizationResult:
    """
    Apply Unicode normalization pipeline to text.

    Pipeline:
    1. NFC normalization
    2. Devanagari digit → ASCII
    3. Zero-width character removal
    4. Bidi control character removal
    5. Confusable character normalization
    6. NFC re-normalization

    Maintains offset map: for each character in normalized text,
    stores the corresponding original text offset.
    """
    if not text:
        return NormalizationResult("", [], False)

    original = text
    current_text = text
    # offset_map[i] = original_offset of normalized_text[i]
    offset_map: List[int] = list(range(len(text)))

    # Step 1: NFC normalization
    current_text, offset_map = _apply_nfc(current_text, offset_map)

    # Step 2: Devanagari digits → ASCII
    current_text, offset_map = _apply_devanagari_digits(current_text, offset_map)

    # Step 3: Remove zero-width chars
    current_text, offset_map = _apply_remove_chars(current_text, offset_map, ZERO_WIDTH_CHARS, 'zero_width')

    # Step 4: Remove bidi control chars
    current_text, offset_map = _apply_remove_chars(current_text, offset_map, BIDI_CHARS, 'bidi')

    # Step 5: Normalize confusables
    current_text, offset_map = _apply_confusables(current_text, offset_map)

    # Step 6: Final NFC normalization
    current_text, offset_map = _apply_nfc(current_text, offset_map)

    had_changes = original != current_text

    if had_changes:
        logger.debug("normalization_applied",
                    original=original[:100],
                    normalized=current_text[:100],
                    orig_len=len(original),
                    norm_len=len(current_text))

    # Convert offset_map to list of (orig_start, orig_end) for each normalized char
    # But we need list of (norm_start, norm_end, orig_start, orig_end) for spans
    # Return as list of (orig_offset, norm_offset) pairs
    offset_pairs = [(orig_off, i) for i, orig_off in enumerate(offset_map)]

    return NormalizationResult(
        normalized_text=current_text,
        offset_map=offset_pairs,
        had_changes=had_changes
    )


def _apply_nfc(text: str, offset_map: List[int]) -> Tuple[str, List[int]]:
    """Apply NFC normalization with offset tracking."""
    result_chars = []
    result_offsets = []
    
    i = 0
    while i < len(text):
        # Check if this character will be composed with next
        char = text[i]
        orig_offset = offset_map[i]
        
        # Try to find NFC composition
        # Look ahead to see if combining
        if i + 1 < len(text):
            combined = unicodedata.normalize('NFC', char + text[i+1])
            if len(combined) == 1 and combined != char:
                # Composition happened
                result_chars.append(combined)
                result_offsets.append(orig_offset)
                i += 2
                continue
        
        # No composition
        result_chars.append(char)
        result_offsets.append(orig_offset)
        i += 1
    
    return ''.join(result_chars), result_offsets


def _apply_devanagari_digits(text: str, offset_map: List[int]) -> Tuple[str, List[int]]:
    """Convert Devanagari digits to ASCII with offset tracking."""
    result_chars = []
    result_offsets = []
    
    for char, orig_offset in zip(text, offset_map):
        if char in DEVANAGARI_DIGITS:
            result_chars.append(DEVANAGARI_DIGITS[char])
            result_offsets.append(orig_offset)
        else:
            result_chars.append(char)
            result_offsets.append(orig_offset)
    
    return ''.join(result_chars), result_offsets


def _apply_remove_chars(
    text: str, 
    offset_map: List[int], 
    chars_to_remove: set, 
    transform_name: str
) -> Tuple[str, List[int]]:
    """Remove specified characters with offset tracking."""
    result_chars = []
    result_offsets = []
    
    for char, orig_offset in zip(text, offset_map):
        if char not in chars_to_remove:
            result_chars.append(char)
            result_offsets.append(orig_offset)
        # If removed, we skip adding to result - offset_map naturally shortens
    
    return ''.join(result_chars), result_offsets


def _apply_confusables(text: str, offset_map: List[int]) -> Tuple[str, List[int]]:
    """Normalize confusable characters with offset tracking."""
    result_chars = []
    result_offsets = []
    
    for char, orig_offset in zip(text, offset_map):
        if char in CONFUSABLE_MAP:
            result_chars.append(CONFUSABLE_MAP[char])
            result_offsets.append(orig_offset)
        else:
            result_chars.append(char)
            result_offsets.append(orig_offset)
    
    return ''.join(result_chars), result_offsets


def apply_normalization(record) -> Tuple[str, List[Tuple[int, int]]]:
    """
    Apply normalization to a UnifiedRecord.

    Returns:
        Tuple of (normalized_text, offset_map) where offset_map is 
        list of (orig_offset, norm_offset) for each normalized character
    """
    result = normalize_text(record.raw_text)
    return result.normalized_text, result.offset_map


def map_normalized_to_original(
    norm_start: int, 
    norm_end: int, 
    offset_map: List[Tuple[int, int]]
) -> Tuple[int, int]:
    """
    Map normalized text offsets back to original text offsets.

    Args:
        norm_start: Start offset in normalized text
        norm_end: End offset in normalized text
        offset_map: List of (orig_offset, norm_offset) for each normalized character

    Returns:
        Tuple of (orig_start, orig_end)
    """
    if not offset_map or norm_start >= len(offset_map):
        return (norm_start, norm_end)

    # Get original offsets for the span
    orig_start = offset_map[norm_start][0] if norm_start < len(offset_map) else norm_start
    
    if norm_end - 1 < len(offset_map):
        orig_end = offset_map[norm_end - 1][0] + 1
    else:
        orig_end = orig_start + (norm_end - norm_start)

    return (orig_start, orig_end)


def map_original_to_normalized(
    orig_start: int, 
    orig_end: int, 
    offset_map: List[Tuple[int, int]]
) -> Tuple[int, int]:
    """
    Map original text offsets to normalized text offsets.

    Args:
        orig_start: Start offset in original text
        orig_end: End offset in original text
        offset_map: List of (orig_offset, norm_offset) for each normalized character

    Returns:
        Tuple of (norm_start, norm_end)
    """
    if not offset_map:
        return (orig_start, orig_end)

    # Find first normalized char with orig_offset >= orig_start
    norm_start = 0
    for i, (orig_off, norm_off) in enumerate(offset_map):
        if orig_off >= orig_start:
            norm_start = i
            break
    else:
        norm_start = len(offset_map)

    # Find last normalized char with orig_offset < orig_end
    norm_end = norm_start
    for i in range(norm_start, len(offset_map)):
        if offset_map[i][0] < orig_end:
            norm_end = i + 1
        else:
            break

    return (norm_start, norm_end)


def get_original_text_for_span(
    norm_start: int, 
    norm_end: int, 
    original_text: str,
    offset_map: List[Tuple[int, int]]
) -> str:
    """
    Get the original text corresponding to a normalized span.
    
    Args:
        norm_start: Start in normalized text
        norm_end: End in normalized text
        original_text: The original unnormalized text
        offset_map: List of (orig_offset, norm_offset)
        
    Returns:
        Original text substring
    """
    orig_start, orig_end = map_normalized_to_original(norm_start, norm_end, offset_map)
    return original_text[orig_start:orig_end]


__all__ = [
    "normalize_text",
    "NormalizationResult",
    "apply_normalization",
    "map_normalized_to_original",
    "map_original_to_normalized",
    "get_original_text_for_span",
    "DEVANAGARI_DIGITS",
    "ZERO_WIDTH_CHARS",
    "BIDI_CHARS",
    "CONFUSABLE_MAP",
]