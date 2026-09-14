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