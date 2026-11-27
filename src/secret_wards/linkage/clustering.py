"""
LOCKMATE — Record Clustering for Patient Identity Resolution

Implements evidence-based clustering of records into patient clusters.
Uses connected components with conflict detection and evidence thresholds.
Optimized with Union-Find (Disjoint Set) for O(α(n)) find/union operations.
"""

from __future__ import annotations

import logging
import re
import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from collections import defaultdict

from ..contracts import UnifiedRecord, PatientCluster, IdentityCandidate
from ..utils.logging import get_logger_adapter
from .matching import compute_match_score, clear_feature_cache

logger = get_logger_adapter("linkage.clustering")


class UnionFind:
    """Union-Find (Disjoint Set) with path compression and union by rank."""
    
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n
        self.size = [1] * n
    
    def find(self, x: int) -> int:
        # Path compression
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    
    def union(self, x: int, y: int) -> bool:
        # Union by rank
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        self.size[rx] += self.size[ry]
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1
        return True
    
    def get_components(self) -> Dict[int, List[int]]:
        """Get all components as root -> list of members."""
        components = defaultdict(list)
        for i in range(len(self.parent)):
            components[self.find(i)].append(i)
        return components


@dataclass
class ClusterResult:
    """Result of clustering operation."""
    clusters: List['PatientCluster']
    unresolved_pairs: List[Tuple[Any, Any, str]]  # (record_a, record_b, reason)
    singleton_records: List[Any]


@dataclass
class ClusteringConfig:
    """Configuration for clustering algorithm."""
    # Minimum score to consider records as candidates for linkage
    min_candidate_score: float = 0.7
    
    # Minimum score to form a link
    min_link_score: float = 0.85
    
    # Maximum score difference to consider ambiguous
    ambiguity_threshold: float = 0.1
    
    # Maximum cluster size before forcing review
    max_cluster_size: int = 50
    
    # Require at least one strong identifier for high-confidence links
    require_strong_id_for_high_confidence: bool = True
    
    # Weights for match scoring
    match_weights: Dict[str, float] = field(default_factory=lambda: {
        'aadhaar': 1.0,
        'abha': 1.0,
        'phone': 0.9,
        'email': 0.9,
        'pan': 0.8,
        'insurance_id': 0.8,
        'uhid': 0.9,
        'name': 0.7,
        'relative_name': 0.5,
    })


