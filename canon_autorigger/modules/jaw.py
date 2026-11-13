from dataclasses import dataclass

from Workshop.canon_autorigger.build_management.dev import create_dev_attribute
from Workshop.canon_autorigger.module_schema import ModuleGuide, ModuleRelationship, ModuleSetting
from Workshop.maya_api.attribute_utils import create_attribute, connect_attributes
from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.maya_api.node import RemapValueNode
from Workshop.transform.utils import create_transform

from .module_shared import create_driver_offset, module_prep, module_space

import maya.cmds as cmds
import math


@dataclass
class module_info:
    jaw:Control
    larynx:Control
    joint:list[str]

class Jaw:
    MODULE_NAME = "jaw"
    DISPLAY_NAME = "Jaw"
    GUIDES = (
        ModuleGuide(name="jaw"),
        ModuleGuide(name="jaw_end"),
        ModuleGuide(name="larynx"),
    )
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="jaw_control_size", setting_type="float", default=1 / 6),
        ModuleSetting(name="larynx_control_size", setting_type="float", default=1 / 40),
        ModuleSetting(name="jaw_control_shape", setting_type="control_shape", default="jaw"),
        ModuleSetting(name="larynx_control_shape", setting_type="control_shape", default="circle"),
        ModuleSetting(name="jaw_dimensions", setting_type="vector3", default=(1.0, 1.3, 1.3)),
        ModuleSetting(name="jaw_shape_offset", setting_type="vector3", default=(0.0, -1 / 60, 0.0)),
        ModuleSetting(name="larynx_shape_rotation", setting_type="vector3", default=(90.0, 0.0, 0.0)),
        ModuleSetting(name="jaw_rotation_offset", setting_type="float", default=-90.0),
        ModuleSetting(name="control_direction", setting_type="string", default="y"),
        ModuleSetting(name="larynx_follow_weight", setting_type="float", default=0.5),
        ModuleSetting(name="larynx_remap_range", setting_type="float", default=90.0),
        ModuleSetting(name="jaw_remap_range", setting_type="float", default=90.0),
        ModuleSetting(name="larynx_multiplier", setting_type="float", default=-1 / 6),
        ModuleSetting(name="jaw_multiplier", setting_type="float", default=1 / 80),
        ModuleSetting(name="mid_face_rotation_multiplier", setting_type="float", default=0.8),
        ModuleSetting(name="mid_face_translation_multiplier", setting_type="float", default=0.25),
        ModuleSetting(name="main_control_color", setting_type="string", default="Middle"),
        ModuleSetting(name="sub_control_color", setting_type="string", default="SubMiddle"),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
        ModuleRelationship(name="control_space", relationship_type="control_space", default="auto"),
        ModuleRelationship(name="larynx_follow_space", relationship_type="transform", default="auto"),
    )

    def __init__(
        self,
        part: str = "jaw",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel',
        control_space:list = [],
        larynx_follow_space: str | None = None,
        mid_face:Control|None = None,
        jaw_control_size: float = 1 / 6,
        larynx_control_size: float = 1 / 40,
        jaw_control_shape: str = "jaw",
        larynx_control_shape: str = "circle",
        jaw_dimensions: tuple[float, float, float] = (1.0, 1.3, 1.3),
        jaw_shape_offset: tuple[float, float, float] = (0.0, -1 / 60, 0.0),
        larynx_shape_rotation: tuple[float, float, float] = (90.0, 0.0, 0.0),
        jaw_rotation_offset: float = -90.0,
        control_direction: str = "y",
        larynx_follow_weight: float = 0.5,
        larynx_remap_range: float = 90.0,
        jaw_remap_range: float = 90.0,
        larynx_multiplier: float = -1 / 6,
        jaw_multiplier: float = 1 / 80,
        mid_face_rotation_multiplier: float = 0.8,
        mid_face_translation_multiplier: float = 0.25,
        main_control_color: str = "Middle",
        sub_control_color: str = "SubMiddle",

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.rig_size: float = rig_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.control_space = control_space if control_space is not None else []
        self.main_control_color = main_control_color
        self.sub_control_color = sub_control_color
        self.jaw_control_size = jaw_control_size
        self.larynx_control_size = larynx_control_size
        self.jaw_control_shape = jaw_control_shape
        self.larynx_control_shape = larynx_control_shape
        self.jaw_dimensions = jaw_dimensions
        self.jaw_shape_offset = jaw_shape_offset
        self.larynx_shape_rotation = larynx_shape_rotation
        self.jaw_rotation_offset = jaw_rotation_offset
        self.control_direction = control_direction
        self.larynx_follow_weight = larynx_follow_weight
        self.larynx_remap_range = larynx_remap_range
        self.jaw_remap_range = jaw_remap_range
        self.larynx_multiplier = larynx_multiplier
        self.jaw_multiplier = jaw_multiplier
        self.mid_face_rotation_multiplier = mid_face_rotation_multiplier
        self.mid_face_translation_multiplier = mid_face_translation_multiplier
        self.larynx_follow_space=larynx_follow_space
        self.mid_face = mid_face

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

        follow_attr = create_dev_attribute(
            attribute_name=f"{self.part}_{self.side}_larynx_follow_weight",
            control=self.larynx_ctrl.ctrl,
            rig_part=self.part,
            default=weight,
            attr_type="double",
        )
        connect_attributes(follow_attr, [f"{mult}.input2X", f"{mult}.input2Y", f"{mult}.input2Z"])
        connect_attributes(f"{delta}.output3D", [f"{mult}.input1"])
        connect_attributes(f"{mult}.output", [f"{larynx_offset}.translate"])

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

    def build(self)->module_info:

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
            size=self.rig_size * self.jaw_control_size,
            control_shape=self.jaw_control_shape,
            direction=self.control_direction,
            sdk_offset=True, 
            color_type=self.sub_control_color,
            shape_rotation_offset=(rot + self.jaw_rotation_offset,0,0),
            dimensions=self.jaw_dimensions,
            shape_position_offset=tuple(x * self.rig_size for x in self.jaw_shape_offset)
        )

        module_space(control=self.jaw_ctrl, space_list=self.control_space)

        #joints

        self.jaw_joint = create_joint(name=f'def_{self.guides[0].descriptor}', transform=self.jaw_ctrl.ctrl, connect=True, parent=self.joint_parent)
        self.jaw_ee_joint = create_joint(name=f'def_{self.guides[1].descriptor}', transform=self.guides[1].name, connect=False, parent=self.jaw_joint)

        self.larynx_ctrl = create_control(
            name=self.guides[2].descriptor,
            parent=self.control_grp,
            transform=self.guides[2].name,
            size=self.rig_size * self.larynx_control_size,
            control_shape=self.larynx_control_shape,
            direction=self.control_direction,
            sdk_offset=True, 
            shape_rotation_offset=self.larynx_shape_rotation,
            color_type=self.main_control_color
        )

        # Extra offset for soft jaw follow
        self.larynx_jaw_offset = create_transform(name=f"{self.larynx_ctrl.name}_jaw_offset", parent=self.larynx_ctrl.top, transform=self.larynx_ctrl.top)
        cmds.parent(self.larynx_ctrl.sdk, self.larynx_jaw_offset)

        self.connect_larynx_jaw_follow(
            jaw_ee=self.jaw_ee_joint,
            larynx_offset=self.larynx_jaw_offset ,
            space=self.larynx_follow_space,
            weight=self.larynx_follow_weight,
        )

        larynx_remap = RemapValueNode(name='larynx_remap')
        larynx_remap.input_value.connect_from(f'{self.jaw_ctrl.ctrl}.rotateX')
        larynx_range = create_dev_attribute(
            attribute_name=f"{self.part}_{self.side}_larynx_remap_range",
            control=self.jaw_ctrl.ctrl, rig_part=self.part,
            default=self.larynx_remap_range, attr_type="double",
        )
        larynx_remap.input_max.connect_from(larynx_range)

        create_attribute(
            primary_object=self.jaw_ctrl.ctrl, attr_name="larynx_mult",
            default=self.rig_size * self.larynx_multiplier, attr_type="double",
            proxy_objects=[self.larynx_ctrl.ctrl],
        )

        larynx_remap.output_max.connect_from(f'{self.jaw_ctrl.ctrl}.larynx_mult')
        larynx_remap.output.connect_to(f'{self.larynx_ctrl.sdk}.translateY')

        jaw_remap = RemapValueNode(name='jaw_remap')
        jaw_remap.input_value.connect_from(f'{self.jaw_ctrl.ctrl}.rotateX')
        jaw_range = create_dev_attribute(
            attribute_name=f"{self.part}_{self.side}_jaw_remap_range",
            control=self.jaw_ctrl.ctrl, rig_part=self.part,
            default=self.jaw_remap_range, attr_type="double",
        )
        jaw_remap.input_max.connect_from(jaw_range)

        create_attribute(
            primary_object=self.jaw_ctrl.ctrl, attr_name="jaw_mult",
            default=self.rig_size * self.jaw_multiplier, attr_type="double",
        )

        jaw_remap.output_max.connect_from(f'{self.jaw_ctrl.ctrl}.jaw_mult')
        jaw_remap.output.connect_to(f'{self.jaw_ctrl.sdk}.translateZ')


        module_space(control=self.larynx_ctrl, space_list=[self.larynx_follow_space])
        #constraint(drivers=[self.control_space[0], ], driven=self.larynx_ctrl.top, constraint_type='parent', parent=self.guts)

        #joints

        self.larynx_joint = create_joint(name=f'def_{self.guides[2].descriptor}', transform=self.larynx_ctrl.ctrl, connect=True, parent=self.jaw_joint)

        #constraint(drivers=[self.larynx_ctrl.ctrl, self.jaw_ctrl.ctrl], driven=self.larynx_joint, constraint_type='parent', parent=self.guts)
        
        if self.mid_face:
            create_driver_offset(control=self.mid_face, driver=self.jaw_ctrl, x_range=(-90,0), rot_mult=self.mid_face_rotation_multiplier, trans_mult=self.mid_face_translation_multiplier, y_range=(0,0), z_range=(-5,5))

        jaw_info = module_info(jaw =self.jaw_ctrl, joint=[self.jaw_joint, self.jaw_ee_joint, self.larynx_joint], larynx=self.larynx_ctrl)
        return jaw_info