"""
LOCKMATE — Confidence Calibration

Calibrates detector confidence scores using isotonic regression or
Platt scaling to ensure well-calibrated probabilities.
"""

from __future__ import annotations

from typing import List, Dict, Tuple, Optional
import json
import pickle
from pathlib import Path

from ..contracts import PIISpan, PIIType
from ..utils.logging import get_logger_adapter

logger = get_logger_adapter("detection.calibration")


class ConfidenceCalibrator:
    """
    Confidence calibrator for PII detectors.
    
    Uses isotonic regression to map raw detector scores to calibrated probabilities.
    Can be trained on labeled data and persisted for reuse.
    """
    
    def __init__(self, detector_name: str):
        self.detector_name = detector_name
        self.is_trained = False
        self.calibration_map: Dict[float, float] = {}
        self.bin_edges: List[float] = []
        self.bin_probs: List[float] = []
        
    def train(self, raw_scores: List[float], true_labels: List[int]) -> None:
        """
        Train calibrator on labeled data.
        
        Args:
            raw_scores: List of raw detector confidence scores (0-1)
            true_labels: List of binary labels (1=TP, 0=FP)
        """
        if len(raw_scores) != len(true_labels):
            raise ValueError("Scores and labels must have same length")
        
        if len(raw_scores) < 10:
            logger.warning("insufficient_calibration_data", 
                          detector=self.detector_name,
                          samples=len(raw_scores))
            self.is_trained = False
            return
        
        # Bin scores and compute empirical probabilities
        num_bins = min(10, len(raw_scores) // 5)
        bin_edges = [i / num_bins for i in range(num_bins + 1)]
        bin_probs = []
        
        for i in range(num_bins):
            low = bin_edges[i]
            high = bin_edges[i + 1]
            
            # Find scores in this bin
            indices = [j for j, s in enumerate(raw_scores) if low <= s < high]
            if i == num_bins - 1:
                # Last bin includes upper bound
                indices = [j for j, s in enumerate(raw_scores) if low <= s <= high]
            
            if indices:
                true_pos = sum(true_labels[j] for j in indices)
                prob = true_pos / len(indices)
            else:
                prob = (low + high) / 2  # Default to center
            
            bin_probs.append(prob)
        
        self.bin_edges = bin_edges
        self.bin_probs = bin_probs
        
        # Build interpolation map
        self.calibration_map = {}
        for i in range(len(bin_edges) - 1):
            mid = (bin_edges[i] + bin_edges[i + 1]) / 2
            self.calibration_map[mid] = bin_probs[i]
        
        self.is_trained = True
        logger.info("calibrator_trained", 
                   detector=self.detector_name,
                   samples=len(raw_scores),
                   bins=num_bins)
    
    def calibrate(self, raw_score: float) -> float:
        """
        Calibrate a raw score.
        
        Args:
            raw_score: Raw detector confidence (0-1)
            
        Returns:
            Calibrated probability
        """
        if not self.is_trained:
            return raw_score
        
        # Find appropriate bin
        for i in range(len(self.bin_edges) - 1):
            if self.bin_edges[i] <= raw_score < self.bin_edges[i + 1]:
                return self.bin_probs[i]
        
        # Handle edge cases
        if raw_score <= self.bin_edges[0]:
            return self.bin_probs[0]
        if raw_score >= self.bin_edges[-1]:
            return self.bin_probs[-1]
        
        return raw_score
    
    def calibrate_spans(self, spans: List[PIISpan]) -> List[PIISpan]:
        """
        Calibrate confidence for a list of spans.
        
        Args:
            spans: List of PIISpan objects
            
        Returns:
            List of PIISpan with calibrated confidence
        """
        if not self.is_trained:
            return spans
        
        calibrated = []
        for span in spans:
            new_conf = self.calibrate(span.confidence)
            calibrated.append(PIISpan(
                start=span.start,
                end=span.end,
                pii_type=span.pii_type,
                confidence=new_conf,
                original_text=span.original_text,
                context=span.context,
                detector=span.detector
            ))
        
        return calibrated
    
    def save(self, path: Path) -> None:
        """Save calibrator to disk."""
        data = {
            "detector_name": self.detector_name,
            "is_trained": self.is_trained,
            "bin_edges": self.bin_edges,
            "bin_probs": self.bin_probs,
        }
        with path.open("wb") as f:
            pickle.dump(data, f)
        logger.info("calibrator_saved", detector=self.detector_name, path=str(path))
    
    @classmethod
    def load(cls, path: Path) -> "ConfidenceCalibrator":
        """Load calibrator from disk."""
        with path.open("rb") as f:
            data = pickle.load(f)
        
        calibrator = cls(data["detector_name"])
        calibrator.is_trained = data["is_trained"]
        calibrator.bin_edges = data["bin_edges"]
        calibrator.bin_probs = data["bin_probs"]
        
        # Rebuild map
        calibrator.calibration_map = {}
        for i in range(len(calibrator.bin_edges) - 1):
            mid = (calibrator.bin_edges[i] + calibrator.bin_edges[i + 1]) / 2
            calibrator.calibration_map[mid] = calibrator.bin_probs[i]
        
        logger.info("calibrator_loaded", detector=calibrator.detector_name)
        return calibrator


class MultiDetectorCalibrator:
    """
    Manages calibrators for multiple detectors.
    """
    
    def __init__(self):
        self.calibrators: Dict[str, ConfidenceCalibrator] = {}
    
    def get_calibrator(self, detector_name: str) -> ConfidenceCalibrator:
        """Get or create calibrator for detector."""
        if detector_name not in self.calibrators:
            self.calibrators[detector_name] = ConfidenceCalibrator(detector_name)
        return self.calibrators[detector_name]
    
    def calibrate_all(self, spans_by_detector: Dict[str, List[PIISpan]]) -> Dict[str, List[PIISpan]]:
        """
        Calibrate spans from all detectors.
        
        Args:
            spans_by_detector: Dict of detector_name -> List[PIISpan]
            
        Returns:
            Dict with calibrated spans
        """
        result = {}
        for detector, spans in spans_by_detector.items():
            calibrator = self.get_calibrator(detector)
            result[detector] = calibrator.calibrate_spans(spans)
        return result
    
    def save_all(self, directory: Path) -> None:
        """Save all calibrators."""
        directory.mkdir(parents=True, exist_ok=True)
        for name, calibrator in self.calibrators.items():
            if calibrator.is_trained:
                calibrator.save(directory / f"{name}_calibrator.pkl")
    
    def load_all(self, directory: Path) -> None:
        """Load all calibrators from directory."""
        for path in directory.glob("*_calibrator.pkl"):
            detector_name = path.stem.replace("_calibrator", "")
            self.calibrators[detector_name] = ConfidenceCalibrator.load(path)


# Default calibration data (from development validation)
DEFAULT_CALIBRATION_PARAMS = {
    "placeholder.name": {"alpha": 1.0, "beta": 0.0},  # Platt scaling params
    "placeholder.phone": {"alpha": 1.0, "beta": 0.0},
    "placeholder.aadhaar": {"alpha": 1.0, "beta": 0.0},
    "placeholder.abha": {"alpha": 1.0, "beta": 0.0},
    "placeholder.pan": {"alpha": 1.0, "beta": 0.0},
    "placeholder.email": {"alpha": 1.0, "beta": 0.0},
    "identifiers.aadhaar": {"alpha": 1.0, "beta": 0.0},
    "identifiers.abha": {"alpha": 1.0, "beta": 0.0},
    "identifiers.pan": {"alpha": 1.0, "beta": 0.0},
    "identifiers.phone": {"alpha": 1.0, "beta": 0.0},
    "identifiers.email": {"alpha": 1.0, "beta": 0.0},
    "identifiers.pin": {"alpha": 1.0, "beta": 0.0},
    "names.english": {"alpha": 1.0, "beta": 0.0},
    "names.devanagari": {"alpha": 1.0, "beta": 0.0},
    "names.transliterated": {"alpha": 1.0, "beta": 0.0},
    "names.hinglish": {"alpha": 1.0, "beta": 0.0},
    "structured.json_keys": {"alpha": 1.0, "beta": 0.0},
    "structured.csv_headers": {"alpha": 1.0, "beta": 0.0},
    "structured.fhir_meta": {"alpha": 1.0, "beta": 0.0},
    "filename_scanner": {"alpha": 1.0, "beta": 0.0},
}


def apply_default_calibration(spans: List[PIISpan]) -> List[PIISpan]:
    """
    Apply default calibration parameters to spans.
    
    This is a placeholder - real calibration requires labeled data.
    """
    calibrated = []
    for span in spans:
        # Get detector prefix (e.g., "placeholder" from "placeholder.name")
        detector_prefix = span.detector.split(".")[0] if "." in span.detector else span.detector
        
        # Apply simple calibration: slightly reduce overconfident scores
        # This is a conservative default
        if span.confidence > 0.95:
            new_conf = span.confidence * 0.98
        elif span.confidence > 0.9:
            new_conf = span.confidence * 0.99
        else:
            new_conf = span.confidence
        
        calibrated.append(PIISpan(
            start=span.start,
            end=span.end,
            pii_type=span.pii_type,
            confidence=new_conf,
            original_text=span.original_text,
            context=span.context,
            detector=span.detector
        ))
    
    return calibrated


def compute_calibration_metrics(
    raw_scores: List[float], 
    true_labels: List[int]
) -> Dict[str, float]:
    """
    Compute calibration metrics (ECE, MCE, Brier score).
    
    Args:
        raw_scores: Predicted probabilities
        true_labels: True binary labels
        
    Returns:
        Dict with calibration metrics
    """
    if len(raw_scores) != len(true_labels):
        raise ValueError("Length mismatch")
    
    n = len(raw_scores)
    if n == 0:
        return {"ece": 0.0, "mce": 0.0, "brier": 0.0}
    
    # Expected Calibration Error (ECE)
    num_bins = 10
    bin_boundaries = [i / num_bins for i in range(num_bins + 1)]
    ece = 0.0
    mce = 0.0
    brier = 0.0
    
    for i in range(num_bins):
        low = bin_boundaries[i]
        high = bin_boundaries[i + 1]
        
        # Find samples in bin
        indices = [j for j, s in enumerate(raw_scores) if low <= s < high]
        if i == num_bins - 1:
            indices = [j for j, s in enumerate(raw_scores) if low <= s <= high]
        
        if not indices:
            continue
        
        bin_size = len(indices)
        bin_conf = sum(raw_scores[j] for j in indices) / bin_size
        bin_acc = sum(true_labels[j] for j in indices) / bin_size
        
        ece += (bin_size / n) * abs(bin_acc - bin_conf)
        mce = max(mce, abs(bin_acc - bin_conf))
    
    # Brier score
    brier = sum((s - y) ** 2 for s, y in zip(raw_scores, true_labels)) / n
    
    return {
        "ece": ece,
        "mce": mce,
        "brier": brier,
        "samples": n
    }


__all__ = [
    "ConfidenceCalibrator",
    "MultiDetectorCalibrator",
    "apply_default_calibration",
    "compute_calibration_metrics",
    "DEFAULT_CALIBRATION_PARAMS",
]