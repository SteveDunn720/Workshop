import maya.cmds as cmds


def get_edges(mesh: str) -> list[str]:
    """Return all edges on a mesh."""
    return cmds.ls(f"{mesh}.e[*]", flatten=True) or []


def get_edge_vertices(edge: str) -> list[str]:
    """Return the two vertices belonging to an edge."""
    vertices = cmds.polyListComponentConversion(
        edge,
        fromEdge=True,
        toVertex=True,
    )

    return cmds.ls(vertices, flatten=True) or []


def get_edge_faces(edge: str) -> list[str]:
    """Return faces connected to an edge."""
    faces = cmds.polyListComponentConversion(
        edge,
        fromEdge=True,
        toFace=True,
    )

    return cmds.ls(faces, flatten=True) or []


def get_connected_edges(edge: str) -> list[str]:
    """Return all edges connected to either vertex of an edge."""
    vertices = get_edge_vertices(edge)

    connected = cmds.polyListComponentConversion(
        vertices,
        fromVertex=True,
        toEdge=True,
    )

    connected = cmds.ls(connected, flatten=True) or []

    return [
        connected_edge
        for connected_edge in connected
        if connected_edge != edge
    ]


def get_edge_index(edge: str) -> int:
    """Get the integer index from an edge component."""
    return int(
        edge.rsplit("[", 1)[1].rstrip("]")
    )


def get_edge_loop(edge: str) -> list[str]:
    """Return the full edge loop containing the supplied edge."""

    mesh = edge.split(".e[", 1)[0]
    edge_index = get_edge_index(edge)

    loop_indices = cmds.polySelect(
        mesh,
        edgeLoop=edge_index,
        noSelection=True,
    ) or []

    return [
        f"{mesh}.e[{index}]"
        for index in loop_indices
    ]


def get_edge_ring(edge: str) -> list[str]:
    """Return the full edge ring containing the supplied edge."""

    mesh = edge.split(".e[", 1)[0]
    edge_index = get_edge_index(edge)

    ring_indices = cmds.polySelect(
        mesh,
        edgeRing=edge_index,
        noSelection=True,
    ) or []

    return [
        f"{mesh}.e[{index}]"
        for index in ring_indices
    ]


def is_edge(component: str) -> bool:
    return ".e[" in component


def get_component_mesh(component: str) -> str:
    return component.split(".", 1)[0]