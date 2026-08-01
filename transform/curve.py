#type:ignore
import maya.cmds as cmds


def create_line_curve(
    name: str,
    start_position: tuple[float, float, float],
    end_position: tuple[float, float, float],
) -> str:
    """Create a straight curve with duplicated endpoint CVs."""

    return cmds.curve(
        name=name,
        degree=3,
        point=[
            start_position,
            start_position,
            end_position,
            end_position,
        ],
    )

def style_curve(curve: str, line_width: float = 5.0, draw_on_top:bool=False, template:bool=True) -> None:
    """Style a curve for guide display."""

    shapes = cmds.listRelatives(curve, shapes=True, fullPath=True) or []

    for shape in shapes:
        cmds.setAttr(f"{shape}.lineWidth", line_width)
        cmds.setAttr(f"{shape}.alwaysDrawOnTop", draw_on_top)
        cmds.setAttr(f"{shape}.template", template)


def curve_cvs(curve: str, clusters:bool=False):
    """Create one cluster per curve CV.

    Returns:
        A 2 lists containing:
        [
            (cluster_handle, cv_world_position),
            ...
        ]
    """

    cvs = cmds.ls(f"{curve}.cv[*]", flatten=True) or []
    cluster_data = []
    cv_pos = []

    for index, cv in enumerate(cvs):
        position = cmds.xform(
            cv,
            query=True,
            worldSpace=True,
            translation=True,
        )

        if clusters:
            cluster_node, cluster_handle = cmds.cluster(
                cv,
                name=f"{curve}_cv{index}_cluster",
            )
            cluster_data.append(cluster_handle)
        cv_pos.append(position)

    return cluster_data, cv_pos