import maya.cmds as cmds

from Workshop.joint import create_joint
from Workshop.transform.constraint import constraint
from Workshop.maya_api.node import (
    EulerToQuatNode,
    QuatSlerpNode,
    QuatToEulerNode,
    RemapValueNode,
)

from ..module_initialize import module_prep


class Blend:

    def __init__(
        self,
        driver: str,
        part: str = "blend",
        side: str = "M",
        parent: str = "rig",
        guides: list = [],
        joint_parent: str = "skel",

        # Base rotation blend
        blend: float = 0.5,

        # Optional rotation-driven activation
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
        self.guides = guides
        self.joint_parent = joint_parent

        self.blend = blend

        self.driver_axis = driver_axis
        self.driver_rot_range = driver_rot_range
        self.mult_range = mult_range

        self.pop_amount = pop_amount
        self.pop_axis = pop_axis

    # --------------------------------------------------
    # Build
    # --------------------------------------------------

    def build(self):

        # ==================================================
        # MODULE PREP
        # ==================================================

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

        # ==================================================
        # SWITCH HIERARCHY
        #
        # guts
        #   |
        #   switch_parent
        #       |
        #       switch_blend
        #           |
        #           switch_joint
        #               |
        #               switch_pop (optional)
        #
        # switch_parent:
        #     follows joint_parent
        #
        # switch_blend:
        #     receives corrective rotation
        #
        # switch_joint:
        #     stores the guide position/orientation
        #
        # switch_pop:
        #     receives optional corrective translation
        # ==================================================

        # --------------------------------------------------
        # Parent switch
        #
        # Match the joint parent in world space.
        # This becomes the base space for the entire
        # corrective system.
        # --------------------------------------------------

        switch_parent = create_joint(
            name=f"switch_parent_{descriptor}",
            transform=self.driver,
            connect=False,
            parent=self.guts,
            bind_set=False,
            ue_set=False,
        )

        # Follow the actual skeleton joint.
        constraint(
            drivers=[self.joint_parent],
            driven=switch_parent,
            parent=self.guts,
        )

        # --------------------------------------------------
        # Blend switch
        #
        # Starts at exactly the same transform as
        # switch_parent.
        #
        # Because it is parented underneath switch_parent,
        # it should begin with an identity local transform.
        #
        # Corrective rotation is applied here.
        # --------------------------------------------------

        switch_blend = create_joint(
            name=f"switch_blend_{descriptor}",
            transform=switch_parent,
            connect=False,
            parent=switch_parent,
            bind_set=False,
            ue_set=False,
        )

        # --------------------------------------------------
        # Main switch
        #
        # This is positioned/oriented from the guide.
        # It stores the corrective's offset from the
        # parent joint.
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

        # ==================================================
        # DRIVER ROTATION -> QUATERNION
        # ==================================================

        euler_to_quat = EulerToQuatNode(
            name=f"{descriptor}_blend_etq"
        )

        euler_to_quat.input_rotate.connect_from(
            f"{self.driver}.rotate"
        )

        euler_to_quat.input_rotate_order.connect_from(
            f"{self.driver}.rotateOrder"
        )

        # ==================================================
        # QUATERNION BLEND
        #
        # Identity -> Driver Rotation
        #
        # input1 remains identity.
        # input2 receives the driver rotation.
        #
        # inputT controls the amount of corrective rotation.
        # ==================================================

        quat_slerp = QuatSlerpNode(
            name=f"{descriptor}_blend_slerp"
        )

        quat_slerp.input2_quat.connect_from(
            euler_to_quat.output_quat
        )

        cmds.setAttr(
            f"{quat_slerp.name}.angleInterpolation",
            1,
        )

        # ==================================================
        # OPTIONAL ACTIVATION RAMP
        #
        # driver rotation
        #       |
        #       v
        #   RemapValue
        #       |
        #       v
        #  activation 0-1
        #
        # This activation can drive both:
        #
        #   rotation blend
        #   pop
        # ==================================================

        activation_remap = None

        if self.driver_axis is not None:

            activation_remap = RemapValueNode(
                name=f"{descriptor}_blend_activation_remap"
            )

            # Driver rotation range

            activation_remap.input_min.set(
                self.driver_rot_range[0]
            )

            activation_remap.input_max.set(
                self.driver_rot_range[1]
            )

            # Activation multiplier range

            activation_remap.output_min.set(
                self.mult_range[0]
            )

            activation_remap.output_max.set(
                self.mult_range[1]
            )

            activation_remap.input_value.connect_from(
                f"{self.driver}.rotate{self.driver_axis}"
            )

            # --------------------------------------------------
            # activation * base blend
            # --------------------------------------------------

            blend_mult = cmds.createNode(
                "multDoubleLinear",
                name=f"{descriptor}_blend_mult",
            )

            cmds.connectAttr(
                f"{activation_remap.name}.outValue",
                f"{blend_mult}.input1",
            )

            cmds.setAttr(
                f"{blend_mult}.input2",
                self.blend,
            )

            cmds.connectAttr(
                f"{blend_mult}.output",
                f"{quat_slerp.name}.inputT",
            )

        else:

            # No activation ramp.
            # Always use the base blend amount.

            quat_slerp.input_t.set(
                self.blend
            )

        # ==================================================
        # QUATERNION -> EULER
        #
        # Apply the corrective rotation to switch_blend.
        #
        # switch_parent handles skeleton motion.
        # switch_blend handles corrective motion.
        # ==================================================

        quat_to_euler = QuatToEulerNode(
            name=f"{descriptor}_blend_qte"
        )

        quat_to_euler.input_quat.connect_from(
            quat_slerp.output_quat
        )

        quat_to_euler.input_rotate_order.connect_from(
            f"{switch_blend}.rotateOrder"
        )

        quat_to_euler.output_rotate.connect_to(
            f"{switch_blend}.rotate"
        )

        # ==================================================
        # OPTIONAL POP
        # ==================================================

        output_switch = switch_joint
        self.pop_joint = None

        if self.pop_amount is not None:

            # --------------------------------------------------
            # Pop switch
            #
            # Match switch_joint rather than the guide.
            #
            # Because this is parented directly underneath
            # switch_joint, it begins as a zeroed local offset.
            # --------------------------------------------------

            pop_joint = create_joint(
                name=f"switch_pop_{descriptor}",
                transform=switch_joint,
                connect=False,
                parent=switch_joint,
                bind_set=False,
                ue_set=False,
            )

            self.pop_joint = pop_joint

            # --------------------------------------------------
            # Pop driven by activation ramp
            # --------------------------------------------------

            if activation_remap is not None:

                pop_mult = cmds.createNode(
                    "multDoubleLinear",
                    name=f"{descriptor}_pop_mult",
                )

                cmds.connectAttr(
                    f"{activation_remap.name}.outValue",
                    f"{pop_mult}.input1",
                )

                cmds.setAttr(
                    f"{pop_mult}.input2",
                    self.pop_amount,
                )

                cmds.connectAttr(
                    f"{pop_mult}.output",
                    f"{pop_joint}.translate{self.pop_axis}",
                )

            else:

                # No activation ramp.
                # Apply the full pop amount.

                cmds.setAttr(
                    f"{pop_joint}.translate{self.pop_axis}",
                    self.pop_amount,
                )

            output_switch = pop_joint

        # ==================================================
        # BIND JOINT
        #
        # The actual deformation joint contains none of the
        # corrective logic.
        #
        # It simply follows the final output of the switch
        # hierarchy.
        # ==================================================

        self.blend_joint = create_joint(
            name=f"def_{descriptor}",
            transform=guide.name,
            connect=True,
            parent=self.driver,
        )

        constraint(
            drivers=[output_switch],
            driven=self.blend_joint,
            parent=self.parent,
        )

        return self.blend_joint