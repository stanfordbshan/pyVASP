"""Shared payload mapping and validation for adapter-facing contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import re
from pathlib import Path
from typing import Any

from pyvasp.core.errors import ValidationError
from pyvasp.core.models import (
    BandGapSummary,
    ConvergenceProfile,
    DosMetadata,
    ElectronicStructureMetadata,
    GeneratedInputBundle,
    OutcarDiagnostics,
    OutcarIonicSeries,
    OutcarSummary,
    RelaxInputSpec,
    RelaxStructure,
    StressTensor,
    StructureAtom,
)
from pyvasp.core.validators import validate_file_path, validate_outcar_path

try:  # pragma: no cover - import guarded for portability
    from ase.data import atomic_numbers as ASE_ATOMIC_NUMBERS
except Exception:  # pragma: no cover - fallback when ASE is unavailable
    ASE_ATOMIC_NUMBERS = {}

ELEMENT_RE = re.compile(r"^[A-Z][a-z]?$")
INCAR_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


@dataclass(frozen=True)
class SummaryRequestPayload:
    """Canonical request payload for OUTCAR summarization."""

    outcar_path: str
    include_history: bool = False

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "SummaryRequestPayload":
        path_value = raw.get("outcar_path")
        include_history = bool(raw.get("include_history", False))

        resolved = validate_outcar_path(str(path_value) if path_value is not None else "")
        return cls(outcar_path=str(resolved), include_history=include_history)

    def validated_path(self) -> Path:
        return validate_outcar_path(self.outcar_path)


@dataclass(frozen=True)
class DiagnosticsRequestPayload:
    """Canonical request payload for OUTCAR diagnostics."""

    outcar_path: str
    energy_tolerance_ev: float = 1e-4
    force_tolerance_ev_per_a: float = 0.02

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "DiagnosticsRequestPayload":
        path_value = raw.get("outcar_path")
        resolved = validate_outcar_path(str(path_value) if path_value is not None else "")

        energy_tolerance_ev = _coerce_positive_float(raw.get("energy_tolerance_ev", 1e-4), "energy_tolerance_ev")
        force_tolerance_ev_per_a = _coerce_positive_float(
            raw.get("force_tolerance_ev_per_a", 0.02),
            "force_tolerance_ev_per_a",
        )

        return cls(
            outcar_path=str(resolved),
            energy_tolerance_ev=energy_tolerance_ev,
            force_tolerance_ev_per_a=force_tolerance_ev_per_a,
        )

    def validated_path(self) -> Path:
        return validate_outcar_path(self.outcar_path)


@dataclass(frozen=True)
class ConvergenceProfileRequestPayload:
    """Canonical request payload for OUTCAR convergence profile."""

    outcar_path: str

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "ConvergenceProfileRequestPayload":
        path_value = raw.get("outcar_path")
        resolved = validate_outcar_path(str(path_value) if path_value is not None else "")
        return cls(outcar_path=str(resolved))

    def validated_path(self) -> Path:
        return validate_outcar_path(self.outcar_path)


@dataclass(frozen=True)
class IonicSeriesRequestPayload:
    """Canonical request payload for OUTCAR ionic-series visualization data."""

    outcar_path: str

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "IonicSeriesRequestPayload":
        path_value = raw.get("outcar_path")
        resolved = validate_outcar_path(str(path_value) if path_value is not None else "")
        return cls(outcar_path=str(resolved))

    def validated_path(self) -> Path:
        return validate_outcar_path(self.outcar_path)


@dataclass(frozen=True)
class ExportTabularRequestPayload:
    """Canonical request payload for OUTCAR tabular export."""

    outcar_path: str
    dataset: str = "ionic_series"
    delimiter: str = ","

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "ExportTabularRequestPayload":
        path_value = raw.get("outcar_path")
        resolved = validate_outcar_path(str(path_value) if path_value is not None else "")

        dataset = str(raw.get("dataset", "ionic_series")).strip().lower()
        if dataset not in {"convergence_profile", "ionic_series"}:
            raise ValidationError("dataset must be one of: convergence_profile, ionic_series")

        delimiter = _normalize_tabular_delimiter(raw.get("delimiter", ","))

        return cls(
            outcar_path=str(resolved),
            dataset=dataset,
            delimiter=delimiter,
        )

    def validated_path(self) -> Path:
        return validate_outcar_path(self.outcar_path)


@dataclass(frozen=True)
class ElectronicMetadataRequestPayload:
    """Canonical request payload for EIGENVAL/DOSCAR metadata parsing."""

    eigenval_path: str | None = None
    doscar_path: str | None = None

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "ElectronicMetadataRequestPayload":
        eigenval = _parse_optional_file(
            raw.get("eigenval_path"),
            field_name="eigenval_path",
            label="EIGENVAL",
        )
        doscar = _parse_optional_file(
            raw.get("doscar_path"),
            field_name="doscar_path",
            label="DOSCAR",
        )

        if eigenval is None and doscar is None:
            raise ValidationError("At least one of eigenval_path or doscar_path must be provided")

        return cls(eigenval_path=eigenval, doscar_path=doscar)

    def validated_paths(self) -> tuple[Path | None, Path | None]:
        eigenval = None if self.eigenval_path is None else validate_file_path(
            self.eigenval_path,
            field_name="eigenval_path",
            label="EIGENVAL",
        )
        doscar = None if self.doscar_path is None else validate_file_path(
            self.doscar_path,
            field_name="doscar_path",
            label="DOSCAR",
        )
        return (eigenval, doscar)


@dataclass(frozen=True)
class GenerateRelaxInputRequestPayload:
    """Canonical request payload for VASP relaxation input generation."""

    structure: RelaxStructure
    kmesh: tuple[int, int, int] = (6, 6, 6)
    gamma_centered: bool = True
    encut: int = 520
    ediff: float = 1e-5
    ediffg: float = -0.02
    ismear: int = 0
    sigma: float = 0.05
    ibrion: int = 2
    isif: int = 3
    nsw: int = 120
    ispin: int = 2
    magmom: str | None = None
    incar_overrides: tuple[tuple[str, Any], ...] = ()

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "GenerateRelaxInputRequestPayload":
        structure = _parse_structure(raw.get("structure"))
        kmesh = _parse_kmesh(raw.get("kmesh", (6, 6, 6)))

        encut = _coerce_positive_int(raw.get("encut", 520), "encut")
        ediff = _coerce_positive_float(raw.get("ediff", 1e-5), "ediff")
        ediffg = _coerce_float(raw.get("ediffg", -0.02), "ediffg")
        ismear = _coerce_int(raw.get("ismear", 0), "ismear")
        sigma = _coerce_positive_float(raw.get("sigma", 0.05), "sigma")
        ibrion = _coerce_int(raw.get("ibrion", 2), "ibrion")
        isif = _coerce_int(raw.get("isif", 3), "isif")
        nsw = _coerce_positive_int(raw.get("nsw", 120), "nsw")
        ispin = _coerce_int(raw.get("ispin", 2), "ispin")

        if ispin not in (1, 2):
            raise ValidationError("ispin must be 1 or 2")

        magmom = raw.get("magmom")
        if magmom is not None:
            magmom = str(magmom).strip() or None

        overrides_raw = raw.get("incar_overrides") or {}
        if not isinstance(overrides_raw, dict):
            raise ValidationError("incar_overrides must be an object/map")
        overrides_normalized: list[tuple[str, Any]] = []
        for key, value in sorted(overrides_raw.items()):
            normalized_key = str(key).upper().strip()
            if not normalized_key or not INCAR_KEY_RE.match(normalized_key):
                raise ValidationError(
                    f"Invalid INCAR override key: {key}",
                    details={"field": "incar_overrides"},
                )
            overrides_normalized.append((normalized_key, value))
        overrides = tuple(overrides_normalized)

        if encut < 150:
            raise ValidationError("encut must be >= 150 eV for reliable relax input generation")
        if nsw > 5000:
            raise ValidationError("nsw must be <= 5000")
        if abs(ediffg) < 1e-12:
            raise ValidationError("ediffg must be non-zero")

        return cls(
            structure=structure,
            kmesh=kmesh,
            gamma_centered=bool(raw.get("gamma_centered", True)),
            encut=encut,
            ediff=ediff,
            ediffg=ediffg,
            ismear=ismear,
            sigma=sigma,
            ibrion=ibrion,
            isif=isif,
            nsw=nsw,
            ispin=ispin,
            magmom=magmom,
            incar_overrides=overrides,
        )

    def to_spec(self) -> RelaxInputSpec:
        """Convert request payload into domain generation spec."""

        return RelaxInputSpec(
            structure=self.structure,
            kmesh=self.kmesh,
            gamma_centered=self.gamma_centered,
            encut=self.encut,
            ediff=self.ediff,
            ediffg=self.ediffg,
            ismear=self.ismear,
            sigma=self.sigma,
            ibrion=self.ibrion,
            isif=self.isif,
            nsw=self.nsw,
            ispin=self.ispin,
            magmom=self.magmom,
            incar_overrides=dict(self.incar_overrides),
        )


@dataclass(frozen=True)
class SummaryResponsePayload:
    """Canonical response payload consumed by API/GUI/CLI adapters."""

    source_path: str
    system_name: str | None
    nions: int | None
    ionic_steps: int
    electronic_iterations: int
    final_total_energy_ev: float | None
    final_fermi_energy_ev: float | None
    max_force_ev_per_a: float | None
    energy_history: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]

    @classmethod
    def from_summary(
        cls,
        summary: OutcarSummary,
        *,
        include_history: bool,
    ) -> "SummaryResponsePayload":
        history: tuple[dict[str, Any], ...] = ()
        if include_history:
            history = tuple(
                {
                    "ionic_step": point.ionic_step,
                    "total_energy_ev": point.total_energy_ev,
                }
                for point in summary.energy_history
            )

        return cls(
            source_path=summary.source_path,
            system_name=summary.system_name,
            nions=summary.nions,
            ionic_steps=summary.ionic_steps,
            electronic_iterations=summary.electronic_iterations,
            final_total_energy_ev=summary.final_total_energy_ev,
            final_fermi_energy_ev=summary.final_fermi_energy_ev,
            max_force_ev_per_a=summary.max_force_ev_per_a,
            energy_history=history,
            warnings=summary.warnings,
        )

    def to_mapping(self) -> dict[str, Any]:
        """Serialize to a transport-neutral mapping for adapters."""

        mapped = asdict(self)
        mapped["warnings"] = list(self.warnings)
        mapped["energy_history"] = list(self.energy_history)
        return mapped


@dataclass(frozen=True)
class DiagnosticsResponsePayload:
    """Canonical diagnostics response consumed by API/GUI/CLI adapters."""

    source_path: str
    system_name: str | None
    nions: int | None
    ionic_steps: int
    electronic_iterations: int
    final_total_energy_ev: float | None
    final_fermi_energy_ev: float | None
    max_force_ev_per_a: float | None
    external_pressure_kb: float | None
    stress_tensor_kb: dict[str, float] | None
    magnetization: dict[str, Any] | None
    convergence: dict[str, Any]
    warnings: tuple[str, ...]

    @classmethod
    def from_diagnostics(cls, diagnostics: OutcarDiagnostics) -> "DiagnosticsResponsePayload":
        stress_tensor = _serialize_stress_tensor(diagnostics.stress_tensor_kb)
        magnetization = _serialize_magnetization(diagnostics)

        return cls(
            source_path=diagnostics.source_path,
            system_name=diagnostics.summary.system_name,
            nions=diagnostics.summary.nions,
            ionic_steps=diagnostics.summary.ionic_steps,
            electronic_iterations=diagnostics.summary.electronic_iterations,
            final_total_energy_ev=diagnostics.summary.final_total_energy_ev,
            final_fermi_energy_ev=diagnostics.summary.final_fermi_energy_ev,
            max_force_ev_per_a=diagnostics.summary.max_force_ev_per_a,
            external_pressure_kb=diagnostics.external_pressure_kb,
            stress_tensor_kb=stress_tensor,
            magnetization=magnetization,
            convergence={
                "energy_tolerance_ev": diagnostics.convergence.energy_tolerance_ev,
                "force_tolerance_ev_per_a": diagnostics.convergence.force_tolerance_ev_per_a,
                "final_energy_change_ev": diagnostics.convergence.final_energy_change_ev,
                "is_energy_converged": diagnostics.convergence.is_energy_converged,
                "is_force_converged": diagnostics.convergence.is_force_converged,
                "is_converged": diagnostics.convergence.is_converged,
            },
            warnings=diagnostics.warnings,
        )

    def to_mapping(self) -> dict[str, Any]:
        mapped = asdict(self)
        mapped["warnings"] = list(self.warnings)
        return mapped


@dataclass(frozen=True)
class ConvergenceProfileResponsePayload:
    """Canonical convergence-profile response consumed by adapters."""

    source_path: str
    points: tuple[dict[str, Any], ...]
    final_total_energy_ev: float | None
    max_force_ev_per_a: float | None
    warnings: tuple[str, ...]

    @classmethod
    def from_profile(
        cls,
        profile: ConvergenceProfile,
        *,
        summary: OutcarSummary,
    ) -> "ConvergenceProfileResponsePayload":
        points = tuple(
            {
                "ionic_step": point.ionic_step,
                "total_energy_ev": point.total_energy_ev,
                "delta_energy_ev": point.delta_energy_ev,
                "relative_energy_ev": point.relative_energy_ev,
            }
            for point in profile.points
        )
        return cls(
            source_path=summary.source_path,
            points=points,
            final_total_energy_ev=summary.final_total_energy_ev,
            max_force_ev_per_a=summary.max_force_ev_per_a,
            warnings=summary.warnings,
        )

    def to_mapping(self) -> dict[str, Any]:
        mapped = asdict(self)
        mapped["warnings"] = list(self.warnings)
        mapped["points"] = list(self.points)
        return mapped


@dataclass(frozen=True)
class IonicSeriesResponsePayload:
    """Canonical ionic-series response consumed by adapters."""

    source_path: str
    points: tuple[dict[str, Any], ...]
    n_steps: int
    warnings: tuple[str, ...]

    @classmethod
    def from_series(cls, series: OutcarIonicSeries) -> "IonicSeriesResponsePayload":
        points = tuple(
            {
                "ionic_step": point.ionic_step,
                "total_energy_ev": point.total_energy_ev,
                "delta_energy_ev": point.delta_energy_ev,
                "relative_energy_ev": point.relative_energy_ev,
                "max_force_ev_per_a": point.max_force_ev_per_a,
                "external_pressure_kb": point.external_pressure_kb,
                "fermi_energy_ev": point.fermi_energy_ev,
            }
            for point in series.points
        )
        return cls(
            source_path=series.source_path,
            points=points,
            n_steps=len(points),
            warnings=series.warnings,
        )

    def to_mapping(self) -> dict[str, Any]:
        mapped = asdict(self)
        mapped["warnings"] = list(self.warnings)
        mapped["points"] = list(self.points)
        return mapped


@dataclass(frozen=True)
class ExportTabularResponsePayload:
    """Canonical OUTCAR tabular-export response consumed by adapters."""

    source_path: str
    dataset: str
    format: str
    delimiter: str
    filename_hint: str
    n_rows: int
    content: str
    warnings: tuple[str, ...]

    def to_mapping(self) -> dict[str, Any]:
        mapped = asdict(self)
        mapped["warnings"] = list(self.warnings)
        return mapped


@dataclass(frozen=True)
class ElectronicMetadataResponsePayload:
    """Canonical EIGENVAL/DOSCAR metadata response consumed by adapters."""

    eigenval_path: str | None
    doscar_path: str | None
    band_gap: dict[str, Any] | None
    dos_metadata: dict[str, Any] | None
    warnings: tuple[str, ...]

    @classmethod
    def from_metadata(cls, metadata: ElectronicStructureMetadata) -> "ElectronicMetadataResponsePayload":
        return cls(
            eigenval_path=metadata.eigenval_path,
            doscar_path=metadata.doscar_path,
            band_gap=_serialize_band_gap(metadata.band_gap),
            dos_metadata=_serialize_dos_metadata(metadata.dos_metadata),
            warnings=metadata.warnings,
        )

    def to_mapping(self) -> dict[str, Any]:
        mapped = asdict(self)
        mapped["warnings"] = list(self.warnings)
        return mapped


@dataclass(frozen=True)
class GenerateRelaxInputResponsePayload:
    """Canonical generated-input response consumed by adapters."""

    system_name: str
    n_atoms: int
    incar_text: str
    kpoints_text: str
    poscar_text: str
    warnings: tuple[str, ...]

    @classmethod
    def from_bundle(cls, bundle: GeneratedInputBundle) -> "GenerateRelaxInputResponsePayload":
        return cls(
            system_name=bundle.system_name,
            n_atoms=bundle.n_atoms,
            incar_text=bundle.incar_text,
            kpoints_text=bundle.kpoints_text,
            poscar_text=bundle.poscar_text,
            warnings=bundle.warnings,
        )

    def to_mapping(self) -> dict[str, Any]:
        mapped = asdict(self)
        mapped["warnings"] = list(self.warnings)
        return mapped


def validate_summary_request(raw: dict[str, Any]) -> SummaryRequestPayload:
    """Map arbitrary adapter payload into canonical summary request object."""

    try:
        return SummaryRequestPayload.from_mapping(raw)
    except ValidationError:
        raise
    except Exception as exc:  # pragma: no cover - defensive normalization
        raise ValidationError(str(exc)) from exc


def validate_diagnostics_request(raw: dict[str, Any]) -> DiagnosticsRequestPayload:
    """Map arbitrary adapter payload into canonical diagnostics request object."""

    try:
        return DiagnosticsRequestPayload.from_mapping(raw)
    except ValidationError:
        raise
    except Exception as exc:  # pragma: no cover - defensive normalization
        raise ValidationError(str(exc)) from exc


def validate_convergence_profile_request(raw: dict[str, Any]) -> ConvergenceProfileRequestPayload:
    """Map arbitrary adapter payload into canonical convergence-profile request."""

    try:
        return ConvergenceProfileRequestPayload.from_mapping(raw)
    except ValidationError:
        raise
    except Exception as exc:  # pragma: no cover - defensive normalization
        raise ValidationError(str(exc)) from exc


def validate_ionic_series_request(raw: dict[str, Any]) -> IonicSeriesRequestPayload:
    """Map arbitrary adapter payload into canonical ionic-series request."""

    try:
        return IonicSeriesRequestPayload.from_mapping(raw)
    except ValidationError:
        raise
    except Exception as exc:  # pragma: no cover - defensive normalization
        raise ValidationError(str(exc)) from exc


def validate_export_tabular_request(raw: dict[str, Any]) -> ExportTabularRequestPayload:
    """Map arbitrary adapter payload into canonical tabular-export request."""

    try:
        return ExportTabularRequestPayload.from_mapping(raw)
    except ValidationError:
        raise
    except Exception as exc:  # pragma: no cover - defensive normalization
        raise ValidationError(str(exc)) from exc


def validate_electronic_metadata_request(raw: dict[str, Any]) -> ElectronicMetadataRequestPayload:
    """Map arbitrary adapter payload into canonical electronic metadata request."""

    try:
        return ElectronicMetadataRequestPayload.from_mapping(raw)
    except ValidationError:
        raise
    except Exception as exc:  # pragma: no cover - defensive normalization
        raise ValidationError(str(exc)) from exc


def validate_generate_relax_input_request(raw: dict[str, Any]) -> GenerateRelaxInputRequestPayload:
    """Map arbitrary adapter payload into canonical relaxation-input request."""

    try:
        return GenerateRelaxInputRequestPayload.from_mapping(raw)
    except ValidationError:
        raise
    except Exception as exc:  # pragma: no cover - defensive normalization
        raise ValidationError(str(exc)) from exc


def _serialize_stress_tensor(tensor: StressTensor | None) -> dict[str, float] | None:
    if tensor is None:
        return None
    return {
        "xx_kb": tensor.xx_kb,
        "yy_kb": tensor.yy_kb,
        "zz_kb": tensor.zz_kb,
        "xy_kb": tensor.xy_kb,
        "yz_kb": tensor.yz_kb,
        "zx_kb": tensor.zx_kb,
    }


def _serialize_magnetization(diagnostics: OutcarDiagnostics) -> dict[str, Any] | None:
    if diagnostics.magnetization is None:
        return None
    return {
        "axis": diagnostics.magnetization.axis,
        "total_moment_mu_b": diagnostics.magnetization.total_moment_mu_b,
        "site_moments_mu_b": list(diagnostics.magnetization.site_moments_mu_b),
    }


def _serialize_band_gap(summary: BandGapSummary | None) -> dict[str, Any] | None:
    if summary is None:
        return None

    channels = [
        {
            "spin": channel.spin,
            "gap_ev": channel.gap_ev,
            "vbm_ev": channel.vbm_ev,
            "cbm_ev": channel.cbm_ev,
            "is_direct": channel.is_direct,
            "kpoint_index_vbm": channel.kpoint_index_vbm,
            "kpoint_index_cbm": channel.kpoint_index_cbm,
            "is_metal": channel.is_metal,
        }
        for channel in summary.channels
    ]

    return {
        "is_spin_polarized": summary.is_spin_polarized,
        "is_metal": summary.is_metal,
        "fundamental_gap_ev": summary.fundamental_gap_ev,
        "vbm_ev": summary.vbm_ev,
        "cbm_ev": summary.cbm_ev,
        "is_direct": summary.is_direct,
        "channel": summary.channel,
        "channels": channels,
    }


def _serialize_dos_metadata(metadata: DosMetadata | None) -> dict[str, Any] | None:
    if metadata is None:
        return None

    return {
        "energy_min_ev": metadata.energy_min_ev,
        "energy_max_ev": metadata.energy_max_ev,
        "nedos": metadata.nedos,
        "efermi_ev": metadata.efermi_ev,
        "is_spin_polarized": metadata.is_spin_polarized,
        "has_integrated_dos": metadata.has_integrated_dos,
        "energy_step_ev": metadata.energy_step_ev,
        "total_dos_at_fermi": metadata.total_dos_at_fermi,
    }


def _parse_structure(raw: Any) -> RelaxStructure:
    if not isinstance(raw, dict):
        raise ValidationError("structure must be an object/map")

    comment = str(raw.get("comment", "Generated by pyVASP")).strip()
    if not comment:
        comment = "Generated by pyVASP"

    vectors_raw = raw.get("lattice_vectors")
    if not isinstance(vectors_raw, (list, tuple)) or len(vectors_raw) != 3:
        raise ValidationError("structure.lattice_vectors must contain exactly 3 vectors")

    vectors: list[tuple[float, float, float]] = []
    for idx, vector in enumerate(vectors_raw, start=1):
        parsed_vector = _parse_vec3(vector, f"structure.lattice_vectors[{idx}]")
        if _vec_norm(parsed_vector) <= 1e-12:
            raise ValidationError(f"structure.lattice_vectors[{idx}] must be non-zero")
        vectors.append(parsed_vector)

    atoms_raw = raw.get("atoms")
    if not isinstance(atoms_raw, (list, tuple)) or not atoms_raw:
        raise ValidationError("structure.atoms must be a non-empty list")

    atoms: list[StructureAtom] = []
    for idx, atom_raw in enumerate(atoms_raw, start=1):
        if not isinstance(atom_raw, dict):
            raise ValidationError(f"structure.atoms[{idx}] must be an object")

        element = _normalize_element(str(atom_raw.get("element", "")))
        _validate_element(element)
        frac = _parse_vec3(atom_raw.get("frac_coords"), f"structure.atoms[{idx}].frac_coords")

        atoms.append(StructureAtom(element=element, frac_coords=frac))

    return RelaxStructure(
        comment=comment,
        lattice_vectors=(vectors[0], vectors[1], vectors[2]),
        atoms=tuple(atoms),
    )


def _parse_kmesh(raw: Any) -> tuple[int, int, int]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 3:
        raise ValidationError("kmesh must contain exactly 3 integers")

    values = []
    for idx, value in enumerate(raw, start=1):
        parsed = _coerce_positive_int(value, f"kmesh[{idx}]")
        if parsed > 64:
            raise ValidationError(f"kmesh[{idx}] must be <= 64")
        values.append(parsed)
    return (values[0], values[1], values[2])


def _parse_vec3(raw: Any, field_name: str) -> tuple[float, float, float]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 3:
        raise ValidationError(f"{field_name} must contain exactly 3 numbers")

    try:
        x, y, z = float(raw[0]), float(raw[1]), float(raw[2])
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must contain numeric values") from exc

    if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
        raise ValidationError(f"{field_name} contains non-finite values")

    return (x, y, z)


def _parse_optional_file(value: Any, *, field_name: str, label: str) -> str | None:
    if value is None:
        return None

    string_value = str(value).strip()
    if not string_value:
        return None

    validated = validate_file_path(string_value, field_name=field_name, label=label)
    return str(validated)


def _normalize_element(raw: str) -> str:
    token = raw.strip()
    if not token:
        return token
    if len(token) == 1:
        return token.upper()
    return token[0].upper() + token[1:].lower()


def _validate_element(element: str) -> None:
    if not ELEMENT_RE.match(element):
        raise ValidationError(f"Invalid element symbol: {element}")
    if ASE_ATOMIC_NUMBERS and element not in ASE_ATOMIC_NUMBERS:
        raise ValidationError(f"Unknown element symbol: {element}")


def _coerce_positive_float(value: Any, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a positive number") from exc

    if number <= 0:
        raise ValidationError(f"{field_name} must be > 0")
    if not math.isfinite(number):
        raise ValidationError(f"{field_name} must be finite")
    return number


def _coerce_float(value: Any, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be numeric") from exc

    if not math.isfinite(number):
        raise ValidationError(f"{field_name} must be finite")
    return number


def _coerce_positive_int(value: Any, field_name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be an integer > 0") from exc

    if number <= 0:
        raise ValidationError(f"{field_name} must be > 0")
    return number


def _coerce_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be an integer") from exc


def _vec_norm(vec: tuple[float, float, float]) -> float:
    return math.sqrt((vec[0] * vec[0]) + (vec[1] * vec[1]) + (vec[2] * vec[2]))


def _normalize_tabular_delimiter(value: Any) -> str:
    raw = str(value)
    if raw == "\t":
        return "\t"
    token = raw.strip().lower()
    named = {
        ",": ",",
        "comma": ",",
        ";": ";",
        "semicolon": ";",
        "\\t": "\t",
        "tab": "\t",
    }
    if token in named:
        return named[token]
    raise ValidationError("delimiter must be one of: comma, semicolon, tab")
