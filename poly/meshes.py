import maya.cmds as cmds

from Workshop.poly.convert import flatten_components


def is_mesh(obj: str) -> bool:
    """
    Check whether an object is a polygon mesh transform or mesh shape.

    Args:
        obj: Object to check.

    Returns:
        True if the object is a polygon mesh.
    """

    if not cmds.objExists(obj):
        return False

    node_type = cmds.nodeType(obj)

    if node_type == "mesh":
        return True

    if node_type == "transform":
        shapes = cmds.listRelatives(
            obj,
            shapes=True,
            noIntermediate=True,
            fullPath=True,
        ) or []

        return any(
            cmds.nodeType(shape) == "mesh"
            for shape in shapes
        )

    return False


def get_mesh_shape(mesh: str) -> str:
    """
    Get the polygon mesh shape from a mesh transform.

    Args:
        mesh: Mesh transform or mesh shape.

    Returns:
        Mesh shape.

    Raises:
        RuntimeError: If no polygon mesh shape is found.
    """

    if not cmds.objExists(mesh):
        raise RuntimeError(
            f"Object does not exist: '{mesh}'."
        )

    if cmds.nodeType(mesh) == "mesh":
        return mesh

    shapes = cmds.listRelatives(
        mesh,
        shapes=True,
        noIntermediate=True,
        fullPath=True,
    ) or []

    for shape in shapes:
        if cmds.nodeType(shape) == "mesh":
            return shape

    raise RuntimeError(
        f"No polygon mesh shape found on '{mesh}'."
    )


def get_mesh_transform(mesh: str) -> str:
    """
    Get the transform belonging to a polygon mesh.

    Args:
        mesh: Mesh transform or mesh shape.

    Returns:
        Mesh transform.
    """

    if not cmds.objExists(mesh):
        raise RuntimeError(
            f"Object does not exist: '{mesh}'."
        )

    if cmds.nodeType(mesh) == "transform":
        if not is_mesh(mesh):
            raise RuntimeError(
                f"Object is not a polygon mesh: '{mesh}'."
            )

        return mesh

    if cmds.nodeType(mesh) == "mesh":
        parent = cmds.listRelatives(
            mesh,
            parent=True,
            fullPath=True,
        )

        if parent:
            return parent[0]

    raise RuntimeError(
        f"Could not find mesh transform for '{mesh}'."
    )


def get_face_count(mesh: str) -> int:
    """
    Get the number of polygon faces on a mesh.

    Args:
        mesh: Mesh transform or shape.

    Returns:
        Number of faces.
    """

    return cmds.polyEvaluate(
        mesh,
        face=True,
    ) or 0


def get_edge_count(mesh: str) -> int:
    """
    Get the number of polygon edges on a mesh.

    Args:
        mesh: Mesh transform or shape.

    Returns:
        Number of edges.
    """

    return cmds.polyEvaluate(
        mesh,
        edge=True,
    ) or 0


def get_vertex_count(mesh: str) -> int:
    """
    Get the number of polygon vertices on a mesh.

    Args:
        mesh: Mesh transform or shape.

    Returns:
        Number of vertices.
    """

    return cmds.polyEvaluate(
        mesh,
        vertex=True,
    ) or 0


def get_uv_count(
    mesh: str,
    uv_set: str | None = None,
) -> int:
    """
    Get the number of UVs on a mesh.

    Args:
        mesh: Mesh transform or shape.
        uv_set: UV set to query. Uses the current UV set if None.

    Returns:
        Number of UVs.
    """

    kwargs = {
        "uvcoord": True,
    }

    if uv_set is not None:
        kwargs["uvSetName"] = uv_set

    return cmds.polyEvaluate(
        mesh,
        **kwargs,
    ) or 0



def get_mesh_shells(
    mesh: str,
) -> list[list[str]]:
    """
    Get disconnected polygon regions of a mesh as face lists.
    """

    face_count = get_face_count(
        mesh=mesh,
    )

    remaining = set(
        f"{mesh}.f[{index}]"
        for index in range(face_count)
    )

    shells = []

    while remaining:
        start_face = next(iter(remaining))

        shell = cmds.polyListComponentConversion(
            start_face,
            fromFace=True,
            toFace=True,
        )

        shell = flatten_components(
            shell or []
        )

        # If your Maya version doesn't expand connected face shells
        # here, we'll replace this part with explicit adjacency traversal.

        shells.append(shell)

        remaining.difference_update(
            shell
        )

    return shells