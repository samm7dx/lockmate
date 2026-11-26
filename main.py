#!/usr/bin/env python3
"""
LOCKMATE — Offline Healthcare Privacy Firewall
Track 3: Secret Wards — Yugaantar DevForge

Entry point for the LOCKMATE sanitization pipeline.
"""

import argparse
import os
import sys
import traceback
from pathlib import Path

# Ensure we can import secret_wards
sys.path.insert(0, str(Path(__file__).parent / "src"))

from secret_wards.pipeline.full import run_pipeline
from secret_wards.utils.logging import setup_logging
from secret_wards.utils.metrics import ProcessingMetricsCollector
from secret_wards.exceptions import LockmateError, QuarantineAllError


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="lockmate",
        description="LOCKMATE — Offline Healthcare Privacy Firewall (Track 3: Secret Wards)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --input /path/to/input --output /path/to/output
  RAKSHA_SECRET="..." python main.py -i ./data -o ./output
        """
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        required=True,
        help="Input directory containing hospital records"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        required=True,
        help="Output directory for sanitized files and reports"
    )
    parser.add_argument(
        "--config", "-c",
        type=Path,
        default=Path("config/policy.yaml"),
        help="Path to policy configuration file (default: config/policy.yaml)"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="LOCKMATE 1.0.0"
    )
    return parser.parse_args()


def validate_environment() -> bytes:
    """
    Validate and return RAKSHA_SECRET from environment.
    
    Returns:
        Secret as bytes (validated ≥32 bytes)
        
    Raises:
        LockmateError: If secret not set or invalid
    """
    secret_env = os.environ.get("RAKSHA_SECRET")
    if not secret_env:
        raise LockmateError(
            "RAKSHA_SECRET environment variable not set. "
            "Set it to a base64 or hex encoded secret (>=32 bytes)."
        )
    
    # Try to decode as base64 first, then hex
    secret_bytes = None
    for decoder in ("base64", "hex"):
        try:
            if decoder == "base64":
                import base64
                secret_bytes = base64.b64decode(secret_env)
            else:
                secret_bytes = bytes.fromhex(secret_env)
            break
        except Exception:
            continue
    
    if secret_bytes is None:
        raise LockmateError(
            "RAKSHA_SECRET must be valid base64 or hex encoded string"
        )
    
    if len(secret_bytes) < 32:
        raise LockmateError(
            f"RAKSHA_SECRET must be at least 32 bytes (got {len(secret_bytes)} bytes)"
        )
    
    return secret_bytes


def validate_paths(input_dir: Path, output_dir: Path) -> tuple[Path, Path]:
    """Validate and resolve input/output paths."""
    # Resolve input directory
    if not input_dir.exists():
        raise LockmateError(f"Input directory does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise LockmateError(f"Input path is not a directory: {input_dir}")
    
    input_resolved = input_dir.resolve()
    
    # Resolve output directory (create if needed)
    output_resolved = output_dir.resolve()
    output_resolved.mkdir(parents=True, exist_ok=True)
    
    # Ensure output is not inside input (prevent accidental overwrites)
    try:
        output_resolved.relative_to(input_resolved)
        raise LockmateError("Output directory must not be inside input directory")
    except ValueError:
        pass  # Good - output is not inside input
    
    return input_resolved, output_resolved


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    # Setup logging early
    logger = setup_logging()
    
    try:
        # Validate environment
        secret = validate_environment()
        
        # Validate paths
        input_dir, output_dir = validate_paths(args.input, args.output)
        
        logger.info("pipeline_start", extra={"input_dir": str(input_dir), "output_dir": str(output_dir), "config_path": str(args.config)})
        
        # Run the pipeline
        metrics_collector = ProcessingMetricsCollector()
        run_pipeline(
            input_dir=input_dir,
            output_dir=output_dir,
            secret=secret,
            config_path=args.config,
            metrics_collector=metrics_collector
        )
        
        logger.info("pipeline_complete", extra=metrics_collector.get_totals())
        return 0
        
    except QuarantineAllError as e:
        # Top-level quarantine - write partial report and exit
        logger.error("pipeline_quarantined_all", extra={"error": str(e)})
        return 1
        
    except LockmateError as e:
        logger.error("pipeline_error", extra={"error": str(e)})
        return 1
        
    except KeyboardInterrupt:
        logger.error("pipeline_interrupted")
        return 130
        
    except Exception as e:
        # Log error with hash only (no raw data)
        logger.critical(
            "pipeline_crash",
            error_type=type(e).__name__,
            error_message=str(e)[:200],  # Truncate
            traceback=traceback.format_exc()
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())