"""
LOCKMATE — Phase 8: Synthetic Adversarial Test Data Generator

Generates fabricated records containing:
- English names, Hindi names, Hinglish, transliteration variations
- Different name orders, relative names, similar names for different people
- Different identifier formats, hospital-specific MRNs
- Addresses in multiple formats, embedded metadata, Base64 attachments
- Unusual date formats, malformed structured files

All generated data is synthetic - no real PII.
"""

from __future__ import annotations

import random
import string
import base64
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterator, Tuple
from enum import Enum

from ..utils.logging import get_logger

logger = get_logger("evaluation.synthetic_generator")


class NameScript(Enum):
    """Script/type of name."""
    ENGLISH = "english"
    HINDI = "hindi"
    HINGLISH = "hinglish"
    TRANSLITERATED = "transliterated"


@dataclass
class SyntheticConfig:
    """Configuration for synthetic data generation."""
    # Name generation
    english_first_names: List[str] = field(default_factory=lambda: [
        "Rajesh", "Priya", "Amit", "Sunita", "Vikram", "Anjali", "Rahul", "Pooja",
        "Sanjay", "Meera", "Arjun", "Kavita", "Manoj", "Shilpa", "Deepak", "Neha",
        "Ravi", "Sonia", "Ajay", "Ritu", "Kiran", "Geeta", "Suresh", "Lakshmi"
    ])
    hindi_first_names: List[str] = field(default_factory=lambda: [
        "राजेश", "प्रिया", "अमित", "सुनीता", "विक्रम", "अंजलि", "राहुल", "पूजा",
        "संजय", "मीरा", "अर्जुन", "कविता", "मनोज", "शिल्पा", "दीपक", "नेहा"
    ])
    surnames: List[str] = field(default_factory=lambda: [
        "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Agarwal", "Jain", "Shah",
        "Patel", "Reddy", "Nair", "Iyer", "Chopra", "Malhotra", "Kapoor", "Bhatia"
    ])
    hindi_surnames: List[str] = field(default_factory=lambda: [
        "शर्मा", "वर्मा", "गुप्ता", "सिंह", "कुमार", "अग्रवाल", "जैन", "शाह"
    ])
    
    # Identifier formats
    hospital_codes: List[str] = field(default_factory=lambda: ["HOSP", "MED", "CLINIC", "CARE", "HLTH"])
    
    # Address components
    streets: List[str] = field(default_factory=lambda: [
        "MG Road", "Gandhi Road", "Nehru Street", "Park Avenue", "Lake View Road",
        "Temple Road", "Market Street", "Station Road", "College Road", "Hospital Road"
    ])
    localities: List[str] = field(default_factory=lambda: [
        "Sector 12", "Phase 2", "Block A", "Extension", "Enclave", "Colony",
        "Nagar", "Vihar", "Puram", "Layout"
    ])
    villages: List[str] = field(default_factory=lambda: [
        "Rampur", "Shivpur", "Krishnapur", "Ganeshpur", "Laxmipur", "Sitapur"
    ])
    tehsils: List[str] = field(default_factory=lambda: [
        "Central", "North", "South", "East", "West", "Rural", "Urban"
    ])
    districts: List[str] = field(default_factory=lambda: [
        "Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Hyderabad",
        "Pune", "Ahmedabad", "Jaipur", "Lucknow", "Kanpur", "Nagpur"
    ])
    states: List[str] = field(default_factory=lambda: [
        "Maharashtra", "Delhi", "Karnataka", "Tamil Nadu", "West Bengal",
        "Telangana", "Gujarat", "Rajasthan", "Uttar Pradesh", "Madhya Pradesh"
    ])
    
    # Medical data
    diagnoses: List[str] = field(default_factory=lambda: [
        "Hypertension", "Type 2 Diabetes", "Acute Bronchitis", "Viral Fever",
        "Gastroenteritis", "Urinary Tract Infection", "Anemia", "Migraine",
        "Osteoarthritis", "Dengue Fever", "Malaria", "Typhoid", "COVID-19"
    ])
    drugs: List[str] = field(default_factory=lambda: [
        "Paracetamol", "Amoxicillin", "Metformin", "Amlodipine", "Omeprazole",
        "Azithromycin", "Ciprofloxacin", "Diclofenac", "Cetirizine", "Pantoprazole"
    ])
    lab_tests: List[str] = field(default_factory=lambda: [
        "CBC", "Blood Glucose", "Lipid Profile", "Liver Function Test",
        "Kidney Function Test", "HbA1c", "Thyroid Panel", "Vitamin D",
        "Urine Routine", "Chest X-Ray", "ECG", "Ultrasound Abdomen"
    ])
    
    # Rare diseases for attack simulation
    rare_diagnoses: List[str] = field(default_factory=lambda: [
        "Gaucher Disease", "Huntington Disease", "Wilson Disease",
        "Amyloidosis", "Sarcoidosis", "Wegener Granulomatosis",
        "Goodpasture Syndrome", "Alport Syndrome"
    ])
    
    # Generation control
    seed: Optional[int] = None
    locale_weights: Dict[str, float] = field(default_factory=lambda: {
        "english": 0.4, "hindi": 0.2, "hinglish": 0.2, "transliterated": 0.2
    })


