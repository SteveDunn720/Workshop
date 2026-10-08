import maya.api.OpenMaya as om

from Workshop.poly.polygroups import PolyGroup
from Workshop.poly.topology_map.fingerprint import (
    _get_mesh_dag_path,
)


def get_polygroup_vertex_indices(
    polygroup: PolyGroup,
) -> list[int]:
    """
    Get the vertex indices belonging to a polygroup.
    """

    verts = polygroup.get_verts()

    return [
        int(
            vert.split("[")[-1].rstrip("]")
        )
        for vert in verts
    ]


def get_polygroup_center(
    polygroup: PolyGroup,
) -> tuple[float, float, float]:
    """
    Get the average object-space position of all vertices
    belonging to a polygroup.
    """

    vertex_indices = get_polygroup_vertex_indices(
        polygroup
    )

    if not vertex_indices:
        raise RuntimeError(
            f"Polygroup '{polygroup.name}' contains no vertices."
        )

    mesh_path = _get_mesh_dag_path(
        polygroup.mesh
    )

    mesh_fn = om.MFnMesh(
        mesh_path
    )

    points = mesh_fn.getPoints(
        om.MSpace.kObject
    )

    center = om.MVector()

    for index in vertex_indices:
        center += om.MVector(
            points[index]
        )

    center /= len(vertex_indices)

    return (
        center.x,
        center.y,
        center.z,
    )