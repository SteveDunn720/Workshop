import maya.cmds as cmds

from Workshop.joint import create_joint
from Workshop.transform.constraint import constraint
from Workshop.transform.quat import (
    relative_rotation,
    signed_relative_twist,
)
from Workshop.maya_api.node import RemapValueNode

from Workshop.canon_autorigger.build_management.dev import create_dev_attribute
from Workshop.canon_autorigger.module_schema import ModuleRelationship, ModuleSetting
from Workshop.maya_api.attribute_utils import set_attribute

from ..module_shared import module_prep


class Pull:
    MODULE_NAME = "pull"
    DISPLAY_NAME = "Pull Corrective"
    GUIDES = ()
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="range", setting_type="vector2", default=(-90, 90)),
        ModuleSetting(name="driver_axis", setting_type="string", default="X"),
        ModuleSetting(name="pull_axis", setting_type="string", default="Y"),
        ModuleSetting(name="pull_amount", setting_type="float", default=1.0),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="driver", relationship_type="joint", default="auto"),
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
    )


    def __init__(
        self,
        driver: str,
        parent_part:str | None = None, 
        part: str = "pull",
        side: str = "M",
        parent: str = "rig",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list | None = None,
        joint_parent: str = "skel",
        range: tuple = (-90, 90),
        driver_axis: str = "X",
        pull_axis: str = "Y",
        pull_amount: float = 1.0,
        rotation_reference: str | None = None,
    ):

        self.driver = driver
        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.rig_size = rig_size
        self.guides = guides or []
        self.joint_parent = joint_parent

        self.range = range
        self.driver_axis = driver_axis.upper()
        self.pull_axis = pull_axis.upper()
        self.pull_amount = pull_amount

        self.rotation_reference = rotation_reference

    def build(self):

        # --------------------------------------------------
        # Module setup
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

        if self.driver_axis not in ("X", "Y", "Z"):
            raise ValueError(
                f"Invalid driver_axis: {self.driver_axis}"
            )

        if self.pull_axis not in ("X", "Y", "Z"):
            raise ValueError(
                f"Invalid pull_axis: {self.pull_axis}"
            )

        if self.range[0] == self.range[1]:
            raise ValueError(
                "Pull range cannot have identical endpoints."
            )

        # --------------------------------------------------
        # Resolve rotation reference
        # --------------------------------------------------

        # Use the actual parent of the driver by default.
        # This keeps the rotation measurement independent
        # of the corrective's joint_parent.

        rotation_reference = self.rotation_reference

        if rotation_reference is None:

            parents = cmds.listRelatives(
                self.driver,
                parent=True,
                fullPath=True,
            ) or []

            if not parents:
                raise RuntimeError(
                    f"Driver '{self.driver}' has no parent. "
                    "Specify rotation_reference explicitly."
                )

            rotation_reference = parents[0]

        self.rotation_reference = rotation_reference

        # --------------------------------------------------
        # Switch joints
        # --------------------------------------------------

        root_switch_joint = create_joint(
            name=f"switch_root_{descriptor}",
            transform=guide.name,
            connect=False,
            parent=self.guts,
            bind_set=False,
            ue_set=False,
        )

        switch_joint = create_joint(
            name=f"switch_{descriptor}",
            transform=guide.name,
            connect=False,
            parent=root_switch_joint,
            bind_set=False,
            ue_set=False,
        )

        self.root_switch_joint = root_switch_joint
        self.switch_joint = switch_joint

        # --------------------------------------------------
        # Parent follow
        # --------------------------------------------------

        constraint(
            drivers=[self.joint_parent],
            driven=root_switch_joint,
            parent=self.guts,
        )

        # --------------------------------------------------
        # Rest-relative rotation
        # --------------------------------------------------

        relative = relative_rotation(
            driver=self.driver,
            reference=rotation_reference,
            name=f"{descriptor}_pull",
        )

        self.relative_motion = relative

        # --------------------------------------------------
        # Signed twist activation
        # --------------------------------------------------

        activation_angle = signed_relative_twist(
            rotation=relative.rotation,
            axis=self.driver_axis,
            name=f"{descriptor}_pull_activation",
        )

        self.activation_angle = activation_angle

        # --------------------------------------------------
        # Pull remap
        # --------------------------------------------------

        pull_remap = RemapValueNode(
            name=f"{descriptor}_remap"
        )

        start_angle, end_angle = self.range

        # Maya remapValue expects ascending input bounds.
        # Reverse the output when the range is descending.

        if start_angle < end_angle:
            input_min, input_max = start_angle, end_angle
            output_min, output_max = 0.0, self.pull_amount
        else:
            input_min, input_max = end_angle, start_angle
            output_min, output_max = self.pull_amount, 0.0

        pull_remap.input_min.connect_from(dev_value("input_min", input_min))
        pull_remap.input_max.connect_from(dev_value("input_max", input_max))
        pull_remap.output_min.connect_from(dev_value("output_min", output_min))
        pull_remap.output_max.connect_from(dev_value("output_max", output_max))

        pull_remap.input_value.connect_from(
            activation_angle
        )

        pull_remap.output.connect_to(
            f"{switch_joint}.translate{self.pull_axis}"
        )

        self.pull_remap = pull_remap

        # --------------------------------------------------
        # Deformation joint
        # --------------------------------------------------

        self.pull_joint = create_joint(
            name=f"def_{descriptor}",
            transform=switch_joint,
            connect=True,
            parent=self.joint_parent,
        )

        return self.pull_joint