def cluster_records(
    records: List[Any],
    config: Optional[ClusteringConfig] = None,
    score_func: Optional[Callable[[Any, Any], Tuple[float, Dict[str, float]]]] = None
) -> ClusterResult:
    """
    Cluster records into patient clusters using evidence-based linkage.
    
    Algorithm:
    1. Generate all candidate pairs using blocking
    2. Score each candidate pair
    3. Build graph of links above threshold
    4. Find connected components using Union-Find
    5. Detect and resolve conflicts
    6. Assign pseudonyms to confident clusters
    
    Args:
        records: List of records to cluster
        config: Clustering configuration
        score_func: Function to compute match score between two records
        
    Returns:
        ClusterResult with clusters, unresolved pairs, and singletons
    """
    if config is None:
        config = ClusteringConfig()
    
    if score_func is None:
        from .matching import compute_match_score
        score_func = lambda a, b: compute_match_score(a, b, config.match_weights)
    
    start_time = time.perf_counter()
    logger.info("clustering_start", record_count=len(records))
    
    # Clear feature cache at start of clustering
    clear_feature_cache()
    
    # Step 1: Generate candidate pairs using blocking
    t0 = time.perf_counter()
    candidate_pairs = generate_candidate_pairs(records)
    t1 = time.perf_counter()
    logger.info("candidates_generated", count=len(candidate_pairs), duration_ms=int((t1 - t0) * 1000))
    
    # Step 2: Score candidates and build adjacency for Union-Find
    t2 = time.perf_counter()
    n = len(records)
    record_ids = [_get_record_id(r) for r in records]
    id_to_idx = {rid: i for i, rid in enumerate(record_ids)}
    
    # Use Union-Find for O(α(n)) connected components
    uf = UnionFind(n)
    below_threshold = []
    edges = []
    
    for record_a, record_b in candidate_pairs:
        score, breakdown = score_func(record_a, record_b)
        id_a = _get_record_id(record_a)
        id_b = _get_record_id(record_b)
        idx_a = id_to_idx[id_a]
        idx_b = id_to_idx[id_b]
        
        if score >= config.min_candidate_score:
            edges.append((idx_a, idx_b, score, breakdown))
            uf.union(idx_a, idx_b)
        else:
            below_threshold.append((record_a, record_b, score, breakdown))
    
    t3 = time.perf_counter()
    logger.info("scoring_complete", candidates_scored=len(candidate_pairs), edges_above=len(edges), duration_ms=int((t3 - t2) * 1000))
    
    # Step 3: Find connected components using Union-Find
    t4 = time.perf_counter()
    components = uf.get_components()
    record_map = {_get_record_id(r): r for r in records}
    clusters = []
    
    for root, member_indices in components.items():
        component_records = [record_map[record_ids[idx]] for idx in member_indices]
        if component_records:
            cluster_id = str(uuid.uuid4())[:8]
            cluster = PatientCluster(
                cluster_id=cluster_id,
                records=component_records,
                canonical_identity=derive_canonical_identity(component_records),
            )
            clusters.append(cluster)
    
    t5 = time.perf_counter()
    logger.info("initial_clusters", count=len(clusters), duration_ms=int((t5 - t4) * 1000))
    
    # Step 4: Detect and resolve conflicts
    t6 = time.perf_counter()
    resolved_clusters = resolve_conflicts(clusters, config)
    t7 = time.perf_counter()
    logger.info("conflicts_resolved", clusters_before=len(clusters), clusters_after=len(resolved_clusters), duration_ms=int((t7 - t6) * 1000))
    
    # Step 5: Assign pseudonyms and finalize
    t8 = time.perf_counter()
    final_clusters = finalize_clusters(resolved_clusters, config)
    t9 = time.perf_counter()
    logger.info("clusters_finalized", count=len(final_clusters), duration_ms=int((t9 - t8) * 1000))
    
    # Find unresolved pairs and singletons
    linked_ids = set()
    for cluster in final_clusters:
        for record in cluster.records:
            linked_ids.add(_get_record_id(record))
    
    singletons = [r for r in records if _get_record_id(r) not in linked_ids]
    
    # Find unresolved (below threshold but have some evidence)
    unresolved = []
    for record_a, record_b, score, breakdown in below_threshold:
        unresolved.append((record_a, record_b, f"score {score:.2f} below threshold"))
    
    total_time = time.perf_counter() - start_time
    logger.info("clustering_complete", 
               clusters=len(final_clusters),
               singletons=len(singletons),
               unresolved=len(unresolved),
               total_duration_ms=int(total_time * 1000))
    
    return ClusterResult(
        clusters=final_clusters,
        unresolved_pairs=unresolved,
        singleton_records=singletons
    )


def generate_candidate_pairs(records: List[Any]) -> List[Tuple[Any, Any]]:
    """
    Generate candidate pairs using blocking keys to avoid O(n^2) comparison.
    
    Blocking keys:
    - Exact strong identifiers (Aadhaar, ABHA, phone, email, PAN, insurance)
    - Name blocking: first letter + last letter + length
    - DOB + gender
    - Hospital + date range
    """
    blocks = defaultdict(list)
    
    for record in records:
        keys = generate_blocking_keys(record)
        for key in keys:
            blocks[key].append(record)
    
    pairs = []
    for block_records in blocks.values():
        if len(block_records) > 1:
            # Generate all pairs within block
            for i in range(len(block_records)):
                for j in range(i + 1, len(block_records)):
                    pairs.append((block_records[i], block_records[j]))
    
    # Deduplicate pairs
    unique_pairs = set()
    for a, b in pairs:
        pair_key = tuple(sorted([_get_record_id(a), _get_record_id(b)]))
        unique_pairs.add(pair_key)
    
    # Convert back to record pairs
    record_map = {_get_record_id(r): r for r in records}
    return [(record_map[a], record_map[b]) for a, b in unique_pairs]


