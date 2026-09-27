from Workshop.guide.hierarchy import get_parent_guide
from Workshop.guide.resolver import ModuleInstance
from Workshop.canon_autorigger.module_preview import preview_module_instance


def find_instance_from_guide(
    guide: str,
    instances: list[ModuleInstance],
) -> ModuleInstance | None:
    """
    Find the module instance that contains a guide.
    """

    for instance in instances:
        if guide in instance.guides:
            return instance

    return None


def resolve_joint_parent(
    instance: ModuleInstance,
    instances: list[ModuleInstance],
) -> str:
    """
    Resolve the joint parent for a module instance.

    If explicitly overridden, use that value.

    Otherwise:
        module guide
            -> logical parent guide
            -> parent module instance
            -> parent module preview
            -> output joint
    """

    joint_parent = instance.relationships.get(
        "joint_parent",
        "auto",
    )

    # Explicit override
    if joint_parent != "auto":
        return joint_parent

    if not instance.guides:
        return "skel"

    root_guide = instance.guides[0]

    parent_guide = get_parent_guide(
        root_guide
    )

    if parent_guide is None:
        return "skel"

    parent_instance = find_instance_from_guide(
        parent_guide,
        instances,
    )

    if parent_instance is None:
        return "skel"

    preview = preview_module_instance(
        parent_instance
    )

    output_joint = preview.get(
        "output_joint"
    )

    if not output_joint:
        return "skel"

    return output_joint


def resolve_control_space(
    instance: ModuleInstance,
    instances: list[ModuleInstance],
) -> list[str]:
    """
    Resolve the control spaces for a module instance.

    If explicitly overridden, use those values.

    Otherwise:
        module guide
            -> logical parent guide
            -> parent module instance
            -> parent module preview
            -> parent output control
    """

    control_space = instance.relationships.get(
        "control_space",
        "auto",
    )

    # Explicit override
    if control_space != "auto":

        # Keep the return type consistent.
        if isinstance(control_space, str):
            return [control_space]

        return control_space

    if not instance.guides:
        return []

    root_guide = instance.guides[0]

    parent_guide = get_parent_guide(
        root_guide
    )

    if parent_guide is None:
        return []

    parent_instance = find_instance_from_guide(
        parent_guide,
        instances,
    )

    if parent_instance is None:
        return []

    preview = preview_module_instance(
        parent_instance
    )

    output_control = preview.get(
        "output_control"
    )

    if not output_control:
        return []

    return [output_control]