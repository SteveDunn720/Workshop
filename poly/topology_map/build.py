import maya.api.OpenMaya as om

from .structs import (
    SurfaceBinding,
    TopologyMap,
)


def _get_dag_path(node: str) -> om.MDagPath:
    """
    Get the DAG path for a Maya node.
    """

    selection = om.MSelectionList()
    selection.add(node)

    return selection.getDagPath(0)


def _get_mesh_dag_path(node: str) -> om.MDagPath:
    """
    Get a DAG path pointing to a mesh shape.

    Accepts either a mesh transform or mesh shape.
    """

    dag_path = _get_dag_path(node)

    if dag_path.node().hasFn(om.MFn.kTransform):
        dag_path.extendToShape()

    if not dag_path.node().hasFn(om.MFn.kMesh):
        raise TypeError(
            f"{node} is not a polygon mesh."
        )

    return dag_path


def build_topology_map(
    source: str,
    target: str,
) -> TopologyMap:
    """
    Build a surface mapping from target topology onto source topology.

    Each target vertex is projected to the closest point on the source
    mesh. The source triangle and barycentric coordinates are stored.

    The resulting map can later reconstruct the target topology from
    any mesh sharing the source topology.

    Args:
        source:
            Source mesh defining the canonical surface.

        target:
            Target topology to bind to the source surface.

    Returns:
        TopologyMap.
    """

    source_path = _get_mesh_dag_path(source)
    target_path = _get_mesh_dag_path(target)

    source_fn = om.MFnMesh(source_path)
    target_fn = om.MFnMesh(target_path)

    source_vertex_count = source_fn.numVertices
    target_vertex_count = target_fn.numVertices

    # ---------------------------------------------------------
    # Build source surface intersector
    # ---------------------------------------------------------

    intersector = om.MMeshIntersector()

    source_matrix = source_path.inclusiveMatrix()

    intersector.create(
        source_path.node(),
        source_matrix,
    )

    # ---------------------------------------------------------
    # Target positions
    # ---------------------------------------------------------

    target_points = target_fn.getPoints(
        om.MSpace.kWorld
    )

    bindings = []

    # ---------------------------------------------------------
    # Bind every target vertex
    # ---------------------------------------------------------

    for target_index, target_point in enumerate(target_points):

        point_on_mesh = intersector.getClosestPoint(
            target_point
        )

        source_face = point_on_mesh.face
        source_triangle = point_on_mesh.triangle

        barycentric = point_on_mesh.barycentricCoords

        w0 = barycentric[0]
        w1 = barycentric[1]
        w2 = 1.0 - w0 - w1

        triangle_vertices = source_fn.getPolygonTriangleVertices(
            source_face,
            source_triangle,
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

    return TopologyMap(
        source_vertex_count=source_vertex_count,
        target_vertex_count=target_vertex_count,
        bindings=bindings,
    )