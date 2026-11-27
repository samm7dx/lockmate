"""
LOCKMATE — Phase 8: Privacy Attack Simulator

Creates a local experimental attack framework inspired by the organizer's ATTACKS.md.
Tests:
- Direct identifier matching
- Voter-list-style linkage
- Quasi-identifier combinations
- Rare disease profiles
- Known visit dates
- Length-of-stay clues
- Pseudonym inversion attempts
- Cross-release linkage

Uses synthetic attacker knowledge. Reports attack success rates and limitations.
"""

from __future__ import annotations

import logging
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum

from ..utils.logging import get_logger

logger = get_logger("evaluation.attack_simulator")


class AttackType(Enum):
    """Types of privacy attacks simulated."""
    DIRECT_IDENTIFIER = "direct_identifier"
    VOTER_LIST_LINKAGE = "voter_list_linkage"
    QUASI_IDENTIFIER = "quasi_identifier"
    RARE_DISEASE = "rare_disease"
    KNOWN_VISIT_DATE = "known_visit_date"
    LENGTH_OF_STAY = "length_of_stay"
    PSEUDONYM_INVERSION = "pseudonym_inversion"
    CROSS_RELEASE = "cross_release"


@dataclass
class AttackConfig:
    """Configuration for attack simulation."""
    # Attacker knowledge
    known_identifiers: Dict[str, Set[str]] = field(default_factory=dict)  # type -> values
    known_quasi_identifiers: Dict[str, Any] = field(default_factory=dict)
    known_visit_dates: List[date] = field(default_factory=list)
    known_hospitals: Set[str] = field(default_factory=set)
    known_diagnoses: Set[str] = field(default_factory=set)
    
    # Attack parameters
    max_linkage_distance: float = 0.8
    min_group_size: int = 1  # For quasi-identifier attacks
    
    # Target population
    target_patients: List[str] = field(default_factory=list)  # Patient IDs to attack


@dataclass
class AttackResult:
    """Result of a single attack simulation."""
    attack_type: AttackType
    target_count: int
    successful_matches: int
    ambiguous_matches: int
    protected_targets: int
    attack_success_rate: float
    details: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)


@dataclass
class SyntheticAttackerKnowledge:
    """Synthetic knowledge the attacker might have."""
    # Direct identifiers (from data breaches, etc.)
    aadhaar_db: Dict[str, str] = field(default_factory=dict)  # patient_id -> aadhaar
    phone_db: Dict[str, str] = field(default_factory=dict)
    pan_db: Dict[str, str] = field(default_factory=dict)
    
    # Voter list style: name + address + age
    voter_records: List[Dict[str, Any]] = field(default_factory=list)
    
    # Known visit information
    known_visits: List[Dict[str, Any]] = field(default_factory=list)  # patient_id, hospital, date, diagnosis
    
    # Rare disease registry
    rare_disease_patients: Dict[str, List[str]] = field(default_factory=dict)  # diagnosis -> patient_ids
    
    # Pseudonym mapping (if leaked)
    pseudonym_map: Dict[str, str] = field(default_factory=dict)  # pseudonym -> patient_id