def generate_blocking_keys(record: Any) -> List[str]:
    """Generate blocking keys for a record."""
    keys = []
    
    # Extract fields using the unified extraction function
    fields = extract_identifier_fields(record)
    
    # Strong identifiers (exact matching)
    for field_name in ['aadhaar', 'abha', 'pan', 'insurance_id', 'uhid', 'mrn']:
        if field_name in fields and fields[field_name]:
            clean = re.sub(r'[\s\-\.]', '', fields[field_name])
            if clean:
                keys.append(f"{field_name}:{clean.lower()}")
    
    # Phone
    phone = fields.get('phone') or fields.get('mobile') or fields.get('mobile_no')
    if phone:
        clean = re.sub(r'\D', '', phone)
        if clean.startswith('91') and len(clean) == 12:
            clean = clean[2:]
        elif clean.startswith('0') and len(clean) == 11:
            clean = clean[1:]
        if len(clean) == 10 and clean[0] in '6789':
            keys.append(f"phone:{clean}")
    
    # Email
    email = fields.get('email')
    if email:
        keys.append(f"email:{email.lower().strip()}")
    
    # Name blocking (first letter + last letter + length)
    name = None
    for field_path, value in fields.items():
        if 'name' in field_path.lower() and 'relative' not in field_path.lower() and 'father' not in field_path.lower():
            if isinstance(value, str):
                name = value.strip()
                break
    
    if name:
        parts = name.strip().split()
        if len(parts) >= 2:
            first = parts[0][0].lower()
            last = parts[-1][0].lower()
            keys.append(f"name:{first}{last}{len(name)}")
    
    # DOB
    dob = None
    for field_name in ['dob', 'date_of_birth', 'birth_date', 'janm tithi']:
        if field_name in fields and fields[field_name]:
            dob = fields[field_name]
            break
    if dob:
        keys.append(f"dob:{dob}")
    
    # Gender
    gender = fields.get('gender') or fields.get('ling')
    if gender:
        keys.append(f"gender:{gender.lower().strip()}")
    
    # Hospital + date range (month/year)
    # This would require parsing dates from the record
    
    return keys


def _get_record_id(record: Any) -> str:
    """Extract record_id from a record (handles both UnifiedRecord and SanitizedRecord)."""
    if hasattr(record, 'record_id'):
        return record.record_id
    if hasattr(record, 'record') and hasattr(record.record, 'record_id'):
        return record.record.record_id
    if hasattr(record, 'record') and isinstance(record.record, dict):
        return record.record.get('record_id', '')
    raise AttributeError(f"Cannot extract record_id from {type(record)}")


def resolve_conflicts(
    clusters: List['PatientCluster'],
    config: 'ClusteringConfig'
) -> List['PatientCluster']:
    """
    Detect and resolve conflicts within clusters.
    
    Conflicts:
    - Same name, different strong identifiers (different people)
    - Conflicting strong identifiers (same person, different IDs)
    - Homonyms (same name, different people)
    """
    resolved = []
    
    for cluster in clusters:
        if len(cluster.records) <= 1:
            resolved.append(cluster)
            continue
        
        # Check for conflicts
        conflicts = detect_conflicts(cluster)
        
        if not conflicts:
            resolved.append(cluster)
            continue
        
        # Resolve by splitting
        sub_clusters = split_cluster(cluster, conflicts, config)
        resolved.extend(sub_clusters)
    
    return resolved


def detect_conflicts(cluster: 'PatientCluster') -> List[Tuple[Any, Any, str]]:
    """Detect conflicts within a cluster."""
    conflicts = []
    records = cluster.records
    
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            a = records[i]
            b = records[j]
            
            # Check for conflicting strong identifiers
            conflict = check_strong_id_conflict(a, b)
            if conflict:
                conflicts.append((a, b, conflict))
    
    return conflicts


