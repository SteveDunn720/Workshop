from __future__ import annotations

from dataclasses import dataclass, field

from Workshop.name import get_side
from Workshop.guide.hierarchy import get_guide_descendants
from Workshop.guide.module import (
    get_module_root,
    get_module_relationships,
    get_module_settings,
    get_modules,
)


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
    guides.extend(get_guide_descendants(root))

    # Remove duplicates while preserving hierarchy order.
    guides = list(dict.fromkeys(guides))

    # ==========================================
    # COLLECT GUIDE MEMBERSHIPS
    # ==========================================

    module_guides: dict[str, list[str]] = {}

    for guide in guides:

        module_root = get_module_root(guide)

        if module_root is None:
            continue

        module_guides.setdefault(
            module_root, []
        ).append(guide)

    # ==========================================
    # RESOLVE MODULE INSTANCES
    # ==========================================

    instances: list[ModuleInstance] = []

    for guide in guides:

        memberships = get_modules(guide)

        if not memberships:
            continue

        # The guide containing the module metadata
        # is the owner of this module instance.
        module_root = guide

        members = module_guides.get(
            module_root, []
        )

        # Ensure the module root is always first.
        ordered_guides = [
            module_root,
            *[
                member
                for member in members
                if member != module_root
            ],
        ]

        for membership in memberships:

            instances.append(
                ModuleInstance(
                    module=membership.module,
                    part=membership.part,
                    guides=ordered_guides.copy(),
                    settings=get_module_settings(
                        module_root,
                        membership.module,
                        membership.part,
                    ),
                    relationships=get_module_relationships(
                        module_root,
                        membership.module,
                        membership.part,
                    ),
                )
            )

    return instances