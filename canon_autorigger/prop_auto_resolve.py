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
    control_size: float = 1.0,
    dry_run: bool = False,
) -> PropBuildResults:
    """
    Resolve and build all module instances
    found beneath the root guide.
    """

    instances = resolve_module_instances(
        root
    )

    results = PropBuildResults(
        instances=instances
    )

    if dry_run:

        print_build_plan(
            instances
        )

        return results

    # --------------------------------------------------
    # BUILD MODULES
    # --------------------------------------------------

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
            instances=instances,
            parent=parent,
            control_size=control_size,
        )

        results.modules[key] = result

    return results