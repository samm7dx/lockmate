"""
LOCKMATE — Pseudonym Generation and Management

Implements stable HMAC-based pseudonym generation using RAKSHA_SECRET.
Supports domain-separated HMAC for pseudonyms and date shifts.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from typing import Optional, Dict, List, Any

from ..contracts import generate_pseudonym_format, derive_date_shift
from ..utils.logging import get_logger_adapter

logger = get_logger_adapter("linkage.pseudonym")


class PseudonymManager:
    """
    Manages pseudonym generation and mapping for patient clusters.
    
    Ensures stable pseudonyms across runs with the same RAKSHA_SECRET.
    """
    
    def __init__(self, secret: bytes):
        """
        Initialize pseudonym manager.
        
        Args:
            secret: RAKSHA_SECRET bytes (>=32 bytes)
        """
        if len(secret) < 32:
            raise ValueError("Secret must be at least 32 bytes")
        self.secret = secret
        self._pseudonym_cache: Dict[str, str] = {}  # canonical_identity -> pseudonym
        self._cluster_map: Dict[str, str] = {}  # cluster_id -> pseudonym
    
    def get_pseudonym(self, canonical_identity: str) -> str:
        """
        Get or generate pseudonym for a canonical identity.
        
        Uses HMAC-SHA256 with domain separation for stable pseudonyms.
        
        Args:
            canonical_identity: Canonical identity string from derive_canonical_identity
            
        Returns:
            Pseudonym in PSN-XXXXXXXX format
        """
        if canonical_identity in self._pseudonym_cache:
            return self._pseudonym_cache[canonical_identity]
        
        pseudonym = generate_pseudonym_format(canonical_identity, self.secret)
        self._pseudonym_cache[canonical_identity] = pseudonym
        return pseudonym
    
    def get_pseudonym_for_cluster(self, cluster: Any) -> Optional[str]:
        """
        Get pseudonym for a cluster.
        
        Args:
            cluster: PatientCluster object
            
        Returns:
            Pseudonym string or None if cluster not confident
        """
        # Check cache first
        if hasattr(cluster, 'cluster_id') and cluster.cluster_id in self._cluster_map:
            return self._cluster_map[cluster.cluster_id]
        
        if not hasattr(cluster, 'is_confident') or not cluster.is_confident:
            return None
        
        if not cluster.canonical_identity:
            logger.warning("cluster_missing_canonical_identity", cluster_id=getattr(cluster, 'cluster_id', 'unknown'))
            return None
        
        pseudonym = self.get_pseudonym(cluster.canonical_identity)
        if hasattr(cluster, 'cluster_id'):
            self._cluster_map[cluster.cluster_id] = pseudonym
        return pseudonym
    
    def assign_pseudonyms(self, clusters: List[Any]) -> Dict[str, str]:
        """
        Assign pseudonyms to all confident clusters.
        
        Args:
            clusters: List of PatientCluster objects
            
        Returns:
            Dict mapping cluster_id -> pseudonym
        """
        results = {}
        for cluster in clusters:
            pseudonym = self.get_pseudonym_for_cluster(cluster)
            if pseudonym and hasattr(cluster, 'cluster_id'):
                cluster.pseudonym = pseudonym
                self._cluster_map[cluster.cluster_id] = pseudonym
                results[cluster.cluster_id] = pseudonym
        return results
    
    def get_date_shift(self, pseudonym: str) -> int:
        """
        Derive date shift for a pseudonym.
        
        Returns:
            Date shift in days [-365, +365]
        """
        return derive_date_shift(pseudonym, self.secret)
    
    def clear_cache(self) -> None:
        """Clear internal caches."""
        self._pseudonym_cache.clear()
        self._cluster_map.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "pseudonym_cache_size": len(self._pseudonym_cache),
            "cluster_map_size": len(self._cluster_map),
        }


def generate_pseudonym(canonical_identity: str, secret: bytes) -> str:
    """
    Generate stable pseudonym for a canonical identity.
    
    Uses the same algorithm as contracts.generate_pseudonym_format
    but as a standalone function for convenience.
    """
    from ..contracts import generate_pseudonym_format
    return generate_pseudonym_format(canonical_identity, secret)


def derive_canonical_identity(records: List[Any]) -> str:
    """
    Derive canonical identity from a list of records.
    
    Uses the strongest available identifiers to create a stable
    representation of the patient's identity.
    """
    from .clustering import derive_canonical_identity as _derive
    return _derive(records)


class PseudonymInserter:
    """
    Inserts pseudonyms into sanitized records and records.jsonl.
    """
    
    def __init__(self, pseudonym_manager: PseudonymManager):
        self.manager = pseudonym_manager
    
    def insert_pseudonyms(
        self,
        clusters: List[Any],
        sanitized_records: Dict[str, List[Any]],
        records_jsonl_path: Optional[str] = None
    ) -> None:
        """
        Insert pseudonyms into sanitized records and records.jsonl.
        
        Args:
            clusters: List of PatientCluster objects
            sanitized_records: Dict of file_sha256 -> List[SanitizedRecord]
            records_jsonl_path: Optional path to records.jsonl for updating
        """
        # Build record_id -> pseudonym mapping
        record_pseudonyms = {}
        for cluster in clusters:
            if not hasattr(cluster, 'is_confident') or not cluster.is_confident:
                continue
            if not cluster.pseudonym:
                continue
            for record in cluster.records:
                # record is SanitizedRecord, need to access record.record.record_id
                if hasattr(record, 'record') and hasattr(record.record, 'record_id'):
                    record_pseudonyms[record.record.record_id] = cluster.pseudonym
                elif hasattr(record, 'record_id'):
                    record_pseudonyms[record.record_id] = cluster.pseudonym
        
        # Insert into sanitized records
        for file_sha256, records_list in sanitized_records.items():
            for sr in records_list:
                # sr is SanitizedRecord, access sr.record.record_id
                if hasattr(sr, 'record') and hasattr(sr.record, 'record_id'):
                    rid = sr.record.record_id
                elif hasattr(sr, 'record_id'):
                    rid = sr.record_id
                else:
                    continue
                if rid in record_pseudonyms:
                    sr.pseudonym = record_pseudonyms[rid]
        
        # Update records.jsonl if path provided
        if records_jsonl_path:
            self._update_records_jsonl(records_jsonl_path, record_pseudonyms)
    
    def _update_records_jsonl(self, jsonl_path: str, record_pseudonyms: Dict[str, str]) -> None:
        """Update records.jsonl with pseudonyms."""
        import json
        from pathlib import Path
        
        lines = []
        if Path(jsonl_path).exists():
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        record_id = entry.get('loc', '').split(':')[-1] if ':' in entry.get('loc', '') else entry.get('loc', '')
                        # The records.jsonl uses location as key, not record_id
                        # We need to match by file and location
                        lines.append(entry)
        
        # For now, records.jsonl is generated fresh in the pipeline
        # This method would be used for updates
        pass


def insert_pseudonyms_into_sanitized(
    clusters: List[Any],
    sanitized_records: Dict[str, List[Any]],
    secret: bytes
) -> None:
    """
    Convenience function to insert pseudonyms into sanitized records.
    
    Args:
        clusters: List of PatientCluster objects
        sanitized_records: Dict of file_sha256 -> List[SanitizedRecord]
        secret: RAKSHA_SECRET bytes
    """
    manager = PseudonymManager(secret)
    manager.assign_pseudonyms(clusters)
    
    inserter = PseudonymInserter(manager)
    inserter.insert_pseudonyms(clusters, sanitized_records)


def generate_pseudonym_from_canonical(canonical_identity: str, secret: bytes) -> str:
    """Generate pseudonym from canonical identity using HMAC."""
    from ..contracts import generate_pseudonym_format
    return generate_pseudonym_format(canonical_identity, secret)