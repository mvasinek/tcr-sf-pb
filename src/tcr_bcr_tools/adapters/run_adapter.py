"""CLI entry point for dataset adapter validation and normalization."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from tcr_bcr_tools.adapters.base import AdapterNotFoundError
from tcr_bcr_tools.adapters.registry import get_adapter
from tcr_bcr_tools.adapters.report import write_adapter_report
from tcr_bcr_tools.adapters.report import write_adapter_report
from tcr_bcr_tools.adapters.schema import ADAPTER_REPORT_FILE, UNIFIED_ANNOTATIONS_FILE


def _write_adapter_report(
    dataset_path: Path,
    *,
    adapter_name: str,
    adapter_version: str,
    started: str,
    finished: str,
    status: str,
    detected_files: list[Path],
    output_path: Path,
    df: pd.DataFrame | None = None,
) -> Path:
    return write_adapter_report(
        dataset_path,
        adapter_name=adapter_name,
        adapter_version=adapter_version,
        started=started,
        finished=finished,
        status=status,
        detected_files=detected_files,
        output_path=output_path,
        df=df,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate or normalize a dataset with a registered adapter."
    )
    parser.add_argument(
        "--adapter",
        required=True,
        help="Adapter name (tenx, bdrhapsody, airr, custom).",
    )
    parser.add_argument(
        "--dataset",
        required=True,
        type=Path,
        help="Path to dataset directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path for normalization.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate raw inputs without writing unified output.",
    )
    args = parser.parse_args()

    try:
        adapter_cls = get_adapter(args.adapter)
    except AdapterNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    started = datetime.now().isoformat(timespec="seconds")
    result = adapter_cls.validate_input(args.dataset)
    if args.validate_only:
        print("valid" if result.valid else "invalid")
        for error in result.errors:
            print(f"ERROR: {error}")
        for warning in result.warnings:
            print(f"WARNING: {warning}")
        raise SystemExit(0 if result.valid else 1)

    if not result.valid:
        raise SystemExit("; ".join(result.errors))

    output = args.output or (
        args.dataset / "intermediate" / UNIFIED_ANNOTATIONS_FILE
    )
    adapter_cls.normalize(args.dataset, output)
    df = pd.read_csv(output)
    finished = datetime.now().isoformat(timespec="seconds")
    report = _write_adapter_report(
        args.dataset,
        adapter_name=adapter_cls.name,
        adapter_version=adapter_cls.version,
        started=started,
        finished=finished,
        status="completed",
        detected_files=result.detected_files,
        output_path=output,
        df=df,
    )
    print(f"Wrote {output}")
    print(f"Wrote {report}")


if __name__ == "__main__":
    main()
