from __future__ import annotations

import maya.cmds as cmds

from .core import is_guide


def get_parent_guide(guide: str) -> str | None:
    """
    Find the nearest guide above this guide in the Maya hierarchy.

    Non-guide transforms/groups are ignored.
    """

    if not cmds.objExists(guide):
        raise ValueError(
            f"Guide does not exist: {guide}"
        )

    parent = cmds.listRelatives(
        guide,
        parent=True,
        fullPath=False,
    )

    while parent:
        parent = parent[0]

        if is_guide(parent):
            return parent

        parent = cmds.listRelatives(
            parent,
            parent=True,
            fullPath=False,
        )

    return None


def get_child_guides(guide: str) -> list[str]:
    """
    Return the immediate logical child guides.

    Non-guide DAG nodes are treated as transparent organizational nodes.
    Once a guide is encountered on a branch, traversal stops on that
    branch because that guide is now the logical child.
    """

    if not cmds.objExists(guide):
        raise ValueError(
            f"Guide does not exist: {guide}"
        )

    result = []

    def walk(node: str) -> None:

        children = cmds.listRelatives(
            node,
            children=True,
            fullPath=False,
        ) or []

        for child in children:

            if is_guide(child):
                result.append(child)
                continue

            # Don't walk into shapes.
            if cmds.objectType(child, isAType="shape"):
                continue

            walk(child)

    walk(guide)

    return result


def get_guide_descendants(
    guide: str,
) -> list[str]:
    """
    Return all logical guide descendants in depth-first order.
    """

    result = []

    for child in get_child_guides(guide):
        result.append(child)
        result.extend(
            get_guide_descendants(child)
        )

    return result
