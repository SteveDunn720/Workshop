from __future__ import annotations

from dataclasses import dataclass

import maya.cmds as cmds

from Workshop.guide.core import GuideInfo, create_guide_from_position, read_guide
from Workshop.transform.utils import create_transform
from Workshop.color.outliner_overwrite import set_outliner_color


@dataclass
class GuideSceneInfo:
    geo: str
    guides: str
    root_guide:GuideInfo


def prepare_guide_scene() -> GuideSceneInfo:
    """
    Prepare a Maya scene for guide creation.

    Creates:
        geo
        guides
            root_M_guide

    Existing nodes are reused.
    """

    # --------------------------------------------------
    # Create geo group
    # --------------------------------------------------

    geo = "geo"

    if not cmds.objExists(geo):
        geo = create_transform(
            name=geo,
        )
    set_outliner_color(
        object=geo,
        hue=196.154,
        saturation=0.750,
        value=0.876,
    )

    # --------------------------------------------------
    # Create guides group
    # --------------------------------------------------

    guides = "guides"

    if not cmds.objExists(guides):
        guides = create_transform(
            name=guides,
        )

    set_outliner_color(
            object=guides,
            hue=34.985,
            saturation=0.750,
            value=0.876,
        )

    # --------------------------------------------------
    # Create root guide
    # --------------------------------------------------

    root_guide_name = "root_M_guide"

    if not cmds.objExists(root_guide_name):

        root_info = create_guide_from_position(
            pos=(0.0, 0.0, 0.0),
            guide_name="root_M",
            parent=guides,
        )

        root_guide = root_info

    else:
        root_guide = read_guide(root_guide_name)

    cmds.setAttr(f'{root_guide.name}.radius', 5)
    cmds.setAttr(f'{root_guide.name}.drawStyle', 3)

    # --------------------------------------------------
    # Return scene info
    # --------------------------------------------------

    return GuideSceneInfo(
        geo=geo,
        guides=guides,
        root_guide=root_guide,
    )