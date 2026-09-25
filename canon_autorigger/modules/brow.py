from attr import dataclass

from Workshop.control.core import Control, align_control_shape_world_z
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.spline.matrix_spline.build import matrix_spline_from_transforms
from Workshop.transform.utils import create_transform
from .module_shared import create_mid_blend_driver_offset
from Workshop.guide.core import GuideInfo, create_guide_from_position, mirror_guide, read_guide, align_guides
from Workshop.skin.split.tag import tag_for_weight_split

from .module_initialize import module_prep, module_space

import maya.cmds as cmds


@dataclass
class module_info:
    control:Control
    joint:str

class Brow:
    def __init__(
        self,
        part: str = "brow",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel',
        control_space:list = [],
        control_color:str = 'MISC',
        control_shape:str = 'circle',
        divisions:int=7

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.control_space = control_space
        self.control_color = control_color
        self.control_shape = control_shape
        self.divisions = divisions
        if self.side == 'L':
            self.main_color = 'Left'
            self.sub_color = 'SubLeft'
        else:
            self.main_color = 'Right'
            self.sub_color = 'SubRight'

    # -------------------
    # Build steps
    # -------------------

    def brow_build(self)->module_info:

        #modeule prep work
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
            g = create_guide_from_position(guide_name=f'{self.part}_master_{self.side}', pos=pos, parent='guides')

        master_ctrl = create_control(
            name=g.descriptor,
            parent=self.control_grp,
            transform=g.name,
            size=self.control_size/80,
            control_shape='round_square',
            direction="y",
            color_type=self.main_color,
            sdk_offset=False,
            dimensions=(arc_length/2, 1, 1),
            shape_rotation_offset=(90,0,0),
            shape_position_offset=(-self.control_size/40,self.control_size/50, self.control_size/30)
        )

        pos_offset = (self.control_size/30) + pos[2] #type:ignore

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
                g = create_guide_from_position(guide_name=f'{self.part}_{mac}_{self.side}', pos=pos, parent='guides')
    
            ctrl = create_control(
                name=g.descriptor,
                parent=master_ctrl.ctrl,
                transform=g.name,
                size=self.control_size/120,
                control_shape='round_square',
                direction="y",
                color_type=self.main_color,
                sdk_offset=False,
                shape_rotation_offset=(90,0,0),
                shape_position_offset=(-self.control_size/40,self.control_size/50,0)
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
                g = create_guide_from_position(guide_name=f'{self.part}_0{i}_driver_{self.side}', pos=pos, parent='guides')

            ctrl = create_control(
                name=g.descriptor,
                parent=par.ctrl,
                transform=g.name,
                size=self.control_size/120,
                control_shape='round_square',
                direction="y",
                color_type=self.sub_color,
                sdk_offset=False,
                shape_rotation_offset=(90,0,0),
                shape_position_offset=(0,0,self.control_size/60)
                
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
                g = create_guide_from_position(guide_name=f'{self.part}_0{i}_{self.side}', pos=pos, parent='guides')
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
                size=self.control_size/180,
                control_shape='circle',
                direction="y",
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
