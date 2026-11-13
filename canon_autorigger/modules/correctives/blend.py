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

from Workshop.canon_autorigger.build_management.dev import create_dev_attribute
from Workshop.canon_autorigger.module_schema import ModuleRelationship, ModuleSetting
from Workshop.maya_api.attribute_utils import connect_attributes, set_attribute

from ..module_shared import module_prep


class Blend:
    MODULE_NAME = "blend"
    DISPLAY_NAME = "Blend Corrective"
    GUIDES = ()
    SETTINGS = (
        ModuleSetting(name="blend", setting_type="float", default=0.5),
        ModuleSetting(name="translate_blend", setting_type="float", default=1.0),
        ModuleSetting(name="driver_axis", setting_type="string", default=None),
        ModuleSetting(name="driver_rot_range", setting_type="vector2", default=(-90, 90)),
        ModuleSetting(name="mult_range", setting_type="vector2", default=(0.0, 1.0)),
        ModuleSetting(name="pop_amount", setting_type="float", default=None),
        ModuleSetting(name="pop_axis", setting_type="string", default="Y"),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="driver", relationship_type="joint", default="auto"),
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
    )


    def __init__(
        self,
        driver: str,
        parent_part:str | None = None, 
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
        self.parent_part = parent_part

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

        def dev_value(name: str, value: float, **kwargs: float) -> str:
            """Expose a driver value without changing its initial behavior."""
            return create_dev_attribute(
                attribute_name=f"{self.part}_{self.side}_{descriptor}_{name}",
                control=self.control_grp,
                rig_part=self.part,
                default=value,
                attr_type="double",
                **kwargs,
            )

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

        set_attribute(f"{switch_blend}.translate", (0, 0, 0))
        set_attribute(f"{switch_blend}.rotate", (0, 0, 0))

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

            activation.input_min.connect_from(
                dev_value("activation_input_min", self.driver_rot_range[0])
            )
            activation.input_max.connect_from(
                dev_value("activation_input_max", self.driver_rot_range[1])
            )
            activation.output_min.connect_from(
                dev_value("activation_output_min", self.mult_range[0])
            )
            activation.output_max.connect_from(
                dev_value("activation_output_max", self.mult_range[1])
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

            rotation_mult.input2.x.connect_from(
                dev_value("rotation_weight", self.blend)
            )

            rotation_mult.output.x.connect_to(
                f"{descriptor}_weighted_slerp.inputT"
            )

        else:
            # The weighted quaternion helper initialized this value; expose it live.
            connect_attributes(
                dev_value("rotation_weight", self.blend),
                [f"{descriptor}_weighted_slerp.inputT"],
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

        translation_weight = dev_value("translation_weight", self.translate_blend)
        for axis in "xyz":
            getattr(translation_mult.input2, axis).connect_from(translation_weight)

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

            pop_remap.input_min.connect_from(
                dev_value("pop_input_min", self.driver_rot_range[0])
            )
            pop_remap.input_max.connect_from(
                dev_value("pop_input_max", self.driver_rot_range[1])
            )
            pop_remap.output_min.connect_from(dev_value("pop_output_min", 0.0))
            pop_remap.output_max.connect_from(
                dev_value("pop_amount", self.pop_amount)
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