class PrivacyAttackSimulator:
    """
    Simulates privacy attacks on LOCKMATE output.
    
    Uses synthetic attacker knowledge to evaluate re-identification risk.
    This is NOT the organizer's hidden attacker - it's a local experimental framework.
    """
    
    def __init__(
        self, 
        sanitized_records: List[Dict[str, Any]],
        attacker_knowledge: SyntheticAttackerKnowledge,
        config: Optional[AttackConfig] = None
    ):
        """
        Initialize attack simulator.
        
        Args:
            sanitized_records: Output records from LOCKMATE (PII-free)
            attacker_knowledge: Synthetic attacker knowledge base
            config: Attack configuration
        """
        self.records = sanitized_records
        self.attacker = attacker_knowledge
        self.config = config or AttackConfig()
        self.results: List[AttackResult] = []
        
        # Build indexes for efficient lookup
        self._build_indexes()
    
    def _build_indexes(self):
        """Build lookup indexes for attacks."""
        self.by_pseudonym = {r.get("patient"): r for r in self.records if r.get("patient")}
        self.by_hospital = defaultdict(list)
        self.by_diagnosis = defaultdict(list)
        self.by_age_band = defaultdict(list)
        self.by_district = defaultdict(list)
        
        for record in self.records:
            # These would be in the sanitized structured fields
            hospital = record.get("hospital")
            if hospital:
                self.by_hospital[hospital].append(record)
            
            # Note: In real sanitized output, these would be generalized
            # This simulates what an attacker could infer
    
    def run_all_attacks(self) -> List[AttackResult]:
        """Run all configured attack simulations."""
        self.results = []
        
        # 1. Direct identifier matching
        self.results.append(self._attack_direct_identifier())
        
        # 2. Voter-list-style linkage
        self.results.append(self._attack_voter_list_linkage())
        
        # 3. Quasi-identifier combination
        self.results.append(self._attack_quasi_identifier())
        
        # 4. Rare disease profile
        self.results.append(self._attack_rare_disease())
        
        # 5. Known visit date
        self.results.append(self._attack_known_visit_date())
        
        # 6. Length of stay
        self.results.append(self._attack_length_of_stay())
        
        # 7. Pseudonym inversion
        self.results.append(self._attack_pseudonym_inversion())
        
        # 8. Cross-release linkage
        self.results.append(self._attack_cross_release())
        
        logger.info("attack_simulation_complete", 
                   total_attacks=len(self.results),
                   total_targets=sum(r.target_count for r in self.results))
        
        return self.results
    
    def _attack_direct_identifier(self) -> AttackResult:
        """
        Attack: Direct identifier matching.
        
        Attacker has Aadhaar/phone/PAN database and tries to match
        against any residual identifiers in output.
        """
        # In properly sanitized output, there should be NO direct identifiers
        # This attack should always fail if sanitization works
        
        successful = 0
        ambiguous = 0
        
        # Check if any direct identifiers leaked
        for record in self.records:
            # Check all fields for potential direct identifier leakage
            record_str = str(record)
            
            # Check against attacker's Aadhaar database
            for patient_id, aadhaar in self.attacker.aadhaar_db.items():
                if aadhaar.replace(" ", "") in record_str.replace(" ", ""):
                    successful += 1
                    break
            
            # Check phone
            for patient_id, phone in self.attacker.phone_db.items():
                if phone.replace(" ", "").replace("+91", "") in record_str.replace(" ", "").replace("+91", ""):
                    successful += 1
                    break
            
            # Check PAN
            for patient_id, pan in self.attacker.pan_db.items():
                if pan in record_str:
                    successful += 1
                    break
        
        target_count = len(self.attacker.aadhaar_db) + len(self.attacker.phone_db) + len(self.attacker.pan_db)
        protected = target_count - successful
        
        return AttackResult(
            attack_type=AttackType.DIRECT_IDENTIFIER,
            target_count=target_count,
            successful_matches=successful,
            ambiguous_matches=ambiguous,
            protected_targets=protected,
            attack_success_rate=successful / target_count if target_count > 0 else 0.0,
            details={
                "aadhaar_targets": len(self.attacker.aadhaar_db),
                "phone_targets": len(self.attacker.phone_db),
                "pan_targets": len(self.attacker.pan_db),
            },
            limitations=[
                "Assumes attacker has complete identifier database",
                "Real attackers may have partial/noisy data",
                "Does not account for identifier format variations"
            ]
        )
    
    def _attack_voter_list_linkage(self) -> AttackResult:
        """
        Attack: Voter-list-style linkage.
        
        Attacker has name + address + age from voter rolls and tries
        to link to sanitized records using quasi-identifiers.
        """
        successful = 0
        ambiguous = 0
        
        for voter in self.attacker.voter_records:
            voter_name = voter.get("name", "").lower()
            voter_age = voter.get("age")
            voter_district = voter.get("district", "").lower()
            voter_state = voter.get("state", "").lower()
            
            # Find matching records in sanitized output
            # (In real output, name would be pseudonymized, but age_band and district might remain)
            matches = []
            
            for record in self.records:
                # Check age band match
                record_age_band = record.get("age_band")
                if record_age_band and voter_age:
                    # Parse age band like "45-49"
                    if "-" in record_age_band:
                        min_age, max_age = map(int, record_age_band.split("-"))
                        if min_age <= voter_age <= max_age:
                            matches.append(record)
                
                # Check district match (if not generalized to state)
                record_district = record.get("district", "").lower()
                if record_district and record_district == voter_district:
                    if record not in matches:
                        matches.append(record)
            
            if len(matches) == 1:
                successful += 1
            elif len(matches) > 1:
                ambiguous += 1
        
        target_count = len(self.attacker.voter_records)
        protected = target_count - successful - ambiguous
        
        return AttackResult(
            attack_type=AttackType.VOTER_LIST_LINKAGE,
            target_count=target_count,
            successful_matches=successful,
            ambiguous_matches=ambiguous,
            protected_targets=protected,
            attack_success_rate=successful / target_count if target_count > 0 else 0.0,
            details={
                "voter_records": target_count,
                "unique_matches": successful,
                "ambiguous_matches": ambiguous,
            },
            limitations=[
                "Assumes voter list has accurate age/address",
                "Real voter lists have errors and outdated info",
                "Name matching not possible (pseudonymized)",
                "Age band and district may be generalized"
            ]
        )
    
    def _attack_quasi_identifier(self) -> AttackResult:
        """
        Attack: Quasi-identifier combination linkage.
        
        Attacker combines multiple quasi-identifiers (age_band, district, diagnosis, etc.)
        to uniquely identify individuals.
        """
        successful = 0
        ambiguous = 0
        
        # Build combination -> records mapping
        combo_map = defaultdict(list)
        
        for record in self.records:
            # Extract quasi-identifiers that might be in sanitized output
            qi = {}
            qi["age_band"] = record.get("age_band", "unknown")
            qi["district"] = record.get("district", "unknown")
            qi["diagnosis_category"] = record.get("diagnosis_category", "unknown")
            qi["hospital"] = record.get("hospital", "unknown")
            qi["admission_month"] = record.get("admission_month", "unknown")
            
            combo_key = tuple(sorted(qi.items()))
            combo_map[combo_key].append(record)
        
        # Attacker tries each target's known quasi-identifiers
        for target_id in self.config.target_patients:
            # Attacker knows target's quasi-identifiers
            known_qi = self.config.known_quasi_identifiers.get(target_id, {})
            
            if not known_qi:
                continue
            
            # Find matching combinations
            matches = []
            for combo_key, records in combo_map.items():
                combo_dict = dict(combo_key)
                match = True
                for k, v in known_qi.items():
                    if combo_dict.get(k) != v:
                        match = False
                        break
                if match:
                    matches.extend(records)
            
            if len(matches) == 1:
                successful += 1
            elif len(matches) > 1:
                ambiguous += 1
        
        target_count = len(self.config.target_patients)
        protected = target_count - successful - ambiguous
        
        return AttackResult(
            attack_type=AttackType.QUASI_IDENTIFIER,
            target_count=target_count,
            successful_matches=successful,
            ambiguous_matches=ambiguous,
            protected_targets=protected,
            attack_success_rate=successful / target_count if target_count > 0 else 0.0,
            details={
                "unique_combinations": len(combo_map),
                "min_group_size": min(len(r) for r in combo_map.values()) if combo_map else 0,
            },
            limitations=[
                "Assumes attacker knows exact quasi-identifier values",
                "Real quasi-identifiers may be generalized/suppressed",
                "Does not model probabilistic linkage"
            ]
        )
    
    def _attack_rare_disease(self) -> AttackResult:
        """
        Attack: Rare disease profile linkage.
        
        Patients with rare diagnoses are easily identifiable even with
        generalized quasi-identifiers.
        """
        successful = 0
        ambiguous = 0
        
        for diagnosis, patient_ids in self.attacker.rare_disease_patients.items():
            # Find records with this diagnosis category
            matching_records = []
            for record in self.records:
                record_diag = record.get("diagnosis_category", "").lower()
                if diagnosis.lower() in record_diag or record_diag in diagnosis.lower():
                    matching_records.append(record)
            
            # If only a few records have this rare diagnosis, they're identifiable
            if len(matching_records) <= 3:
                # Each patient with this diagnosis is identifiable
                successful += len(patient_ids)
            elif len(matching_records) <= 10:
                ambiguous += len(patient_ids)
            else:
                # Too many, not identifiable
                pass
        
        target_count = sum(len(ids) for ids in self.attacker.rare_disease_patients.values())
        protected = target_count - successful - ambiguous
        
        return AttackResult(
            attack_type=AttackType.RARE_DISEASE,
            target_count=target_count,
            successful_matches=successful,
            ambiguous_matches=ambiguous,
            protected_targets=protected,
            attack_success_rate=successful / target_count if target_count > 0 else 0.0,
            details={
                "rare_diagnoses": len(self.attacker.rare_disease_patients),
                "target_patients": target_count,
            },
            limitations=[
                "Assumes diagnosis category not fully suppressed",
                "Real rare diseases may be categorized more broadly",
                "Attacker needs access to disease registry"
            ]
        )
    
    def _attack_known_visit_date(self) -> AttackResult:
        """
        Attack: Known visit date linkage.
        
        Attacker knows target visited a hospital on a specific date
        and tries to find matching admission/discharge dates.
        """
        successful = 0
        ambiguous = 0
        
        for visit in self.attacker.known_visits:
            target_id = visit.get("patient_id")
            known_date = visit.get("date")
            known_hospital = visit.get("hospital")
            
            if not known_date:
                continue
            
            # Find records matching date and hospital
            matches = []
            for record in self.records:
                record_hospital = record.get("hospital")
                record_admission = record.get("admission_date")
                record_discharge = record.get("discharge_date")
                
                # Check hospital match
                if known_hospital and record_hospital != known_hospital:
                    continue
                
                # Check date match (admission or discharge)
                date_match = False
                if record_admission == known_date.isoformat():
                    date_match = True
                if record_discharge == known_date.isoformat():
                    date_match = True
                
                # Also check if date falls within stay
                if record_admission and record_discharge:
                    try:
                        adm = datetime.fromisoformat(record_admission).date()
                        dis = datetime.fromisoformat(record_discharge).date()
                        if adm <= known_date <= dis:
                            date_match = True
                    except Exception:
                        pass
                
                if date_match:
                    matches.append(record)
            
            if len(matches) == 1:
                successful += 1
            elif len(matches) > 1:
                ambiguous += 1
        
        target_count = len(self.attacker.known_visits)
        protected = target_count - successful - ambiguous
        
        return AttackResult(
            attack_type=AttackType.KNOWN_VISIT_DATE,
            target_count=target_count,
            successful_matches=successful,
            ambiguous_matches=ambiguous,
            protected_targets=protected,
            attack_success_rate=successful / target_count if target_count > 0 else 0.0,
            details={
                "known_visits": target_count,
                "date_shifting_protection": "Date shifting should prevent this",
            },
            limitations=[
                "Date shifting (±365 days) should defeat this attack",
                "Attacker needs precise date knowledge",
                "Interval preservation may leak relative timing"
            ]
        )
    
    def _attack_length_of_stay(self) -> AttackResult:
        """
        Attack: Length of stay clues.
        
        Unusual lengths of stay (very short or very long) combined
        with other quasi-identifiers can identify patients.
        """
        successful = 0
        ambiguous = 0
        
        # Calculate LOS for each record
        los_map = defaultdict(list)
        for record in self.records:
            adm = record.get("admission_date")
            dis = record.get("discharge_date")
            if adm and dis:
                try:
                    adm_dt = datetime.fromisoformat(adm)
                    dis_dt = datetime.fromisoformat(dis)
                    los = (dis_dt - adm_dt).days
                    # Bucket LOS
                    if los <= 1:
                        bucket = "0-1"
                    elif los <= 3:
                        bucket = "2-3"
                    elif los <= 7:
                        bucket = "4-7"
                    elif los <= 14:
                        bucket = "8-14"
                    else:
                        bucket = "15+"
                    los_map[bucket].append(record)
                except Exception:
                    pass
        
        # Attacker knows target had unusual LOS
        # For simulation, check rare LOS buckets
        for bucket, records in los_map.items():
            if len(records) <= 2:  # Very rare LOS
                # Attacker could identify these patients
                successful += len(records)
            elif len(records) <= 5:
                ambiguous += len(records)
        
        target_count = len(self.records)
        protected = target_count - successful - ambiguous
        
        return AttackResult(
            attack_type=AttackType.LENGTH_OF_STAY,
            target_count=target_count,
            successful_matches=successful,
            ambiguous_matches=ambiguous,
            protected_targets=protected,
            attack_success_rate=successful / target_count if target_count > 0 else 0.0,
            details={
                "los_distribution": {k: len(v) for k, v in los_map.items()},
            },
            limitations=[
                "LOS is preserved (interval preservation requirement)",
                "Generalization of LOS buckets would reduce risk",
                "Rare LOS + other QIs = higher risk"
            ]
        )
    
    def _attack_pseudonym_inversion(self) -> AttackResult:
        """
        Attack: Pseudonym inversion.
        
        Attacker tries to reverse-engineer pseudonyms to recover
        original identifiers or link across releases.
        """
        successful = 0
        ambiguous = 0
        
        # Check if pseudonym format reveals information
        # PSN-XXXXXXXX format should not be invertible without secret
        
        # If attacker has leaked pseudonym map
        if self.attacker.pseudonym_map:
            for pseudo, patient_id in self.attacker.pseudonym_map.items():
                # Check if pseudonym appears in output
                for record in self.records:
                    if record.get("patient") == pseudo:
                        successful += 1
                        break
        
        # Without leaked map, pseudonym should be cryptographically secure
        # This attack should always fail with proper implementation
        
        target_count = len(self.attacker.pseudonym_map)
        protected = target_count - successful
        
        return AttackResult(
            attack_type=AttackType.PSEUDONYM_INVERSION,
            target_count=target_count,
            successful_matches=successful,
            ambiguous_matches=ambiguous,
            protected_targets=protected,
            attack_success_rate=successful / target_count if target_count > 0 else 0.0,
            details={
                "pseudonym_format": "PSN-XXXXXXXX (base32, 128-bit HMAC)",
                "leaked_mappings": len(self.attacker.pseudonym_map),
            },
            limitations=[
                "Requires leaked pseudonym map or secret compromise",
                "HMAC-SHA256 with domain separation is cryptographically secure",
                "No known inversion attacks on proper implementation"
            ]
        )
    
    def _attack_cross_release(self) -> AttackResult:
        """
        Attack: Cross-release linkage.
        
        Attacker compares multiple releases of sanitized data to
        link records across releases (e.g., monthly updates).
        """
        successful = 0
        ambiguous = 0
        
        # This would require multiple releases to simulate properly
        # For now, simulate by checking if same pseudonym appears consistently
        # (which it should for same patient)
        
        # In a real attack, attacker would look for stable quasi-identifier
        # combinations across releases
        
        # For simulation, we note this is a theoretical attack
        target_count = len(self.config.target_patients)
        protected = target_count
        
        return AttackResult(
            attack_type=AttackType.CROSS_RELEASE,
            target_count=target_count,
            successful_matches=successful,
            ambiguous_matches=ambiguous,
            protected_targets=protected,
            attack_success_rate=0.0,
            details={
                "note": "Cross-release attack requires multiple releases",
                "mitigation": "Consistent pseudonyms + date shifting + generalization"
            },
            limitations=[
                "Not simulated without multiple releases",
                "Real attack would track pseudonym stability",
                "Date shifting should vary per release if re-run"
            ]
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get attack simulation summary."""
        total_targets = sum(r.target_count for r in self.results)
        total_successful = sum(r.successful_matches for r in self.results)
        total_ambiguous = sum(r.ambiguous_matches for r in self.results)
        total_protected = sum(r.protected_targets for r in self.results)
        
        return {
            "total_attacks": len(self.results),
            "total_targets": total_targets,
            "successful_matches": total_successful,
            "ambiguous_matches": total_ambiguous,
            "protected_targets": total_protected,
            "overall_success_rate": total_successful / total_targets if total_targets > 0 else 0.0,
            "attack_details": [
                {
                    "type": r.attack_type.value,
                    "targets": r.target_count,
                    "successful": r.successful_matches,
                    "ambiguous": r.ambiguous_matches,
                    "protected": r.protected_targets,
                    "success_rate": r.attack_success_rate,
                    "limitations": r.limitations
                }
                for r in self.results
            ]
        }


def create_synthetic_attacker_knowledge(
    num_patients: int = 100,
    identifier_leak_rate: float = 0.1,
    voter_list_coverage: float = 0.5,
    known_visit_rate: float = 0.2,
    rare_disease_rate: float = 0.05
) -> SyntheticAttackerKnowledge:
    """
    Create synthetic attacker knowledge for testing.
    
    All data is synthetic - no real PII.
    """
    import random
    import string
    
    knowledge = SyntheticAttackerKnowledge()
    
    # Generate synthetic patient pool
    patients = [f"PAT{i:06d}" for i in range(num_patients)]
    
    # Identifier database (partial leak)
    for patient_id in patients:
        if random.random() < identifier_leak_rate:
            # Aadhaar
            digits = ''.join(random.choices(string.digits, k=12))
            knowledge.aadhaar_db[patient_id] = f"{digits[:4]} {digits[4:8]} {digits[8:]}"
        
        if random.random() < identifier_leak_rate:
            # Phone
            knowledge.phone_db[patient_id] = f"+91 {random.randint(6000000000, 9999999999)}"
        
        if random.random() < identifier_leak_rate:
            # PAN
            letters = ''.join(random.choices(string.ascii_uppercase, k=5))
            digits = ''.join(random.choices(string.digits, k=4))
            check = random.choice(string.ascii_uppercase)
            knowledge.pan_db[patient_id] = f"{letters}{digits}{check}"
    
    # Voter list records
    for patient_id in patients:
        if random.random() < voter_list_coverage:
            knowledge.voter_records.append({
                "patient_id": patient_id,
                "name": f"Voter {patient_id}",
                "age": random.randint(18, 90),
                "district": random.choice(["Mumbai", "Delhi", "Bangalore", "Chennai"]),
                "state": random.choice(["Maharashtra", "Delhi", "Karnataka", "Tamil Nadu"])
            })
    
    # Known visits
    for patient_id in patients:
        if random.random() < known_visit_rate:
            days_ago = random.randint(1, 365)
            visit_date = date.today() - timedelta(days=days_ago)
            knowledge.known_visits.append({
                "patient_id": patient_id,
                "date": visit_date,
                "hospital": f"Hospital {random.randint(1, 10)}",
                "diagnosis": random.choice(["Flu", "Diabetes", "Hypertension"])
            })
    
    # Rare disease registry
    rare_diseases = ["Gaucher Disease", "Huntington Disease", "Wilson Disease"]
    for disease in rare_diseases:
        affected = random.sample(patients, int(num_patients * rare_disease_rate))
        knowledge.rare_disease_patients[disease] = affected
    
    # Pseudonym map (simulated leak)
    for patient_id in random.sample(patients, int(num_patients * 0.05)):
        knowledge.pseudonym_map[f"PSN-{patient_id.lower()[:8]}"] = patient_id
    
    return knowledge