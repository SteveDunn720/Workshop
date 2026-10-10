from __future__ import annotations

from maya import cmds

from Workshop.canon_autorigger.modules import get_module_class

from Workshop.guide.core import (
    GuideInfo,
    create_guide_from_position,
    read_guide,
)

from Workshop.guide.curve_gen import create_curve_guide
from Workshop.guide.module import add_module

from .module_schema import (
    ModuleGuide,
    ModuleGuideArray,
    ModuleCurveGuide,
)


def create_module_guides(
    module: str,
    part: str,
    side: str = "M",
    guide_count: int | None = None,
    source_curve: str | None = None,
    duplicate: bool = True,
    spans: int | None = None,
    degree: int | None = None,
    length: float | None = None,
) -> list[GuideInfo]:
    """
    Create all guides required by a module.

    Supports:
        ModuleGuide
        ModuleGuideArray
        ModuleCurveGuide

    Curve modes:
        source_curve=None:
            Generate a new curve.

        source_curve provided, duplicate=True:
            Duplicate the source curve.

        source_curve provided, duplicate=False:
            Convert the original curve into a guide.
    """

    module_class = get_module_class(module)

    created_guides = []

    for definition in module_class.GUIDES:

        # -----------------------------------------
        # GUIDE ARRAY
        # -----------------------------------------

        if isinstance(definition, ModuleGuideArray):

            created_guides.extend(
                _create_guide_array(
                    definition=definition,
                    module=module,
                    part=part,
                    side=side,
                    count=guide_count,
                )
            )

        # -----------------------------------------
        # CURVE GUIDE
        # -----------------------------------------

        elif isinstance(definition, ModuleCurveGuide):

            if len(module_class.GUIDES) == 1:
                name = part
            else:
                name = f"{part}_{definition.name}"

            guide = _create_curve_guide(
                name=name,
                side=side,
                module=module,
                part=part,
                source_curve=source_curve,
                duplicate=duplicate,
                spans=(
                    definition.spans
                    if spans is None
                    else spans
                ),
                degree=(
                    definition.degree
                    if degree is None
                    else degree
                ),
                length=(
                    definition.length
                    if length is None
                    else length
                ),
            )

            created_guides.append(guide)

        # -----------------------------------------
        # SINGLE GUIDE
        # -----------------------------------------

        elif isinstance(definition, ModuleGuide):

            if len(module_class.GUIDES) == 1:
                name = f"{part}_{side}"
            else:
                name = (
                    f"{part}_"
                    f"{definition.name}_"
                    f"{side}"
                )

            guide = _create_guide(
                name=name,
                position=definition.position,
                guide_type=definition.guide_type,
                module=module,
                part=part,
            )

            created_guides.append(guide)

        else:
            raise TypeError(
                f"Unsupported guide definition: "
                f"{type(definition).__name__}"
            )

    # Re-read the final guide metadata.
    return [
        read_guide(guide.name)
        for guide in created_guides
    ]


def _create_curve_guide(
    name: str,
    side: str,
    module: str,
    part: str,
    source_curve: str | None = None,
    duplicate: bool = True,
    spans: int = 3,
    degree: int = 3,
    length: float = 10.0,
) -> GuideInfo:
    """Create a curve guide and register its module metadata."""

    guide_name = f"{name}_{side}_guide"

    guide = create_curve_guide(
        name=name,
        side=side,
        spans=spans,
        degree=degree,
        length=length,
        source_curve=source_curve,
        duplicate=duplicate,
    )

    # The curve generator may return None even when
    # the Maya curve was successfully created.
    if guide is None:
        if not cmds.objExists(guide_name):
            raise RuntimeError(
                f"Curve guide was not created: {guide_name}"
            )

        guide = read_guide(guide_name)

    elif isinstance(guide, str):
        guide = read_guide(guide)

    # Register the module on the created guide.
    add_module(
        guide.name,
        module=module,
        part=part,
    )

    return read_guide(guide.name)