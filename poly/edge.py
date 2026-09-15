import maya.cmds as cmds

from Workshop.poly.convert import flatten_components
from Workshop.poly.meshes import get_edge_count


def get_all_edges(
    mesh: str,
) -> list[str]:
    """
    Get all edges on a polygon mesh.

    Args:
        mesh: Mesh to query.

    Returns:
        Flattened list of polygon edges.
    """

    edge_count = get_edge_count(mesh=mesh)

    if not edge_count:
        return []

    return flatten_components(
        f"{mesh}.e[0:{edge_count - 1}]"
    )


def get_connected_edges(
    edge: str,
) -> list[str]:
    """
    Get edges directly connected to an edge.

    Args:
        edge: Polygon edge.

    Returns:
        Flattened list of connected edges.
    """

    vertices = cmds.polyListComponentConversion(
        edge,
        fromEdge=True,
        toVertex=True,
    )

    connected_edges = cmds.polyListComponentConversion(
        vertices,
        fromVertex=True,
        toEdge=True,
    )

    edges = flatten_components(
        connected_edges or []
    )

    return [
        connected_edge
        for connected_edge in edges
        if connected_edge != edge
    ]




def split_connected_edges(
    edges: list[str],
) -> list[list[str]]:
    """
    Split edges into separate connected groups.

    Args:
        edges: Polygon edges to separate.

    Returns:
        List of connected edge groups.
    """

    remaining = set(
        flatten_components(edges)
    )

    groups = []

    while remaining:
        start_edge = remaining.pop()

        group = [start_edge]
        pending = [start_edge]

        while pending:
            current_edge = pending.pop()

            connected_edges = get_connected_edges(
                current_edge
            )

            for connected_edge in connected_edges:
                if connected_edge not in remaining:
                    continue

                remaining.remove(connected_edge)

                group.append(connected_edge)
                pending.append(connected_edge)

        groups.append(group)

    return groups