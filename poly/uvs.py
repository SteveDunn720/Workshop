import maya.cmds as cmds

from Workshop.poly.convert import to_border_edges, to_internal_edges
from Workshop.poly.uv_sets import (
    get_current_uv_set,
    get_uv_sets,
    set_current_uv_set,
    validate_uv_set,
)
from Workshop.poly.face import get_selected_faces


def cut_uv_edges(
    edges: str | list[str],
    uv_set: str,
) -> None:
    """
    Cut UVs along the given polygon edges.

    Args:
        edges: Polygon edges to cut.
        uv_set: UV set to modify.
    """

    if not edges:
        return

    mesh = edges[0].split(".")[0] if isinstance(edges, list) else edges.split(".")[0]

    uv_sets = get_uv_sets(mesh=mesh)

    if uv_set not in uv_sets:
        raise RuntimeError(
            f"UV set '{uv_set}' does not exist on {mesh}."
        )

    current_uv_set = get_current_uv_set(mesh=mesh)

    try:
        set_current_uv_set(
            mesh=mesh,
            uv_set=uv_set,
        )

        cmds.polyMapCut(
            edges,
            constructionHistory=False,
        )

    finally:
        if current_uv_set is not None:
            set_current_uv_set(
                mesh=mesh,
                uv_set=current_uv_set,
            )

def sew_uv_edges(
    edges: str | list[str],
    uv_set: str,
) -> None:
    """
    Sew UVs along the given polygon edges.

    Args:
        edges: Polygon edges to sew.
        uv_set: UV set to modify.
    """

    if not edges:
        return

    mesh = edges[0].split(".")[0] if isinstance(edges, list) else edges.split(".")[0]

    validate_uv_set(
        mesh=mesh,
        uv_set=uv_set,
    )

    current_uv_set = get_current_uv_set(mesh=mesh)

    try:
        set_current_uv_set(
            mesh=mesh,
            uv_set=uv_set,
        )

        cmds.polyMapSew(
            edges,
            constructionHistory=False,
        )

    finally:
        if current_uv_set is not None:
            set_current_uv_set(
                mesh=mesh,
                uv_set=current_uv_set,
            )

def faces_to_uv_shell(
    faces: str | list[str],
    uv_set: str | None,
    create_uv_set_if_missing: bool = True,
    sew_interior: bool = True,
) -> None:
    """
    Convert a group of faces into a single UV shell.

    Args:
        faces: Faces to separate into a UV shell.
        uv_set: UV set to modify. Uses the current set if None.
        create_uv_set_if_missing: Create the UV set if it does not exist.
        sew_interior: Sew internal UV edges before cutting the outer border.
    """

    mesh = (
        faces[0].split(".")[0]
        if isinstance(faces, list)
        else faces.split(".")[0]
    )

    if uv_set:
        uv_set = validate_uv_set(
            mesh=mesh,
            uv_set=uv_set,
            create=create_uv_set_if_missing,
        )
    else:
        uv_set = get_current_uv_set(
            mesh=mesh,
        )

    if uv_set is None:
        raise RuntimeError(
            f"No current UV set found on '{mesh}'."
        )

    if sew_interior:
        interior_edges = to_internal_edges(
            faces,
        )

        sew_uv_edges(
            edges=interior_edges,
            uv_set=uv_set,
        )

    border_edges = to_border_edges(
        faces,
    )

    cut_uv_edges(
        edges=border_edges,
        uv_set=uv_set,
    )

def selected_faces_to_uv_shell(
    uv_set: str|None = None,
    create_missing: bool = False,
) -> None:
    """
    Convert the currently selected faces into a UV shell.

    Args:
        uv_set: UV set to modify.
        create_missing: Create the UV set if it does not exist.
    """

    faces = get_selected_faces()

    if not faces:
        raise RuntimeError("No polygon faces selected.")

    faces_to_uv_shell(
        faces=faces,
        uv_set=uv_set,
        create_uv_set_if_missing=create_missing,
    )

