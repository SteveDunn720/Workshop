import maya.cmds as cmds
import maya.api.OpenMaya as om2

from Workshop.poly.convert import flatten_components, to_border_edges, to_internal_edges, to_uvs, uv_shell_to_faces
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

def get_uv_shell(
    uv: str,
    uv_set: str | None = None,
) -> list[str]:
    """
    Get every UV belonging to the same UV shell as the given UV.

    Args:
        uv: UV component belonging to the shell.
        uv_set: UV set to query. If None, use the current UV set.

    Returns:
        Flattened list of UV components in the shell.
    """

    mesh = uv.split(".")[0]

    if uv_set is None:
        uv_set = get_current_uv_set(
            mesh=mesh,
        )

    if uv_set is None:
        raise RuntimeError(
            f"No current UV set found on '{mesh}'."
        )

    validate_uv_set(
        mesh=mesh,
        uv_set=uv_set,
    )

    current_uv_set = get_current_uv_set(
        mesh=mesh,
    )

    try:
        set_current_uv_set(
            mesh=mesh,
            uv_set=uv_set,
        )

        shell = cmds.polyListComponentConversion(
            uv,
            fromUV=True,
            toUV=True,
            uvShell=True,
        )

        return flatten_components(shell or [])

    finally:
        if current_uv_set is not None:
            set_current_uv_set(
                mesh=mesh,
                uv_set=current_uv_set,
            )


def get_uv_shell_from_id(
    mesh: str,
    shell_id: int,
    uv_set: str | None = None,
) -> list[str]:
    """
    Get all UVs belonging to a UV shell ID.
    """

    if uv_set is None:
        uv_set = get_current_uv_set(
            mesh=mesh,
        )

    if uv_set is None:
        raise RuntimeError(
            f"No current UV set found on '{mesh}'."
        )

    validate_uv_set(
        mesh=mesh,
        uv_set=uv_set,
    )

    uv_count = cmds.polyEvaluate(
        mesh,
        uv=True,
        uvSetName=uv_set,
    ) or 0

    for uv_index in range(uv_count):
        uv = f"{mesh}.map[{uv_index}]"

        current_shell_id = get_uv_shell_id(
            uv=uv,
            uv_set=uv_set,
        )

        if current_shell_id == shell_id:
            return get_uv_shell(
                uv=uv,
                uv_set=uv_set,
            )

    raise RuntimeError(
        f"UV shell '{shell_id}' does not exist "
        f"in UV set '{uv_set}' on '{mesh}'."
    )

def get_uv_shell_id(
    uv: str,
    uv_set: str | None = None,
) -> int:
    """
    Get the shell ID containing a UV.
    """

    mesh = uv.split(".")[0]

    if uv_set is None:
        uv_set = get_current_uv_set(
            mesh=mesh,
        )

    if uv_set is None:
        raise RuntimeError(
            f"No current UV set found on '{mesh}'."
        )

    validate_uv_set(
        mesh=mesh,
        uv_set=uv_set,
    )

    current_uv_set = get_current_uv_set(
        mesh=mesh,
    )

    try:
        set_current_uv_set(
            mesh=mesh,
            uv_set=uv_set,
        )

        shell_id = cmds.polyEvaluate(
            uv,
            uvShellIds=True,
        )

        if shell_id is None:
            raise RuntimeError(
                f"Could not get UV shell ID for '{uv}'."
            )

        if isinstance(shell_id, list):
            return shell_id[0]

        return shell_id

    finally:
        if current_uv_set is not None:
            set_current_uv_set(
                mesh=mesh,
                uv_set=current_uv_set,
            )


def get_uv_shell_count(
    mesh: str,
    uv_set: str,
) -> int:
    """Get the number of UV shells in a UV set."""

    validate_uv_set(
        mesh=mesh,
        uv_set=uv_set,
    )

    return cmds.polyEvaluate(
        mesh,
        uvShell=True,
        uvSetName=uv_set,
    ) or 0



def print_uv_shells(
    mesh: str,
    uv_set: str,
) -> None:
    """Print each UV shell and the faces belonging to it."""

    shell_count = get_uv_shell_count(
        mesh=mesh,
        uv_set=uv_set,
    )

    print(
        f"{mesh} | {uv_set} | "
        f"Shell count: {shell_count}"
    )

    for shell_id in range(shell_count):
        uvs = get_uv_shell_from_id(
            mesh=mesh,
            shell_id=shell_id,
            uv_set=uv_set,
        )

        faces = uv_shell_to_faces(
            uvs
        )

        print(
            f"Shell {shell_id}: {faces}"
        )


def get_uvs_in_udim(
    mesh: str,
    udim: int,
    uv_set: str,
) -> list[str]:
    """
    Get all UVs located inside a UDIM tile.

    Args:
        mesh: Mesh to query.
        udim: UDIM tile number.
        uv_set: UV set to query.

    Returns:
        UV components inside the UDIM.
    """

    validate_uv_set(
        mesh=mesh,
        uv_set=uv_set,
    )

    tile_index = udim - 1001

    u_tile = tile_index % 10
    v_tile = tile_index // 10

    uv_count = cmds.polyEvaluate(
        mesh,
        uv=True,
        uvSetName=uv_set,
    ) or 0

    uvs = []

    current_uv_set = get_current_uv_set(
        mesh=mesh,
    )

    try:
        set_current_uv_set(
            mesh=mesh,
            uv_set=uv_set,
        )

        for uv_index in range(uv_count):
            uv = f"{mesh}.map[{uv_index}]"

            position = cmds.polyEditUV(
                uv,
                query=True,
            )

            if not position:
                continue

            u, v = position

            if (
                u_tile <= u < u_tile + 1
                and
                v_tile <= v < v_tile + 1
            ):
                uvs.append(uv)

    finally:
        if current_uv_set is not None:
            set_current_uv_set(
                mesh=mesh,
                uv_set=current_uv_set,
            )

    return uvs


