"""
LOCKMATE — Multilingual Person Name Detection

Detects person names across Latin, Devanagari and Hinglish scripts.
Uses gazetteers, contextual patterns, and clinical veto logic.
"""

from __future__ import annotations

import re
import logging
from typing import List, Set, Tuple, Optional
from pathlib import Path

from ..contracts import PIISpan, PIIType, UnifiedRecord, RecordLocation
from ..detection.gazetteer import get_gazetteer
from ..detection.transliterate import devanagari_to_latin
from ..utils.logging import get_logger_adapter

logger = get_logger_adapter("detection.names")

# Common Indian first names and surnames (fallback when gazetteer unavailable)
COMMON_INDIAN_FIRST_NAMES = {
    "aakash", "aarav", "abhay", "abhishek", "aditya", "ajay", "akash", "akshay",
    "amit", "anand", "anil", "ankit", "arjun", "arun", "ashish", "ashok", "atul",
    "avinas", "bharat", "bhavesh", "chetan", "deepak", "dinesh", "fatma", "gagan",
    "gaurav", "girish", "govind", "harish", "harsh", "hemant", "ilavenil", "jaspreet",
    "jatin", "jay", "jeet", "jitendra", "karan", "kartik", "kaveri", "keshav",
    "krish", "krishna", "kunal", "laksh", "lalit", "mahesh", "manish", "manoj",
    "mayank", "mohan", "mukesh", "nakul", "naresh", "naveen", "neeraj", "nikhil",
    "nilesh", "nitin", "omkar", "pankaj", "paresh", "pawan", "piyush", "prakash",
    "prashant", "pravesh", "prem", "raghav", "rahul", "raj", "rajan", "rajesh",
    "rakesh", "ram", "ramesh", "ranjan", "ravi", "ravindra", "rohit", "sachin",
    "sagar", "sameer", "sanjay", "santosh", "sarvesh", "satish", "saurabh",
    "shankar", "shashank", "shekhar", "shiv", "shiva", "shivam", "shubham",
    "siddharth", "somesh", "subhash", "sudhir", "sumit", "sunil", "sunita",
    "suresh", "sushil", "swaroop", "tushar", "tsering", "uday", "umesh", "varun",
    "vijay", "vikas", "vikram", "vinay", "vineet", "vipul", "vishal", "vivek",
    "yash", "yogesh", "zorawar",
    # Female
    "aarti", "aditi", "alka", "amita", "anita", "anjali", "ankita", "anuradha",
    "aparna", "archana", "arti", "asha", "astha", "bhavna", "bindu", "chitra",
    "deepa", "deepika", "divya", "geeta", "gunjan", "hema", "indira", "jaya",
    "jyoti", "kavita", "kirti", "kriti", "laxmi", "madhuri", "mamta", "manju",
    "meena", "meera", "monika", "namrata", "neelam", "neeta", "neha", "nidhi",
    "nisha", "nita", "payal", "pooja", "poornima", "prabha", "pratibha", "preeti",
    "priya", "priyanka", "pushpa", "radha", "rajni", "rekha", "renuka", "reshma",
    "rhea", "riya", "roopa", "rupali", "sabita", "sadhna", "sakshi", "sandhya",
    "sangeeta", "sanjana", "sapna", "sarika", "sarita", "seema", "shalini",
    "shikha", "shilpa", "shivani", "shobha", "shraddha", "shreya", "shruti",
    "shweta", "simran", "smita", "sonal", "sonia", "soumya", "sridevi", "srujan",
    "srushti", "sudha", "sujata", "sukanya", "suman", "sumita", "sunita",
    "supriya", "sushma", "swati", "tara", "trisha", "upasana", "usha", "vaishali",
    "varsha", "vibha", "vidya", "vijaya", "vishakha", "yashika", "yogita"
}