@dataclass
class SyntheticRecord:
    """A single synthetic patient record."""
    patient_id: str
    name: str
    name_script: NameScript
    age: int
    gender: str
    phone: str
    aadhaar: str
    abha: str
    pan: str
    email: str
    address: str
    village: str
    tehsil: str
    district: str
    state: str
    pin_code: str
    hospital: str
    mrn: str
    admission_date: str
    discharge_date: str
    diagnosis: str
    drugs: List[str]
    lab_tests: List[str]
    doctor: str
    relative_name: str
    attachments: List[str]  # Base64 encoded
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "name": self.name,
            "name_script": self.name_script.value,
            "age": self.age,
            "gender": self.gender,
            "phone": self.phone,
            "aadhaar": self.aadhaar,
            "abha": self.abha,
            "pan": self.pan,
            "email": self.email,
            "address": self.address,
            "village": self.village,
            "tehsil": self.tehsil,
            "district": self.district,
            "state": self.state,
            "pin_code": self.pin_code,
            "hospital": self.hospital,
            "mrn": self.mrn,
            "admission_date": self.admission_date,
            "discharge_date": self.discharge_date,
            "diagnosis": self.diagnosis,
            "drugs": self.drugs,
            "lab_tests": self.lab_tests,
            "doctor": self.doctor,
            "relative_name": self.relative_name,
            "attachments": self.attachments,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def to_csv_row(self) -> List[str]:
        return [
            self.patient_id, self.name, self.name_script.value, str(self.age),
            self.gender, self.phone, self.aadhaar, self.abha, self.pan, self.email,
            self.address, self.village, self.tehsil, self.district, self.state,
            self.pin_code, self.hospital, self.mrn, self.admission_date,
            self.discharge_date, self.diagnosis, ";".join(self.drugs),
            ";".join(self.lab_tests), self.doctor, self.relative_name,
            ";".join(self.attachments), json.dumps(self.metadata)
        ]


