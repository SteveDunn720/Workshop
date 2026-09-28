import maya.cmds as cmds


def create_connection_curve(
    start: str,
    end: str,
    parent: str | None = None,
    name: str = "connection",
) -> str:
    """
    Create a display-only straight curve between two transforms.

    The curve CVs are driven directly from the world positions of
    start and end, converted into the curve's local space.

    Args:
        start:
            Transform driving the start of the curve.

        end:
            Transform driving the end of the curve.

        parent:
            Optional parent for the curve.

        name:
            Name for the curve transform.

    Returns:
        str: Curve transform.
    """

    # --------------------------------------------------
    # Create curve
    # --------------------------------------------------

    curve = cmds.curve(
        degree=1,
        point=[
            (0, 0, 0),
            (0, 0, 0),
        ],
        name=name,
    )

    shape = cmds.listRelatives(
        curve,
        shapes=True,
        noIntermediate=True,
        fullPath=False,
    )[0]

    if parent:
        curve = cmds.parent(curve, parent)[0]

    # Keep the curve transform clean.
    cmds.setAttr(f"{curve}.translate", 0, 0, 0)
    cmds.setAttr(f"{curve}.rotate", 0, 0, 0)
    cmds.setAttr(f"{curve}.scale", 1, 1, 1)

    # --------------------------------------------------
    # Drive CVs
    # --------------------------------------------------

    for index, driver in enumerate((start, end)):

        mult_matrix = cmds.createNode(
            "multMatrix",
            name=f"{name}_{index:02d}_mm",
        )

        point_matrix = cmds.createNode(
            "pointMatrixMult",
            name=f"{name}_{index:02d}_pmm",
        )

        # Driver world space
        cmds.connectAttr(
            f"{driver}.worldMatrix[0]",
            f"{mult_matrix}.matrixIn[0]",
        )

        # Convert world space -> curve local space
        cmds.connectAttr(
            f"{curve}.worldInverseMatrix[0]",
            f"{mult_matrix}.matrixIn[1]",
        )

        cmds.connectAttr(
            f"{mult_matrix}.matrixSum",
            f"{point_matrix}.inMatrix",
        )

        # Origin transformed by the resulting matrix gives
        # us the driver's position in curve-local space.
        cmds.setAttr(
            f"{point_matrix}.inPoint",
            0,
            0,
            0,
            type="double3",
        )

        cmds.connectAttr(
            f"{point_matrix}.output",
            f"{shape}.controlPoints[{index}]",
        )

    # --------------------------------------------------
    # Display
    # --------------------------------------------------

    cmds.setAttr(f"{shape}.overrideEnabled", 1)

    # Reference: visible but not selectable.
    cmds.setAttr(f"{shape}.overrideDisplayType", 1)

    return curve