from dataclasses import dataclass, field
from typing import Any

from Workshop.guide.resolver import (
    ModuleInstance,
    resolve_module_instances,
)

from Workshop.canon_autorigger.prop_builder import (
    build_module_instance,
    print_build_plan,
)


@dataclass
class PropBuildResults:
    instances: list[ModuleInstance] = field(
        default_factory=list
    )
    modules: dict[str, Any] = field(
        default_factory=dict
    )


def auto_build_prop(
    root: str = "root_M_guide",
    parent: str = "rig",
    rig_size: float = 1.0,
    dry_run: bool = False,
    build_root: bool = True,
    external_instances: list[ModuleInstance] | None = None,
) -> PropBuildResults:
    """
    Resolve and build all module instances
    found beneath the root guide.

    build_root:
        Whether to build the root module itself.

    external_instances:
        Existing module instances available for
        relationship resolution, but not building.
    """

    instances = resolve_module_instances(root)

    # Optionally skip the root module.
    if not build_root:
        instances = [
            instance
            for instance in instances
            if not (
                instance.module == "root"
                and instance.guides
                and instance.guides[0] == root
            )
        ]

    # Modules available for relationship resolution.
    relationship_instances = [
        *(external_instances or []),
        *instances,
    ]

    results = PropBuildResults(
        instances=instances,
    )

    if dry_run:
        print_build_plan(instances)
        return results

    # Build only the requested modules.
    for index, instance in enumerate(instances):

        key = (
            f"{instance.module}:"
            f"{instance.part}:"
            f"{instance.side}"
        )

        print(
            f"[{index + 1}/{len(instances)}] "
            f"Building {key}"
        )

        result = build_module_instance(
            instance=instance,
            instances=relationship_instances,
            parent=parent,
            rig_size=rig_size,
        )

        results.modules[key] = result

    return results