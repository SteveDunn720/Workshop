from dataclasses import dataclass

from Workshop.guide.placement.solve import solve_position
from Workshop.guide.placement.structs import (
    GuidePlacement,
    SplinePlacement,
)


@dataclass
class SplinePlacementResult:
    lower: tuple[float, float, float]
    upper: tuple[float, float, float]


def solve_spline_placement(
    placement: SplinePlacement,
    mesh: str,
    uv_set: str = "PG_Guides",
) -> SplinePlacementResult:
    """Solve the endpoint positions for a spline guide."""

    lower = solve_position(
        placement=GuidePlacement(
            name=placement.lower_name,
            region=placement.lower_region,
        ),
        mesh=mesh,
        uv_set=uv_set,
    )

    upper = solve_position(
        placement=GuidePlacement(
            name=placement.upper_name,
            region=placement.upper_region,
        ),
        mesh=mesh,
        uv_set=uv_set,
    )

    return SplinePlacementResult(
        lower=lower,
        upper=upper,
    )