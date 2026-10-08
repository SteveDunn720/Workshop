from Workshop.poly.polygroups import (
    PolyGroup,
    PolyGroupLayer,
    PolyGroupSubLayer,
    get_polygroup,
    read_polygroup_layer_from_scene,
)

from .region import get_polygroup_center
from .structs import GuidePlacement


def solve_position(
    placement: GuidePlacement,
    mesh: str,
    uv_set: str,
) -> tuple[float, float, float]:
    """
    Solve the world-space position of a guide placement.
    """

    layer = read_polygroup_layer_from_scene(
        mesh=mesh,
        uv_set=uv_set,
    )

    polygroup = get_polygroup(
        layer=layer,
        name=placement.region,
    )

    if placement.method == "center":
        position = get_polygroup_center(
            polygroup=polygroup,
        )

    else:
        raise ValueError(
            f"Unsupported guide placement method: "
            f"'{placement.method}'."
        )

    return tuple(
        value + offset
        for value, offset in zip(
            position,
            placement.offset,
        )
    )