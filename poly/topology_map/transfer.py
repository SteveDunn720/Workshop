import maya.api.OpenMaya as om

from .fingerprint import (
    _get_mesh_dag_path,
    validate_topology,
)

from .snapshot import validate_snapshot

from .structs import (
    MeshSnapshot,
    TopologyMap,
)


def _calculate_target_positions(
    source_positions: list[tuple[float, float, float]],
    topology_map: TopologyMap,
) -> om.MPointArray:
    """
    Calculate target positions from source vertex data and a
    TopologyMap.
    """

    if (
        len(source_positions)
        != topology_map.source_fingerprint.vertex_count
    ):
        raise ValueError(
            "Source position count does not match "
            "TopologyMap source topology."
        )

    target_count = (
        topology_map.target_fingerprint.vertex_count
    )

    # Initialize to correct size.
    target_positions = om.MPointArray(
        target_count,
        om.MPoint(),
    )

    for binding in topology_map.bindings:

        v0, v1, v2 = binding.source_vertices
        w0, w1, w2 = binding.barycentric

        p0 = om.MVector(
            *source_positions[v0]
        )

        p1 = om.MVector(
            *source_positions[v1]
        )

        p2 = om.MVector(
            *source_positions[v2]
        )

        position = (
            p0 * w0
            + p1 * w1
            + p2 * w2
        )

        target_positions[
            binding.target_index
        ] = om.MPoint(position)

    return target_positions


def transfer_positions(
    source: str,
    target: str,
    topology_map: TopologyMap,
):
    """
    Transfer shape from a Maya source mesh to a Maya target mesh using
    a previously generated TopologyMap.

    The source may have a completely different form from the mesh used
    when the TopologyMap was originally generated, provided its
    topology is identical.
    """

    validate_topology(
        source,
        topology_map.source_fingerprint,
    )

    validate_topology(
        target,
        topology_map.target_fingerprint,
    )

    source_path = _get_mesh_dag_path(source)
    source_fn = om.MFnMesh(source_path)

    source_points = source_fn.getPoints(
        om.MSpace.kObject
    )

    source_positions = [
        (
            point.x,
            point.y,
            point.z,
        )
        for point in source_points
    ]

    transfer_positions_from_data(
        source_positions=source_positions,
        target=target,
        topology_map=topology_map,
    )


def transfer_positions_from_data(
    source_positions: list[tuple[float, float, float]],
    target: str,
    topology_map: TopologyMap,
):
    """
    Conform a Maya target mesh using source vertex positions that do
    not need to come from a mesh currently in the scene.
    """

    validate_topology(
        target,
        topology_map.target_fingerprint,
    )

    target_path = _get_mesh_dag_path(target)
    target_fn = om.MFnMesh(target_path)

    target_positions = _calculate_target_positions(
        source_positions=source_positions,
        topology_map=topology_map,
    )

    target_fn.setPoints(
        target_positions,
        om.MSpace.kObject,
    )


def transfer_positions_from_snapshot(
    snapshot: MeshSnapshot,
    target: str,
    topology_map: TopologyMap,
):
    """
    Conform a target using a standalone MeshSnapshot.
    """

    validate_snapshot(
        snapshot,
        topology_map.source_fingerprint,
    )

    transfer_positions_from_data(
        source_positions=snapshot.positions,
        target=target,
        topology_map=topology_map,
    )


def conform_from_topology_map(
    target: str,
    topology_map: TopologyMap,
):
    """
    Conform a target mesh using the source snapshot embedded inside a
    TopologyMap.
    """

    if topology_map.source_snapshot is None:
        raise ValueError(
            "TopologyMap does not contain an embedded "
            "source snapshot."
        )

    transfer_positions_from_snapshot(
        snapshot=topology_map.source_snapshot,
        target=target,
        topology_map=topology_map,
    )


def build_conformed_mesh(
    topology_map: TopologyMap,
    name: str = "conformed_mesh",
) -> str:
    """
    Build the target topology from stored data and conform it to the
    stored source form.

    Neither the source nor target Maya mesh needs to exist.
    """

    if topology_map.source_snapshot is None:
        raise ValueError(
            "TopologyMap does not contain a source snapshot."
        )

    if topology_map.target_snapshot is None:
        raise ValueError(
            "TopologyMap does not contain a target snapshot."
        )

    # Import here to avoid unnecessary module dependencies.
    from .snapshot import build_mesh_from_snapshot

    # ---------------------------------------------------------
    # Build target topology
    # ---------------------------------------------------------

    target = build_mesh_from_snapshot(
        snapshot=topology_map.target_snapshot,
        name=name,
    )

    # ---------------------------------------------------------
    # Conform target to source snapshot
    # ---------------------------------------------------------

    transfer_positions_from_snapshot(
        snapshot=topology_map.source_snapshot,
        target=target,
        topology_map=topology_map,
    )

    return target