COMMON_INDIAN_SURNAMES = {
    "agarwal", "agrawal", "ahuja", "arora", "bansal", "bansil", "bano", "bhatia",
    "chopra", "dhawan", "dhillon", "garg", "goel", "goenka", "goyal", "gupta",
    "jain", "jindal", "khan", "kapoor", "kashyap", "khurana", "kohli", "malhotra",
    "mehra", "mehta", "mittal", "narang", "narula", "nambiar", "puri", "qadri",
    "sachdeva", "saxena", "sehgal", "seth", "sethi", "sharma", "singh", "sodhi",
    "sood", "talwar", "tandon", "thakur", "tuli", "verma", "vij", "wadhwa",
    # South Indian
    "acharya", "ayyar", "ayyer", "bhat", "bhatt", "choudhary", "chowdhury",
    "desai", "deshmukh", "dubey", "gaikwad", "gokhale", "gupte", "iyer",
    "iyengar", "jadhav", "jadhav", "jain", "joshi", "kamble", "karpe",
    "kulkarni", "mahajan", "malik", "mehra", "more", "naik", "nair",
    "namboodiri", "narayanan", "nayak", "pai", "patel", "patil", "prabhu",
    "rao", "raval", "reddy", "savant", "shah", "shetty", "singh", "swamy",
    "thakur", "tiwari", "upadhyay", "vaidya", "varma", "yadav",
    # East Indian
    "banerjee", "bhattacharjee", "bhattacharya", "basu", "bose", "chakraborty",
    "chatterjee", "das", "datta", "de", "dey", "ghosh", "guha", "gupta",
    "halder", "kar", "karmakar", "kundu", "laha", "maity", "majumdar", "mallick",
    "mandal", "mishra", "mitra", "mukherjee", "mukhopadhyay", "nag", "nandy",
    "pal", "pandey", "paul", "ray", "roy", "saha", "sarkar", "sen", "sengupta",
    "shome", "sinha", "sanyal", "saha", "sarkar", "sen", "sengupta"
}

# Medical context indicators that should veto name detection
MEDICAL_CONTEXT_INDICATORS = {
    "mg", "ml", "mcg", "iu", "tablet", "capsule", "injection", "syrup", "drops",
    "prescribed", "advised", "recommended", "treated", "diagnosed", "examined",
    "dosage", "frequency", "duration", "route", "oral", "iv", "im", "sc",
    "haemoglobin", "creatinine", "sugar", "glucose", "wbc", "rbc", "platelet",
    "sodium", "potassium", "urea", "bilirubin", "alt", "ast", "alp", "ggt",
    "tsh", "hba1c", "bp", "blood pressure", "pulse", "temperature", "spo2",
    "diagnosis", "medicine", "treatment", "therapy", "procedure", "surgery"
}

# Relationship markers for relative name classification
RELATIONSHIP_MARKERS = {
    "s/o", "d/o", "w/o", "c/o", "son of", "daughter of", "wife of", "husband of",
    "father of", "mother of", "brother of", "sister of"
}

# Doctor prefixes
DOCTOR_PREFIXES = {
    "dr", "dr.", "doctor", "डॉ", "डॉ.", "डॉक्टर"
}

# Clinical context indicators for doctor detection
CLINICAL_CONTEXT_INDICATORS = {
    "prescribed", "advised", "recommended", "treated", "diagnosed", "examined",
    "consulted", "referred", "admitted", "discharged", "followup", "follow-up",
    "review", "checkup", "prescription", "medication", "dosage", "dosage",
    "tablet", "capsule", "injection", "syrup", "drops", "ordered", "started",
    "stopped", "continued", "increased", "decreased", "adjusted", "titrated",
    "monitored", "assessed", "opd", "ipd", "ward", "bed", "hospital", "clinic"
}

# Devanagari name detection patterns - with capturing group for the full name
DEVANAGARI_NAME_PATTERN = re.compile(
    r'([\u0900-\u097F]{2,}(?:\s+[\u0900-\u097F]{2,})+)'
)