def check_strong_id_conflict(record_a: Any, record_b: Any) -> Optional[str]:
    """Check if two records have conflicting strong identifiers.
    
    Only flags a conflict if the records have NO matching strong identifiers.
    If they share at least one strong identifier (email, phone, etc.), 
    differences in other identifiers are treated as data entry variations.
    """
    fields_a = extract_identifier_fields(record_a)
    fields_b = extract_identifier_fields(record_b)
    
    # Check for ANY matching strong identifier first
    has_any_match = False
    conflicts = []
    
    # Check Aadhaar
    aadhaar_a = normalize_identifier(fields_a.get('aadhaar', ''))
    aadhaar_b = normalize_identifier(fields_b.get('aadhaar', ''))
    if aadhaar_a and aadhaar_b:
        if aadhaar_a == aadhaar_b:
            has_any_match = True
        else:
            conflicts.append(f"conflicting aadhaar: {aadhaar_a} vs {aadhaar_b}")
    
    # ABHA
    abha_a = normalize_identifier(fields_a.get('abha', ''))
    abha_b = normalize_identifier(fields_b.get('abha', ''))
    if abha_a and abha_b:
        if abha_a == abha_b:
            has_any_match = True
        else:
            conflicts.append(f"conflicting abha: {abha_a} vs {abha_b}")
    
    # PAN
    pan_a = fields_a.get('pan', '').upper().strip()
    pan_b = fields_b.get('pan', '').upper().strip()
    if pan_a and pan_b:
        if pan_a == pan_b:
            has_any_match = True
        else:
            conflicts.append(f"conflicting pan: {pan_a} vs {pan_b}")
    
    # Phone
    phone_a = normalize_phone(fields_a.get('phone', ''))
    phone_b = normalize_phone(fields_b.get('phone', ''))
    if phone_a and phone_b:
        if phone_a == phone_b:
            has_any_match = True
        else:
            conflicts.append(f"conflicting phone: {phone_a} vs {phone_b}")
    
    # Email
    email_a = fields_a.get('email', '').lower().strip()
    email_b = fields_b.get('email', '').lower().strip()
    if email_a and email_b:
        if email_a == email_b:
            has_any_match = True
        else:
            conflicts.append(f"conflicting email: {email_a} vs {email_b}")
    
    # Only return conflict if there are conflicts AND no matching identifiers
    if conflicts and not has_any_match:
        return "; ".join(conflicts)
    
    return None


def split_cluster(
    cluster: 'PatientCluster',
    conflicts: List[Tuple[Any, Any, str]],
    config: 'ClusteringConfig'
) -> List['PatientCluster']:
    """Split a conflicted cluster into sub-clusters."""
    # Build conflict graph
    conflict_graph = defaultdict(set)
    for a, b, reason in conflicts:
        id_a = _get_record_id(a)
        id_b = _get_record_id(b)
        conflict_graph[id_a].add(id_b)
        conflict_graph[id_b].add(id_a)
    
    # Find independent sets (records with no conflicts between them)
    records = cluster.records
    record_ids = {_get_record_id(r) for r in records}
    
    # Simple greedy coloring to find independent sets
    color = {}
    for rid in record_ids:
        if rid in color:
            continue
        
        # Find color not used by neighbors
        used_colors = {color.get(nid) for nid in conflict_graph.get(rid, set()) if nid in color}
        c = 0
        while c in used_colors:
            c += 1
        color[rid] = c
    
    # Group by color
    color_groups = defaultdict(list)
    for rid, c in color.items():
        color_groups[c].append(next(r for r in records if _get_record_id(r) == rid))
    
    # Create sub-clusters
    sub_clusters = []
    for color_id, group in color_groups.items():
        if len(group) == 1:
            # Singleton - keep as is but mark as not confident
            sub_cluster = PatientCluster(
                cluster_id=str(uuid.uuid4())[:8],
                records=group,
                canonical_identity=derive_canonical_identity(group),
                is_confident=False
            )
            sub_clusters.append(sub_cluster)
        else:
            # Group - check if confident
            sub_cluster = PatientCluster(
                cluster_id=str(uuid.uuid4())[:8],
                records=group,
                canonical_identity=derive_canonical_identity(group),
                is_confident=check_cluster_confidence(group)
            )
            sub_clusters.append(sub_cluster)
    
    return sub_clusters


