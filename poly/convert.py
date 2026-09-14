import maya.cmds as cmds


def flatten_components(components: str | list[str]) -> list[str]:
    """
    Expand component ranges into individual components.

    Example:
        mesh.f[0:3]

    Becomes:
        mesh.f[0]
        mesh.f[1]
        mesh.f[2]
        mesh.f[3]
    """

    return cmds.ls(
        components,
        flatten=True,
    ) or []


def to_faces(
    components: str | list[str],
) -> list[str]:
    """
    Convert polygon components to faces.

    Args:
        components: Polygon components to convert.

    Returns:
        Individual face components.
    """

    faces = cmds.polyListComponentConversion(
        components,
        toFace=True,
    )

    return flatten_components(faces or [])


def to_edges(
    components: str | list[str],
) -> list[str]:
    """
    Convert polygon components to edges.

    Args:
        components: Polygon components to convert.

    Returns:
        Individual edge components.
    """

    edges = cmds.polyListComponentConversion(
        components,
        toEdge=True,
    )

    return flatten_components(edges or [])


def to_verts(
    components: str | list[str],
) -> list[str]:
    """
    Convert polygon components to vertices.

    Args:
        components: Polygon components to convert.

    Returns:
        Individual vertex components.
    """

    verts = cmds.polyListComponentConversion(
        components,
        toVertex=True,
    )

    return flatten_components(verts or [])


def to_uvs(
    components: str | list[str],
) -> list[str]:
    """
    Convert polygon components to UVs.

    Args:
        components: Polygon components to convert.

    Returns:
        Individual UV components.
    """

    uvs = cmds.polyListComponentConversion(
        components,
        toUV=True,
    )

    return flatten_components(uvs or [])


def to_border_edges(
    components: str | list[str],
) -> list[str]:
    """Convert components to their border edges."""

    edges = cmds.polyListComponentConversion(
        components,
        toEdge=True,
        border=True,
    )

    return flatten_components(edges or [])

def to_internal_edges(
    components: str | list[str],
) -> list[str]:
    """Convert components to edges fully contained by the components."""

    edges = cmds.polyListComponentConversion(
        components,
        toEdge=True,
        internal=True,
    )

    return flatten_components(edges or [])