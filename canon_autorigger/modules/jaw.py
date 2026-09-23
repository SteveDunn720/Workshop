from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.maya_api.node import RemapValueNode
from Workshop.transform.utils import create_transform

from .module_initialize import module_prep, module_space

import maya.cmds as cmds
import math


@dataclass
class module_info:
    jaw:Control
    larynx:Control
    joint:list[str]

class Jaw:
    def __init__(
        self,
        part: str = "jaw",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel',
        control_space:list = [],
        larynx_follow_space: str | None = None,
        control_color:str = 'MISC',
        control_shape:str = 'circle'

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.control_space = control_space
        self.main_control_color = 'Middle'
        self.sub_control_color = 'SubMiddle'
        self.larynx_follow_space=larynx_follow_space

    # -------------------
    # Build steps
    # -------------------

    def connect_larynx_jaw_follow(
        self,
        jaw_ee: str,
        larynx_offset: str,
        space: str,
        weight: float = 0.5,
    ):
        """
        Gives the larynx a percentage of the jaw end effector's
        positional change relative to the supplied space.

        Rotation is intentionally ignored.
        """

        # ---------------------------------------------------------
        # Create rest reference in the jaw's parent space
        # ---------------------------------------------------------

        jaw_parent = cmds.listRelatives(
            jaw_ee,
            parent=True,
            fullPath=False,
        )[0]

        rest_offset = create_transform(
            name=f"{jaw_ee}_larynx_follow_rest_offset",
            parent=self.guts,
            transform=jaw_parent,
        )

        rest = create_transform(
            name=f"{jaw_ee}_larynx_follow_rest",
            parent=rest_offset,
            transform=jaw_ee,
        )

        constraint(drivers=[self.control_space[0].ctrl], driven=rest_offset)

        # ---------------------------------------------------------
        # Current jaw EE position in follow space
        # ---------------------------------------------------------

        current_mm = cmds.createNode(
            "multMatrix",
            name=f"{jaw_ee}_larynx_follow_current_mm",
        )

        cmds.connectAttr(
            f"{jaw_ee}.worldMatrix[0]",
            f"{current_mm}.matrixIn[0]",
        )

        cmds.connectAttr(
            f"{space}.worldInverseMatrix[0]",
            f"{current_mm}.matrixIn[1]",
        )

        current_dcmp = cmds.createNode(
            "decomposeMatrix",
            name=f"{jaw_ee}_larynx_follow_current_dcmp",
        )

        cmds.connectAttr(
            f"{current_mm}.matrixSum",
            f"{current_dcmp}.inputMatrix",
        )

        # ---------------------------------------------------------
        # Rest jaw EE position in the same space
        # ---------------------------------------------------------

        rest_mm = cmds.createNode(
            "multMatrix",
            name=f"{jaw_ee}_larynx_follow_rest_mm",
        )

        cmds.connectAttr(
            f"{rest}.worldMatrix[0]",
            f"{rest_mm}.matrixIn[0]",
        )

        cmds.connectAttr(
            f"{space}.worldInverseMatrix[0]",
            f"{rest_mm}.matrixIn[1]",
        )

        rest_dcmp = cmds.createNode(
            "decomposeMatrix",
            name=f"{jaw_ee}_larynx_follow_rest_dcmp",
        )

        cmds.connectAttr(
            f"{rest_mm}.matrixSum",
            f"{rest_dcmp}.inputMatrix",
        )

        # ---------------------------------------------------------
        # Current - rest
        # ---------------------------------------------------------

        delta = cmds.createNode(
            "plusMinusAverage",
            name=f"{jaw_ee}_larynx_follow_delta",
        )

        cmds.setAttr(f"{delta}.operation", 2)

        cmds.connectAttr(
            f"{current_dcmp}.outputTranslate",
            f"{delta}.input3D[0]",
        )

        cmds.connectAttr(
            f"{rest_dcmp}.outputTranslate",
            f"{delta}.input3D[1]",
        )

        # ---------------------------------------------------------
        # Weight
        # ---------------------------------------------------------

        mult = cmds.createNode(
            "multiplyDivide",
            name=f"{jaw_ee}_larynx_follow_mult",
        )

        cmds.setAttr(
            f"{mult}.input2",
            weight,
            weight,
            weight,
        )

        cmds.connectAttr(
            f"{delta}.output3D",
            f"{mult}.input1",
        )

        cmds.connectAttr(
            f"{mult}.output",
            f"{larynx_offset}.translate",
        )

    def get_yz_angle(self, object_a: str, object_b: str) -> float:
        pos_a = cmds.xform(
            object_a,
            query=True,
            worldSpace=True,
            translation=True,
        )

        pos_b = cmds.xform(
            object_b,
            query=True,
            worldSpace=True,
            translation=True,
        )

        delta_y = pos_b[1] - pos_a[1]
        delta_z = pos_b[2] - pos_a[2]

        angle = math.degrees(
            math.atan2(delta_z, delta_y)
        )

        return angle

    def jaw_build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        rot = self.get_yz_angle(self.guides[0].name, self.guides[1].name,)

        #controls
        self.jaw_ctrl = create_control(
            name=self.guides[0].descriptor,
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.control_size/6,
            control_shape="jaw",
            direction="y",
            sdk_offset=True, 
            color_type=self.sub_control_color,
            shape_rotation_offset=(rot - 90,0,0),
            dimensions=(1,1.3,1.3),
            shape_position_offset=(0,-self.control_size/60,0)
        )

        module_space(control=self.jaw_ctrl, space_list=self.control_space)

        #joints

        self.jaw_joint = create_joint(name=f'def_{self.guides[0].descriptor}', transform=self.jaw_ctrl.ctrl, connect=True, parent=self.joint_parent)
        self.jaw_ee_joint = create_joint(name=f'def_{self.guides[1].descriptor}', transform=self.guides[1].name, connect=False, parent=self.jaw_joint)

        self.larynx_ctrl = create_control(
            name=self.guides[2].descriptor,
            parent=self.control_grp,
            transform=self.guides[2].name,
            size=self.control_size/40,
            control_shape="circle",
            direction="y",
            sdk_offset=True, 
            shape_rotation_offset=(90,0,0),
            color_type=self.main_control_color
        )

        # Extra offset for soft jaw follow
        self.larynx_jaw_offset = create_transform(name=f"{self.larynx_ctrl.name}_jaw_offset", parent=self.larynx_ctrl.top, transform=self.larynx_ctrl.top)
        cmds.parent(self.larynx_ctrl.sdk, self.larynx_jaw_offset)

        self.connect_larynx_jaw_follow(
            jaw_ee=self.jaw_ee_joint,
            larynx_offset=self.larynx_jaw_offset ,
            space=self.larynx_follow_space,
            weight=0.5,
        )

        larynx_remap = RemapValueNode(name='larynx_remap')
        larynx_remap.input_value.connect_from(f'{self.jaw_ctrl.ctrl}.rotateX')
        larynx_remap.input_max.set(90)

        cmds.addAttr(self.jaw_ctrl.ctrl, longName="larynx_mult", defaultValue=-self.control_size/6, keyable=True)
        cmds.addAttr(self.larynx_ctrl.ctrl, longName="larynx_mult", proxy=f'{self.jaw_ctrl.ctrl}.larynx_mult')

        larynx_remap.output_max.connect_from(f'{self.jaw_ctrl.ctrl}.larynx_mult')
        larynx_remap.output.connect_to(f'{self.larynx_ctrl.sdk}.translateY')

        jaw_remap = RemapValueNode(name='jaw_remap')
        jaw_remap.input_value.connect_from(f'{self.jaw_ctrl.ctrl}.rotateX')
        jaw_remap.input_max.set(90)

        cmds.addAttr(self.jaw_ctrl.ctrl, longName="jaw_mult", defaultValue=self.control_size/80, keyable=True)

        jaw_remap.output_max.connect_from(f'{self.jaw_ctrl.ctrl}.jaw_mult')
        jaw_remap.output.connect_to(f'{self.jaw_ctrl.sdk}.translateZ')


        module_space(control=self.larynx_ctrl, space_list=[self.larynx_follow_space])
        #constraint(drivers=[self.control_space[0], ], driven=self.larynx_ctrl.top, constraint_type='parent', parent=self.guts)

        #joints

        self.larynx_joint = create_joint(name=f'def_{self.guides[2].descriptor}', transform=self.larynx_ctrl.ctrl, connect=True, parent=self.jaw_joint)

        #constraint(drivers=[self.larynx_ctrl.ctrl, self.jaw_ctrl.ctrl], driven=self.larynx_joint, constraint_type='parent', parent=self.guts)

        jaw_info = module_info(jaw =self.jaw_ctrl, joint=[self.jaw_joint, self.jaw_ee_joint, self.larynx_joint], larynx=self.larynx_ctrl)
        return jaw_info