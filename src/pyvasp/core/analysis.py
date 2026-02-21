"""Domain analysis algorithms independent of transport and parsers."""

from __future__ import annotations

from pyvasp.core.models import (
    ConvergenceProfile,
    ConvergenceProfilePoint,
    ConvergenceReport,
    OutcarSummary,
)


def build_convergence_report(
    summary: OutcarSummary,
    *,
    energy_tolerance_ev: float,
    force_tolerance_ev_per_a: float,
) -> ConvergenceReport:
    """Evaluate OUTCAR convergence status from parsed summary metrics."""

    final_energy_change_ev: float | None = None
    if len(summary.energy_history) >= 2:
        final_energy_change_ev = abs(
            summary.energy_history[-1].total_energy_ev - summary.energy_history[-2].total_energy_ev
        )

    is_energy_converged: bool | None = None
    if final_energy_change_ev is not None:
        is_energy_converged = final_energy_change_ev <= energy_tolerance_ev

    is_force_converged: bool | None = None
    if summary.max_force_ev_per_a is not None:
        is_force_converged = summary.max_force_ev_per_a <= force_tolerance_ev_per_a

    is_converged = bool(is_energy_converged is True and is_force_converged is True)

    return ConvergenceReport(
        energy_tolerance_ev=energy_tolerance_ev,
        force_tolerance_ev_per_a=force_tolerance_ev_per_a,
        final_energy_change_ev=final_energy_change_ev,
        is_energy_converged=is_energy_converged,
        is_force_converged=is_force_converged,
        is_converged=is_converged,
    )


def build_convergence_profile(summary: OutcarSummary) -> ConvergenceProfile:
    """Build chart-ready convergence profile from OUTCAR energy history."""

    if not summary.energy_history:
        return ConvergenceProfile(points=())

    final_energy = summary.energy_history[-1].total_energy_ev
    points: list[ConvergenceProfilePoint] = []

    previous: float | None = None
    for energy in summary.energy_history:
        delta_energy = None if previous is None else energy.total_energy_ev - previous
        points.append(
            ConvergenceProfilePoint(
                ionic_step=energy.ionic_step,
                total_energy_ev=energy.total_energy_ev,
                delta_energy_ev=delta_energy,
                relative_energy_ev=energy.total_energy_ev - final_energy,
            )
        )
        previous = energy.total_energy_ev

    return ConvergenceProfile(points=tuple(points))
