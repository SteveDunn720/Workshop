#type:ignore
import colorsys

import maya.cmds as cmds


def set_children_outliner_color(
    parent: str,
    hue: float,
    saturation: float,
    value: float,
    recursive: bool = False,
) -> None:
    """Set the Outliner color of an object's children using HSV values.

    Args:
        parent: Parent Maya object.
        hue: Hue in degrees (0-360).
        saturation: Saturation from 0-1.
        value: Value from 0-1.
        recursive: If True, affect all descendants instead of direct children.
    """

    rgb = colorsys.hsv_to_rgb(
        hue / 360.0,
        saturation,
        value,
    )

    if recursive:
        children = cmds.listRelatives(
            parent,
            allDescendents=True,
            fullPath=True,
        ) or []
    else:
        children = cmds.listRelatives(
            parent,
            children=True,
            fullPath=True,
        ) or []

    for child in children:
        if not cmds.attributeQuery("useOutlinerColor", node=child, exists=True):
            continue

        cmds.setAttr(f"{child}.useOutlinerColor", True)
        cmds.setAttr(
            f"{child}.outlinerColor",
            *rgb,
            type="double3",
        )