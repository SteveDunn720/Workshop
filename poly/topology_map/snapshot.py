import maya.api.OpenMaya as om
import maya.cmds as cmds

from .fingerprint import (
    _get_mesh_dag_path,
    get_topology_fingerprint,
    validate_topology,
)

from .structs import (
    MeshSnapshot,
    MeshTopology,
    TopologyFingerprint,
)


def create_mesh_snapshot(
    mesh: str,
) -> MeshSnapshot:
    """
    Capture enough mesh data to reconstruct the mesh without the
    original Maya node.
    """

    mesh_path = _get_mesh_dag_path(mesh)
    mesh_fn = om.MFnMesh(mesh_path)

    # ---------------------------------------------------------
    # Positions
    # ---------------------------------------------------------

    points = mesh_fn.getPoints(
        om.MSpace.kObject
    )

    positions = [
        (
            point.x,
            point.y,
            point.z,
        )
        for point in points
    ]

    # ---------------------------------------------------------
    # Polygon topology
    # ---------------------------------------------------------

    faces = []

    for face_index in range(
        mesh_fn.numPolygons
    ):
        vertices = mesh_fn.getPolygonVertices(
            face_index
        )

        faces.append(
            tuple(vertices)
        )

    topology = MeshTopology(
        vertex_count=mesh_fn.numVertices,
        faces=faces,
    )

    return MeshSnapshot(
        fingerprint=get_topology_fingerprint(
            mesh
        ),
        topology=topology,
        positions=positions,
    )


def validate_snapshot(
    snapshot: MeshSnapshot,
    fingerprint: TopologyFingerprint,
):
    """
    Validate that a snapshot belongs to the expected topology.
    """

    if (
        snapshot.fingerprint.vertex_count
        != fingerprint.vertex_count
        or snapshot.fingerprint.edge_count
        != fingerprint.edge_count
        or snapshot.fingerprint.face_count
        != fingerprint.face_count
        or snapshot.fingerprint.connectivity_hash
        != fingerprint.connectivity_hash
    ):
        raise ValueError(
            "MeshSnapshot topology does not match "
            "the expected source topology."
        )

    if len(snapshot.positions) != fingerprint.vertex_count:
        raise ValueError(
            "MeshSnapshot position count does not match "
            "its topology fingerprint."
        )


def build_mesh_from_snapshot(
    snapshot: MeshSnapshot,
    name: str = "mesh",
) -> str:
    """
    Build a Maya polygon mesh from a MeshSnapshot.

    Args:
        snapshot:
            Snapshot containing positions and polygon connectivity.

        name:
            Name for the created mesh transform.

    Returns:
        Created mesh transform.
    """

    import maya.cmds as cmds
    import maya.api.OpenMaya as om

    # ---------------------------------------------------------
    # Points
    # ---------------------------------------------------------

    points = om.MPointArray()

    for position in snapshot.positions:

        points.append(
            om.MPoint(
                position[0],
                position[1],
                position[2],
            )
        )

    # ---------------------------------------------------------
    # Polygon connectivity
    # ---------------------------------------------------------

    polygon_counts = []
    polygon_connects = []

    for face in snapshot.topology.faces:

        polygon_counts.append(
            len(face)
        )

        polygon_connects.extend(
            face
        )

    # ---------------------------------------------------------
    # Create mesh
    # ---------------------------------------------------------

    mesh_fn = om.MFnMesh()

    mesh_object = mesh_fn.create(
        points,
        polygon_counts,
        polygon_connects,
    )

    # ---------------------------------------------------------
    # Resolve transform
    # ---------------------------------------------------------

    dag_fn = om.MFnDagNode(
        mesh_object
    )

    created_node = dag_fn.fullPathName()

    # Depending on what Maya returns, we may already have the
    # transform or we may have the mesh shape.
    if cmds.nodeType(created_node) == "mesh":

        parents = cmds.listRelatives(
            created_node,
            parent=True,
            fullPath=True,
        ) or []

        if not parents:
            raise RuntimeError(
                f"Could not find transform for "
                f"created mesh: {created_node}"
            )

        transform = parents[0]

    else:
        transform = created_node

    # ---------------------------------------------------------
    # Rename transform
    # ---------------------------------------------------------

    transform = cmds.rename(
        transform,
        name,
    )

    return transform