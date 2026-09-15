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