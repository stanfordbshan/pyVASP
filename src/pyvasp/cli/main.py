"""CLI adapter for pyVASP workflows."""

from __future__ import annotations

import argparse
import json
import sys

from pyvasp.gui.bridge import GuiBackendBridge


def _add_shared_backend_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mode", default="auto", choices=["direct", "api", "auto"], help="Execution mode")
    parser.add_argument(
        "--api-base-url",
        default="http://127.0.0.1:8000",
        help="API base URL used by api/auto modes",
    )


def build_parser() -> argparse.ArgumentParser:
    """Create command line parser."""

    parser = argparse.ArgumentParser(prog="pyvasp-cli", description="pyVASP command line interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    summary = subparsers.add_parser("summary", help="Summarize an OUTCAR file")
    summary.add_argument("outcar_path", help="Path to OUTCAR file")
    summary.add_argument("--include-history", action="store_true", help="Include full TOTEN history")
    _add_shared_backend_args(summary)

    diagnostics = subparsers.add_parser("diagnostics", help="Convergence/stress/magnetization diagnostics")
    diagnostics.add_argument("outcar_path", help="Path to OUTCAR file")
    diagnostics.add_argument(
        "--energy-tol",
        type=float,
        default=1e-4,
        help="Energy convergence tolerance in eV (|ΔE| <= tol)",
    )
    diagnostics.add_argument(
        "--force-tol",
        type=float,
        default=0.02,
        help="Force convergence tolerance in eV/Ang (max force <= tol)",
    )
    _add_shared_backend_args(diagnostics)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run CLI command and return process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)

    bridge = GuiBackendBridge(mode=args.mode, api_base_url=args.api_base_url)

    if args.command == "summary":
        try:
            data = bridge.summarize_outcar(
                outcar_path=args.outcar_path,
                include_history=args.include_history,
            )
        except Exception as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            return 1

        print(json.dumps(data, indent=2))
        return 0

    if args.command == "diagnostics":
        try:
            data = bridge.diagnose_outcar(
                outcar_path=args.outcar_path,
                energy_tolerance_ev=args.energy_tol,
                force_tolerance_ev_per_a=args.force_tol,
            )
        except Exception as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            return 1

        print(json.dumps(data, indent=2))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
