import maya.cmds as cmds

from Workshop.poly.convert import flatten_components
from Workshop.poly.meshes import get_vertex_count


def get_all_verts(
    mesh: str,
) -> list[str]:
    """
    Get all vertices on a polygon mesh.

    Args:
        mesh: Mesh to query.

    Returns:
        Flattened list of polygon vertices.
    """

    vertex_count = get_vertex_count(
        mesh=mesh,
    )

    if not vertex_count:
        return []

    return flatten_components(
        f"{mesh}.vtx[0:{vertex_count - 1}]"
    )


def get_vertex_position(
    vertex: str,
    world_space: bool = True,
) -> tuple[float, float, float]:
    """
    Get the position of a polygon vertex.

    Args:
        vertex: Polygon vertex.
        world_space: Return the position in world space if True.

    Returns:
        XYZ position.
    """

    position = cmds.pointPosition(
        vertex,
        world=world_space,
        local=not world_space,
    )

    return (
        position[0],
        position[1],
        position[2],
    )


def get_vertex_positions(
    vertices: str | list[str],
    world_space: bool = True,
) -> list[tuple[float, float, float]]:
    """
    Get positions for multiple polygon vertices.

    Args:
        vertices: Polygon vertices.
        world_space: Return positions in world space if True.

    Returns:
        List of XYZ positions.
    """

    vertices = flatten_components(
        vertices,
    )

    return [
        get_vertex_position(
            vertex=vertex,
            world_space=world_space,
        )
        for vertex in vertices
    ]


def get_vertex_average_position(
    vertices: str | list[str],
    world_space: bool = True,
) -> tuple[float, float, float]:
    """
    Get the average position of a group of vertices.

    Args:
        vertices: Polygon vertices.
        world_space: Calculate in world space if True.

    Returns:
        Average XYZ position.
    """

    positions = get_vertex_positions(
        vertices=vertices,
        world_space=world_space,
    )

    if not positions:
        raise RuntimeError(
            "No vertices provided."
        )

    count = len(positions)

    x = sum(position[0] for position in positions) / count
    y = sum(position[1] for position in positions) / count
    z = sum(position[2] for position in positions) / count

    return x, y, z