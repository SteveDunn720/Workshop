
from dataclasses import dataclass

import maya.cmds as cmds

from Workshop.control.core import Control
from Workshop.joint import create_joint
from Workshop.guide.core import GuideInfo
from Workshop.maya_api.node import DistanceBetweenNode
from Workshop.transform.constraint import constraint
from Workshop.transform.utils import create_transform

from Workshop.canon_autorigger.module_schema import (
    ModuleRelationship,
    ModuleSetting,
)

from ..module_shared import module_prep
from ..ik import create_IK_single_chain
from ..twist import create_twist, TwistData


@dataclass
class module_info:
    ik_joints: list[str]
    bind_joints: list[str]
    twists: list[TwistData]
    controls: list[Control]


class Ik_correctives:

    MODULE_NAME = "ik_correctives"
    DISPLAY_NAME = "IK Correctives"

    GUIDES = ()

    SETTINGS = (
        ModuleSetting(
            name="rig_size",
            setting_type="float",
            default=1.0,
        ),
        ModuleSetting(
            name="control_color",
            setting_type="string",
            default="MISC",
        ),
        ModuleSetting(
            name="control_shape",
            setting_type="control_shape",
            default="circle",
        ),
        ModuleSetting(
            name="divisions",
            setting_type="int",
            default=1,
        ),
        ModuleSetting(
            name="mid_control",
            setting_type="bool",
            default=False,
        ),
        ModuleSetting(
            name="primary_axis",
            setting_type="string",
            default="Y",
        ),
    )

    RELATIONSHIPS = (
        ModuleRelationship(
            name="joint_parent",
            relationship_type="joint",
            default="auto",
        ),
        ModuleRelationship(
            name="control_parent",
            relationship_type="control_space",
            default="auto",
        ),
    )

    def __init__(
        self,
        parent_part: str | None = None,
        part: str = "pec",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list[GuideInfo] | None = None,
        joint_parent: str = "skel",
        end_ik_space: list | None = None,
        root_ik_space: list | None = None,
        control_color: str = "MISC",
        control_shape: str = "circle",
        divisions: int = 1,
        mid_control: bool = False,
        primary_axis: str = "Y",
    ):

        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.rig_size = rig_size

        self.guides = guides or []
        self.joint_parent = joint_parent

        self.root_ik_space = root_ik_space or []
        self.end_ik_space = end_ik_space or []

        self.control_color = control_color
        self.control_shape = control_shape

        self.primary_axis = primary_axis.upper()

        if self.primary_axis not in {"X", "Y", "Z"}:
            raise ValueError(
                "primary_axis must be X, Y, or Z"
            )

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
        # Primary and secondary aim axes
        # --------------------------------------------------

        axis_vectors = {
            "X": (1, 0, 0),
            "Y": (0, 1, 0),
            "Z": (0, 0, 1),
        }

        aim_vector = axis_vectors[self.primary_axis]

        up_vectors = {
            "X": (0, 1, 0),
            "Y": (0, 0, 1),
            "Z": (0, 1, 0),
        }

        up_vector = up_vectors[self.primary_axis]

        # --------------------------------------------------
        # Build IK corrective segments
        # --------------------------------------------------

        for guide in self.guides[1:]:

            descriptor = guide.descriptor

            # ----------------------------------------------
            # Root driver
            # ----------------------------------------------

            root_driver = create_transform(
                name=f"{descriptor}_root_driver",
                parent=self.guts,
                transform=guide.name,
            )

            if self.root_ik_space:
                constraint(
                    drivers=self.root_ik_space,
                    driven=root_driver,
                    constraint_type="parent",
                    parent=self.guts,
                )

            # ----------------------------------------------
            # Root offset
            # ----------------------------------------------

            root_offset = create_transform(
                name=f"{descriptor}_ik_root_offset",
                parent=self.guts,
                transform=guide.name,
            )

            # ----------------------------------------------
            # Root IK joint
            # ----------------------------------------------

            root_ik = create_joint(
                name=f"ik_{descriptor}",
                transform=guide.name,
                parent=root_offset,
                connect=False,
                bind_set=False,
                ue_set=False,
            )

            # ----------------------------------------------
            # Initial root orientation
            #
            # Aim toward the end guide and bake
            # the result into jointOrient.
            # ----------------------------------------------

            swing_axes = "".join(
                axis.lower()
                for axis in "XYZ"
                if axis != self.primary_axis
            )

            cmds.joint(
                root_ik,
                edit=True,
                degreeOfFreedom=swing_axes,
            )
            # ----------------------------------------------
            # End NULL joint
            #
            # The IK solver ends here.
            # This joint receives the stretch length.
            # ----------------------------------------------

            root_pos = cmds.xform(
                guide.name,
                query=True,
                worldSpace=True,
                translation=True,
            )

            end_pos = cmds.xform(
                end_guide.name,
                query=True,
                worldSpace=True,
                translation=True,
            )

            initial_length = (
                (end_pos[0] - root_pos[0]) ** 2
                + (end_pos[1] - root_pos[1]) ** 2
                + (end_pos[2] - root_pos[2]) ** 2
            ) ** 0.5

            if initial_length < 1e-6:
                raise ValueError(
                    f"{descriptor}: corrective guides "
                    "cannot occupy the same position."
                )

            end_null = cmds.createNode(
                "joint",
                name=f"ik_{descriptor}_end_null",
                parent=root_ik,
            )

            cmds.setAttr(
                f"{end_null}.segmentScaleCompensate",
                0,
            )

            # Positive length along the primary axis.
            cmds.setAttr(
                f"{end_null}.translate{self.primary_axis}",
                initial_length,
            )

            # ----------------------------------------------
            # End IK driver joint
            #
            # This joint is separate from the IK endpoint,
            # allowing additional corrective rotations.
            # ----------------------------------------------

            end_ik = cmds.createNode(
                "joint",
                name=f"ik_{descriptor}_end",
                parent=end_null,
            )

            cmds.setAttr(
                f"{end_ik}.segmentScaleCompensate",
                0,
            )

            # Both end joints inherit the root's orientation.
            # Their local rotations remain zero.

            # ----------------------------------------------
            # Single chain IK
            # ----------------------------------------------

            ik = create_IK_single_chain(
                name=descriptor,
                start_joint=root_ik,
                end_joint=end_null,
            )

            cmds.parent(
                ik.handle,
                self.guts,
            )

            # ----------------------------------------------
            # Root constraint
            #
            # Drive the offset rather than the IK joint.
            # The IK solver owns root_ik.rotate.
            # ----------------------------------------------

            constraint(
                drivers=[root_driver],
                driven=root_offset,
                constraint_type="parent",
                parent=self.guts,
            )

            # ----------------------------------------------
            # Stretch
            # ----------------------------------------------

            ik_dist = DistanceBetweenNode.create(
                name=f"{descriptor}_distance",
            )

            ik_dist.input_matrix1.connect_from(
                f"{root_driver}.worldMatrix[0]"
            )

            ik_dist.input_matrix2.connect_from(
                f"{self.ik_end_loc}.worldMatrix[0]"
            )

            ik_dist.distance.connect_to(
                f"{end_null}.translate{self.primary_axis}"
            )

            # ----------------------------------------------
            # IK handle constraint
            # ----------------------------------------------

            constraint(
                drivers=[self.ik_end_loc],
                driven=ik.handle,
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
                name=f"def_{descriptor}",
                transform=root_ik,
                connect=False,
                parent=self.joint_parent,
            )

            end_joint = create_joint(
                name=f"def_{descriptor}_end",
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
                rig_size=self.rig_size,
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
