"""
LOCKMATE — Phase 5: Cross-Hospital Patient Identity Resolution

Implements cross-hospital patient identity resolution with:
- Strong identifier matching (Aadhaar, ABHA, phone, email, PAN, insurance ID)
- Cross-script name matching with transliteration
- Phonetic comparison (Double Metaphone)
- Evidence-based record clustering
- Same-name/different-patient separation
- Ambiguity handling with safe null returns
- HMAC pseudonym generation using RAKSHA_SECRET
- Stable pseudonym insertion into sanitized records
"""

from __future__ import annotations

from .matching import (
    match_strong_identifiers,
    match_names_cross_script,
    match_relative_names,
    compute_match_score,
)
from .clustering import (
    cluster_records,
    ClusterResult,
)
from .pseudonym import (
    generate_pseudonym,
    derive_canonical_identity,
)
from .identity_candidates import (
    generate_candidates,
    IdentityCandidate,
    BlockingKey,
)

__all__ = [
    "match_strong_identifiers",
    "match_names_cross_script",
    "match_relative_names",
    "compute_match_score",
    "cluster_records",
    "ClusterResult",
    "generate_pseudonym",
    "derive_canonical_identity",
    "generate_candidates",
    "IdentityCandidate",
    "BlockingKey",
]