def move_uv_shell_to_udim(
    uvs: str | list[str],
    udim: int,
    uv_set: str,
) -> None:
    """
    Move UVs into a target UDIM tile.

    Args:
        uvs: UV components to move.
        udim: Target UDIM.
        uv_set: UV set containing the UVs.
    """

    uvs = flatten_components(
        uvs
    )

    if not uvs:
        return

    mesh = uvs[0].split(".")[0]

    validate_uv_set(
        mesh=mesh,
        uv_set=uv_set,
    )

    tile_index = udim - 1001

    u_tile = tile_index % 10
    v_tile = tile_index // 10

    current_uv_set = get_current_uv_set(
        mesh=mesh,
    )

    try:
        set_current_uv_set(
            mesh=mesh,
            uv_set=uv_set,
        )

        positions = [
            cmds.polyEditUV(
                uv,
                query=True,
            )
            for uv in uvs
        ]

        positions = [
            position
            for position in positions
            if position
        ]

        if not positions:
            return

        min_u = min(
            position[0]
            for position in positions
        )

        min_v = min(
            position[1]
            for position in positions
        )

        offset_u = u_tile - min_u
        offset_v = v_tile - min_v

        cmds.polyEditUV(
            uvs,
            relative=True,
            uValue=offset_u,
            vValue=offset_v,
        )

    finally:
        if current_uv_set is not None:
            set_current_uv_set(
                mesh=mesh,
                uv_set=current_uv_set,
            )



def faces_to_uvs(
    faces: str | list[str],
    uv_set: str,
) -> list[str]:
    """Get UVs belonging to faces in a specific UV set."""

    mesh = (
        faces[0].split(".")[0]
        if isinstance(faces, list)
        else faces.split(".")[0]
    )

    validate_uv_set(
        mesh=mesh,
        uv_set=uv_set,
    )

    current_uv_set = get_current_uv_set(
        mesh=mesh,
    )

    try:
        set_current_uv_set(
            mesh=mesh,
            uv_set=uv_set,
        )

        return to_uvs(
            faces
        )

    finally:
        if current_uv_set is not None:
            set_current_uv_set(
                mesh=mesh,
                uv_set=current_uv_set,
            )


def fit_uvs_to_udim(
    uvs: str | list[str],
    udim: int,
    uv_set: str,
    padding: float = 0.1,
) -> None:
    """
    Scale and move UVs to fit inside a UDIM tile.
    """

    uvs = flatten_components(
        uvs
    )

    if not uvs:
        return

    mesh = uvs[0].split(".")[0]

    validate_uv_set(
        mesh=mesh,
        uv_set=uv_set,
    )

    tile_index = udim - 1001

    u_tile = tile_index % 10
    v_tile = tile_index // 10

    current_uv_set = get_current_uv_set(
        mesh=mesh,
    )

    try:
        set_current_uv_set(
            mesh=mesh,
            uv_set=uv_set,
        )

        positions = [
            cmds.polyEditUV(
                uv,
                query=True,
            )
            for uv in uvs
        ]

        positions = [
            position
            for position in positions
            if position
        ]

        if not positions:
            return

        min_u = min(position[0] for position in positions)
        max_u = max(position[0] for position in positions)

        min_v = min(position[1] for position in positions)
        max_v = max(position[1] for position in positions)

        width = max_u - min_u
        height = max_v - min_v

        available_size = 1.0 - (padding * 2.0)

        scale = available_size / max(
            width,
            height,
        )

        center_u = (min_u + max_u) * 0.5
        center_v = (min_v + max_v) * 0.5

        target_u = u_tile + 0.5
        target_v = v_tile + 0.5

        cmds.polyEditUV(
            uvs,
            relative=True,
            pivotU=center_u,
            pivotV=center_v,
            scaleU=scale,
            scaleV=scale,
        )

        cmds.polyEditUV(
            uvs,
            relative=True,
            uValue=target_u - center_u,
            vValue=target_v - center_v,
        )

    finally:
        if current_uv_set is not None:
            set_current_uv_set(
                mesh=mesh,
                uv_set=current_uv_set,
            )

def get_uv_shells(
    mesh: str,
    uv_set: str,
) -> list[list[str]]:
    """Get all UV shells in a UV set."""

    validate_uv_set(
        mesh=mesh,
        uv_set=uv_set,
    )

    selection = om2.MSelectionList()
    selection.add(mesh)

    dag = selection.getDagPath(0)
    fn_mesh = om2.MFnMesh(dag)

    shell_count, shell_ids = fn_mesh.getUvShellsIds(
        uv_set
    )

    shells = [
        []
        for _ in range(shell_count)
    ]

    for uv_index, shell_id in enumerate(shell_ids):
        shells[shell_id].append(
            f"{mesh}.map[{uv_index}]"
        )

    return shells