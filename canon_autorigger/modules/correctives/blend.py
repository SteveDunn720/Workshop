import maya.cmds as cmds

from Workshop.joint import create_joint
from Workshop.transform.constraint import constraint
from Workshop.transform.utils import create_transform
from Workshop.transform.quat import (
    relative_rotation,
    weighted_rotation_quat,
    drive_rotation_with_quat,
    signed_relative_twist,
)
from Workshop.maya_api.node import MultiplyDivideNode, RemapValueNode

from ..module_initialize import module_prep


class Blend:

    def __init__(
        self,
        driver: str,
        part: str = "blend",
        side: str = "M",
        parent: str = "rig",
        guides: list | None = None,
        joint_parent: str = "skel",

        # Corrective motion weights
        blend: float = 0.5,
        translate_blend: float = 1.0,

        # Optional activation
        driver_axis: str | None = None,
        driver_rot_range: tuple = (-90, 90),
        mult_range: tuple = (0.0, 1.0),

        # Optional pop
        pop_amount: float | None = None,
        pop_axis: str = "Y",
    ):

        self.driver = driver
        self.part = part
        self.side = side
        self.parent = parent
        self.guides = guides or []
        self.joint_parent = joint_parent

        self.blend = blend
        self.translate_blend = translate_blend

        self.driver_axis = driver_axis
        self.driver_rot_range = driver_rot_range
        self.mult_range = mult_range

        self.pop_amount = pop_amount
        self.pop_axis = pop_axis

    def build(self):

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

        guide = self.guides[0]
        descriptor = guide.descriptor

        # --------------------------------------------------
        # Parent follow
        # --------------------------------------------------

        switch_parent = create_transform(
            name=f"switch_parent_{descriptor}",
            parent=self.guts,
            transform=self.joint_parent,
        )

        constraint(
            drivers=[self.joint_parent],
            driven=switch_parent,
            parent=self.guts,
        )

        # --------------------------------------------------
        # Corrective motion layer
        # --------------------------------------------------

        switch_offset = create_transform(
            name=f"switch_offset_{descriptor}",
            parent=switch_parent,
            transform=self.driver,
        )

        switch_blend = create_transform(
            name=f"switch_blend_{descriptor}",
            parent=switch_offset,
            transform=self.driver,
        )

        cmds.setAttr(
            f"{switch_blend}.translate",
            0, 0, 0,
            type="double3",
        )

        cmds.setAttr(
            f"{switch_blend}.rotate",
            0, 0, 0,
            type="double3",
        )

        # --------------------------------------------------
        # Guide offset
        # --------------------------------------------------

        switch_joint = create_joint(
            name=f"switch_{descriptor}",
            transform=guide.name,
            connect=False,
            parent=switch_blend,
            bind_set=False,
            ue_set=False,
        )

        self.switch_parent = switch_parent
        self.switch_blend = switch_blend
        self.switch_joint = switch_joint

        # --------------------------------------------------
        # Shared relative motion
        # --------------------------------------------------

        relative = relative_rotation(
            driver=self.driver,
            reference=self.joint_parent,
            name=f"{descriptor}_blend",
        )

        self.relative_motion = relative

        # --------------------------------------------------
        # Signed rest-relative activation
        # --------------------------------------------------

        activation_angle = None
        activation = None

        if self.driver_axis is not None:

            axis = self.driver_axis.upper()

            if axis not in ("X", "Y", "Z"):
                raise ValueError(
                    f"Invalid driver axis: {axis}"
                )

            activation_angle = signed_relative_twist(
                rotation=relative.rotation,
                axis=axis,
                name=f"{descriptor}_activation",
            )

            self.activation_angle = activation_angle

            activation = RemapValueNode(
                name=f"{descriptor}_activation_remap"
            )

            activation.input_min.set(
                self.driver_rot_range[0]
            )

            activation.input_max.set(
                self.driver_rot_range[1]
            )

            activation.output_min.set(
                self.mult_range[0]
            )

            activation.output_max.set(
                self.mult_range[1]
            )

            activation.input_value.connect_from(
                activation_angle
            )

        # --------------------------------------------------
        # Weighted quaternion rotation
        # --------------------------------------------------

        weighted_quat = weighted_rotation_quat(
            rotation=relative.rotation,
            name=f"{descriptor}_weighted",
            weight=self.blend,
        )

        if activation is not None:

            rotation_mult = MultiplyDivideNode(
                name=f"{descriptor}_rotation_weight_mult"
            )

            rotation_mult.operation.set(1)

            rotation_mult.input1.x.connect_from(
                activation.output
            )

            rotation_mult.input2.x.set(
                self.blend
            )

            rotation_mult.output.x.connect_to(
                f"{descriptor}_weighted_slerp.inputT"
            )

        drive_rotation_with_quat(
            transform=switch_blend,
            quat_attribute=weighted_quat,
        )

        # --------------------------------------------------
        # Relative translation
        # --------------------------------------------------

        translation_mult = MultiplyDivideNode(
            name=f"{descriptor}_translation_mult"
        )

        translation_mult.operation.set(1)

        translation_mult.input1.connect_from(
            relative.translation
        )

        translation_mult.input2.set(
            (
                self.translate_blend,
                self.translate_blend,
                self.translate_blend,
            )
        )

        translation_mult.output.connect_to(
            f"{switch_blend}.translate"
        )

        # --------------------------------------------------
        # Optional pop
        # --------------------------------------------------

        output_switch = switch_joint
        self.pop_joint = None

        if self.pop_amount is not None:

            if activation_angle is None:
                raise ValueError(
                    "pop_amount requires driver_axis."
                )

            pop_joint = create_joint(
                name=f"switch_pop_{descriptor}",
                transform=switch_joint,
                connect=False,
                parent=switch_joint,
                bind_set=False,
                ue_set=False,
            )

            self.pop_joint = pop_joint

            pop_remap = RemapValueNode(
                name=f"{descriptor}_pop_remap"
            )

            pop_remap.input_min.set(
                self.driver_rot_range[0]
            )

            pop_remap.input_max.set(
                self.driver_rot_range[1]
            )

            pop_remap.output_min.set(0.0)

            pop_remap.output_max.set(
                self.pop_amount
            )

            pop_remap.input_value.connect_from(
                activation_angle
            )

            pop_remap.output.connect_to(
                f"{pop_joint}.translate{self.pop_axis.upper()}"
            )

            output_switch = pop_joint

        # --------------------------------------------------
        # Final deformation joint
        # --------------------------------------------------

        self.blend_joint = create_joint(
            name=f"def_{descriptor}",
            transform=guide.name,
            connect=False,
            parent=self.driver,
        )

        constraint(
            drivers=[output_switch],
            driven=self.blend_joint,
            parent=self.parent,
        )

        return self.blend_joint