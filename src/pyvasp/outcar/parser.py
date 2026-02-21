"""OUTCAR parsing logic for common, high-value post-processing metrics."""

from __future__ import annotations

import math
import re
from pathlib import Path

from pyvasp.core.errors import ErrorCode, ParseError
from pyvasp.core.models import (
    EnergyPoint,
    MagnetizationSummary,
    OutcarObservables,
    OutcarSummary,
    StressTensor,
)

SYSTEM_RE = re.compile(r"^\s*SYSTEM\s*=\s*(.+)$")
NIONS_RE = re.compile(r"NIONS\s*=\s*(\d+)")
TOTEN_RE = re.compile(r"free\s+energy\s+TOTEN\s*=\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)")
FERMI_RE = re.compile(r"E-fermi\s*:\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)")
ELEC_ITER_RE = re.compile(r"^\s*(?:DAV|RMM|CG)\s*:\s*\d+")
EXTERNAL_PRESSURE_RE = re.compile(
    r"external\s+pressure\s*=\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)\s*kB",
    re.IGNORECASE,
)
NUM_RE = r"([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)"
STRESS_RE = re.compile(
    rf"^\s*in\s+kB\s+{NUM_RE}\s+{NUM_RE}\s+{NUM_RE}\s+{NUM_RE}\s+{NUM_RE}\s+{NUM_RE}\s*$",
    re.MULTILINE,
)
FORCE_HEADER = "TOTAL-FORCE (eV/Angst)"


