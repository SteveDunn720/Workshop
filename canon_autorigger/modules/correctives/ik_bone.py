from dataclasses import dataclass

import maya.cmds as cmds
from maya.api import OpenMaya as om

from Workshop.control import create_control
from Workshop.control.core import Control
from Workshop.joint import create_joint
from Workshop.guide.core import GuideInfo
from Workshop.transform.utils import create_transform

from Workshop.canon_autorigger.module_schema import ModuleRelationship, ModuleSetting
from Workshop.canon_autorigger.build_management.dev import create_dev_attribute
from Workshop.maya_api.attribute_utils import create_attribute, set_attribute, connect_attributes
from Workshop.transform.constraint import constraint

from ..module_shared import module_prep
from ..ik import create_IK_single_chain


@dataclass
class BoneData:
    root_ik: str
    end_ik: str
    ik_handle: str

    root_guide: str
    end_guide: str

    control: Control
    bind_joint: str

    stretch_node: str
    midpoint_driver: str


def _validate_axis(axis: str) -> str:
    axis = axis.upper()

    if axis not in {"X", "Y", "Z"}:
        raise ValueError(
            f"Invalid axis: {axis}. Expected X, Y, or Z."
        )

    return axis


def _get_world_position(node: str) -> om.MVector:
    return om.MVector(
        cmds.xform(
            node,
            query=True,
            worldSpace=True,
            translation=True,
        )
    )


def _generate_offset_position(
    driver: str,
    axis: str,
    offset: float,
) -> tuple[float, float, float]:
    """
    Offset a position along the driver's local axis.

    Uses the driver's world matrix so the generated
    position respects its current orientation.
    """

    matrix = om.MMatrix(
        cmds.getAttr(f"{driver}.worldMatrix[0]")
    )

    axis_vector = {
        "X": om.MVector(1, 0, 0),
        "Y": om.MVector(0, 1, 0),
        "Z": om.MVector(0, 0, 1),
    }[axis]

    direction = axis_vector * matrix

    if direction.length() < 1e-8:
        raise ValueError(
            f"Cannot calculate offset direction for {driver}"
        )

    direction.normalize()

    position = _get_world_position(driver)
    result = position + direction * offset

    return result.x, result.y, result.z


