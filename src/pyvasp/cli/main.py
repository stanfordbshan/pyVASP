"""CLI adapter for pyVASP workflows."""

from __future__ import annotations

import argparse
import json
import sys

from pyvasp.gui.bridge import GuiBackendBridge


def build_parser() -> argparse.ArgumentParser:
    """Create command line parser."""

    parser = argparse.ArgumentParser(prog="pyvasp-cli", description="pyVASP command line interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    summary = subparsers.add_parser("summary", help="Summarize an OUTCAR file")
    summary.add_argument("outcar_path", help="Path to OUTCAR file")
    summary.add_argument("--include-history", action="store_true", help="Include full TOTEN history")
    summary.add_argument("--mode", default="auto", choices=["direct", "api", "auto"], help="Execution mode")
    summary.add_argument(
        "--api-base-url",
        default="http://127.0.0.1:8000",
        help="API base URL used by api/auto modes",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run CLI command and return process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "summary":
        bridge = GuiBackendBridge(mode=args.mode, api_base_url=args.api_base_url)
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

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