class OutcarParser:
    """Parser for extracting converged scalar diagnostics from OUTCAR files."""

    def parse_file(self, outcar_path: Path) -> OutcarSummary:
        """Read and parse an OUTCAR file from disk."""

        text = self._read_file(outcar_path)
        return self.parse_text(text, source_path=str(outcar_path))

    def parse_observables_file(self, outcar_path: Path) -> OutcarObservables:
        """Read and parse diagnostic observables from an OUTCAR file."""

        text = self._read_file(outcar_path)
        return self.parse_observables_text(text, source_path=str(outcar_path))

    def parse_text(self, text: str, *, source_path: str = "<memory>") -> OutcarSummary:
        """Parse OUTCAR text and produce a transport-neutral summary."""

        lines = text.splitlines()
        system_name = self._parse_system_name(lines)
        nions = self._parse_nions(text)
        energy_history = self._parse_energy_history(text)
        fermi_energy = self._parse_fermi_energy(text)
        electronic_iterations = self._count_electronic_iterations(lines)
        max_force = self._parse_max_force(lines)

        if not energy_history and system_name is None and nions is None and fermi_energy is None:
            raise ParseError("Input does not look like a valid VASP OUTCAR file")

        warnings: list[str] = []
        if not energy_history:
            warnings.append("No TOTEN energy records were found")
        if fermi_energy is None:
            warnings.append("No Fermi energy records were found")
        if max_force is None:
            warnings.append("No force table was found")

        return OutcarSummary(
            source_path=source_path,
            system_name=system_name,
            nions=nions,
            ionic_steps=len(energy_history),
            electronic_iterations=electronic_iterations,
            final_total_energy_ev=energy_history[-1].total_energy_ev if energy_history else None,
            final_fermi_energy_ev=fermi_energy,
            max_force_ev_per_a=max_force,
            energy_history=tuple(energy_history),
            warnings=tuple(warnings),
        )

    def parse_observables_text(self, text: str, *, source_path: str = "<memory>") -> OutcarObservables:
        """Parse OUTCAR text into diagnostics observables."""

        summary = self.parse_text(text, source_path=source_path)
        lines = text.splitlines()
        external_pressure_kb = self._parse_external_pressure(text)
        stress_tensor_kb = self._parse_stress_tensor(text)
        magnetization = self._parse_magnetization(lines, axis="z")

        warnings: list[str] = []
        if external_pressure_kb is None:
            warnings.append("No external pressure records were found")
        if stress_tensor_kb is None:
            warnings.append("No stress tensor records were found")
        if magnetization is None:
            warnings.append("No magnetization (z) table was found")

        return OutcarObservables(
            source_path=source_path,
            summary=summary,
            external_pressure_kb=external_pressure_kb,
            stress_tensor_kb=stress_tensor_kb,
            magnetization=magnetization,
            warnings=tuple(warnings),
        )

    def _read_file(self, outcar_path: Path) -> str:
        try:
            return outcar_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            raise ParseError(
                f"Unable to read OUTCAR: {outcar_path}",
                code=ErrorCode.IO_ERROR,
                details={"path": str(outcar_path)},
            ) from exc

    def _parse_system_name(self, lines: list[str]) -> str | None:
        for line in lines:
            match = SYSTEM_RE.search(line)
            if match:
                return match.group(1).strip()
        return None

    def _parse_nions(self, text: str) -> int | None:
        match = NIONS_RE.search(text)
        if not match:
            return None
        return int(match.group(1))

    def _parse_energy_history(self, text: str) -> list[EnergyPoint]:
        energies = [float(raw) for raw in TOTEN_RE.findall(text)]
        return [EnergyPoint(ionic_step=index + 1, total_energy_ev=value) for index, value in enumerate(energies)]

    def _parse_fermi_energy(self, text: str) -> float | None:
        matches = FERMI_RE.findall(text)
        if not matches:
            return None
        return float(matches[-1])

    def _parse_external_pressure(self, text: str) -> float | None:
        matches = EXTERNAL_PRESSURE_RE.findall(text)
        if not matches:
            return None
        return float(matches[-1])

    def _parse_stress_tensor(self, text: str) -> StressTensor | None:
        matches = STRESS_RE.findall(text)
        if not matches:
            return None

        last = matches[-1]
        xx, yy, zz, xy, yz, zx = (float(value) for value in last)
        return StressTensor(
            xx_kb=xx,
            yy_kb=yy,
            zz_kb=zz,
            xy_kb=xy,
            yz_kb=yz,
            zx_kb=zx,
        )

    def _parse_magnetization(self, lines: list[str], *, axis: str) -> MagnetizationSummary | None:
        header = f"magnetization ({axis.lower()})"
        latest: MagnetizationSummary | None = None
        idx = 0

        while idx < len(lines):
            if lines[idx].strip().lower() != header:
                idx += 1
                continue

            idx += 1
            while idx < len(lines) and "----" not in lines[idx]:
                idx += 1
            if idx >= len(lines):
                break
            idx += 1

            site_moments: list[float] = []
            total_moment: float | None = None

            while idx < len(lines):
                row = lines[idx].strip()
                if not row:
                    break
                if "----" in row or row.lower().startswith("# of ion"):
                    idx += 1
                    continue

                parts = row.split()
                if not parts:
                    break

                lead = parts[0].lower()
                if lead == "tot":
                    try:
                        total_moment = float(parts[-1])
                    except ValueError:
                        total_moment = None
                    break

                if parts[0].isdigit():
                    try:
                        site_moments.append(float(parts[-1]))
                    except ValueError:
                        pass
                    idx += 1
                    continue

                break

            latest = MagnetizationSummary(
                axis=axis.lower(),
                total_moment_mu_b=total_moment,
                site_moments_mu_b=tuple(site_moments),
            )
            idx += 1

        return latest

    def _count_electronic_iterations(self, lines: list[str]) -> int:
        return sum(1 for line in lines if ELEC_ITER_RE.match(line))

    def _parse_max_force(self, lines: list[str]) -> float | None:
        block_maxima: list[float] = []
        idx = 0

        while idx < len(lines):
            line = lines[idx]
            if FORCE_HEADER not in line:
                idx += 1
                continue

            idx += 1
            while idx < len(lines) and "----" not in lines[idx]:
                idx += 1
            idx += 1

            current_block_max = 0.0
            found_force_row = False
            while idx < len(lines):
                row = lines[idx].strip()
                if not row or "----" in row:
                    break

                parts = row.split()
                if len(parts) < 6:
                    idx += 1
                    continue

                try:
                    fx, fy, fz = map(float, parts[-3:])
                except ValueError:
                    idx += 1
                    continue

                found_force_row = True
                force_norm = math.sqrt((fx * fx) + (fy * fy) + (fz * fz))
                current_block_max = max(current_block_max, force_norm)
                idx += 1

            if found_force_row:
                block_maxima.append(current_block_max)

            idx += 1

        if not block_maxima:
            return None
        return block_maxima[-1]
