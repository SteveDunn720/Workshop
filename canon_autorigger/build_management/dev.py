
from typing import Any

import maya.cmds as cmds

from Workshop.maya_api.attribute_utils import (
    add_attribute_header,
    create_attribute,
    
)
from Workshop.control.core import create_control
from Workshop.tag.core import lock_tag


DEV_CONTROL = "DEV_ctrl"


def create_dev_control(parent:str, size:float, offset:tuple=(0,0,0)):
    dev = create_control(
        name='DEV',
        parent=parent,
        shape_position_offset=offset,
        control_shape='DEV',
        color_type='DEV',
        size=size
    )
    lock_tag(dev.ctrl, hide_tag=True)

def create_dev_attribute(
    attribute_name: str,
    control: str,
    rig_part: str,
    default: Any = None,
    min: float | None = None,
    max: float | None = None,
    enum_index: list[str] | None = None,
    connect_from: str | None = None,
    connect_to: list[str] | None = None,
    attr_type: str = "bool",
    proxy_name: str | None = None,
) -> str:
    """
    Create a development attribute on DEV_CONTROL and proxy
    it onto a specified control.

    Creates a rig-part header if missing.

    Development attributes are always visible, keyable,
    and unlocked.

    Returns:
        Full attribute path on DEV_CONTROL.
    """

    if not cmds.objExists(DEV_CONTROL):
        raise ValueError(
            f"Development control '{DEV_CONTROL}' does not exist"
        )

    if not cmds.objExists(control):
        raise ValueError(f"Control '{control}' does not exist")

    # Create rig-part header if missing
    header = f"{DEV_CONTROL}.{rig_part}"

    if not cmds.objExists(header):
        add_attribute_header(
            target=DEV_CONTROL,
            name=rig_part,
        )

    # Create development attribute
    dev_attr_name = f"DEV_{attribute_name}"
    dev_attr = f"{DEV_CONTROL}.{dev_attr_name}"

    if not cmds.objExists(dev_attr):
        return create_attribute(
            primary_object=DEV_CONTROL,
            attr_name=dev_attr_name,
            default=default,
            min=min,
            max=max,
            enum_index=enum_index,
            proxy_objects=[control],
            connect_from=connect_from,
            connect_to=connect_to,
            attr_type=attr_type,
            keyable=True,
            hidden=False,
            locked=False,
            proxy_name=proxy_name,
        )

    return dev_attr