def check_cluster_confidence(records: List[Any]) -> bool:
    """Check if a cluster has high confidence (has strong identifiers)."""
    for record in records:
        fields = extract_identifier_fields(record)
        
        # Check for strong identifiers
        for field in ['aadhaar', 'abha', 'pan', 'insurance_id', 'uhid', 'mrn']:
            if fields.get(field):
                return True
        
        # Phone/email
        phone = normalize_phone(fields.get('phone', '') or fields.get('mobile', '') or fields.get('mobile_no', ''))
        if phone:
            return True
        
        email = fields.get('email', '').lower().strip()
        if email:
            return True
    
    return False


def finalize_clusters(clusters: List['PatientCluster'], config: 'ClusteringConfig') -> List['PatientCluster']:
    """Finalize clusters by assigning pseudonyms and canonical identities."""
    final = []
    
    for cluster in clusters:
        # Derive canonical identity
        cluster.canonical_identity = derive_canonical_identity(cluster.records)
        
        # Generate pseudonym if confident
        if cluster.is_confident and cluster.canonical_identity:
            from ..contracts import generate_pseudonym_format
            # Note: secret should come from config/env
            # cluster.pseudonym = generate_pseudonym_format(cluster.canonical_identity, secret)
            # For now, leave as placeholder - will be filled in by pipeline
            pass
        
        final.append(cluster)
    
    return final


def derive_canonical_identity(records: List[Any]) -> str:
    """
    Derive a canonical identity string for a cluster of records.
    
    Uses the strongest available identifiers to create a stable
    representation of the patient's identity.
    """
    # Collect all identifiers
    all_aadhaar = set()
    all_abha = set()
    all_pan = set()
    all_phone = set()
    all_email = set()
    all_names = set()
    
    for record in records:
        fields = extract_identifier_fields(record)
        
        aadhaar = normalize_identifier(fields.get('aadhaar', ''))
        if aadhaar:
            all_aadhaar.add(aadhaar)
        
        abha = fields.get('abha', '').replace(' ', '').replace('-', '')
        if abha:
            all_abha.add(abha)
        
        pan = fields.get('pan', '').upper().strip()
        if pan:
            all_pan.add(pan)
        
        phone = normalize_phone(fields.get('phone', '') or fields.get('mobile', '') or fields.get('mobile_no', ''))
        if phone:
            all_phone.add(phone)
        
        email = fields.get('email', '').lower().strip()
        if email:
            all_email.add(email)
        
        name = extract_name(fields)
        if name:
            all_names.add(name.strip())
    
    # Build canonical identity from strongest available identifiers
    parts = []
    
    if all_aadhaar:
        parts.append(f"AADHAAR:{sorted(all_aadhaar)[0]}")
    if all_abha:
        parts.append(f"ABHA:{sorted(all_abha)[0]}")
    if all_pan:
        parts.append(f"PAN:{sorted(all_pan)[0]}")
    if all_phone:
        parts.append(f"PHONE:{sorted(all_phone)[0]}")
    if all_email:
        parts.append(f"EMAIL:{sorted(all_email)[0]}")
    if all_names:
        parts.append(f"NAME:{sorted(all_names)[0]}")
    
    return "|".join(parts) if parts else str(uuid.uuid4())


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
    
    # UnifiedRecord has fields
    if hasattr(record, 'fields'):
        for field_path, field_value in record.fields.items():
            if isinstance(field_value.value, str):
                fields[field_path.lower()] = field_value.value
    elif isinstance(record, dict):
        for k, v in record.items():
            if isinstance(v, str):
                fields[k.lower()] = v
    
    return fields


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


def extract_name_from_fields(fields: Dict[str, str]) -> Optional[str]:
    """Extract patient name from fields dict."""
    for field_path, value in fields.items():
        field_lower = field_path.lower()
        if any(k in field_lower for k in ['patient_name', 'patient name', 'name', 'naam']):
            if isinstance(value, str):
                return value
    return None


def normalize_phone(phone: str) -> str:
    """Normalize phone number to 10-digit format."""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', phone)
    if clean := digits:
        if clean.startswith('91') and len(clean) == 12:
            clean = clean[2:]
        elif clean.startswith('0') and len(clean) == 11:
            clean = clean[1:]
        if len(clean) == 10 and clean[0] in '6789':
            return clean
    return ""


def normalize_identifier(value: str) -> str:
    """Normalize identifier for comparison."""
    if not value:
        return ""
    return re.sub(r'[\s\-\.]', '', value).lower()