from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.spline.matrix_spline.build import matrix_spline_from_transforms
from Workshop.transform.utils import create_transform
from Workshop.maya_api.node import RemapValueNode
from .module_shared import create_mid_blend_driver_offset
from Workshop.guide.core import GuideInfo, create_guide_from_position, mirror_guide, read_guide
from Workshop.skin.split.tag import tag_for_weight_split

from .module_initialize import module_prep, module_space

import maya.cmds as cmds


@dataclass
class module_info:
    control:Control
    joint:str

class NL_Fold:
    def __init__(
        self,
        upper_driver,
        lower_driver,
        corner,
        part: str = "nl_fold",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel',
        control_space:list = [],
        control_color:str = 'MISC',
        control_shape:str = 'circle',
        divisions:int=5

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
        self.upper_driver = upper_driver
        self.lower_driver = lower_driver
        self.corner = corner

    # -------------------
    # Build steps
    # -------------------

    def align_guides(self, guide_01:GuideInfo, guide_02:GuideInfo, flip_y:bool=False):
        if guide_01.pos[2] > guide_02.pos[2]:
            mod = -1
        else:
            mod = 1
        ymod = -1 if flip_y else 1

        aim = cmds.aimConstraint(
                guide_02.name,
                guide_01.name,
                aimVector=(0, 1 * ymod, 0),      # Primary / aim axis = +X
                upVector=(0, 0, -1 * mod),       # Up axis = +Y
                worldUpType="vector",
                worldUpVector=(0, 1, 0),
                maintainOffset=False
            )

        cmds.delete(aim)

    def nl_fold_build(self)->module_info:

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

        driver_percent = .5


        for i in range(3):
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
                parent=self.control_grp,
                transform=g.name,
                size=self.control_size/100,
                control_shape='circle',
                direction="y",
                color_type=self.main_color,
                sdk_offset=True
            )
            controls.append(ctrl)

        module_space(control=controls[0], space_list=[self.upper_driver])
        module_space(control=controls[2], space_list=[self.lower_driver])
        module_space(control=controls[1], space_list=self.control_space)
        create_mid_blend_driver_offset(control=controls[1], driver_a=controls[0], driver_b=controls[2], parent_space=self.control_space[0],blend=.5 )
        
        control_max = cmds.getAttr(f'{self.corner.ctrl}.maxTransXLimit')
        corner_remap = RemapValueNode(name = f'{controls[2].name}_remap')
        corner_remap.input_value.connect_from(f'{self.corner.ctrl}.translateX')
        corner_remap.input_max.set(control_max)
        corner_remap.output_max.set(self.control_size/45)
        corner_remap.output.connect_to(f'{controls[2].ctrl}.translateX')
        corner_remap.output.connect_to(f'{controls[2].ctrl}.translateZ')

            
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
                pass
            else:
                self.align_guides(guide_01=g, guide_02=guides[i-1], flip_y=True)
            
            """ctrl = create_control(
                name=g.descriptor,
                parent=ctrl_par,
                transform=g.name,
                size=self.control_size/100,
                control_shape='circle',
                direction="y",
                color_type=self.main_color
            )"""

            pin = create_transform(name=f'{g.descriptor}_pin', transform=g.name, parent=self.guts)

            joint = create_joint(name=f'def_{g.descriptor}', transform=pin, connect=True, parent=joint_parent)
            joints.append(joint)

            constraint(drivers=[pin], driven=joint, constraint_type='parent', parent=self.guts)
            pins.append(pin)




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

        """#controls
        self.nl_fold_ctrl = create_control(
            name=f'{self.part}_{self.side}',
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.control_size,
            control_shape=self.control_shape,
            direction="y",
            color_type=self.control_color
        )

        module_space(control=self.nl_fold_ctrl, space_list=self.control_space)

        #joints

        self.nl_fold_joint = create_joint(name=f'def_{self.part}_{self.side}', transform=self.nl_fold_ctrl.ctrl, connect=True, parent=self.joint_parent)

        constraint(drivers=[self.nl_fold_ctrl.ctrl], driven=self.nl_fold_joint, constraint_type='parent', parent=self.guts)

        nl_fold_info = module_info(control =self.nl_fold_ctrl, joint=self.nl_fold_joint)
        return nl_fold_info"""