class IK_Bone:
    MODULE_NAME = "ik_bone"
    DISPLAY_NAME = "IK Bone"
    GUIDES = ()
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="offset", setting_type="float", default=1.0),
        ModuleSetting(name="primary_axis", setting_type="string", default="Y"),
        ModuleSetting(name="control_shape", setting_type="control_shape", default="circle"),
        ModuleSetting(name="control_color", setting_type="string", default="MISC"),
        ModuleSetting(name="stretch_default", setting_type="float", default=1.0),
        ModuleSetting(name="mid_control_size_multiplier", setting_type="float", default=1.0),
        ModuleSetting(name="mid_control_name", setting_type="string", default="mid"),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="root_driver", relationship_type="joint", default="auto"),
        ModuleRelationship(name="end_driver", relationship_type="joint", default="auto"),
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
    )

    def __init__(
        self,
        
        root_driver: str,
        end_driver: str,

        parent_part:str | None = None, 
        part: str = "bone",
        side: str = "M",

        parent: str = "components",
        control_parent: str | None = None,
        joint_parent: str = "skel",

        guides: list[GuideInfo] | None = None,

        primary_axis: str = "Y",
        offset: float = 1.0,

        rig_size: float = 1.0,
        control_shape: str = "circle",
        control_color: str = "MISC",

        stretch_default: float = 1.0,
        mid_control_size_multiplier: float = 1.0,
        mid_control_name: str = "mid",
    ):

        self.root_driver = root_driver
        self.end_driver = end_driver

        self.part = part
        self.side = side

        self.parent = parent
        self.control_parent = control_parent
        self.joint_parent = joint_parent

        self.guides = guides or []

        self.primary_axis = _validate_axis(primary_axis)
        self.offset = offset

        self.rig_size = rig_size
        self.control_shape = control_shape
        self.control_color = control_color

        self.stretch_default = stretch_default
        self.mid_control_size_multiplier = mid_control_size_multiplier
        self.mid_control_name = mid_control_name

    # --------------------------------------------------
    # Guides
    # --------------------------------------------------

    def _create_guides(self):

        descriptor = f"{self.part}_{self.side}"

        if self.guides:

            if len(self.guides) != 2:
                raise ValueError(
                    "Bone requires exactly two guides."
                )

            return (
                self.guides[0].name,
                self.guides[1].name,
            )

        root_position = _generate_offset_position(
            self.root_driver,
            self.primary_axis,
            self.offset,
        )

        end_position = _generate_offset_position(
            self.end_driver,
            self.primary_axis,
            self.offset,
        )

        root_guide = cmds.spaceLocator(
            name=f"{descriptor}_root_guide"
        )[0]

        end_guide = cmds.spaceLocator(
            name=f"{descriptor}_end_guide"
        )[0]

        cmds.xform(
            root_guide,
            worldSpace=True,
            translation=root_position,
        )

        cmds.xform(
            end_guide,
            worldSpace=True,
            translation=end_position,
        )

        # Orient the root guide toward the end guide.
        # Its primary axis becomes the bone's length axis.

        aim = {
            "X": (1, 0, 0),
            "Y": (0, 1, 0),
            "Z": (0, 0, 1),
        }[self.primary_axis]

        up = {
            "X": (0, 1, 0),
            "Y": (0, 0, 1),
            "Z": (0, 1, 0),
        }[self.primary_axis]

        aim_constraint = cmds.aimConstraint(
            end_guide,
            root_guide,
            aimVector=aim,
            upVector=up,
            worldUpType="objectrotation",
            worldUpObject=self.root_driver,
            worldUpVector=up,
        )[0]

        cmds.delete(aim_constraint)

        # The end joint should inherit the root's orientation.

        cmds.xform(
            end_guide,
            worldSpace=True,
            rotation=cmds.xform(
                root_guide,
                query=True,
                worldSpace=True,
                rotation=True,
            ),
        )

        return root_guide, end_guide

    # --------------------------------------------------
    # IK joints
    # --------------------------------------------------

    def _create_ik_joints(
        self,
        root_guide: str,
        end_guide: str,
    ):

        descriptor = f"{self.part}_{self.side}"

        root_ik = create_joint(
            name=f"{descriptor}_root_ik",
            transform=root_guide,
            parent=self.guts,
            connect=False,
            bind_set=False,
            ue_set=False,
        )

        end_ik = create_joint(
            name=f"{descriptor}_end_ik",
            transform=end_guide,
            parent=root_ik,
            connect=False,
            bind_set=False,
            ue_set=False,
        )

        # Preserve the root orientation and zero the
        # end joint's local rotation orientation.

        set_attribute(f"{end_ik}.jointOrient", (0, 0, 0))

        # Ensure the endpoint lies on the primary axis.
        # This assumes guides define a straight bone.

        root_pos = _get_world_position(root_guide)
        end_pos = _get_world_position(end_guide)

        length = (end_pos - root_pos).length()

        local_end = cmds.getAttr(
            f"{end_ik}.translate{self.primary_axis}"
        )

        sign = -1 if local_end < 0 else 1

        for axis in "XYZ":
            set_attribute(f"{end_ik}.translate{axis}", 0)

        set_attribute(f"{end_ik}.translate{self.primary_axis}", length * sign)

        return root_ik, end_ik

    # --------------------------------------------------
    # Stretch
    # --------------------------------------------------

    def _create_stretch(
        self,
        root_ik: str,
        end_ik: str,
        root_target: str,
        end_target: str,
        control: Control,
    ) -> str:
        """
        Create stretch behavior for the IK bone.

        Stretch:
            0.0 = Original bone length
            1.0 = Full distance between root and end targets

        Returns:
            The stretch blend node.
        """

        descriptor = f"{self.part}_{self.side}"
        axis = self.primary_axis.upper()

        # --------------------------------------------------
        # Rest length
        # --------------------------------------------------

        rest_length = cmds.getAttr(
            f"{end_ik}.translate{axis}"
        )

        rest_sign = -1.0 if rest_length < 0 else 1.0
        rest_length = abs(rest_length)

        # --------------------------------------------------
        # Stretch attribute
        # --------------------------------------------------

        stretch_attr = f"{control.ctrl}.stretch"

        if not cmds.attributeQuery(
            "stretch",
            node=control.ctrl,
            exists=True,
        ):
            create_attribute(
                primary_object=control.ctrl,
                attr_name="stretch",
                attr_type="double",
                min=0.0,
                max=1.0,
                default=self.stretch_default,
            )

        # --------------------------------------------------
        # Distance between targets
        # --------------------------------------------------

        distance_node = cmds.createNode(
            "distanceBetween",
            name=f"{descriptor}_stretch_distance",
        )

        connect_attributes(f"{root_target}.worldMatrix[0]", [f"{distance_node}.inMatrix1"])

        connect_attributes(f"{end_target}.worldMatrix[0]", [f"{distance_node}.inMatrix2"])

        # --------------------------------------------------
        # Blend rest length and target distance
        # --------------------------------------------------

        stretch_blend = cmds.createNode(
            "blendColors",
            name=f"{descriptor}_stretch_blend",
        )

        # Preserve the build-time rest length as an editable live driver.
        rest_length_attr = create_dev_attribute(
            attribute_name="rest_length",
            control=control.ctrl,
            rig_part=f"{self.part}_{self.side}",
            attr_type="double",
            default=rest_length,
        )
        connect_attributes(rest_length_attr, [f"{stretch_blend}.color1R"])

        connect_attributes(f"{distance_node}.distance", [f"{stretch_blend}.color2R"])

        # --------------------------------------------------
        # Reverse stretch attribute
        # --------------------------------------------------

        # blendColors:
        # blender = 1 -> color1 (rest length)
        # blender = 0 -> color2 (target distance)
        #
        # We reverse the animator's stretch attribute so:
        # stretch = 0 -> rest length
        # stretch = 1 -> target distance

        stretch_reverse = cmds.createNode(
            "reverse",
            name=f"{descriptor}_stretch_reverse",
        )

        connect_attributes(stretch_attr, [f"{stretch_reverse}.inputX"])

        connect_attributes(f"{stretch_reverse}.outputX", [f"{stretch_blend}.blender"])

        # --------------------------------------------------
        # Restore joint translation direction
        # --------------------------------------------------

        stretch_sign = cmds.createNode(
            "multiplyDivide",
            name=f"{descriptor}_stretch_sign",
        )

        set_attribute(f"{stretch_sign}.operation", 1)

        sign_attr = create_dev_attribute(
            attribute_name="stretch_direction",
            control=control.ctrl,
            rig_part=f"{self.part}_{self.side}",
            attr_type="double",
            default=rest_sign,
            min=-1.0,
            max=1.0,
        )
        connect_attributes(sign_attr, [f"{stretch_sign}.input2X"])

        connect_attributes(f"{stretch_blend}.outputR", [f"{stretch_sign}.input1X"])

        # --------------------------------------------------
        # Drive IK chain length
        # --------------------------------------------------

        connect_attributes(
            f"{stretch_sign}.outputX",
            [f"{end_ik}.translate{axis}"],
        )

        return stretch_blend

    # --------------------------------------------------
    # Midpoint control
    # --------------------------------------------------

    def _create_midpoint_control(
        self,
        root_ik: str,
        end_ik: str,
    ):

        descriptor = f"{self.part}_{self.side}"

        root_pos = _get_world_position(root_ik)
        end_pos = _get_world_position(end_ik)

        midpoint = (root_pos + end_pos) * 0.5

        # Create a midpoint transform with the
        # same orientation as the IK root.

        midpoint_driver = create_transform(
            name=f"{descriptor}_midpoint_driver",
            parent=self.guts,
            transform=root_ik,
        )

        cmds.xform(
            midpoint_driver,
            worldSpace=True,
            translation=(
                midpoint.x,
                midpoint.y,
                midpoint.z,
            ),
        )

        # --------------------------------------------------
        # Control
        # --------------------------------------------------

        control = create_control(
            name=f"{descriptor}_{self.mid_control_name}",
            transform=midpoint_driver,
            parent=self.control_parent or self.control_grp,
            size=self.rig_size * self.mid_control_size_multiplier,
            control_shape=self.control_shape,
            color_type=self.control_color,
            direction=self.primary_axis.lower(),
        )

        # --------------------------------------------------
        # Midpoint translation
        # --------------------------------------------------

        cmds.pointConstraint(
            root_ik,
            end_ik,
            midpoint_driver,
            maintainOffset=False,
        )

        # --------------------------------------------------
        # Orientation
        # --------------------------------------------------

        constraint(
            drivers=[root_ik],
            driven=midpoint_driver,
            constraint_type="orient",
            parent=self.guts,
        )

        # Follow the midpoint driver, while preserving
        # the animator's local control offsets.

        cmds.parentConstraint(
            midpoint_driver,
            control.top,
            maintainOffset=True,
        )

        return control, midpoint_driver

    # --------------------------------------------------
    # Bind joint
    # --------------------------------------------------

    def _create_bind_joint(
        self,
        control: Control,
    ):

        descriptor = f"{self.part}_{self.side}"

        bind_joint = create_joint(
            name=f"{descriptor}_mid",
            transform=control.ctrl,
            parent=self.joint_parent,
            connect=False,
        )

        cmds.parentConstraint(
            control.ctrl,
            bind_joint,
            maintainOffset=False,
        )

        return bind_joint

    # --------------------------------------------------
    # Build
    # --------------------------------------------------

    def build(self) -> BoneData:

        descriptor = f"{self.part}_{self.side}"

        if not cmds.objExists(self.root_driver):
            raise ValueError(
                f"Root driver does not exist: {self.root_driver}"
            )

        if not cmds.objExists(self.end_driver):
            raise ValueError(
                f"End driver does not exist: {self.end_driver}"
            )

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

        # --------------------------------------------------
        # Guides
        # --------------------------------------------------

        root_guide, end_guide = self._create_guides()

        # --------------------------------------------------
        # IK joints
        # --------------------------------------------------

        root_ik, end_ik = self._create_ik_joints(
            root_guide,
            end_guide,
        )

        # --------------------------------------------------
        # IK handle
        # --------------------------------------------------

        ik = create_IK_single_chain(
            name=descriptor,
            start_joint=root_ik,
            end_joint=end_ik,
        )

        cmds.parent(
            ik.handle,
            self.guts,
        )

        # --------------------------------------------------
        # Driver targets
        # --------------------------------------------------

        root_target = create_transform(
            name=f"{descriptor}_root_target",
            parent=self.guts,
            transform=root_guide,
        )

        end_target = create_transform(
            name=f"{descriptor}_end_target",
            parent=self.guts,
            transform=end_guide,
        )

        cmds.parentConstraint(
            self.root_driver,
            root_target,
            maintainOffset=True,
        )

        cmds.parentConstraint(
            self.end_driver,
            end_target,
            maintainOffset=True,
        )

        # --------------------------------------------------
        # IK constraints
        # --------------------------------------------------

        cmds.parentConstraint(
            root_target,
            root_ik,
            maintainOffset=True,
        )

        cmds.pointConstraint(
            end_target,
            ik.handle,
            maintainOffset=False,
        )

        # --------------------------------------------------
        # Midpoint control
        # --------------------------------------------------

        control, midpoint_driver = (
            self._create_midpoint_control(
                root_ik,
                end_ik,
            )
        )

        # --------------------------------------------------
        # Stretch
        # --------------------------------------------------

        stretch_node = self._create_stretch(
            root_ik=root_ik,
            end_ik=end_ik,
            root_target=root_target,
            end_target=end_target,
            control=control,
        )

        # --------------------------------------------------
        # Bind joint
        # --------------------------------------------------

        bind_joint = self._create_bind_joint(
            control,
        )

        # --------------------------------------------------
        # Hide internals
        # --------------------------------------------------

        set_attribute(f"{root_ik}.visibility", False)

        set_attribute(f"{ik.handle}.visibility", False)

        set_attribute(f"{midpoint_driver}.visibility", False)

        # Generated guides are temporary placement objects.

        if not self.guides:
            cmds.delete(
                root_guide,
                end_guide,
            )

        # --------------------------------------------------
        # Module info
        # --------------------------------------------------

        self.info = BoneData(
            root_ik=root_ik,
            end_ik=end_ik,
            ik_handle=ik.handle,
            root_guide=root_guide if self.guides else "",
            end_guide=end_guide if self.guides else "",
            control=control,
            bind_joint=bind_joint,
            stretch_node=stretch_node,
            midpoint_driver=midpoint_driver,
        )

        return self.info