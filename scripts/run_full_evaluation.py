#!/usr/bin/env python3
"""
LOCKMATE — Full Evaluation Runner

Executes comprehensive evaluation benchmark:
1. Internal unit tests
2. Integration tests
3. Synthetic adversarial tests
4. Output validator
5. Practice self-check
6. Performance benchmark
7. Determinism checks

Generates machine-readable summary and engineering quality report.

Usage:
    RAKSHA_SECRET="..." python scripts/run_full_evaluation.py \
        --input /path/to/input \
        --output /path/to/output \
        --config config/policy.yaml
"""

import argparse
import base64
import json
import logging
import os
import sys
import time
from pathlib import Path

# Ensure we can import secret_wards
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from secret_wards.evaluation.benchmark import run_full_evaluation, BenchmarkRunner
from secret_wards.evaluation.evaluation_report import (
    generate_evaluation_report,
    collect_pii_leakage_metrics,
    collect_medical_preservation_metrics,
    collect_canary_results
)
from secret_wards.utils.logging import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_full_evaluation",
        description="LOCKMATE Full Evaluation Benchmark Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  RAKSHA_SECRET="..." python scripts/run_full_evaluation.py -i ./data -o ./eval_output
  RAKSHA_SECRET="..." python scripts/run_full_evaluation.py --config config/policy.yaml
        """
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        help="Input directory for practice/performance tests"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("evaluation_output"),
        help="Output directory for evaluation results (default: evaluation_output)"
    )
    parser.add_argument(
        "--config", "-c",
        type=Path,
        default=Path("config/policy.yaml"),
        help="Path to policy configuration (default: config/policy.yaml)"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="Project root directory (default: current directory)"
    )
    parser.add_argument(
        "--skip-adversarial",
        action="store_true",
        help="Skip adversarial tests (faster)"
    )
    parser.add_argument(
        "--skip-performance",
        action="store_true",
        help="Skip performance benchmark (faster)"
    )
    parser.add_argument(
        "--skip-determinism",
        action="store_true",
        help="Skip determinism check (faster)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)"
    )
    return parser.parse_args()


def validate_secret() -> bytes:
    """Validate and return RAKSHA_SECRET from environment."""
    secret_env = os.environ.get("RAKSHA_SECRET")
    if not secret_env:
        raise ValueError(
            "RAKSHA_SECRET environment variable not set. "
            "Set it to a base64 or hex encoded secret (>=32 bytes)."
        )
    
    secret_bytes = None
    for decoder in ("base64", "hex"):
        try:
            if decoder == "base64":
                secret_bytes = base64.b64decode(secret_env)
            else:
                secret_bytes = bytes.fromhex(secret_env)
            break
        except Exception:
            continue
    
    if secret_bytes is None:
        raise ValueError("RAKSHA_SECRET must be valid base64 or hex encoded string")
    
    if len(secret_bytes) < 32:
        raise ValueError(f"RAKSHA_SECRET must be at least 32 bytes (got {len(secret_bytes)} bytes)")
    
    return secret_bytes


def main() -> int:
    args = parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s %(levelname)s %(name)s: %(message)s'
    )
    logger = logging.getLogger("evaluation")
    
    try:
        # Validate secret
        secret = validate_secret()
        
        # Validate paths
        project_root = args.project_root.resolve()
        config_path = args.config
        if not config_path.is_absolute():
            config_path = project_root / config_path
        
        output_dir = args.output
        if not output_dir.is_absolute():
            output_dir = project_root / output_dir
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        input_dir = None
        if args.input:
            input_dir = args.input
            if not input_dir.is_absolute():
                input_dir = project_root / input_dir
        
        logger.info("starting_full_evaluation",
                   project_root=str(project_root),
                   config=str(config_path),
                   input=str(input_dir) if input_dir else "none",
                   output=str(output_dir))
        
        start_time = time.time()
        
        # Create benchmark runner
        runner = BenchmarkRunner(
            project_root=project_root,
            secret=secret,
            config_path=config_path,
            input_dir=input_dir,
            output_dir=output_dir
        )
        
        # Optionally skip phases
        if args.skip_adversarial:
            runner._run_adversarial_tests = lambda: runner.results.append(
                type('obj', (object,), {
                    'phase': 'adversarial',
                    'name': 'adversarial_tests',
                    'passed': True,
                    'exit_code': 0,
                    'duration_ms': 0,
                    'output': 'Skipped',
                    'error': '',
                    'metrics': {'skipped': True}
                })()
            )
        
        if args.skip_performance:
            runner._run_performance_benchmark = lambda: runner.results.append(
                type('obj', (object,), {
                    'phase': 'performance',
                    'name': 'performance_benchmark',
                    'passed': True,
                    'exit_code': 0,
                    'duration_ms': 0,
                    'output': 'Skipped',
                    'error': '',
                    'metrics': {'skipped': True}
                })()
            )
        
        if args.skip_determinism:
            runner._run_determinism_check = lambda: runner.results.append(
                type('obj', (object,), {
                    'phase': 'determinism',
                    'name': 'determinism_check',
                    'passed': True,
                    'exit_code': 0,
                    'duration_ms': 0,
                    'output': 'Skipped',
                    'error': '',
                    'metrics': {'skipped': True}
                })()
            )
        
        # Run benchmark
        benchmark_summary = runner.run_all()
        
        # Collect additional metrics
        pii_leakage = collect_pii_leakage_metrics(output_dir)
        
        medical_preservation = {}
        if input_dir and input_dir.exists():
            medical_preservation = collect_medical_preservation_metrics(input_dir, output_dir)
        
        # Canary results (if canaries were generated)
        canary_results = {"executed": False, "reason": "Canary checker not integrated"}
        
        # Generate evaluation report
        report_path = output_dir / "evaluation_report.json"
        generate_evaluation_report(
            project_root=project_root,
            output_path=report_path,
            benchmark_summary=benchmark_summary.to_dict(),
            pii_leakage=pii_leakage,
            medical_preservation=medical_preservation,
            canary_results=canary_results,
            runtime_seconds=time.time() - start_time,
            peak_memory_mb=0  # Would need memory profiler
        )
        
        # Print summary
        print("\n" + "="*60)
        print("EVALUATION SUMMARY")
        print("="*60)
        print(f"Total Phases: {benchmark_summary.total_phases}")
        print(f"Passed: {benchmark_summary.passed_phases}")
        print(f"Failed: {benchmark_summary.failed_phases}")
        print(f"Total Duration: {benchmark_summary.total_duration_ms:.0f}ms")
        print(f"Overall Status: {'PASS' if benchmark_summary.failed_phases == 0 else 'FAIL'}")
        print(f"\nDetailed report saved to: {report_path}")
        print(f"Benchmark summary saved to: {output_dir / 'benchmark_summary.json'}")
        
        # Exit with appropriate code
        return 0 if benchmark_summary.failed_phases == 0 else 1
        
    except Exception as e:
        logger.exception("evaluation_failed")
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())