
from typing import Any

import maya.cmds as cmds


def create_attribute(
    primary_object: str,
    attr_name: str,
    default: Any = None,
    min: float | None = None,
    max: float | None = None,
    enum_index: list[str] | None = None,
    proxy_objects: list[str] | None = None,
    connect_from: str | None = None,
    connect_to: list[str] | None = None,
    attr_type: str = "double",
    keyable: bool = True,
    hidden: bool = False,
    locked: bool = False,
    proxy_name: str | None = None,
) -> str:
    """
    Create a Maya attribute with optional proxies and connections.

    Args:
        primary_object: Node receiving the attribute.
        attr_name: Name of the attribute.
        default: Default attribute value.
        min: Minimum numeric value.
        max: Maximum numeric value.
        enum_index: Enum labels in index order.
        proxy_objects: Nodes receiving proxy attributes.
        connect_from: Attribute connected into the new attribute.
        connect_to: Attribute receiving the new attribute's output.
        attr_type: Maya attribute type (double, bool, long, enum).
        keyable: Whether the attribute is keyable.
        hidden: Whether the attribute is hidden.
        locked: Whether the attribute is locked.
        proxy_name: Optional alternate name for proxy attributes.

    Returns:
        Full attribute path.
    """

    attr = f"{primary_object}.{attr_name}"

    if not cmds.objExists(primary_object):
        raise ValueError(f"{primary_object} does not exist")

    if cmds.objExists(attr):
        raise ValueError(f"{attr} already exists")

    # Normalize supported attribute types
    attr_type = {
        "int": "long",
        "float": "double",
    }.get(attr_type, attr_type)

    supported_types = {"double", "bool", "long", "enum"}

    if attr_type not in supported_types:
        raise ValueError(f"Attribute type '{attr_type}' not supported")

    # Build attribute settings
    kwargs = {
        "longName": attr_name,
        "attributeType": attr_type,
        "keyable": keyable,
        "hidden": hidden,
    }

    if default is not None:
        kwargs["defaultValue"] = default

    if min is not None and attr_type in {"double", "long"}:
        kwargs["minValue"] = min

    if max is not None and attr_type in {"double", "long"}:
        kwargs["maxValue"] = max

    if attr_type == "enum":
        if not enum_index:
            raise ValueError("enum_index is required for enum attributes")

        kwargs["enumName"] = ":".join(enum_index)

    # Validate proxy nodes before creating anything
    for proxy_object in proxy_objects or []:
        if not cmds.objExists(proxy_object):
            raise ValueError(f"Proxy object '{proxy_object}' does not exist")

        name = proxy_name or attr_name

        if cmds.objExists(f"{proxy_object}.{name}"):
            raise ValueError(
                f"Proxy attribute '{proxy_object}.{name}' already exists"
            )

    # Create primary attribute
    cmds.addAttr(primary_object, **kwargs)

    # Create proxies
    for proxy_object in proxy_objects or []:
        name = proxy_name or attr_name

        cmds.addAttr(
            proxy_object,
            longName=name,
            proxy=attr,
        )

    # Connect attributes
    if connect_from:
        cmds.connectAttr(connect_from, attr)

    if connect_to:
        for target in connect_to:
            cmds.connectAttr(attr, target)

    # Lock after connections
    if locked:
        cmds.setAttr(attr, lock=True)

    return attr


def connect_attributes(
    source: str,
    destination: list[str],
    force: bool = True,
) -> None:
    """Connect one source attribute to multiple destinations."""

    if not cmds.objExists(source):
        raise ValueError(f"Source attribute '{source}' does not exist")

    # Validate destinations before making changes
    for attr in destination:
        if not cmds.objExists(attr):
            raise ValueError(f"Destination attribute '{attr}' does not exist")

    for attr in destination:
        is_locked = cmds.getAttr(attr, lock=True)

        existing_source = cmds.connectionInfo(
            attr,
            sourceFromDestination=True,
        )

        if not force:
            if is_locked:
                raise RuntimeError(f"Destination '{attr}' is locked")

            if existing_source:
                raise RuntimeError(
                    f"Destination '{attr}' is already connected "
                    f"from '{existing_source}'"
                )

        # Already connected correctly
        if existing_source == source:
            continue

        try:
            if is_locked:
                cmds.setAttr(attr, lock=False)

            if existing_source:
                cmds.disconnectAttr(existing_source, attr)

            cmds.connectAttr(source, attr)

        finally:
            if is_locked:
                cmds.setAttr(attr, lock=True)