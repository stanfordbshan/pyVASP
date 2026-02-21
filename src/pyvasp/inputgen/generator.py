"""Input-generation algorithms for common VASP workflows."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from pyvasp.core.models import GeneratedInputBundle, RelaxInputSpec


class RelaxInputGenerator:
    """Generate INCAR/KPOINTS/POSCAR for standard geometry relaxation."""

    def generate_relax_input(self, spec: RelaxInputSpec) -> GeneratedInputBundle:
        """Render a transport-neutral VASP input bundle from domain spec."""

        incar_text = self._render_incar(spec)
        kpoints_text = self._render_kpoints(spec)
        poscar_text = self._render_poscar(spec)

        return GeneratedInputBundle(
            system_name=spec.structure.comment,
            n_atoms=len(spec.structure.atoms),
            incar_text=incar_text,
            kpoints_text=kpoints_text,
            poscar_text=poscar_text,
            warnings=(),
        )

    def _render_incar(self, spec: RelaxInputSpec) -> str:
        lines: "OrderedDict[str, Any]" = OrderedDict(
            [
                ("SYSTEM", spec.structure.comment),
                ("ENCUT", spec.encut),
                ("PREC", "Accurate"),
                ("EDIFF", spec.ediff),
                ("EDIFFG", spec.ediffg),
                ("IBRION", spec.ibrion),
                ("ISIF", spec.isif),
                ("NSW", spec.nsw),
                ("ISMEAR", spec.ismear),
                ("SIGMA", spec.sigma),
                ("ISPIN", spec.ispin),
                ("LREAL", "Auto"),
            ]
        )

        if spec.magmom:
            lines["MAGMOM"] = spec.magmom

        for key, value in spec.incar_overrides.items():
            lines[str(key).upper()] = value

        rendered = [f"{key} = {self._format_incar_value(value)}" for key, value in lines.items()]
        return "\n".join(rendered) + "\n"

    def _render_kpoints(self, spec: RelaxInputSpec) -> str:
        scheme = "Gamma" if spec.gamma_centered else "Monkhorst-Pack"
        kx, ky, kz = spec.kmesh

        return "\n".join(
            [
                "Automatic mesh",
                "0",
                scheme,
                f"{kx} {ky} {kz}",
                "0 0 0",
                "",
            ]
        )

    def _render_poscar(self, spec: RelaxInputSpec) -> str:
        species: list[str] = []
        for atom in spec.structure.atoms:
            if atom.element not in species:
                species.append(atom.element)

        counts = [sum(1 for atom in spec.structure.atoms if atom.element == element) for element in species]

        lines: list[str] = [spec.structure.comment, "1.0"]

        for vec in spec.structure.lattice_vectors:
            lines.append(f"{vec[0]: .10f} {vec[1]: .10f} {vec[2]: .10f}")

        lines.append(" ".join(species))
        lines.append(" ".join(str(count) for count in counts))
        lines.append("Direct")

        for element in species:
            for atom in spec.structure.atoms:
                if atom.element != element:
                    continue
                x, y, z = atom.frac_coords
                lines.append(f"{x: .10f} {y: .10f} {z: .10f}")

        lines.append("")
        return "\n".join(lines)

    def _format_incar_value(self, value: Any) -> str:
        if isinstance(value, bool):
            return ".TRUE." if value else ".FALSE."
        if isinstance(value, float):
            return f"{value:.8g}"
        return str(value)
