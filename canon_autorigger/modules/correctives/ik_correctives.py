from dataclasses import dataclass, field

import maya.cmds as cmds

from Workshop.control.core import Control
from Workshop.joint import create_joint
from Workshop.guide.core import GuideInfo
from Workshop.maya_api.node import DistanceBetweenNode
from Workshop.transform.constraint import constraint
from Workshop.transform.utils import create_transform

from ..module_initialize import module_prep
from ..ik import create_IK_single_chain
from ..twist import create_twist, TwistData


@dataclass
class module_info:
    ik_joints: list[str]
    bind_joints: list[str]
    twists: list[TwistData]
    controls: list[Control]


class Ik_correctives:

    def __init__(
        self,
        part: str = "pec",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list[GuideInfo] | None = None,
        joint_parent: str = "skel",
        end_ik_space: list | None = None,
        root_ik_space: list | None = None,
        control_color: str = "MISC",
        control_shape: str = "circle",
        divisions: int = 1,
        mid_control: bool = False,
    ):
        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.control_size = control_size

        self.guides = guides or []
        self.joint_parent = joint_parent

        self.root_ik_space = root_ik_space or []
        self.end_ik_space = end_ik_space or []

        self.control_color = control_color
        self.control_shape = control_shape

        self.primary_axis = "Y"

        self.divisions = divisions
        self.mid_control = mid_control

        self.ik_joints = []
        self.bind_joints = []
        self.twists = []
        self.controls = []

    def build(self):

        if len(self.guides) < 2:
            raise ValueError(
                "Ik_correctives requires at least two guides."
            )

        # --------------------------------------------------
        # Module preparation
        # --------------------------------------------------

        prep = module_prep(
            part=self.part,
            parent=self.parent,
            side=self.side,
            fkik=False,
            gut=True,
        )

        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        control_parent = (
            self.control_parent or self.control_grp
        )

        # --------------------------------------------------
        # End IK driver
        # --------------------------------------------------

        end_guide = self.guides[0]

        self.ik_end_grp = create_transform(
            name=f"{end_guide.descriptor}_grp",
            parent=self.guts,
            transform=end_guide.name,
        )

        self.ik_end_loc = create_transform(
            name=f"{end_guide.descriptor}_driver",
            parent=self.ik_end_grp,
            transform=end_guide.name,
        )

        if self.end_ik_space:
            constraint(
                drivers=self.end_ik_space,
                driven=self.ik_end_grp,
                constraint_type="parent",
                parent=self.guts,
            )

        # --------------------------------------------------
        # Build IK corrective segments
        # --------------------------------------------------

        for guide in self.guides[1:]:

            descriptor = guide.descriptor

            # ----------------------------------------------
            # IK driver joints
            # ----------------------------------------------

            root_ik = create_joint(
                name=f"ik_{descriptor}",
                transform=guide.name,
                connect=False,
                bind_set=False,
                ue_set=False,
                parent=self.guts,
            )

            end_ik = create_joint(
                name=f"ik_{descriptor}_end",
                transform=end_guide.name,
                connect=False,
                bind_set=False,
                ue_set=False,
                parent=root_ik,
            )

            cmds.setAttr(
                f"{end_ik}.jointOrient",
                0, 0, 0,
            )

            # ----------------------------------------------
            # Single chain IK
            # ----------------------------------------------

            ik = create_IK_single_chain(
                name=descriptor,
                start_joint=root_ik,
                end_joint=end_ik,
            )

            cmds.parent(
                ik.handle,
                self.guts,
            )

            # ----------------------------------------------
            # Stretch
            # ----------------------------------------------

            ik_dist = DistanceBetweenNode(
                name=descriptor,
            )

            ik_dist.input_matrix1.connect_from(
                f"{root_ik}.worldMatrix[0]"
            )

            ik_dist.input_matrix2.connect_from(
                f"{self.ik_end_loc}.worldMatrix[0]"
            )

            ik_dist.distance.connect_to(
                f"{end_ik}.translate{self.primary_axis}"
            )

            # ----------------------------------------------
            # IK constraints
            # ----------------------------------------------

            constraint(
                drivers=[self.ik_end_loc],
                driven=ik.handle,
                constraint_type="parent",
                parent=self.guts,
            )

            if self.root_ik_space:
                constraint(
                    drivers=self.root_ik_space,
                    driven=root_ik,
                    constraint_type="parent",
                    parent=self.guts,
                )

            self.ik_joints.extend([
                root_ik,
                end_ik,
            ])

            # ----------------------------------------------
            # Bind joints
            # ----------------------------------------------

            start_joint = create_joint(
                name=descriptor,
                transform=root_ik,
                connect=False,
                parent=self.joint_parent,
            )

            end_joint = create_joint(
                name=f"{descriptor}_end",
                transform=end_ik,
                connect=False,
                parent=start_joint,
            )

            self.bind_joints.extend([
                start_joint,
                end_joint,
            ])

            # ----------------------------------------------
            # Twist system
            # ----------------------------------------------

            twist = create_twist(
                start_driver=root_ik,
                end_driver=end_ik,

                start_joint=start_joint,
                end_joint=end_joint,

                cst_parent=self.guts,

                twist_count=self.divisions,
                primary_axis=self.primary_axis,

                mid_control=self.mid_control,
                control_parent=control_parent,
                control_size=self.control_size,
                control_shape=self.control_shape,
            )

            self.twists.append(twist)

            if twist.control:
                self.controls.append(twist.control)

        # --------------------------------------------------
        # Module information
        # --------------------------------------------------

        self.info = module_info(
            ik_joints=self.ik_joints,
            bind_joints=self.bind_joints,
            twists=self.twists,
            controls=self.controls,
        )

        return self.info