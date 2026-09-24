from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.core import GuideInfo, create_guide_from_position
from Workshop.skin.split.tag import tag_for_weight_split

from .module_initialize import module_prep, module_space

import maya.cmds as cmds


@dataclass
class module_info:
    control:Control
    joint:str

class Tongue:
    def __init__(
        self,
        part: str = "tongue",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel',
        control_space:list = [],
        control_shape:str = 'circle',
        divisions:int= 7,

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.control_space = control_space
        self.main_M_color = 'Middle'
        self.sub_M_color = 'SubMiddle'
        self.control_shape = control_shape
        self.divisions = divisions

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

    def tongue_build(self):

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        guides = []
        controls = []
        joints = []
        joint_parent = self.joint_parent
        ctrl_par= self.control_grp

        percent = 1/(self.divisions)

        for i in range(self.divisions + 1):
            pos = cmds.pointOnCurve(
                self.guides[0].name,
                parameter=percent * (i),
                position=True,
                turnOnPercentage=True,
            )
            g = create_guide_from_position(guide_name=f'{self.part}_0{i}_{self.side}', pos=pos, parent='guides')
            guides.append(g)

            if i == 0:
                pass
            else:
                self.align_guides(guide_01=g, guide_02=guides[i-1])
            
            ctrl = create_control(
                name=g.descriptor,
                parent=ctrl_par,
                transform=g.name,
                size=self.control_size/100,
                control_shape='circle',
                direction="y",
                color_type=self.main_M_color
            )

            #joints
            if i == 0:
                module_space(control=ctrl, space_list=self.control_space)

            joint = create_joint(name=f'def_{g.descriptor}', transform=ctrl.ctrl, connect=True, parent=joint_parent)

            constraint(drivers=[ctrl.ctrl], driven=joint, constraint_type='parent', parent=self.guts)
            controls.append(ctrl)
            joints.append(joint)
            joint_parent = joint
            ctrl_par= ctrl.ctrl

        tag_for_weight_split(
            influence= joints[0],  # <-- your SOURCE joint (must already exist)
            split_influences=joints,  # <-- the ones you just created
        )






        """#controls
        self.tongue_ctrl = create_control(
            name=f'{self.part}_{self.side}',
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.control_size,
            control_shape=self.control_shape,
            direction="y",
            color_type=self.control_color
        )

        module_space(control=self.tongue_ctrl, space_list=self.control_space)

        #joints

        self.tongue_joint = create_joint(name=f'def_{self.part}_{self.side}', transform=self.tongue_ctrl.ctrl, connect=True, parent=self.joint_parent)

        constraint(drivers=[self.tongue_ctrl.ctrl], driven=self.tongue_joint, constraint_type='parent', parent=self.guts)

        tongue_info = module_info(control =self.tongue_ctrl, joint=self.tongue_joint)
        return tongue_info"""