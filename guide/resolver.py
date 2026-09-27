from __future__ import annotations

from dataclasses import dataclass, field

from Workshop.name import get_side
from Workshop.guide.hierarchy import get_guide_descendants
from Workshop.guide.module import get_module_relationships, get_module_settings, get_modules


@dataclass
class ModuleInstance:
    module: str
    part: str
    guides: list[str] = field(default_factory=list)

    settings: dict = field(default_factory=dict)
    relationships: dict = field(default_factory=dict)

    @property
    def side(self) -> str:
        if not self.guides:
            return "M"

        return get_side(self.guides[0])

def resolve_module_instances(
    root: str = "root_M_guide",
) -> list[ModuleInstance]:

    guides = [root]
    guides.extend(
        get_guide_descendants(root)
    )

    instances: dict[
        tuple[str, str],
        ModuleInstance,
    ] = {}

    for guide in guides:

        memberships = get_modules(guide)

        for membership in memberships:

            key = (
                membership.module,
                membership.part,
            )

            if key not in instances:
                instances[key] = ModuleInstance(
                    module=membership.module,
                    part=membership.part,
                    settings=get_module_settings(
                        guide,
                        membership.module,
                        membership.part,
                    ),
                    relationships=get_module_relationships(
                        guide,
                        membership.module,
                        membership.part,
                    ),
                )

            instances[key].guides.append(guide)

    return list(instances.values())


