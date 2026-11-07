
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
    lock_tag(dev, hide_tag=True)

def create_dev_attribute(
    attribute_name: str,
    control: str,
    rig_part: str,
) -> str:
    """
    Create a development attribute on DEV_CONTROL and proxy
    it onto the specified control.

    Creates a rig-part header if one doesn't already exist.
    """

    if not cmds.objExists(DEV_CONTROL):
        raise ValueError(f"Development control '{DEV_CONTROL}' does not exist")

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
        create_attribute(
            primary_object=DEV_CONTROL,
            attr_name=dev_attr_name,
            attr_type="bool",
            default=False,
            proxy_objects=[control],
        )

    return dev_attr
