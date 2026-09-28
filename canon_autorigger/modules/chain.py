from attr import dataclass

import maya.cmds as cmds

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.canon_autorigger.module_schema import ModuleGuideArray, ModuleRelationship, ModuleSetting
from Workshop.guide.core import read_guide

from .module_initialize import module_prep, module_space


@dataclass
class module_info:
    control:list[Control]
    joint:list[str]

class Chain:

    MODULE_NAME = "chain"
    DISPLAY_NAME = "Chain"

    GUIDES = (
        ModuleGuideArray(
            name="chain",
            default_count=3,
            minimum_count=1,
            spacing=(0.0, 5.0, 0.0),
            parented=True,
        ),
    )

    SETTINGS = (
        ModuleSetting(
            name="control_size",
            setting_type="float",
            default=1.0,
        ),
        ModuleSetting(
            name="main_control_shape",
            setting_type="control_shape",
            default="circle",
        ),
        ModuleSetting(
            name="main_control_color",
            setting_type="string",
            default=None,
        ),
        ModuleSetting(
            name="roll_control_shape",
            setting_type="control_shape",
            default="sphere",
        ),
        ModuleSetting(
            name="roll_control_color",
            setting_type="color",
            default=None,
        ),
        ModuleSetting(
            name="roll",
            setting_type="bool",
            default=True,
        ),
        ModuleSetting(
            name="driver_name",
            setting_type="string",
            default='curl',
        ),
    )

    RELATIONSHIPS = (
        ModuleRelationship(
            name="joint_parent",
            relationship_type="joint",
            default="auto",
        ),
        ModuleRelationship(
            name="control_space",
            relationship_type="control_space",
            default="auto",
        ),
    )


    def __init__(
        self,
        part: str = "chain",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel',
        control_space:list = [],
        main_control_shape: str = "circle",
        main_control_color: str | None = None,
        roll_control_shape: str = "sphere",
        roll_control_color: str | None = None,
        roll: bool = True,
        driver_name:str = 'curl'

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.control_space = control_space
        self.roll = roll
        self.main_control_shape = main_control_shape
        self.roll_control_shape = roll_control_shape
        self.main_control_color = (
            main_control_color
            if main_control_color is not None
            else "Left" if self.side == "L"
            else "Right" if self.side == "R"
            else "Middle" if self.side == "M"
            else "MISC"
        )
        self.roll_control_color = (
            roll_control_color
            if roll_control_color is not None
            else "SubLeft" if self.side == "L"
            else "SubRight" if self.side == "R"
            else "SubMiddle" if self.side == "M"
            else "MISC"
        )
        self.driver_name = driver_name

    @classmethod
    def preview(
        cls,
        part: str,
        side: str,
        guides: list[str],
        settings: dict,
    ) -> dict:

        controls = []
        joints = []

        roll = settings.get(
            "roll",
            True,
        )

        if roll:
            controls.append(
                f"{part}_curl_{side}_ctrl"
            )

        chain_controls = []

        for guide_name in guides:

            guide = read_guide(
                guide_name
            )

            control = (
                f"{guide.descriptor}_ctrl"
            )

            joint = (
                f"def_{guide.descriptor}_jnt"
            )

            chain_controls.append(
                control
            )

            controls.append(
                control
            )

            joints.append(
                joint
            )

        if not chain_controls:
            return {
                "controls": controls,
                "joints": [],
                "output_control": None,
                "output_joint": None,
            }

        return {
            "controls": controls,
            "joints": joints,

            # The curl control isn't the output.
            "output_control": chain_controls[-1],
            "output_joint": joints[-1],
        }

    # -------------------
    # Build steps
    # -------------------

    def chain_build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=False)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts
        self.chain_ctrls = []
        self.chain_joints = []

        if self.roll:

            self.roll_ctrl = create_control(
                            name=f'{self.part}_{self.driver_name}_{self.side}',
                            parent=self.control_grp,
                            transform=self.guides[0].name,
                            size=self.control_size/64,
                            control_shape=self.roll_control_shape,
                            direction="y",
                            color_type=self.roll_control_color,
                            shape_position_offset=(-(self.control_size/16), 0, 0)
                        )
            module_space(control=self.roll_ctrl, space_list=[self.control_space])

        jnt_par = self.joint_parent
        ctrl_par = self.control_grp

        for i, guide in enumerate(self.guides):

            #controls
            ctrl = create_control(
                name=guide.descriptor,
                parent=ctrl_par,
                transform=guide.name,
                size=self.control_size/32,
                control_shape=self.main_control_shape,
                direction="y",
                color_type=self.main_control_color,
                sdk_offset=self.roll
            )
            self.chain_ctrls.append(ctrl)
            if self.roll:
                cmds.connectAttr(f'{self.roll_ctrl.ctrl}.rotateZ', f'{ctrl.sdk}.rotateZ')
                if i == 0:
                    cmds.connectAttr(f'{self.roll_ctrl.ctrl}.rotateX', f'{ctrl.sdk}.rotateX')
                    cmds.connectAttr(f'{self.roll_ctrl.ctrl}.rotateY', f'{ctrl.sdk}.rotateY')
            #joints
            joint = create_joint(name=f'def_{guide.descriptor}', transform=ctrl.ctrl, connect=True, parent=jnt_par)
            self.chain_joints.append(joint)
            constraint(drivers=[ctrl.ctrl], driven=joint, constraint_type='parent', parent=self.guts)
            jnt_par = joint
            ctrl_par = ctrl.ctrl

        module_space(control=self.chain_ctrls[0], space_list=[self.control_space])

        chain_info = module_info(control=self.chain_ctrls, joint=self.chain_joints)
        return chain_info
    