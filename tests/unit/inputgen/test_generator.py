from __future__ import annotations

from pyvasp.core.payloads import GenerateRelaxInputRequestPayload
from pyvasp.inputgen.generator import RelaxInputGenerator


def test_relax_input_generator_renders_all_files() -> None:
    request = GenerateRelaxInputRequestPayload.from_mapping(
        {
            "structure": {
                "comment": "Si2",
                "lattice_vectors": [[5.43, 0, 0], [0, 5.43, 0], [0, 0, 5.43]],
                "atoms": [
                    {"element": "Si", "frac_coords": [0, 0, 0]},
                    {"element": "Si", "frac_coords": [0.25, 0.25, 0.25]},
                ],
            },
            "kmesh": [4, 4, 4],
            "magmom": "2*0.0",
            "incar_overrides": {"LWAVE": False},
        }
    )

    bundle = RelaxInputGenerator().generate_relax_input(request.to_spec())

    assert "ENCUT = 520" in bundle.incar_text
    assert "LWAVE = .FALSE." in bundle.incar_text
    assert "Gamma" in bundle.kpoints_text
    assert "Si" in bundle.poscar_text
    assert bundle.n_atoms == 2
