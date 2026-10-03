from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from maya import cmds
from maya.api.OpenMaya import MMatrix

from Workshop.control.core import Control
from Workshop.transform import match_transform, matrix_constraint, set_world_matrix
from Workshop.tag.core import sets_tag
from Workshop.transform.utils import create_transform, get_distance_between
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
    rotate_order: RotateOrder = RotateOrder.YXZ,
    dont_mirror:bool=False
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
        source_transform = transform.ctrl
    elif isinstance(transform, str):
        source_transform = transform
    elif isinstance(transform, MMatrix):
        set_world_matrix(joint, transform, use_joint_orient=True)
    else:
        raise RuntimeError(f"{transform} is not a valid transform name or MMatrix")
    if source_transform is not None:
        if "_R_" in joint and bind_set and not dont_mirror:
            corrected_guide, mirror_group = get_behavior_mirrored_joint_matrix(
                source_transform,
                mirror_axis="X",
            )

            match_transform(
                joint,
                corrected_guide,
                use_joint_orient=True,
            )

            cmds.delete(mirror_group)

        else:
            match_transform(
                joint,
                source_transform,
                use_joint_orient=True,
            )
        if connect:
            matrix_constraint(source_transform, joint, False, use_joint_orient=True)

    if radius != 1:
        cmds.setAttr(f"{joint}.radius", radius)  # type: ignore

    cmds.setAttr(f"{joint}.segmentScaleCompensate", 0)

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



def get_behavior_mirrored_joint_matrix(
    guide: str,
    mirror_axis: str = "X",
    temp_parent: str = "guides",
):
    """
    Convert a geometrically mirrored guide into a Maya Behavior-mirrored
    joint matrix.

    Process:
        1. Duplicate the mirrored guide.
        2. Remove it from its existing hierarchy.
        3. Create an origin mirror transform.
        4. Mirror that transform.
        5. Parent the duplicated guide beneath it.
        6. Un-mirror the transform.
           -> duplicated guide is now reconstructed on the source side.
        7. Create a temporary joint from that source-side transform.
        8. Use Maya mirrorJoint with mirrorBehavior=True.
        9. Return the resulting mirrored joint's world matrix.
       10. Clean up temporary nodes.
    """

    axis = mirror_axis.upper()

    temp_nodes = []

    try:
        # -----------------------------------------------------
        # Duplicate the mirrored guide
        # -----------------------------------------------------

        mirror_group = create_transform(name=f'{guide}_reverse_flip_grp')
        temp_nodes.append(mirror_group)

        cmds.parent(
            mirror_group,
            temp_parent,
            absolute=True,
        )

        # Explicitly ensure identity at world origin.
        cmds.xform(
            mirror_group,
            worldSpace=True,
            translation=(0, 0, 0),
            rotation=(0, 0, 0),
            scale=(-1, 1, 1),
        )

        guide_duplicate = cmds.duplicate(
            guide,
            parentOnly=True,
            name=f"{guide}_jointMirror_TEMP",
        )[0]

        # Remove any child joints so mirrorJoint only mirrors this joint
        child_joints = cmds.listRelatives(
            guide_duplicate,
            children=True,
            type="joint",
            fullPath=True,
        ) or []

        if child_joints:
            cmds.delete(child_joints)

        temp_nodes.append(guide_duplicate)

        # Pull it completely out of the mirrored guide hierarchy.
        cmds.parent(
            guide_duplicate,
            mirror_group,
        )

        # -----------------------------------------------------
        # Create an origin transform
        # -----------------------------------------------------



        # -----------------------------------------------------
        # Mirror the group
        # -----------------------------------------------------

        cmds.setAttr(
            f"{mirror_group}.scale{axis}",
            1,
        )

        if cmds.nodeType(guide_duplicate) != "joint":

            temp_joint = cmds.createNode(
                "joint",
                name=f"{guide}_jointMirror_TEMP_jnt",
            )

            # Match the reverse-mirrored guide
            match_transform(
                temp_joint,
                guide_duplicate,
                use_joint_orient=True,
            )

            # Track it if/when we turn cleanup back on
            temp_nodes.append(temp_joint)
            cmds.parent(temp_joint, mirror_group)

            # From this point forward, use the joint instead
            guide_duplicate = temp_joint

        cmds.select(clear=True)
        cmds.select(guide_duplicate)
        mirrored_guide= cmds.mirrorJoint(mirrorYZ=True, mirrorBehavior=True, searchReplace=('_R_', '_R0_'))
        # -----------------------------------------------------
        # Maya Behavior mirror
        # -----------------------------------------------------

        

        return mirrored_guide[0], mirror_group

    finally:
        pass
