import maya.api.OpenMaya as om

from .fingerprint import (
    _get_mesh_dag_path,
    get_topology_fingerprint,
)

from .snapshot import create_mesh_snapshot

from .structs import (
    SurfaceBinding,
    TopologyMap,
)


def build_topology_map(
    source: str,
    target: str,
    include_source_snapshot: bool = False,
    include_target_snapshot: bool = False,
) -> TopologyMap:
    """
    Build a reusable surface mapping from target topology onto source
    topology.

    Each target vertex is associated with a triangle on the source
    surface using barycentric coordinates.

    Both meshes should occupy the same object-space form when the map
    is generated.

    Args:
        source:
            Canonical source topology.

        target:
            Target topology to bind to the source.

        include_source_snapshot:
            If True, also store the current source vertex positions
            inside the resulting TopologyMap.

    Returns:
        TopologyMap.
    """

    source_path = _get_mesh_dag_path(source)
    target_path = _get_mesh_dag_path(target)

    source_fn = om.MFnMesh(source_path)
    target_fn = om.MFnMesh(target_path)

    # ---------------------------------------------------------
    # Source surface
    # ---------------------------------------------------------

    intersector = om.MMeshIntersector()

    # Identity matrix means the intersector operates directly in the
    # source mesh's object space.
    intersector.create(
        source_path.node(),
        om.MMatrix(),
    )

    # ---------------------------------------------------------
    # Target positions
    # ---------------------------------------------------------

    target_points = target_fn.getPoints(
        om.MSpace.kObject
    )

    bindings = []

    # ---------------------------------------------------------
    # Bind target vertices
    # ---------------------------------------------------------

    for target_index, target_point in enumerate(
        target_points
    ):

        point_on_mesh = intersector.getClosestPoint(
            target_point
        )

        source_face = point_on_mesh.face
        source_triangle = point_on_mesh.triangle

        # Maya gives us two barycentric values.
        # The third is implicit.
        barycentric = point_on_mesh.barycentricCoords

        w0 = barycentric[0]
        w1 = barycentric[1]
        w2 = 1.0 - w0 - w1

        triangle_vertices = (
            source_fn.getPolygonTriangleVertices(
                source_face,
                source_triangle,
            )
        )

        binding = SurfaceBinding(
            target_index=target_index,

            source_face=source_face,
            source_triangle=source_triangle,

            source_vertices=(
                triangle_vertices[0],
                triangle_vertices[1],
                triangle_vertices[2],
            ),

            barycentric=(
                w0,
                w1,
                w2,
            ),
        )

        bindings.append(binding)

    source_snapshot = None
    target_snapshot = None

    if include_source_snapshot:
        source_snapshot = create_mesh_snapshot(
            source
        )

    if include_target_snapshot:
        target_snapshot = create_mesh_snapshot(
            target
        )

    return TopologyMap(
        source_fingerprint=get_topology_fingerprint(
            source
        ),

        target_fingerprint=get_topology_fingerprint(
            target
        ),

        bindings=bindings,

        source_snapshot=source_snapshot,
        target_snapshot=target_snapshot,
    )