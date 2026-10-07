from dataclasses import dataclass

import maya.api.OpenMaya as om

from Workshop.poly.face import get_face_indices

from .fingerprint import _get_mesh_dag_path


@dataclass
class RegionSurface:
    """
    In-memory source surface for a collection of polygroups.
    """

    intersector: om.MMeshIntersector

    # Local region vertex ID -> original source vertex ID
    vertex_map: dict[int, int]

    # Local region face -> original source face
    face_map: dict[int, int]


def get_polygroup_faces_by_index(
    layer,
) -> dict[int, set[int]]:
    """
    Get face membership for every polygroup in a layer.

    Returns:
        {
            polygroup_index: {face_index, ...}
        }
    """

    return {
        polygroup.index: set(
            get_face_indices(
                polygroup.get_faces()
            )
        )
        for polygroup in layer.polygroups
    }


def get_face_polygroup_lookup(
    layer,
) -> dict[int, int]:
    """
    Build:

        face_index -> polygroup_index
    """

    lookup = {}

    for polygroup in layer.polygroups:

        faces = get_face_indices(
            polygroup.get_faces()
        )

        for face in faces:

            if face in lookup:
                raise RuntimeError(
                    f"Face {face} belongs to multiple "
                    f"polygroups in layer '{layer.name}'."
                )

            lookup[face] = polygroup.index

    return lookup


def get_vertex_polygroup_lookup(
    layer,
) -> dict[int, set[int]]:
    """
    Determine which polygroups touch each vertex.

    A border vertex may belong to more than one polygroup.

    Returns:
        {
            vertex_index: {polygroup_index, ...}
        }
    """

    mesh_path = _get_mesh_dag_path(
        layer.mesh
    )

    mesh_fn = om.MFnMesh(
        mesh_path
    )

    face_lookup = get_face_polygroup_lookup(
        layer
    )

    result = {}

    vertex_iterator = om.MItMeshVertex(
        mesh_path
    )

    while not vertex_iterator.isDone():

        vertex_index = vertex_iterator.index()

        connected_faces = (
            vertex_iterator.getConnectedFaces()
        )

        groups = {
            face_lookup[face]
            for face in connected_faces
            if face in face_lookup
        }

        result[vertex_index] = groups

        vertex_iterator.next()

    return result