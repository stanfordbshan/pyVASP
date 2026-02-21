"""Electronic-structure parsing from standard VASP outputs (EIGENVAL, DOSCAR)."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from pyvasp.core.errors import ErrorCode, ParseError
from pyvasp.core.models import (
    BandGapChannel,
    BandGapSummary,
    DosProfile,
    DosProfilePoint,
    DosMetadata,
    ElectronicStructureMetadata,
)


class ElectronicParser:
    """Extract VASPKIT-like band gap and DOS metadata from VASP output files."""

    def parse_metadata(
        self,
        *,
        eigenval_path: Path | None,
        doscar_path: Path | None,
    ) -> ElectronicStructureMetadata:
        """Parse provided electronic-structure files and return combined metadata."""

        band_gap: BandGapSummary | None = None
        dos_metadata: DosMetadata | None = None
        warnings: list[str] = []

        if eigenval_path is not None:
            band_gap = self.parse_eigenval_file(eigenval_path)
        else:
            warnings.append("EIGENVAL not provided; band gap metadata unavailable")

        if doscar_path is not None:
            dos_metadata = self.parse_doscar_file(doscar_path)
        else:
            warnings.append("DOSCAR not provided; DOS metadata unavailable")

        return ElectronicStructureMetadata(
            eigenval_path=str(eigenval_path) if eigenval_path is not None else None,
            doscar_path=str(doscar_path) if doscar_path is not None else None,
            band_gap=band_gap,
            dos_metadata=dos_metadata,
            warnings=tuple(warnings),
        )

    def parse_eigenval_file(self, path: Path) -> BandGapSummary:
        """Parse EIGENVAL and compute spin-resolved band gap summary."""

        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError as exc:
            raise ParseError(
                f"Unable to read EIGENVAL: {path}",
                code=ErrorCode.IO_ERROR,
                details={"path": str(path)},
            ) from exc

        if len(lines) < 8:
            raise ParseError("EIGENVAL appears too short")

        n_kpoints, n_bands = self._parse_counts(lines)

        # Channel lists contain tuples of (energy, occupation, kpoint_idx)
        channels: list[list[tuple[float, float, int]]] = []

        idx = 6
        parsed_kpoints = 0
        while idx < len(lines) and parsed_kpoints < n_kpoints:
            if not lines[idx].strip():
                idx += 1
                continue

            kparts = lines[idx].split()
            if len(kparts) < 4 or not _all_float(kparts[:4]):
                idx += 1
                continue

            parsed_kpoints += 1
            idx += 1

            for _ in range(n_bands):
                if idx >= len(lines):
                    raise ParseError("EIGENVAL ended before all bands were parsed")
                row = lines[idx].split()
                idx += 1

                if not row:
                    continue

                if len(row) == 3:
                    # band_idx, eigenvalue, occupation
                    self._ensure_channel_count(channels, 1)
                    energy = float(row[1])
                    occ = float(row[2])
                    channels[0].append((energy, occ, parsed_kpoints))
                elif len(row) >= 5:
                    # band_idx, eig_up, eig_dn, occ_up, occ_dn
                    self._ensure_channel_count(channels, 2)
                    e_up = float(row[1])
                    e_dn = float(row[2])
                    occ_up = float(row[3])
                    occ_dn = float(row[4])
                    channels[0].append((e_up, occ_up, parsed_kpoints))
                    channels[1].append((e_dn, occ_dn, parsed_kpoints))
                else:
                    raise ParseError(f"Unexpected EIGENVAL band row format: {' '.join(row)}")

        if parsed_kpoints == 0 or not channels:
            raise ParseError("Unable to parse k-point/band data from EIGENVAL")

        spin_labels = ["total"] if len(channels) == 1 else ["up", "down"]
        channel_summaries: list[BandGapChannel] = []

        for spin_label, data in zip(spin_labels, channels):
            summary = self._build_channel_gap(spin_label, data)
            channel_summaries.append(summary)

        is_metal = any(channel.is_metal for channel in channel_summaries)
        if is_metal:
            representative = next(channel for channel in channel_summaries if channel.is_metal)
        else:
            representative = min(channel_summaries, key=lambda item: item.gap_ev)

        return BandGapSummary(
            is_spin_polarized=len(channel_summaries) == 2,
            is_metal=is_metal,
            fundamental_gap_ev=representative.gap_ev,
            vbm_ev=representative.vbm_ev,
            cbm_ev=representative.cbm_ev,
            is_direct=representative.is_direct,
            channel=representative.spin,
            channels=tuple(channel_summaries),
        )

    def parse_doscar_file(self, path: Path) -> DosMetadata:
        """Parse DOSCAR header and total DOS table metadata."""
        parsed = self._parse_doscar_table(path)
        energies = parsed["energies"]
        dos_totals = parsed["dos_totals"]
        efermi = parsed["efermi_ev"]

        energy_step = None
        if len(energies) >= 2:
            energy_step = energies[1] - energies[0]

        idx_fermi = min(range(len(energies)), key=lambda i: abs(energies[i] - efermi))
        dos_at_fermi = dos_totals[idx_fermi]

        return DosMetadata(
            energy_min_ev=parsed["energy_min_ev"],
            energy_max_ev=parsed["energy_max_ev"],
            nedos=parsed["nedos"],
            efermi_ev=efermi,
            is_spin_polarized=parsed["is_spin_polarized"],
            has_integrated_dos=parsed["has_integrated_dos"],
            energy_step_ev=energy_step,
            total_dos_at_fermi=dos_at_fermi,
        )

    def parse_dos_profile(
        self,
        *,
        doscar_path: Path,
        energy_window_ev: float = 5.0,
        max_points: int = 400,
    ) -> DosProfile:
        """Parse DOSCAR into plotting-friendly total DOS points around E-fermi."""

        if energy_window_ev <= 0:
            raise ParseError("energy_window_ev must be > 0")
        if max_points <= 0:
            raise ParseError("max_points must be > 0")

        parsed = self._parse_doscar_table(doscar_path)
        efermi = parsed["efermi_ev"]
        energies = parsed["energies"]
        dos_totals = parsed["dos_totals"]

        selected: list[tuple[float, float]] = []
        for energy, dos_total in zip(energies, dos_totals):
            if abs(energy - efermi) <= energy_window_ev:
                selected.append((energy, dos_total))

        warnings: list[str] = []
        if not selected:
            selected = list(zip(energies, dos_totals))
            warnings.append("Requested energy window had no points; returning full DOS range")

        sampled = selected
        if len(selected) > max_points:
            sampled = [selected[idx] for idx in self._sample_indices(len(selected), max_points)]
            warnings.append(
                f"DOS points were downsampled from {len(selected)} to {len(sampled)} for UI-friendly rendering"
            )

        points = tuple(
            DosProfilePoint(
                index=index + 1,
                energy_ev=energy,
                energy_relative_ev=energy - efermi,
                dos_total=dos_total,
            )
            for index, (energy, dos_total) in enumerate(sampled)
        )

        return DosProfile(
            source_path=str(doscar_path),
            efermi_ev=efermi,
            energy_window_ev=energy_window_ev,
            points=points,
            warnings=tuple(warnings),
        )

    def _parse_counts(self, lines: Sequence[str]) -> tuple[int, int]:
        counts = lines[5].split()
        if len(counts) < 3:
            raise ParseError("Unable to parse EIGENVAL counts line")

        try:
            n_kpoints = int(float(counts[1]))
            n_bands = int(float(counts[2]))
        except ValueError as exc:
            raise ParseError("EIGENVAL counts line contains invalid values") from exc

        if n_kpoints <= 0 or n_bands <= 0:
            raise ParseError("EIGENVAL counts line has non-positive values")

        return (n_kpoints, n_bands)

    def _build_channel_gap(self, spin: str, data: list[tuple[float, float, int]]) -> BandGapChannel:
        occupied = [(energy, kidx) for energy, occ, kidx in data if occ > 1e-3]
        unoccupied = [(energy, kidx) for energy, occ, kidx in data if occ <= 1e-3]

        if not occupied or not unoccupied:
            raise ParseError(f"Insufficient occupied/unoccupied states for spin channel: {spin}")

        vbm_ev, vbm_kidx = max(occupied, key=lambda item: item[0])
        cbm_ev, cbm_kidx = min(unoccupied, key=lambda item: item[0])

        raw_gap = cbm_ev - vbm_ev
        gap_ev = raw_gap if raw_gap > 0 else 0.0
        is_metal = gap_ev <= 1e-6

        return BandGapChannel(
            spin=spin,
            gap_ev=gap_ev,
            vbm_ev=vbm_ev,
            cbm_ev=cbm_ev,
            is_direct=vbm_kidx == cbm_kidx,
            kpoint_index_vbm=vbm_kidx,
            kpoint_index_cbm=cbm_kidx,
            is_metal=is_metal,
        )

    def _ensure_channel_count(self, channels: list[list[tuple[float, float, int]]], count: int) -> None:
        while len(channels) < count:
            channels.append([])

    def _parse_doscar_table(self, path: Path) -> dict[str, object]:
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError as exc:
            raise ParseError(
                f"Unable to read DOSCAR: {path}",
                code=ErrorCode.IO_ERROR,
                details={"path": str(path)},
            ) from exc

        if len(lines) < 7:
            raise ParseError("DOSCAR appears too short")

        header = lines[5].split()
        if len(header) < 4:
            raise ParseError("Unable to parse DOSCAR header line 6")

        try:
            energy_max = float(header[0])
            energy_min = float(header[1])
            nedos = int(float(header[2]))
            efermi = float(header[3])
        except ValueError as exc:
            raise ParseError("DOSCAR header contains non-numeric values") from exc

        if nedos <= 0:
            raise ParseError("DOSCAR NEDOS must be positive")
        if len(lines) < 6 + nedos:
            raise ParseError("DOSCAR ended before total DOS table was complete")

        total_lines = lines[6 : 6 + nedos]
        first_tokens = total_lines[0].split()
        if len(first_tokens) < 2:
            raise ParseError("Unexpected DOSCAR total DOS row format")

        is_spin_polarized = len(first_tokens) >= 5
        has_integrated_dos = len(first_tokens) >= 3

        energies: list[float] = []
        dos_totals: list[float] = []

        for row in total_lines:
            parts = row.split()
            if len(parts) < 2:
                continue

            try:
                energy = float(parts[0])
            except ValueError:
                continue

            try:
                if is_spin_polarized:
                    dos_total = float(parts[1]) + float(parts[2])
                else:
                    dos_total = float(parts[1])
            except (ValueError, IndexError):
                continue

            energies.append(energy)
            dos_totals.append(dos_total)

        if not energies:
            raise ParseError("Unable to parse total DOS data from DOSCAR")

        return {
            "energy_max_ev": energy_max,
            "energy_min_ev": energy_min,
            "nedos": nedos,
            "efermi_ev": efermi,
            "is_spin_polarized": is_spin_polarized,
            "has_integrated_dos": has_integrated_dos,
            "energies": energies,
            "dos_totals": dos_totals,
        }

    def _sample_indices(self, total_points: int, max_points: int) -> list[int]:
        if total_points <= max_points:
            return list(range(total_points))
        if max_points <= 1:
            return [0]

        last_index = total_points - 1
        return [int(i * last_index / (max_points - 1)) for i in range(max_points)]


def _all_float(tokens: Sequence[str]) -> bool:
    try:
        for token in tokens:
            float(token)
    except ValueError:
        return False
    return True
