import maya.api.OpenMaya as om

from .build import _get_mesh_dag_path
from .structs import TopologyMap


def _validate_topology(
    source_fn: om.MFnMesh,
    target_fn: om.MFnMesh,
    topology_map: TopologyMap,
):
    """
    Validate meshes against the topology map.
    """

    if source_fn.numVertices != topology_map.source_vertex_count:
        raise ValueError(
            "Source topology does not match TopologyMap.\n"
            f"Expected: {topology_map.source_vertex_count} vertices\n"
            f"Received: {source_fn.numVertices} vertices"
        )

    if target_fn.numVertices != topology_map.target_vertex_count:
        raise ValueError(
            "Target topology does not match TopologyMap.\n"
            f"Expected: {topology_map.target_vertex_count} vertices\n"
            f"Received: {target_fn.numVertices} vertices"
        )


def transfer_positions(
    source: str,
    target: str,
    topology_map: TopologyMap,
):
    """
    Transfer source surface shape onto a target topology using a
    previously generated TopologyMap.

    Args:
        source:
            Mesh sharing the topology used to build the map.

        target:
            Mesh sharing the target topology used to build the map.

        topology_map:
            Stored relationship between the two topologies.
    """

    source_path = _get_mesh_dag_path(source)
    target_path = _get_mesh_dag_path(target)

    source_fn = om.MFnMesh(source_path)
    target_fn = om.MFnMesh(target_path)

    _validate_topology(
        source_fn,
        target_fn,
        topology_map,
    )

    # Work in world space because the map was generated from
    # world-space surface relationships.
    source_points = source_fn.getPoints(
        om.MSpace.kWorld
    )

    target_points = target_fn.getPoints(
        om.MSpace.kWorld
    )

    for binding in topology_map.bindings:

        v0, v1, v2 = binding.source_vertices
        w0, w1, w2 = binding.barycentric

        p0 = source_points[v0]
        p1 = source_points[v1]
        p2 = source_points[v2]

        point = om.MPoint(
            om.MVector(p0) * w0 +
            om.MVector(p1) * w1 +
            om.MVector(p2) * w2
        )

        target_points[binding.target_index] = point

    target_fn.setPoints(
        target_points,
        om.MSpace.kWorld,
    )