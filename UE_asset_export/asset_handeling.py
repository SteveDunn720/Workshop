import maya.cmds as cmds
from Workshop.tag.core import add_tag, remove_tag
import ast


def return_to_origin(sub_asset_name: str):
    """
    Stores local transform values on the node, then zeroes it out
    (translate/rotate = 0, scale = 1). Does NOT freeze transforms.
    """

    if not cmds.objExists(sub_asset_name):
        cmds.warning(f"{sub_asset_name} does not exist")
        return

    # Get LOCAL transforms
    t = cmds.getAttr(f"{sub_asset_name}.translate")[0]
    r = cmds.getAttr(f"{sub_asset_name}.rotate")[0]
    s = cmds.getAttr(f"{sub_asset_name}.scale")[0]

    transform_data = {
        "t": list(t),
        "r": list(r),
        "s": list(s)
    }

    # Store as string tag
    add_tag(
        object=sub_asset_name,
        tag_type="ORIGIN_TRANSFORM",
        tag_value=repr(transform_data)
    )

    # Zero out transforms (no freeze)
    cmds.setAttr(f"{sub_asset_name}.translate", 0, 0, 0)
    cmds.setAttr(f"{sub_asset_name}.rotate", 0, 0, 0)
    cmds.setAttr(f"{sub_asset_name}.scale", 1, 1, 1)



def restore_layout(sub_asset_name: str):
    """
    Restores previously stored transform values from ORIGIN_TRANSFORM tag.
    """

    if not cmds.objExists(sub_asset_name):
        cmds.warning(f"{sub_asset_name} does not exist")
        return

    if not cmds.attributeQuery("ORIGIN_TRANSFORM", node=sub_asset_name, exists=True):
        cmds.warning(f"{sub_asset_name} has no ORIGIN_TRANSFORM tag")
        return

    raw = cmds.getAttr(f"{sub_asset_name}.ORIGIN_TRANSFORM")
    if not raw:
        cmds.warning(f"No transform data found on {sub_asset_name}")
        return

    transform_data = ast.literal_eval(raw)

    t = transform_data.get("t", [0, 0, 0])
    r = transform_data.get("r", [0, 0, 0])
    s = transform_data.get("s", [1, 1, 1])

    cmds.setAttr(f"{sub_asset_name}.translate", *t)
    cmds.setAttr(f"{sub_asset_name}.rotate", *r)
    cmds.setAttr(f"{sub_asset_name}.scale", *s)

    remove_tag(
            object=sub_asset_name,
            tag_type="ORIGIN_TRANSFORM",
        )
    
