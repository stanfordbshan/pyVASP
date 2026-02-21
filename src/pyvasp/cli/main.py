"""CLI adapter for pyVASP workflows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

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

    batch_summary = subparsers.add_parser("batch-summary", help="Summarize multiple OUTCAR files")
    batch_summary.add_argument("outcar_paths", nargs="+", help="One or more OUTCAR file paths")
    batch_summary.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop processing after first failed item",
    )
    _add_shared_backend_args(batch_summary)

    batch_diagnostics = subparsers.add_parser("batch-diagnostics", help="Diagnose multiple OUTCAR files")
    batch_diagnostics.add_argument("outcar_paths", nargs="+", help="One or more OUTCAR file paths")
    batch_diagnostics.add_argument(
        "--energy-tol",
        type=float,
        default=1e-4,
        help="Energy convergence tolerance in eV (|ΔE| <= tol)",
    )
    batch_diagnostics.add_argument(
        "--force-tol",
        type=float,
        default=0.02,
        help="Force convergence tolerance in eV/Ang (max force <= tol)",
    )
    batch_diagnostics.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop processing after first failed item",
    )
    _add_shared_backend_args(batch_diagnostics)

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

    profile = subparsers.add_parser("convergence-profile", help="Chart-ready OUTCAR convergence profile")
    profile.add_argument("outcar_path", help="Path to OUTCAR file")
    _add_shared_backend_args(profile)

    ionic_series = subparsers.add_parser("ionic-series", help="Per-step OUTCAR series for visualization")
    ionic_series.add_argument("outcar_path", help="Path to OUTCAR file")
    _add_shared_backend_args(ionic_series)

    export_tabular = subparsers.add_parser("export-tabular", help="Export OUTCAR data as CSV text")
    export_tabular.add_argument("outcar_path", help="Path to OUTCAR file")
    export_tabular.add_argument(
        "--dataset",
        default="ionic_series",
        choices=["ionic_series", "convergence_profile"],
        help="Dataset to export",
    )
    export_tabular.add_argument(
        "--delimiter",
        default="comma",
        choices=["comma", "semicolon", "tab"],
        help="CSV delimiter",
    )
    export_tabular.add_argument(
        "--output-file",
        help="Optional path to write exported tabular text",
    )
    _add_shared_backend_args(export_tabular)

    electronic = subparsers.add_parser(
        "electronic-metadata",
        help="Parse VASPKIT-like band gap/DOS metadata from EIGENVAL and DOSCAR",
    )
    electronic.add_argument("--eigenval-path", help="Path to EIGENVAL", default=None)
    electronic.add_argument("--doscar-path", help="Path to DOSCAR", default=None)
    _add_shared_backend_args(electronic)

    generate = subparsers.add_parser("generate-relax-input", help="Generate INCAR/KPOINTS/POSCAR for relaxation")
    generate.add_argument("structure_json", help="Path to structure JSON payload")
    generate.add_argument("--output-dir", help="Optional output directory for writing INCAR/KPOINTS/POSCAR")
    generate.add_argument("--kmesh", nargs=3, type=int, default=[6, 6, 6], metavar=("KX", "KY", "KZ"))
    mesh_mode = generate.add_mutually_exclusive_group()
    mesh_mode.add_argument("--gamma-centered", dest="gamma_centered", action="store_true")
    mesh_mode.add_argument("--monkhorst", dest="gamma_centered", action="store_false")
    generate.set_defaults(gamma_centered=True)
    generate.add_argument("--encut", type=int, default=520)
    generate.add_argument("--ediff", type=float, default=1e-5)
    generate.add_argument("--ediffg", type=float, default=-0.02)
    generate.add_argument("--ismear", type=int, default=0)
    generate.add_argument("--sigma", type=float, default=0.05)
    generate.add_argument("--ibrion", type=int, default=2)
    generate.add_argument("--isif", type=int, default=3)
    generate.add_argument("--nsw", type=int, default=120)
    generate.add_argument("--ispin", type=int, default=2)
    generate.add_argument("--magmom", type=str, default=None)
    generate.add_argument(
        "--incar-override",
        action="append",
        default=[],
        help="Additional INCAR override as KEY=VALUE (repeatable)",
    )
    _add_shared_backend_args(generate)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run CLI command and return process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)

    bridge = GuiBackendBridge(mode=args.mode, api_base_url=args.api_base_url)

    if args.command == "summary":
        return _run_summary(bridge, args)

    if args.command == "batch-summary":
        return _run_batch_summary(bridge, args)

    if args.command == "batch-diagnostics":
        return _run_batch_diagnostics(bridge, args)

    if args.command == "diagnostics":
        return _run_diagnostics(bridge, args)

    if args.command == "convergence-profile":
        return _run_convergence_profile(bridge, args)

    if args.command == "ionic-series":
        return _run_ionic_series(bridge, args)

    if args.command == "export-tabular":
        return _run_export_tabular(bridge, args)

    if args.command == "electronic-metadata":
        return _run_electronic_metadata(bridge, args)

    if args.command == "generate-relax-input":
        return _run_generate_relax_input(bridge, args)

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _run_summary(bridge: GuiBackendBridge, args: argparse.Namespace) -> int:
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


def _run_batch_summary(bridge: GuiBackendBridge, args: argparse.Namespace) -> int:
    try:
        data = bridge.batch_summarize_outcars(
            outcar_paths=args.outcar_paths,
            fail_fast=args.fail_fast,
        )
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    print(json.dumps(data, indent=2))
    return 0


def _run_batch_diagnostics(bridge: GuiBackendBridge, args: argparse.Namespace) -> int:
    try:
        data = bridge.batch_diagnose_outcars(
            outcar_paths=args.outcar_paths,
            energy_tolerance_ev=args.energy_tol,
            force_tolerance_ev_per_a=args.force_tol,
            fail_fast=args.fail_fast,
        )
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    print(json.dumps(data, indent=2))
    return 0


def _run_diagnostics(bridge: GuiBackendBridge, args: argparse.Namespace) -> int:
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


def _run_convergence_profile(bridge: GuiBackendBridge, args: argparse.Namespace) -> int:
    try:
        data = bridge.build_convergence_profile(outcar_path=args.outcar_path)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    print(json.dumps(data, indent=2))
    return 0


def _run_ionic_series(bridge: GuiBackendBridge, args: argparse.Namespace) -> int:
    try:
        data = bridge.build_ionic_series(outcar_path=args.outcar_path)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    print(json.dumps(data, indent=2))
    return 0


def _run_export_tabular(bridge: GuiBackendBridge, args: argparse.Namespace) -> int:
    delimiter_lookup = {
        "comma": ",",
        "semicolon": ";",
        "tab": "\t",
    }
    delimiter = delimiter_lookup[args.delimiter]

    try:
        data = bridge.export_outcar_tabular(
            outcar_path=args.outcar_path,
            dataset=args.dataset,
            delimiter=delimiter,
        )

        if args.output_file:
            output_path = Path(args.output_file).expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(data["content"], encoding="utf-8")
            data["written_file"] = str(output_path)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    print(json.dumps(data, indent=2))
    return 0


def _run_electronic_metadata(bridge: GuiBackendBridge, args: argparse.Namespace) -> int:
    try:
        data = bridge.parse_electronic_metadata(
            eigenval_path=args.eigenval_path,
            doscar_path=args.doscar_path,
        )
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    print(json.dumps(data, indent=2))
    return 0


def _run_generate_relax_input(bridge: GuiBackendBridge, args: argparse.Namespace) -> int:
    try:
        structure = _load_json_file(args.structure_json)
        overrides = _parse_incar_overrides(args.incar_override)
        data = bridge.generate_relax_input(
            structure=structure,
            kmesh=(args.kmesh[0], args.kmesh[1], args.kmesh[2]),
            gamma_centered=args.gamma_centered,
            encut=args.encut,
            ediff=args.ediff,
            ediffg=args.ediffg,
            ismear=args.ismear,
            sigma=args.sigma,
            ibrion=args.ibrion,
            isif=args.isif,
            nsw=args.nsw,
            ispin=args.ispin,
            magmom=args.magmom,
            incar_overrides=overrides,
        )

        if args.output_dir:
            output_dir = Path(args.output_dir).expanduser().resolve()
            output_dir.mkdir(parents=True, exist_ok=True)

            incar_path = output_dir / "INCAR"
            kpoints_path = output_dir / "KPOINTS"
            poscar_path = output_dir / "POSCAR"

            incar_path.write_text(data["incar_text"], encoding="utf-8")
            kpoints_path.write_text(data["kpoints_text"], encoding="utf-8")
            poscar_path.write_text(data["poscar_text"], encoding="utf-8")

            data["written_files"] = {
                "INCAR": str(incar_path),
                "KPOINTS": str(kpoints_path),
                "POSCAR": str(poscar_path),
            }
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    print(json.dumps(data, indent=2))
    return 0


def _load_json_file(path: str) -> dict[str, Any]:
    with Path(path).expanduser().resolve().open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("structure_json must contain a JSON object")
    return data


def _parse_incar_overrides(items: list[str]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid --incar-override entry: {item}")

        key, raw_value = item.split("=", 1)
        key = key.strip().upper()
        value = _coerce_cli_value(raw_value.strip())
        overrides[key] = value
    return overrides


def _coerce_cli_value(raw: str) -> Any:
    token = raw.strip()
    upper = token.upper()

    if upper in {"TRUE", ".TRUE."}:
        return True
    if upper in {"FALSE", ".FALSE."}:
        return False

    try:
        if any(char in token for char in [".", "e", "E"]):
            return float(token)
        return int(token)
    except ValueError:
        return token


if __name__ == "__main__":
    raise SystemExit(main())
