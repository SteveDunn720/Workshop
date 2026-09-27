from __future__ import annotations

from Workshop.guide.resolver import (
    ModuleInstance,
    resolve_module_instances,
)
from Workshop.canon_autorigger.modules import get_module_class
from Workshop.canon_autorigger.module_preview import preview_module_instance
from Workshop.canon_autorigger.relationship_resolver import (
    resolve_joint_parent,
    resolve_control_space,
)
from Workshop.canon_autorigger.module_schema import (
    get_setting_value,
)

from Workshop.guide.core import read_guide


def get_resolved_settings(
    instance: ModuleInstance,
) -> dict:
    """
    Resolve all settings for a module instance.

    Instance overrides take priority over the module's
    schema defaults.
    """

    module_class = get_module_class(
        instance.module
    )

    settings = {}

    for setting in module_class.SETTINGS:
        settings[setting.name] = get_setting_value(
            instance,
            module_class,
            setting.name,
        )

    return settings


def get_resolved_relationships(
    instance: ModuleInstance,
    instances: list[ModuleInstance],
) -> dict:
    """
    Resolve relationships needed to build a module.

    For now we support:
        joint_parent
        control_space
    """

    return {
        "joint_parent": resolve_joint_parent(
            instance,
            instances,
        ),
        "control_space": resolve_control_space(
            instance,
            instances,
        ),
    }


def get_build_data(
    instance: ModuleInstance,
    instances: list[ModuleInstance],
) -> dict:
    """
    Collect everything needed to eventually build
    a module instance.
    """

    return {
        "module": instance.module,
        "part": instance.part,
        "side": instance.side,
        "guides": instance.guides,
        "settings": get_resolved_settings(
            instance
        ),
        "relationships": get_resolved_relationships(
            instance,
            instances,
        ),
        "preview": preview_module_instance(
            instance
        ),
    }


def print_build_plan(
    instances: list[ModuleInstance],
) -> None:
    """
    Print the resolved module build plan.

    This does NOT create any Maya nodes.
    """

    print("\n")
    print("=" * 60)
    print("PROP RIG BUILD PLAN")
    print("=" * 60)

    for index, instance in enumerate(
        instances,
        start=1,
    ):
        data = get_build_data(
            instance,
            instances,
        )

        print(
            f"\n{index}. "
            f"{data['module']} / "
            f"{data['part']} / "
            f"{data['side']}"
        )

        print(
            "   guides:",
            data["guides"],
        )

        print("   settings:")

        for name, value in data["settings"].items():
            print(
                f"      {name}: {value}"
            )

        print("   relationships:")

        for name, value in data["relationships"].items():
            print(
                f"      {name}: {value}"
            )

        preview = data["preview"]

        print(
            "   output_control:",
            preview.get("output_control"),
        )

        print(
            "   output_joint:",
            preview.get("output_joint"),
        )

    print("\n" + "=" * 60)
    print("DRY RUN ONLY - NOTHING WAS BUILT")
    print("=" * 60)


def build_prop_rig(
    root: str = "root_M_guide",
    build: bool = False,
):
    """
    Resolve a hierarchy-driven prop rig.

    build=False:
        Safely print the build plan without creating
        any Maya nodes.

    build=True:
        Reserved for the actual builder.
    """

    instances = resolve_module_instances(
        root
    )

    if not build:
        print_build_plan(
            instances
        )
        return instances


    results = []

    for instance in instances:

        print(
            f"Building: "
            f"{instance.module} / "
            f"{instance.part} / "
            f"{instance.side}"
        )

        result = build_module_instance(
            instance,
            instances,
        )

        results.append(result)


    return results

def get_module_guides(
    instance: ModuleInstance,
):
    """
    Convert the guide node names stored by ModuleInstance
    into GuideInfo objects expected by existing rig modules.
    """

    return [
        read_guide(guide)
        for guide in instance.guides
    ]


def build_module_instance(
    instance: ModuleInstance,
    instances: list[ModuleInstance],
):
    """
    Build a single resolved module instance.
    """

    module_class = get_module_class(
        instance.module
    )

    guides = get_module_guides(
        instance
    )

    settings = get_resolved_settings(
        instance
    )

    relationships = get_resolved_relationships(
        instance,
        instances,
    )

    module = module_class(
        part=instance.part,
        side=instance.side,
        guides=guides,
        **settings,
        **relationships,
    )

    # Temporary while Arbit is our test module.
    if instance.module == "arbit":
        return module.arbit_build()

    raise NotImplementedError(
        f"Build method not configured for module: "
        f"{instance.module}"
    )