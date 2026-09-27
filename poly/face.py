import maya.cmds as cmds

def get_selected_faces() -> list[str]:
    """
    Get the currently selected polygon faces.

    Returns:
        Flattened list of selected faces.
    """

    faces = cmds.filterExpand(
        selectionMask=34,
        expand=True,
    )

    return faces or []


def get_face_index(
    face: str,
) -> int:
    """Get the integer index from a face component."""

    return int(
        face.split("[")[-1].rstrip("]")
    )


def get_face_indices(
    faces: list[str],
) -> list[int]:
    """Get integer indices from face components."""

    return [
        get_face_index(face)
        for face in faces
    ]

def get_face_index(
    face: str,
) -> int:
    """Get the index of a face component."""

    return int(
        face.split("[")[-1].rstrip("]")
    )


def get_face_indices(
    faces: list[str],
) -> list[int]:
    """Get face indices from face components."""

    return [
        get_face_index(face)
        for face in faces
    ]


def get_face_from_index(
    mesh: str,
    index: int,
) -> str:
    """Get a face component from an index."""

    return f"{mesh}.f[{index}]"


def get_faces_from_indices(
    mesh: str,
    indices: list[int],
) -> list[str]:
    """Get face components from indices."""

    return [
        get_face_from_index(
            mesh=mesh,
            index=index,
        )
        for index in indices
    ]