import hashlib

import maya.api.OpenMaya as om

from .structs import TopologyFingerprint


def _get_mesh_dag_path(node: str) -> om.MDagPath:
    """
    Get a DAG path pointing to a mesh shape.

    Accepts either a mesh transform or mesh shape.
    """

    selection = om.MSelectionList()
    selection.add(node)

    dag_path = selection.getDagPath(0)

    if dag_path.node().hasFn(om.MFn.kTransform):
        dag_path.extendToShape()

    if not dag_path.node().hasFn(om.MFn.kMesh):
        raise TypeError(
            f"{node} is not a polygon mesh."
        )

    return dag_path


def get_topology_fingerprint(
    mesh: str,
) -> TopologyFingerprint:
    """
    Generate a fingerprint describing polygon topology.

    Vertex positions are ignored.

    Face order and vertex order are intentionally preserved because
    TopologyMap bindings reference specific vertex IDs.
    """

    mesh_path = _get_mesh_dag_path(mesh)
    mesh_fn = om.MFnMesh(mesh_path)

    vertex_count = mesh_fn.numVertices
    edge_count = mesh_fn.numEdges
    face_count = mesh_fn.numPolygons

    connectivity = []

    for face_index in range(face_count):

        vertices = mesh_fn.getPolygonVertices(
            face_index
        )

        connectivity.append(
            ",".join(
                str(index)
                for index in vertices
            )
        )

    connectivity_string = "|".join(connectivity)

    connectivity_hash = hashlib.sha256(
        connectivity_string.encode("utf-8")
    ).hexdigest()

    return TopologyFingerprint(
        vertex_count=vertex_count,
        edge_count=edge_count,
        face_count=face_count,
        connectivity_hash=connectivity_hash,
    )


def fingerprints_match(
    a: TopologyFingerprint,
    b: TopologyFingerprint,
) -> bool:
    """
    Compare two topology fingerprints.
    """

    return (
        a.vertex_count == b.vertex_count
        and a.edge_count == b.edge_count
        and a.face_count == b.face_count
        and a.connectivity_hash == b.connectivity_hash
    )


def validate_topology(
    mesh: str,
    fingerprint: TopologyFingerprint,
):
    """
    Validate that a Maya mesh matches a stored fingerprint.
    """

    current = get_topology_fingerprint(mesh)

    if fingerprints_match(current, fingerprint):
        return

    raise ValueError(
        f"Topology does not match for {mesh}.\n"
        f"\n"
        f"Expected:\n"
        f"    Vertices: {fingerprint.vertex_count}\n"
        f"    Edges:    {fingerprint.edge_count}\n"
        f"    Faces:    {fingerprint.face_count}\n"
        f"    Hash:     {fingerprint.connectivity_hash}\n"
        f"\n"
        f"Received:\n"
        f"    Vertices: {current.vertex_count}\n"
        f"    Edges:    {current.edge_count}\n"
        f"    Faces:    {current.face_count}\n"
        f"    Hash:     {current.connectivity_hash}"
    )