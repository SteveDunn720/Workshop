from __future__ import annotations

from maya import cmds

from Workshop.canon_autorigger.modules import get_module_class
from Workshop.guide.core import GuideInfo, create_guide_from_position, read_guide
from Workshop.guide.module import add_module
from .module_schema import ModuleGuide, ModuleGuideArray


def create_module_guides(
    module: str,
    part: str,
    side: str = "M",
    guide_count: int | None = None,
) -> list:

    module_class = get_module_class(
        module
    )

    created_guides = []

    for definition in module_class.GUIDES:

        if isinstance(
            definition,
            ModuleGuideArray,
        ):
            created_guides.extend(
                _create_guide_array(
                    definition=definition,
                    module=module,
                    part=part,
                    side=side,
                    count=guide_count,
                )
            )

        elif isinstance(
            definition,
            ModuleGuide,
        ):

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

            created_guides.append(
                guide
            )

        else:
            raise TypeError(
                f"Unsupported guide definition: "
                f"{type(definition).__name__}"
            )

    # Re-read after module data and parenting have
    # been applied so the returned GuideInfo is current.
    return [
        read_guide(guide.name)
        for guide in created_guides
    ]

def _create_guide(
    name: str,
    position: tuple[float, float, float],
    guide_type: str,
    module: str,
    part: str,
):
    """
    Create and tag a single module guide.
    """

    guide_name = f"{name}_guide"

    if cmds.objExists(guide_name):
        raise ValueError(
            f"Guide already exists: {guide_name}"
        )

    guide = create_guide_from_position(
        guide_name=name,
        pos=position,
        component_type=guide_type,
    )

    add_module(
        guide.name,
        module=module,
        part=part,
    )

    return guide

def _create_guide_array(
    definition: ModuleGuideArray,
    module: str,
    part: str,
    side: str,
    count: int | None = None,
) -> list:

    count = (
        definition.default_count
        if count is None
        else count
    )

    if count < definition.minimum_count:
        raise ValueError(
            f"{module} requires at least "
            f"{definition.minimum_count} guides."
        )

    guides = []

    for index in range(count):

        number = index + 1

        # No _guide suffix here.
        name = f"{part}_{number:02d}_{side}"

        position = tuple(
            value * index
            for value in definition.spacing
        )

        guide = _create_guide(
            name=name,
            position=position,
            guide_type=definition.guide_type,
            module=module,
            part=part,
        )

        if definition.parented and guides:
            cmds.parent(
                guide.name,
                guides[-1].name,
            )

        guides.append(guide)

    return guides