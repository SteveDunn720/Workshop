
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
        kwargs["enumName"] = ":".join(enum_index) if enum_index else " "

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


def add_proxy(source: str, proxy_list:list, proxy_name:str | None):
    for proxy_object in proxy_list:

        _, attr_name = source.rsplit(".", 1)

        name = proxy_name or attr_name

        cmds.addAttr(
            proxy_object,
            longName=name,
            proxy=source,
        )


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
                cmds.disconnectAttr(existing_source, attr) #type:ignore

            cmds.connectAttr(source, attr)

        finally:
            if is_locked:
                cmds.setAttr(attr, lock=True)



def add_attribute_header(target:str, name:str):

    create_attribute(
        primary_object=target,
        attr_name=name,
        attr_type="enum",
        enum_index=["-------------"],
        locked=True,
    )



def rename_attribute(
    attr: str,
    new_name: str,
    display_only: bool = False,
) -> str:
    """
    Rename a user-defined Maya attribute or change its display name.

    Built-in attributes cannot be renamed.

    Args:
        attr: Full attribute path (node.attribute).
        new_name: New attribute name or display name.
        display_only: Only change the displayed name.

    Returns:
        Full attribute path.
    """

    if not cmds.objExists(attr):
        raise ValueError(f"Attribute '{attr}' does not exist")

    node, old_name = attr.rsplit(".", 1)

    user_attrs = cmds.listAttr(
        node,
        userDefined=True,
    ) or []

    # Check if attribute is user-defined
    if old_name not in user_attrs:
        print(f"Cannot rename '{attr}': attribute is not user-defined.")
        return attr

    # Change display name only
    if display_only:
        cmds.addAttr(
            attr,
            edit=True,
            niceName=new_name,
        )
        return attr

    # Rename actual attribute
    if old_name == new_name:
        return attr

    new_attr = f"{node}.{new_name}"

    if cmds.objExists(new_attr):
        raise ValueError(
            f"Attribute '{new_attr}' already exists"
        )

    cmds.renameAttr(attr, new_name)

    return new_attr


def disconnect_attribute(attr: str) -> None:
    """Disconnect the incoming connection to a Maya attribute."""

    if not cmds.objExists(attr):
        raise ValueError(f"Attribute '{attr}' does not exist")

    source = cmds.connectionInfo(
        attr,
        sourceFromDestination=True,
    )

    if source:
        cmds.disconnectAttr(source, attr) #type:ignore




def set_channel_box_order(
    node: str,
    order: list[str],
    channel_box: str = "mainChannelBox",
) -> None:
    """
    Reorder attributes in Maya's Channel Box display.

    Attributes not included in `order` are preserved and
    displayed after the specified attributes.

    Note:
        This modifies the Channel Box UI, not the node's
        underlying attribute order.

    Args:
        node: Maya node containing the attributes.
        order: Attribute names in the desired display order.
        channel_box: Name of the Maya Channel Box control.
    """

    if not cmds.objExists(node):
        raise ValueError(f"Node '{node}' does not exist")

    # Get keyable and channel box visible attributes
    attrs = cmds.listAttr(node, keyable=True) or []

    visible_attrs = cmds.listAttr(
        node,
        channelBox=True,
    ) or []

    # Combine without duplicates
    for attr in visible_attrs:
        if attr not in attrs:
            attrs.append(attr)

    # Validate requested attributes
    for attr in order:
        if attr not in attrs:
            raise ValueError(
                f"Attribute '{node}.{attr}' is not visible "
                "in the Channel Box"
            )

    # Requested attributes first, remaining attributes afterward
    reordered = order + [
        attr for attr in attrs
        if attr not in order
    ]

    cmds.channelBox(
        channel_box,
        edit=True,
        fixedAttrList=reordered,
    )