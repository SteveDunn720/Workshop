from __future__ import annotations

import maya.cmds as cmds

from Workshop.nurbs.curve import (
    get_curve_shape,
    resample_curve as nurbs_resample_curve,
    reverse_curve as nurbs_reverse_curve,
)

from Workshop.guide.core import (
    GuideInfo,
    add_guide_metadata,
    set_guide_tag,
    read_guide,
)


def create_curve_guide(
    name: str,
    side: str = "M",
    spans: int = 3,
    degree: int = 3,
    length: float = 10.0,
    source_curve: str | None = None,
    duplicate: bool = True,
    parent: str | None = None,
) -> GuideInfo:
    """
    Create a Workshop curve guide.

    Modes:
        source_curve=None:
            Generate a new curve.

        source_curve provided, duplicate=True:
            Duplicate the source curve and convert the copy
            into a Workshop guide.

        source_curve provided, duplicate=False:
            Convert the existing curve directly into a
            Workshop guide.

    All modes:
        - Apply Workshop naming conventions.
        - Add guide metadata.
        - Add guide tag.
        - Return GuideInfo.
    """

    side = side.upper()

    if side not in ("M", "L", "R"):
        raise ValueError(
            f"Invalid side: {side}. Expected M, L, or R."
        )

    # -----------------------------------------
    # NAME
    # -----------------------------------------

    # Accept either "tail" or "tail_L"
    if name.endswith(("_M", "_L", "_R")):
        name = name[:-2]

    descriptor = f"{name}_{side}"
    guide_name = f"{descriptor}_guide"

    if cmds.objExists(guide_name):
        # Converting an already correctly named source is valid.
        if not (
            source_curve
            and not duplicate
            and cmds.ls(source_curve, long=True)
            == cmds.ls(guide_name, long=True)
        ):
            raise ValueError(
                f"Guide already exists: {guide_name}"
            )

    # -----------------------------------------
    # SOURCE CURVE
    # -----------------------------------------

    if source_curve:

        shape = get_curve_shape(source_curve)

        # Ensure we're working with the transform,
        # rather than a curve shape.
        if cmds.nodeType(source_curve) == "nurbsCurve":
            parents = cmds.listRelatives(
                shape,
                parent=True,
                fullPath=True,
            ) or []

            if not parents:
                raise RuntimeError(
                    f"Cannot find transform for {source_curve}"
                )

            source_curve = parents[0]

        if duplicate:
            curve = cmds.duplicate(
                source_curve,
                returnRootsOnly=True,
            )[0]

            curve = cmds.rename(
                curve,
                guide_name,
            )

        else:
            # Rename the original curve in place.
            curve = cmds.rename(
                source_curve,
                guide_name,
            )

    # -----------------------------------------
    # GENERATE NEW CURVE
    # -----------------------------------------

    else:

        if spans < 1:
            raise ValueError(
                "Spans must be at least 1."
            )

        if degree not in (1, 2, 3):
            raise ValueError(
                "Degree must be 1, 2, or 3."
            )

        if length <= 0:
            raise ValueError(
                "Length must be positive."
            )

        curve = cmds.curve(
            name=guide_name,
            degree=1,
            point=[
                (0, length * i / spans, 0)
                for i in range(spans + 1)
            ],
        )

        nurbs_resample_curve(
            curve=curve,
            spans=spans,
            degree=degree,
        )

        # -----------------------------------------
        # PARENT
        # -----------------------------------------

        if parent:

            if not cmds.objExists(parent):
                raise ValueError(
                    f"Parent does not exist: {parent}"
                )

            current_parent = cmds.listRelatives(
                curve,
                parent=True,
                fullPath=True,
            ) or []

            target_parent = cmds.ls(
                parent,
                long=True,
            ) or []

            if not current_parent or current_parent[0] != target_parent[0]:
                curve = cmds.parent(
                    curve,
                    parent,
                )[0]

        # -----------------------------------------
        # GUIDE METADATA
        # -----------------------------------------

        add_guide_metadata(
            guide=curve,
            descriptor=descriptor,
            guide_type="curve",
        )

        set_guide_tag(curve)

        # -----------------------------------------
        # RETURN
        # -----------------------------------------

        return read_guide(curve)
    


def resample_curve(
    curve: str,
    spans: int = 3,
    degree: int = 3,
) -> str:
    """
    Resample a curve guide using the general
    Workshop NURBS utilities.
    """

    return nurbs_resample_curve(
        curve=curve,
        spans=spans,
        degree=degree,
    )


def reverse_curve(curve: str) -> str:
    """
    Reverse a curve guide using the general
    Workshop NURBS utilities.
    """

    return nurbs_reverse_curve(curve)