from maya import cmds

from Workshop.name import get_side


def get_tagged_controls(side: str | None = None) -> list[str]:
    """
    Returns all transform nodes tagged as controllers via a connected controller node.

    Returns:
        list: A list of transform node names that are tagged as controllers.
    """
    controller_nodes: list[str] = cmds.ls(type="controller")
    tagged_controls: list[str] = []
    for control_node in controller_nodes:
        connected: list[str] = cmds.listConnections(
            f"{control_node}.controllerObject", source=True, destination=False
        )
        control = connected[0]
        if side:
            if get_side(control_node) == side:
                tagged_controls.append(control)
        elif connected:
            tagged_controls.append(control)

    return tagged_controls

def tag_control(control: str) -> str:
    """Ensure a transform has a Maya controller tag."""

    if not cmds.objExists(control):
        raise RuntimeError(f"Control does not exist: {control}")

    if cmds.nodeType(control) != "transform":
        raise TypeError(f"Expected transform, got: {control}")

    # Check for an existing controller tag
    existing_tags = cmds.listConnections(
        f"{control}.message",
        source=False,
        destination=True,
        type="controller",
    ) or []

    if existing_tags:
        return existing_tags[0]

    # Create the controller tag
    cmds.controller(control)

    # Retrieve the newly created tag
    tags = cmds.listConnections(
        f"{control}.message",
        source=False,
        destination=True,
        type="controller",
    ) or []

    if not tags:
        raise RuntimeError(
            f"Failed to create controller tag for {control}"
        )

    return tags[0]