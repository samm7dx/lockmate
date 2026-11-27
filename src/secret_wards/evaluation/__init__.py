"""
LOCKMATE — Phase 8: Advanced Evaluation, Adversarial Robustness & Continuous Quality

This module implements advanced testing and continuous quality infrastructure:
- Synthetic adversarial test generation
- Hidden-format robustness testing
- Privacy attack simulation
- Unified benchmark runner
- Engineering quality reporting
"""

from .synthetic_generator import SyntheticDataGenerator, SyntheticRecord, SyntheticConfig
from .adversarial_tests import AdversarialTestSuite, run_adversarial_tests
from .attack_simulator import PrivacyAttackSimulator, AttackResult, AttackConfig
from .benchmark import BenchmarkRunner, BenchmarkResult, run_full_evaluation
from .evaluation_report import EvaluationReport, generate_evaluation_report

__all__ = [
    "SyntheticDataGenerator",
    "SyntheticRecord",
    "SyntheticConfig",
    "AdversarialTestSuite",
    "run_adversarial_tests",
    "PrivacyAttackSimulator",
    "AttackResult",
    "AttackConfig",
    "BenchmarkRunner",
    "BenchmarkResult",
    "run_full_evaluation",
    "EvaluationReport",
    "generate_evaluation_report",
]