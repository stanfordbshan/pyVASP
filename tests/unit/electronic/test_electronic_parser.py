from __future__ import annotations

from pathlib import Path

import pytest

from pyvasp.core.errors import ParseError
from pyvasp.electronic.parser import ElectronicParser


FIXTURE_EIGENVAL = Path(__file__).resolve().parents[2] / "fixtures" / "EIGENVAL.sample"
FIXTURE_DOS = Path(__file__).resolve().parents[2] / "fixtures" / "DOSCAR.sample"
FIXTURE_DOS_SPIN = Path(__file__).resolve().parents[2] / "fixtures" / "DOSCAR.spin.sample"


def test_parse_eigenval_band_gap() -> None:
    parser = ElectronicParser()
    summary = parser.parse_eigenval_file(FIXTURE_EIGENVAL)

    assert summary.is_metal is False
    assert summary.fundamental_gap_ev == pytest.approx(1.3)
    assert summary.vbm_ev == pytest.approx(-0.5)
    assert summary.cbm_ev == pytest.approx(0.8)
    assert summary.is_direct is True


def test_parse_doscar_metadata_non_spin() -> None:
    parser = ElectronicParser()
    metadata = parser.parse_doscar_file(FIXTURE_DOS)

    assert metadata.nedos == 5
    assert metadata.efermi_ev == pytest.approx(0.5)
    assert metadata.is_spin_polarized is False
    assert metadata.total_dos_at_fermi == pytest.approx(0.4)


def test_parse_doscar_metadata_spin() -> None:
    parser = ElectronicParser()
    metadata = parser.parse_doscar_file(FIXTURE_DOS_SPIN)

    assert metadata.nedos == 4
    assert metadata.is_spin_polarized is True
    assert metadata.total_dos_at_fermi == pytest.approx(0.55)


def test_parse_dos_profile_with_window_filter() -> None:
    parser = ElectronicParser()
    profile = parser.parse_dos_profile(
        doscar_path=FIXTURE_DOS,
        energy_window_ev=1.0,
        max_points=50,
    )

    assert profile.efermi_ev == pytest.approx(0.5)
    assert len(profile.points) == 2
    assert profile.points[0].energy_ev == pytest.approx(0.0)
    assert profile.points[1].energy_ev == pytest.approx(1.0)
    assert profile.points[0].energy_relative_ev == pytest.approx(-0.5)
    assert profile.points[1].energy_relative_ev == pytest.approx(0.5)


def test_parse_dos_profile_downsamples_and_warns() -> None:
    parser = ElectronicParser()
    profile = parser.parse_dos_profile(
        doscar_path=FIXTURE_DOS,
        energy_window_ev=20.0,
        max_points=3,
    )

    assert len(profile.points) == 3
    assert profile.points[0].energy_ev == pytest.approx(-5.0)
    assert profile.points[1].energy_ev == pytest.approx(0.0)
    assert profile.points[2].energy_ev == pytest.approx(5.0)
    assert any("downsampled" in warning for warning in profile.warnings)


def test_parse_eigenval_invalid_raises() -> None:
    parser = ElectronicParser()
    with pytest.raises(ParseError):
        parser.parse_eigenval_file(Path("/missing/EIGENVAL"))
