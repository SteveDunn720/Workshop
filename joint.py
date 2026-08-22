from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from maya import cmds
from maya.api.OpenMaya import MMatrix

from Workshop.control.core import Control
from Workshop.transform import match_transform, matrix_constraint, set_world_matrix
from Workshop.tag.core import sets_tag
from Workshop.transform.utils import get_distance_between
from Workshop.skin.split.tag import tag_for_weight_split
from Workshop.maya_api.enum import RotateOrder

JOINT_SUFFIX: str = "_jnt"

_joint_collection: ContextVar[list[str] | None] = ContextVar("joint_collection", default=None)


@contextmanager
def collect_joints() -> Iterator[list[str]]:
    """
    Collect joints created inside this block.

    Any joints created within the `with` statement are added to a list,
    which is returned when the block finishes. Nested blocks are supported,
    and inner results are included in the outer list.

    Returns:
        list[str]: Joint names created in the block.
    """
    # Create a bucket to collect the joints created in the with block
    # then put it into the ContextVar so that _register_joint will add to this bucket
    bucket: list[str] = []
    parent_bucket = _joint_collection.get()
    token = _joint_collection.set(bucket)
    try:
        yield bucket
    finally:
        # Restore the previous state
        _joint_collection.reset(token)
        # If there was a parent, bubble up the results
        if parent_bucket is not None:
            parent_bucket.extend(bucket)


def _register_joint(joint: str) -> None:
    bucket = _joint_collection.get()
    if bucket is not None:
        bucket.append(joint)


        


def create_joint(
    name: str,
    transform: str | Control | MMatrix | None = None,
    parent: str | None = None,
    connect: bool = True,
    radius: float = 1,
    suffix:bool = True,
    bind_set:bool = True,
    ue_set:bool = True,
    rotate_order: RotateOrder = RotateOrder.YXZ
) -> str:
    if suffix:
        joint = cmds.createNode("joint", name=f"{name}{JOINT_SUFFIX}")
    else:
        joint = cmds.createNode("joint", name=f"{name}")
    cmds.setAttr(f'{joint}.rotateOrder', int(rotate_order)) #type:ignore
    if parent is not None:
        cmds.parent(joint, parent, relative=True)
    source_transform: str | None = None
    if transform is None:
        pass
    elif isinstance(transform, Control):
        source_transform = transform.transform
    elif isinstance(transform, str):
        source_transform = transform
    elif isinstance(transform, MMatrix):
        set_world_matrix(joint, transform, use_joint_orient=True)
    else:
        raise RuntimeError(f"{transform} is not a valid transform name or MMatrix")
    if source_transform is not None:
        match_transform(joint, source_transform, use_joint_orient=True)
        if connect:
            matrix_constraint(source_transform, joint, False, use_joint_orient=True)

    if radius != 1:
        cmds.setAttr(f"{joint}.radius", radius)  # type: ignore

    sets = []
    if bind_set:
        sets.append('bind_joints_set')
    if ue_set:
        sets.append('unreal_set')

    if sets != []:
        sets_tag(joint, sets)

    _register_joint(joint)
    # This is mGear specific and may need changed if you stop using mGear.
    """    add_to_joint_set(joint) """
    return joint


def twist_split(joint:str, child_joint:str | None = None, primary_axis='Y'):
    if child_joint:
        end = child_joint
    else:
        children = cmds.listRelatives(
            joint,
            children=True,
            type="joint",
            fullPath=False
        ) or []
        if not children:
            raise ValueError(f"{joint} has no child joint.")
        end = children[0]


    bone_len = cmds.getAttr(f"{end}.translate{primary_axis}")

    descriptor = joint.removesuffix(JOINT_SUFFIX)

    twist_jnt = create_joint(name=f'{descriptor}_twist', transform=joint, connect=False, bind_set=True, ue_set=True, parent=joint)

    cmds.setAttr(f"{twist_jnt}.translate{primary_axis}", bone_len * .666) #type:ignore

    old_twist = f"{joint}.rotate{primary_axis}"
    new_twist = f"{twist_jnt}.rotate{primary_axis}"

    tag_for_weight_split(
        influence=joint,  # <-- your SOURCE joint (must already exist)
        split_influences=[joint, twist_jnt, twist_jnt],  # <-- the ones you just created
    )

    source = cmds.listConnections(
        old_twist,
        source=True,
        destination=False,
        plugs=True,
    ) or []

    if source:
        source_twist = source[0]

        cmds.disconnectAttr(source_twist, old_twist)
        cmds.connectAttr(source_twist, new_twist, force=True)

    return twist_jnt