# Hinglish name patterns (transliterated names) - with capturing groups
HINGLISH_NAME_PATTERNS = [
    re.compile(r'\b((?:mr|mrs|ms|dr)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+))\b', re.IGNORECASE),
    re.compile(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+\s+(?:s/o|d/o|w/o|c/o))\b', re.IGNORECASE),
]

# ALL CAPS name pattern (e.g., "VIJAY YADAV", "SUNITA VERMA")
CAPS_NAME_PATTERN = re.compile(
    r'\b([A-Z]{2,}(?:\s+[A-Z]\.?)*\s+[A-Z]{2,})\b'
)

# Title Case name pattern (e.g., "Vijay Yadav", "Sunita Verma")
TITLE_CASE_NAME_PATTERN = re.compile(
    r'\b([A-Z][a-z]{2,}(?:\s+[A-Z]\.?)*\s+[A-Z][a-z]{2,})\b'
)

# Single word capitalized (could be name in context)
SINGLE_CAPITALIZED_PATTERN = re.compile(
    r'\b([A-Z][a-z]{2,})\b'
)


class NameDetector:
    """Multilingual name detector with gazetteer and contextual awareness."""
    
    def __init__(self):
        self.gazetteer = get_gazetteer()
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for name detection."""
        # Load gazetteer data
        self.first_names = self.gazetteer.get("first_names_latin")
        self.first_names_devanagari = self.gazetteer.get("first_names_devanagari")
        self.surnames = self.gazetteer.get("surnames_latin")
        self.surnames_devanagari = self.gazetteer.get("surnames_devanagari")
        self.honorifics = self.gazetteer.get("honorifics_latin") | self.gazetteer.get("honorifics_devanagari")
        self.relationship_markers = self.gazetteer.get("relationship_markers")
        self.districts = self.gazetteer.get("districts_latin")
        
        # Also include common names as fallback
        self.first_names = self.first_names | COMMON_INDIAN_FIRST_NAMES
        self.surnames = self.surnames | COMMON_INDIAN_SURNAMES
        self.devanagari_surnames = self.gazetteer.get("surnames_devanagari")
        
        logger.debug("gazetteer_loaded", 
                    surnames_count=len(self.surnames), 
                    first_names_count=len(self.first_names),
                    districts_count=len(self.districts),
                    has_yadav="yadav" in self.surnames)
    
    def detect(self, record: UnifiedRecord) -> List[PIISpan]:
        """
        Detect person names in a record.
        
        Returns:
            List of PIISpan objects for detected names
        """
        spans = []
        text = record.normalized_text
        
        if not text:
            return spans
        
        logger.debug("name_detector_start", record_id=record.record_id, text_len=len(text))
        
        # Detect Latin script names
        latin_spans = self._detect_latin_names(record, text)
        spans.extend(latin_spans)
        logger.debug("latin_names_detected", record_id=record.record_id, count=len(latin_spans))
        
        # Detect Devanagari names
        devanagari_spans = self._detect_devanagari_names(record, text)
        spans.extend(devanagari_spans)
        logger.debug("devanagari_names_detected", record_id=record.record_id, count=len(devanagari_spans))
        
        # Detect Hinglish names
        hinglish_spans = self._detect_hinglish_names(record, text)
        spans.extend(hinglish_spans)
        logger.debug("hinglish_names_detected", record_id=record.record_id, count=len(hinglish_spans))
        
        # Classify names (patient, relative, doctor, etc.)
        classified_spans = self._classify_names(spans, text, record)
        logger.debug("names_classified", record_id=record.record_id, count=len(classified_spans))
        
        # Apply filters (remove false positives)
        filtered_spans = self._filter_names(classified_spans, text)
        logger.debug("names_filtered", record_id=record.record_id, count=len(filtered_spans))
        
        return filtered_spans
    
    def _detect_latin_names(self, record: UnifiedRecord, text: str) -> List[PIISpan]:
        """Detect names in Latin script."""
        spans = []
        
        # Pattern 1: ALL CAPS names (e.g., "VIJAY YADAV", "SUNITA VERMA")
        caps_matches = list(CAPS_NAME_PATTERN.finditer(text))
        logger.debug("caps_pattern_matches", record_id=record.record_id, count=len(caps_matches))
        
        for match in caps_matches:
            name = match.group(1)
            parts = name.split()
            if len(parts) >= 2:
                first = parts[0].lower()
                last = parts[-1].lower()
                
                # Check if it's a known name pattern
                is_known_first = first in self.first_names or first in COMMON_INDIAN_FIRST_NAMES
                is_known_last = last in self.surnames or last in COMMON_INDIAN_SURNAMES
                
                if is_known_first or is_known_last:
                    confidence = 0.85 if (is_known_first and is_known_last) else 0.7
                else:
                    # Unknown ALL CAPS name - detect with lower confidence
                    confidence = 0.6
                
                # Check for medical veto
                context = text[max(0, match.start()-50):match.end()+50]
                if self._would_be_vetoed(name, context):
                    logger.debug("caps_name_vetoed", record_id=record.record_id)
                    continue
                
                spans.append(PIISpan(
                    start=match.start(),
                    end=match.end(),
                    pii_type=PIIType.NAME,
                    confidence=confidence,
                    original_text=match.group(),
                    context=context,
                    detector="placeholder_name_caps"
                ))
        
        # Pattern 2: Title Case names (e.g., "Vijay Yadav", "Sunita Verma")
        logger.info("detecting_latin_names", record_id=record.record_id)
        standalone_latin_spans = self._detect_standalone_latin_names(record, text)
        spans.extend(standalone_latin_spans)
        
        return spans
    
    def _detect_standalone_latin_names(self, record: UnifiedRecord, text: str) -> List[PIISpan]:
        """Detect standalone Firstname Lastname patterns."""
        from ..contracts import PIISpan, PIIType
        
        spans = []
        logger.info("standalone_latin_names_start", record_id=record.record_id, text_len=len(text))
        
        if not text:
            return spans
        
        # Pattern 1: Firstname Lastname (both capitalized, normal case)
        name_pattern = re.compile(
            r'\b([A-Z][a-z]{2,}(?:\s+[A-Z]\.?)*\s+[A-Z][a-z]{2,})\b'
        )
        
        # Pattern 2: ALL CAPS names (e.g., "VIJAY YADAV", "SUNITA VERMA")
        caps_name_pattern = re.compile(
            r'\b([A-Z]{2,}(?:\s+[A-Z]\.?)*\s+[A-Z]{2,})\b'
        )
        
        # Process normal case names
        for match in name_pattern.finditer(text):
            name = match.group(1)
            parts = name.split()
            if len(parts) >= 2:
                first = parts[0].lower()
                last = parts[-1].lower()
                
                # Check if it's a known name pattern
                is_known_first = first in self.first_names or first in COMMON_INDIAN_FIRST_NAMES
                is_known_last = last in self.surnames or last in COMMON_INDIAN_SURNAMES
                
                if is_known_first or is_known_last:
                    confidence = 0.85 if (is_known_first and is_known_last) else 0.7
                else:
                    # Unknown Title Case name - detect with lower confidence
                    confidence = 0.6
                
                # Check for medical veto
                context = text[max(0, match.start()-50):match.end()+50]
                if self._would_be_vetoed(name, context):
                    continue
                
                spans.append(PIISpan(
                    start=match.start(),
                    end=match.end(),
                    pii_type=PIIType.NAME,
                    confidence=confidence,
                    original_text=match.group(),
                    context=text[max(0, match.start()-50):match.end()+50],
                    detector="placeholder_name"
                ))
        
        # Process ALL CAPS names (additional to caps pattern above)
        for match in caps_name_pattern.finditer(text):
            name = match.group(1)
            parts = name.split()
            if len(parts) >= 2:
                first = parts[0].lower()
                last = parts[-1].lower()
                
                is_known_first = first in self.first_names or first in COMMON_INDIAN_FIRST_NAMES
                is_known_last = last in self.surnames or last in COMMON_INDIAN_SURNAMES
                
                if is_known_first or is_known_last:
                    confidence = 0.85 if (is_known_first and is_known_last) else 0.7
                else:
                    confidence = 0.6
                
                context = text[max(0, match.start()-50):match.end()+50]
                if self._would_be_vetoed(name, context):
                    continue
                
                spans.append(PIISpan(
                    start=match.start(),
                    end=match.end(),
                    pii_type=PIIType.NAME,
                    confidence=confidence,
                    original_text=match.group(),
                    context=text[max(0, match.start()-50):match.end()+50],
                    detector="placeholder_name_caps"
                ))
        
        return spans
    
    def _detect_devanagari_names(self, record: UnifiedRecord, text: str) -> List[PIISpan]:
        """Detect names in Devanagari script."""
        from ..contracts import PIISpan, PIIType
        
        spans = []
        logger.debug("detecting_devanagari_names", record_id=record.record_id)
        
        if not text:
            return spans
        
        for match in DEVANAGARI_NAME_PATTERN.finditer(text):
            name = match.group()
            
            # Transliterate to Latin for gazetteer check
            latin_name = devanagari_to_latin(name)
            
            # Check if transliterated name matches gazetteer
            parts = latin_name.split()
            if len(parts) >= 2:
                first = parts[0].lower()
                last = parts[-1].lower()
                
                is_known_first = first in self.first_names or first in COMMON_INDIAN_FIRST_NAMES
                is_known_last = last in self.surnames or last in COMMON_INDIAN_SURNAMES
                
                if is_known_first or is_known_last:
                    confidence = 0.85 if (is_known_first and is_known_last) else 0.75
                else:
                    confidence = 0.6
                
                context = text[max(0, match.start()-50):match.end()+50]
                if self._would_be_vetoed(latin_name, context):
                    continue
                
                spans.append(PIISpan(
                    start=match.start(),
                    end=match.end(),
                    pii_type=PIIType.NAME,
                    confidence=confidence,
                    original_text=match.group(),
                    context=text[max(0, match.start()-50):match.end()+50],
                    detector="devanagari_name"
                ))
        
        logger.debug("devanagari_names_detected", record_id=record.record_id, count=len(spans))
        return spans
    
    def _detect_hinglish_names(self, record: UnifiedRecord, text: str) -> List[PIISpan]:
        """Detect names in Hinglish (transliterated Hindi)."""
        from ..contracts import PIISpan, PIIType
        
        spans = []
        logger.debug("hinglish_names_detected", record_id=record.record_id)
        
        if not text:
            return spans
        
        # Check Hinglish patterns
        for pattern in HINGLISH_NAME_PATTERNS:
            for match in pattern.finditer(text):
                name = match.group(1)
                parts = name.split()
                if len(parts) >= 2:
                    first = parts[0].lower()
                    last = parts[-1].lower()
                    
                    is_known_first = first in self.first_names or first in COMMON_INDIAN_FIRST_NAMES
                    is_known_last = last in self.surnames or last in COMMON_INDIAN_SURNAMES
                    
                    confidence = 0.8 if (is_known_first and is_known_last) else 0.65
                    
                    context = text[max(0, match.start()-50):match.end()+50]
                    if self._would_be_vetoed(name, context):
                        continue
                    
                    spans.append(PIISpan(
                        start=match.start(),
                        end=match.end(),
                        pii_type=PIIType.NAME,
                        confidence=confidence,
                        original_text=match.group(),
                        context=text[max(0, match.start()-50):match.end()+50],
                        detector="hinglish_name"
                    ))
        
        logger.debug("hinglish_names_detected", record_id=record.record_id, count=len(spans))
        return spans
    
    def _would_be_vetoed(self, text: str, context: str) -> bool:
        """Check if a name would be vetoed by medical context or known non-name entities."""
        text_lower = text.lower()
        context_lower = context.lower()
        
        # Check for medical terms
        if text_lower in ['diabetes', 'hypertension', 'tb', 'hiv', 'cancer',
                          'asthma', 'arthritis', 'parkinson', 'alzheimer',
                          'crohn', 'dolo', 'paracetamol', 'metformin']:
            return True
        
        # Check for medical context patterns
        if re.search(r'\b\d+(?:\.\d+)?\s*(?:mg|g|ml|mcg|iu|u)\b', context, re.IGNORECASE):
            return True
        
        # Check for medical context indicators
        if any(word in context.lower() for word in ['mg', 'ml', 'dosage', 'dosage', 'prescribed', 'tablet']):
            # Check if this looks like a dosage pattern
            if re.search(r'\b\d+\s*(?:mg|g|ml|mcg)\b', context, re.IGNORECASE):
                return True
        
        # Check for known district names (veto false positive name detections)
        # "Rae Bareli" is a district, not a person's name
        if hasattr(self, 'districts') and text_lower in self.districts:
            return True
        
        return False
    
    def _is_doctor_context(self, span: PIISpan, text: str) -> bool:
        """Check if name appears in doctor context."""
        context = span.context.lower()
        
        # Check for doctor prefixes near the name
        for prefix in DOCTOR_PREFIXES:
            if prefix in context:
                return True
        
        # Check for clinical verbs near the name
        clinical_verbs = ['prescribed', 'advised', 'recommended', 'treated', 'diagnosed',
                         'examined', 'consulted', 'referred', 'admitted', 'discharged']
        for verb in clinical_verbs:
            if verb in context:
                return True
        
        # Check for clinical context words
        if any(word in context for word in CLINICAL_CONTEXT_INDICATORS):
            return True
        
        return False
    
    def _is_clinical_context(self, context: str) -> bool:
        """Check if context indicates clinical setting."""
        context_lower = context.lower()
        return any(indicator in context_lower for indicator in CLINICAL_CONTEXT_INDICATORS)
    
    def _classify_names(self, spans: List, text: str, record: UnifiedRecord) -> List:
        """Classify detected names as patient, relative, doctor, or unknown."""
        from ..contracts import PIISpan, PIIType
        
        classified = []
        for span in spans:
            pii_type = span.pii_type
            confidence = span.confidence
            
            if span.pii_type == PIIType.NAME:
                # Check for relationship markers
                is_relative = any(marker in span.original_text.lower() for marker in RELATIONSHIP_MARKERS)
                if is_relative:
                    pii_type = PIIType.RELATIVE
                    confidence = 0.95
                
                # Check for doctor context
                elif self._is_doctor_context(span, text):
                    pii_type = PIIType.DOCTOR
                    confidence = 0.9
                
                # Check for C/O ambiguity
                elif 'c/o' in span.original_text.lower() or 'c/o' in span.context.lower():
                    if self._is_clinical_context(text[max(0, span.start-100):span.end+100]):
                        pii_type = PIIType.NAME  # Could be patient
                    else:
                        pii_type = PIIType.RELATIVE
                
                # Default: patient
                else:
                    pii_type = PIIType.NAME
            
            classified.append(PIISpan(
                start=span.start,
                end=span.end,
                pii_type=pii_type,
                confidence=confidence,
                original_text=span.original_text,
                context=span.context,
                detector=span.detector
            ))
        
        return classified
    
    def _filter_names(self, spans: List, text: str) -> List:
        """Filter out false positive name detections."""
        filtered = []
        for span in spans:
            # Skip very short names
            if len(span.original_text.strip()) < 3:
                continue
            
            # Skip if already covered by another span with higher confidence
            overlap = False
            for other in filtered:
                if (span.start <= other.end and span.end >= other.start and 
                    other.confidence >= span.confidence):
                    overlap = True
                    break
            
            if not overlap:
                filtered.append(span)
        
        return filtered


# Module-level detector instance (singleton)
_name_detector: Optional['NameDetector'] = None


def detect_names(record: UnifiedRecord) -> List:
    """Entry point for name detection (uses cached detector)."""
    global _name_detector
    if _name_detector is None:
        _name_detector = NameDetector()
    return _name_detector.detect(record)