class SyntheticDataGenerator:
    """
    Generates synthetic adversarial test data for LOCKMATE evaluation.
    
    Creates realistic but entirely fictional patient records with
    various formats, scripts, and edge cases to stress-test the pipeline.
    """
    
    def __init__(self, config: Optional[SyntheticConfig] = None):
        self.config = config or SyntheticConfig()
        
        if self.config.seed is not None:
            random.seed(self.config.seed)
        
        # Pre-compute some values for consistency
        self._name_cache: Dict[str, str] = {}
        self._address_cache: Dict[str, str] = {}
    
    def generate_patient_id(self) -> str:
        """Generate a synthetic patient ID."""
        return f"SYN{random.randint(100000, 999999)}"
    
    def generate_name(self, script: Optional[NameScript] = None) -> Tuple[str, NameScript]:
        """Generate a name in the specified script."""
        if script is None:
            # Weighted random selection
            scripts = list(self.config.locale_weights.keys())
            weights = list(self.config.locale_weights.values())
            script = NameScript(random.choices(scripts, weights=weights)[0])
        
        if script == NameScript.ENGLISH:
            first = random.choice(self.config.english_first_names)
            last = random.choice(self.config.surnames)
            # Random name order
            if random.random() < 0.3:
                return f"{last} {first}", script
            return f"{first} {last}", script
        
        elif script == NameScript.HINDI:
            first = random.choice(self.config.hindi_first_names)
            last = random.choice(self.config.hindi_surnames)
            return f"{first} {last}", script
        
        elif script == NameScript.HINGLISH:
            # Mix of English and Hindi
            first = random.choice(self.config.english_first_names)
            last = random.choice(self.config.hindi_surnames)
            return f"{first} {last}", script
        
        elif script == NameScript.TRANSLITERATED:
            # Transliterated Hindi name
            hindi_first = random.choice(self.config.hindi_first_names)
            hindi_last = random.choice(self.config.hindi_surnames)
            # Simple transliteration mapping
            translit_map = {
                'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
                'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n',
                'ः': 'h', '़': '', '्': '', 'ऋ': 'ri', 'ॠ': 'ri',
                'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
                'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
                'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
                'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
                'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
                'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh',
                'ष': 'sh', 'स': 's', 'ह': 'h', 'क्ष': 'ksh', 'त्र': 'tr',
                'ज्ञ': 'gy', 'श्र': 'shr'
            }
            def transliterate(text):
                result = []
                for char in text:
                    result.append(translit_map.get(char, char))
                return ''.join(result)
            
            first = transliterate(hindi_first).capitalize()
            last = transliterate(hindi_last).capitalize()
            return f"{first} {last}", script
        
        return "Unknown Name", script
    
    def generate_phone(self) -> str:
        """Generate Indian phone number."""
        # +91 XXXXXXXXXX or XXXXXXXXXX
        if random.random() < 0.5:
            return f"+91 {random.randint(6000000000, 9999999999)}"
        return str(random.randint(6000000000, 9999999999))
    
    def generate_aadhaar(self) -> str:
        """Generate synthetic Aadhaar (12 digits with Verhoeff check)."""
        # Generate 11 random digits
        digits = [random.randint(0, 9) for _ in range(11)]
        # Simple checksum (not actual Verhoeff for synthetic)
        check = sum(digits) % 10
        digits.append(check)
        # Format with spaces
        return f"{''.join(map(str, digits[:4]))} {''.join(map(str, digits[4:8]))} {''.join(map(str, digits[8:]))}"
    
    def generate_abha(self) -> str:
        """Generate synthetic ABHA (14 digits)."""
        return ''.join(str(random.randint(0, 9)) for _ in range(14))
    
    def generate_pan(self) -> str:
        """Generate synthetic PAN (5 letters, 4 digits, 1 letter)."""
        letters = ''.join(random.choices(string.ascii_uppercase, k=5))
        digits = ''.join(random.choices(string.digits, k=4))
        check = random.choice(string.ascii_uppercase)
        return f"{letters}{digits}{check}"
    
    def generate_email(self, name: str) -> str:
        """Generate email from name."""
        clean_name = re.sub(r'[^a-zA-Z]', '', name.lower())
        domains = ["gmail.com", "yahoo.com", "outlook.com", "hospital.org", "clinic.in"]
        return f"{clean_name}{random.randint(1, 999)}@{random.choice(domains)}"
    
    def generate_address(self) -> Dict[str, str]:
        """Generate full address with components."""
        house_num = random.randint(1, 999)
        street = random.choice(self.config.streets)
        locality = random.choice(self.config.localities)
        village = random.choice(self.config.villages)
        tehsil = random.choice(self.config.tehsils)
        district = random.choice(self.config.districts)
        state = random.choice(self.config.states)
        pin = random.randint(110001, 999999)
        
        # Various address formats
        format_type = random.randint(1, 5)
        if format_type == 1:
            full = f"{house_num}, {street}, {locality}, {village}, {tehsil}, {district}, {state} - {pin}"
        elif format_type == 2:
            full = f"House No {house_num}, {street}, {locality}, {district} {pin}"
        elif format_type == 3:
            full = f"{house_num} {street}, {locality}, {village}, {district}, {state}"
        elif format_type == 4:
            # Hindi-style
            full = f"मकान नं {house_num}, {street}, {locality}, {village}, {tehsil}, {district}, {state} - {pin}"
        else:
            # Minimal
            full = f"{village}, {district}, {state}"
        
        return {
            "full": full,
            "house": str(house_num),
            "street": street,
            "locality": locality,
            "village": village,
            "tehsil": tehsil,
            "district": district,
            "state": state,
            "pin": str(pin)
        }
    
    def generate_hospital_mrn(self, hospital: str) -> str:
        """Generate hospital-specific MRN."""
        code = random.choice(self.config.hospital_codes)
        return f"{code}-{random.randint(100000, 999999)}"
    
    def generate_dates(self) -> Tuple[str, str]:
        """Generate admission and discharge dates."""
        # Random date in last 2 years
        days_ago = random.randint(1, 730)
        admission = date.today() - timedelta(days=days_ago)
        # Stay 1-30 days
        stay = random.randint(1, 30)
        discharge = admission + timedelta(days=stay)
        
        # Various date formats
        fmt = random.choice(["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d"])
        return admission.strftime(fmt), discharge.strftime(fmt)
    
    def generate_attachment(self) -> str:
        """Generate synthetic base64 attachment."""
        # Create fake binary content
        content = f"SYNTHETIC_ATTACHMENT_{random.randint(1000,9999)}".encode()
        # Add some random bytes
        content += bytes(random.randint(0, 255) for _ in range(random.randint(10, 100)))
        return base64.b64encode(content).decode()
    
    def generate_record(self) -> SyntheticRecord:
        """Generate a complete synthetic patient record."""
        patient_id = self.generate_patient_id()
        name, script = self.generate_name()
        age = random.randint(0, 95)
        gender = random.choice(["M", "F", "O"])
        phone = self.generate_phone()
        aadhaar = self.generate_aadhaar()
        abha = self.generate_abha()
        pan = self.generate_pan()
        email = self.generate_email(name)
        address_parts = self.generate_address()
        hospital = f"{random.choice(self.config.hospital_codes)} Hospital"
        mrn = self.generate_hospital_mrn(hospital)
        admission, discharge = self.generate_dates()
        diagnosis = random.choice(self.config.diagnoses + self.config.rare_diagnoses)
        drugs = random.sample(self.config.drugs, random.randint(1, 4))
        lab_tests = random.sample(self.config.lab_tests, random.randint(0, 3))
        doctor = f"Dr. {random.choice(self.config.english_first_names)} {random.choice(self.config.surnames)}"
        
        # Generate relative name (similar but different)
        rel_name, _ = self.generate_name(script)
        # Ensure it's different
        while rel_name == name:
            rel_name, _ = self.generate_name(script)
        
        attachments = [self.generate_attachment() for _ in range(random.randint(0, 2))]
        
        metadata = {
            "source": "synthetic_generator",
            "generated_at": datetime.utcnow().isoformat(),
            "record_version": 1
        }
        
        return SyntheticRecord(
            patient_id=patient_id,
            name=name,
            name_script=script,
            age=age,
            gender=gender,
            phone=phone,
            aadhaar=aadhaar,
            abha=abha,
            pan=pan,
            email=email,
            address=address_parts["full"],
            village=address_parts["village"],
            tehsil=address_parts["tehsil"],
            district=address_parts["district"],
            state=address_parts["state"],
            pin_code=address_parts["pin"],
            hospital=hospital,
            mrn=mrn,
            admission_date=admission,
            discharge_date=discharge,
            diagnosis=diagnosis,
            drugs=drugs,
            lab_tests=lab_tests,
            doctor=doctor,
            relative_name=rel_name,
            attachments=attachments,
            metadata=metadata
        )
    
    def generate_dataset(
        self, 
        count: int, 
        duplicate_rate: float = 0.1,
        similar_name_rate: float = 0.05
    ) -> List[SyntheticRecord]:
        """
        Generate a dataset with controlled duplicates and similar names.
        
        Args:
            count: Number of records to generate
            duplicate_rate: Fraction of records that are exact duplicates
            similar_name_rate: Fraction of records with similar names (different people)
            
        Returns:
            List of SyntheticRecord objects
        """
        records = []
        num_duplicates = int(count * duplicate_rate)
        num_similar = int(count * similar_name_rate)
        num_unique = count - num_duplicates - num_similar
        
        # Generate unique records
        for _ in range(num_unique):
            records.append(self.generate_record())
        
        # Add duplicates (same patient, different records)
        if num_duplicates > 0 and records:
            for _ in range(num_duplicates):
                base = random.choice(records)
                # Create new record with same identifiers but different clinical data
                dup = SyntheticRecord(
                    patient_id=base.patient_id,
                    name=base.name,
                    name_script=base.name_script,
                    age=base.age,
                    gender=base.gender,
                    phone=base.phone,
                    aadhaar=base.aadhaar,
                    abha=base.abha,
                    pan=base.pan,
                    email=base.email,
                    address=base.address,
                    village=base.village,
                    tehsil=base.tehsil,
                    district=base.district,
                    state=base.state,
                    pin_code=base.pin_code,
                    hospital=f"{random.choice(self.config.hospital_codes)} Hospital",
                    mrn=self.generate_hospital_mrn("DUP"),
                    admission_date=base.admission_date,
                    discharge_date=base.discharge_date,
                    diagnosis=random.choice(self.config.diagnoses),
                    drugs=random.sample(self.config.drugs, random.randint(1, 3)),
                    lab_tests=random.sample(self.config.lab_tests, random.randint(0, 2)),
                    doctor=f"Dr. {random.choice(self.config.english_first_names)} {random.choice(self.config.surnames)}",
                    relative_name=base.relative_name,
                    attachments=[],
                    metadata={**base.metadata, "duplicate_of": base.patient_id}
                )
                records.append(dup)
        
        # Add similar names (different people, similar names)
        if num_similar > 0 and records:
            for _ in range(num_similar):
                base = random.choice(records)
                # Modify name slightly
                name_parts = base.name.split()
                if len(name_parts) >= 2:
                    # Change one character
                    modified = list(name_parts[0])
                    if modified:
                        idx = random.randint(0, len(modified) - 1)
                        modified[idx] = random.choice(string.ascii_letters)
                    new_first = ''.join(modified)
                    new_name = f"{new_first} {name_parts[1]}"
                else:
                    new_name = base.name + random.choice(string.ascii_letters)
                
                sim = SyntheticRecord(
                    patient_id=self.generate_patient_id(),
                    name=new_name,
                    name_script=base.name_script,
                    age=random.randint(0, 95),
                    gender=random.choice(["M", "F", "O"]),
                    phone=self.generate_phone(),
                    aadhaar=self.generate_aadhaar(),
                    abha=self.generate_abha(),
                    pan=self.generate_pan(),
                    email=self.generate_email(new_name),
                    address=self.generate_address()["full"],
                    village=base.village,
                    tehsil=base.tehsil,
                    district=base.district,
                    state=base.state,
                    pin_code=base.pin_code,
                    hospital=f"{random.choice(self.config.hospital_codes)} Hospital",
                    mrn=self.generate_hospital_mrn("SIM"),
                    admission_date=self.generate_dates()[0],
                    discharge_date=self.generate_dates()[1],
                    diagnosis=random.choice(self.config.diagnoses),
                    drugs=random.sample(self.config.drugs, random.randint(1, 3)),
                    lab_tests=random.sample(self.config.lab_tests, random.randint(0, 2)),
                    doctor=f"Dr. {random.choice(self.config.english_first_names)} {random.choice(self.config.surnames)}",
                    relative_name=self.generate_name()[0],
                    attachments=[],
                    metadata={"similar_to": base.patient_id}
                )
                records.append(sim)
        
        random.shuffle(records)
        return records
    
    def write_csv(self, records: List[SyntheticRecord], path: Path):
        """Write records to CSV."""
        import csv
        headers = [
            "patient_id", "name", "name_script", "age", "gender", "phone",
            "aadhaar", "abha", "pan", "email", "address", "village", "tehsil",
            "district", "state", "pin_code", "hospital", "mrn", "admission_date",
            "discharge_date", "diagnosis", "drugs", "lab_tests", "doctor",
            "relative_name", "attachments", "metadata"
        ]
        
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for record in records:
                writer.writerow(record.to_csv_row())
    
    def write_json(self, records: List[SyntheticRecord], path: Path):
        """Write records to JSON."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in records], f, ensure_ascii=False, indent=2)
    
    def write_jsonl(self, records: List[SyntheticRecord], path: Path):
        """Write records to JSONL."""
        with open(path, 'w', encoding='utf-8') as f:
            for record in records:
                f.write(record.to_json() + '\n')
    
    def write_fhir_bundle(self, records: List[SyntheticRecord], path: Path):
        """Write records as FHIR Bundle."""
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": []
        }
        
        for record in records:
            # Create Patient resource
            patient = {
                "resourceType": "Patient",
                "id": record.patient_id,
                "identifier": [
                    {"system": "http://hospital.org/mrn", "value": record.mrn},
                    {"system": "http://gov.in/aadhaar", "value": record.aadhaar.replace(" ", "")},
                ],
                "name": [{"text": record.name}],
                "telecom": [
                    {"system": "phone", "value": record.phone},
                    {"system": "email", "value": record.email}
                ],
                "gender": record.gender.lower() if record.gender in ["M", "F"] else "other",
                "birthDate": (date.today() - timedelta(days=record.age * 365)).isoformat(),
                "address": [{
                    "text": record.address,
                    "city": record.village,
                    "district": record.district,
                    "state": record.state,
                    "postalCode": record.pin_code
                }]
            }
            
            # Create Encounter
            encounter = {
                "resourceType": "Encounter",
                "id": f"enc-{record.patient_id}",
                "status": "finished",
                "class": {"code": "inpatient"},
                "subject": {"reference": f"Patient/{record.patient_id}"},
                "period": {
                    "start": record.admission_date,
                    "end": record.discharge_date
                },
                "diagnosis": [{
                    "condition": {"display": record.diagnosis}
                }],
                "location": [{
                    "location": {"display": record.hospital}
                }]
            }
            
            bundle["entry"].extend([
                {"resource": patient},
                {"resource": encounter}
            ])
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(bundle, f, ensure_ascii=False, indent=2)


# Import re at module level
import re