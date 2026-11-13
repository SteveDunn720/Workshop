from dataclasses import dataclass

from Workshop.canon_autorigger.module_schema import ModuleCurveGuide, ModuleRelationship, ModuleSetting

from Workshop.control.core import Control, align_control_shape_world_z
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.spline.matrix_spline.build import matrix_spline_from_transforms
from Workshop.transform.utils import create_transform
from .module_shared import create_mid_blend_driver_offset, module_prep, module_space
from Workshop.guide.core import GuideInfo, create_guide_from_position, mirror_guide, read_guide, align_guides
from Workshop.skin.split.tag import tag_for_weight_split

import maya.cmds as cmds


@dataclass
class module_info:
    control:Control
    joint:str

class Brow:
    MODULE_NAME = "brow"
    DISPLAY_NAME = "Brow"
    GUIDES = (ModuleCurveGuide(name="brow"),)
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="divisions", setting_type="int", default=7),
        ModuleSetting(name="master_size", setting_type="float", default=1 / 80),
        ModuleSetting(name="macro_size", setting_type="float", default=1 / 120),
        ModuleSetting(name="driver_size", setting_type="float", default=1 / 120),
        ModuleSetting(name="sub_size", setting_type="float", default=1 / 180),
        ModuleSetting(name="master_shape", setting_type="control_shape", default="round_square"),
        ModuleSetting(name="macro_shape", setting_type="control_shape", default="round_square"),
        ModuleSetting(name="driver_shape", setting_type="control_shape", default="round_square"),
        ModuleSetting(name="control_shape", setting_type="control_shape", default="circle"),
        ModuleSetting(name="control_direction", setting_type="string", default="y"),
        ModuleSetting(name="master_rotation", setting_type="vector3", default=(90.0, 0.0, 0.0)),
        ModuleSetting(name="master_offset", setting_type="vector3", default=(-1 / 40, 1 / 50, 1 / 30)),
        ModuleSetting(name="macro_offset", setting_type="vector3", default=(-1 / 40, 1 / 50, 0.0)),
        ModuleSetting(name="driver_offset", setting_type="vector3", default=(0.0, 0.0, 1 / 60)),
        ModuleSetting(name="master_width_mult", setting_type="float", default=0.5),
        ModuleSetting(name="guide_parent", setting_type="string", default="guides"),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
        ModuleRelationship(name="control_space", relationship_type="control_space", default="auto"),
    )

    def __init__(
        self,
        part: str = "brow",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list | None = None,
        joint_parent:str = 'skel',
        control_space:list | None = None,
        control_color:str = 'MISC',
        control_shape:str = 'circle',
        divisions:int=7,
        master_size: float = 1 / 80,
        macro_size: float = 1 / 120,
        driver_size: float = 1 / 120,
        sub_size: float = 1 / 180,
        master_shape: str = "round_square",
        macro_shape: str = "round_square",
        driver_shape: str = "round_square",
        control_direction: str = "y",
        master_rotation: tuple[float, float, float] = (90, 0, 0),
        master_offset: tuple[float, float, float] = (-1 / 40, 1 / 50, 1 / 30),
        macro_offset: tuple[float, float, float] = (-1 / 40, 1 / 50, 0),
        driver_offset: tuple[float, float, float] = (0, 0, 1 / 60),
        master_width_mult: float = 0.5,
        guide_parent: str = "guides",

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.rig_size: float = rig_size
        self.guides: list = guides if guides is not None else []
        self.joint_parent = joint_parent
        self.control_space = control_space if control_space is not None else []
        self.control_color = control_color
        self.control_shape = control_shape
        self.divisions = divisions
        self.master_size = master_size
        self.macro_size = macro_size
        self.driver_size = driver_size
        self.sub_size = sub_size
        self.master_shape = master_shape
        self.macro_shape = macro_shape
        self.driver_shape = driver_shape
        self.control_direction = control_direction
        self.master_rotation = master_rotation
        self.master_offset = master_offset
        self.macro_offset = macro_offset
        self.driver_offset = driver_offset
        self.master_width_mult = master_width_mult
        self.guide_parent = guide_parent
        if self.side == 'L':
            self.main_color = 'Left'
            self.sub_color = 'SubLeft'
        else:
            self.main_color = 'Right'
            self.sub_color = 'SubRight'

    # -------------------
    # Build steps
    # -------------------

    def build(self)->module_info:

        if self.divisions < 1:
            raise ValueError("Brow divisions must be at least 1")

        #module prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        guides = []
        joints = []
        controls = []
        joint_parent = self.joint_parent
        percent = 1/(self.divisions)
        pins = []

        arc_length = cmds.arclen(self.guides[0].name)

        pos = cmds.pointOnCurve(
            self.guides[0].name,
            parameter=.5,
            position=True,
            turnOnPercentage=True,
        )
        if self.side == 'R':
            g = mirror_guide(guide=read_guide(f'{self.part}_master_L_guide'))
        else:
            g = create_guide_from_position(guide_name=f'{self.part}_master_{self.side}', pos=pos, parent=self.guide_parent)

        master_ctrl = create_control(
            name=g.descriptor,
            parent=self.control_grp,
            transform=g.name,
            size=self.rig_size * self.master_size,
            control_shape=self.master_shape,
            direction=self.control_direction,
            color_type=self.main_color,
            sdk_offset=False,
            dimensions=(arc_length * self.master_width_mult, 1, 1),
            shape_rotation_offset=self.master_rotation,
            shape_position_offset=tuple(v * self.rig_size for v in self.master_offset)
        )

        pos_offset = (self.rig_size/30) + pos[2] #type:ignore

        module_space(control=master_ctrl, space_list=self.control_space)

        macro_controls = []

        for i in range(2):
            mac = 'inner' if i == 0 else 'outer'
            pos = cmds.pointOnCurve(
                self.guides[0].name,
                parameter=.3333 if i ==0 else .666,
                position=True,
                turnOnPercentage=True,
            )
            if self.side == 'R':
                g = mirror_guide(guide=read_guide(f'{self.part}_{mac}_L_guide'))
            else:
                g = create_guide_from_position(guide_name=f'{self.part}_{mac}_{self.side}', pos=pos, parent=self.guide_parent)
    
            ctrl = create_control(
                name=g.descriptor,
                parent=master_ctrl.ctrl,
                transform=g.name,
                size=self.rig_size * self.macro_size,
                control_shape=self.macro_shape,
                direction=self.control_direction,
                color_type=self.main_color,
                sdk_offset=False,
                shape_rotation_offset=self.master_rotation,
                shape_position_offset=tuple(v * self.rig_size for v in self.macro_offset)
            )
            macro_controls.append(ctrl)

        align_control_shape_world_z(
            [
                macro_controls[0],
                macro_controls[1],
            ],
            target_z=pos_offset
            
        )

        driver_percent = .3333


        for i in range(4):
            par = macro_controls[0] if i in [0,1] else macro_controls[1]
            pos = cmds.pointOnCurve(
                self.guides[0].name,
                parameter=driver_percent * (i),
                position=True,
                turnOnPercentage=True,
            )
            if self.side == 'R':
                g = mirror_guide(guide=read_guide(f'{self.part}_0{i}_driver_L_guide'))
            else:
                g = create_guide_from_position(guide_name=f'{self.part}_0{i}_driver_{self.side}', pos=pos, parent=self.guide_parent)

            ctrl = create_control(
                name=g.descriptor,
                parent=par.ctrl,
                transform=g.name,
                size=self.rig_size * self.driver_size,
                control_shape=self.driver_shape,
                direction=self.control_direction,
                color_type=self.sub_color,
                sdk_offset=False,
                shape_rotation_offset=self.master_rotation,
                shape_position_offset=tuple(v * self.rig_size for v in self.driver_offset)
                
            )
            controls.append(ctrl)


        sub_grp = create_transform(name=f'{self.part}_sub_{self.side}_grp', parent=self.control_grp)

        
        for i in range(self.divisions + 1):
            pos = cmds.pointOnCurve(
                self.guides[0].name,
                parameter=percent * (i),
                position=True,
                turnOnPercentage=True,
            )

            if self.side == 'R':
                g = mirror_guide(guide=read_guide(f'{self.part}_0{i}_L_guide'))
            else:
                g = create_guide_from_position(guide_name=f'{self.part}_0{i}_{self.side}', pos=pos, parent=self.guide_parent)
            guides.append(g)

            if i == 0:
                # First guide exists, but we don't have another guide to aim at yet.
                pass

            elif i == 1:
                # Aim the first guide toward the second.
                align_guides(
                    guide_01=guides[0],
                    guide_02=guides[1],
                )

                # Aim the second guide back toward the first,
                # flipping the orientation.
                align_guides(
                    guide_01=guides[1],
                    guide_02=guides[0],
                    flip=True,
                )

            else:
                # Every remaining guide aims using the previous guide.
                align_guides(
                    guide_01=guides[i],
                    guide_02=guides[i - 1],
                )
            
            ctrl = create_control(
                name=g.descriptor,
                parent=sub_grp,
                transform=g.name,
                size=self.rig_size * self.sub_size,
                control_shape=self.control_shape,
                direction=self.control_direction,
                color_type=self.main_color
            )

            joint = create_joint(name=f'def_{g.descriptor}', transform=ctrl.ctrl, connect=True, parent=joint_parent)
            joints.append(joint)
            pins.append(ctrl.top)

        tag_for_weight_split(
            influence= joints[0],  # <-- your SOURCE joint (must already exist)
            split_influences=joints,  # <-- the ones you just created
        )

        matrix_spline = matrix_spline_from_transforms(
            name=f"{self.part}_{self.side}_ms",
            pinned_transforms=pins,
            cv_transforms=controls,
            parent=self.guts,
            degree=2,
        )
