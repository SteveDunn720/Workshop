import maya.cmds as cmds

from Workshop.color.rig_color_setup import (
    initialize_rig_color_type,
)


def apply_color_tag(object: str) -> None:
    tag = cmds.getAttr(
        f"{object}.CONTROL_COLOR_TAG"
    )

    channels = initialize_rig_color_type(
        tag
    )

    # --------------------------------------------------------------
    # Color stays on the transform
    # --------------------------------------------------------------

    cmds.setAttr(
        f"{object}.overrideEnabled",
        1,
    )

    cmds.setAttr(
        f"{object}.overrideRGBColors",
        1,
    )

    cmds.connectAttr(
        channels.color,
        f"{object}.overrideColorRGB",
        force=True,
    )

    # --------------------------------------------------------------
    # Shape-specific display settings
    # --------------------------------------------------------------

    shapes = cmds.listRelatives(
        object,
        shapes=True,
        fullPath=True,
        type="nurbsCurve",
    ) or []

    for shape in shapes:
        cmds.connectAttr(
            channels.draw_on_top,
            f"{shape}.alwaysDrawOnTop",
            force=True,
        )

        cmds.connectAttr(
            channels.thickness,
            f"{shape}.lineWidth",
            force=True,
        )

    # --------------------------------------------------------------
    # Don't add proxies to color_options_ctrl
    # --------------------------------------------------------------

    if object == "color_options_ctrl":
        return

    # --------------------------------------------------------------
    # Proxy attributes
    # --------------------------------------------------------------

    if not cmds.attributeQuery(
        f"{tag}_Display_Options",
        node=object,
        exists=True,
    ):
        cmds.addAttr(
            object,
            longName=f"{tag}_Display_Options",
            proxy=channels.des,
        )

    if not cmds.attributeQuery(
        "Color",
        node=object,
        exists=True,
    ):
        cmds.addAttr(
            object,
            longName="Color",
            proxy=channels.color,
        )

    if not cmds.attributeQuery(
        f"{tag}_Thickness",
        node=object,
        exists=True,
    ):
        cmds.addAttr(
            object,
            longName=f"{tag}_Thickness",
            proxy=channels.thickness,
        )

    if not cmds.attributeQuery(
        f"{tag}_Draw_On_Top",
        node=object,
        exists=True,
    ):
        cmds.addAttr(
            object,
            longName=f"{tag}_Draw_On_Top",
            proxy=channels.draw_on_top,
        )