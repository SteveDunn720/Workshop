from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.core import create_guide_from_position, create_midpoint_guide, mirror_guide
from Workshop.nurbs.curve import are_curves_mirrored
from Workshop.skin.split.tag import tag_for_weight_split

from .module_initialize import module_prep, module_space
import maya.cmds as cmds


@dataclass
class module_info:
    control:Control
    joint:str

class Arch:
    def __init__(
        self,
        driver, 
        divisions:int=2,
        part: str = "arch",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel',
        control_space:list = [],

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
    
        self.main_L_color = 'Left'
        self.sub_L_color = 'SubLeft'
    
        self.main_R_color = 'Right'
        self.sub_R_color = 'SubRight'
        self.driver = driver
        self.divisions = divisions

    # -------------------
    # Build steps
    # -------------------

    def arch_build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        guides = []
        controls = []
        joints = []

        #are_curves_mirrored(self.guides[0].name, self.guides[1].name)

        center_pos = cmds.pointOnCurve(
            self.guides[0].name,
            parameter=0,
            position=True,
            turnOnPercentage=True,
        )

        center_guide = create_guide_from_position(guide_name=f'{self.part}_00_M', pos=center_pos, parent='guides')

        guides.append(center_guide)

        percent = 1/(self.divisions)

        for i in range(self.divisions):
            pos = cmds.pointOnCurve(
                self.guides[0].name,
                parameter=percent * (i + 1),
                position=True,
                turnOnPercentage=True,
            )
            guide = create_guide_from_position(guide_name=f'{self.part}_0{i + 1}_L', pos=pos, parent='guides')
            guides.append(guide)
            mirroed = mirror_guide(guide=guide)
            guides.append(mirroed)

        main_guide = create_midpoint_guide(guide_a=guides[-1], guide_b=guides[-2], position_only=True, name=f'{self.part}_main_M', parent='guides')
        self.main_ctrl = create_control(
            name=main_guide.descriptor,
            parent=self.control_grp,
            transform=main_guide.name,
            size=self.control_size/140,
            control_shape='round_square',
            direction="y",
            color_type=self.main_M_color,
            shape_rotation_offset=(90,0,0),
            shape_position_offset=(self.control_size/6, 0,0)
        )

        module_space(control=self.main_ctrl, space_list=self.control_space)

        #joints

        self.main_joint = create_joint(name=f'def_{main_guide.descriptor}', transform=self.main_ctrl.ctrl, connect=True, parent=self.joint_parent)


        for g in guides:
            side = next(
                (
                    side
                    for side in ("L", "R", "M")
                    if f"_{side}" in g.name
                ),
                None
            )
            if side == "L":
                color = self.sub_L_color
            elif side == "R":
                color = self.sub_R_color
            else:
                color = self.sub_M_color
            ctrl = create_control(
                name=g.descriptor,
                parent=self.main_ctrl.ctrl,
                transform=g.name,
                size=self.control_size/100,
                control_shape='sphere',
                direction="y",
                color_type=color
            )

            #joints

            joint = create_joint(name=f'def_{g.descriptor}', transform=ctrl.ctrl, connect=True, parent=self.main_joint)

            constraint(drivers=[ctrl.ctrl], driven=joint, constraint_type='parent', parent=self.guts)
            controls.append(ctrl)
            joints.append(joint)


        sorted_joints = sorted(
            joints,
            key=lambda transform: cmds.xform(
                transform,
                query=True,
                worldSpace=True,
                translation=True,
            )[0] #type:ignore
        )

        tag_for_weight_split(
            influence= joints[0],  # <-- your SOURCE joint (must already exist)
            split_influences=sorted_joints,  # <-- the ones you just created
        )

        arch_info = module_info(control =self.main_ctrl, joint=self.main_joint)
        return arch_info


                

        #are_curves_mirrored(self.guides[0].name, self.guides[1].name)

        """#controls
        self.arch_ctrl = create_control(
            name=f'{self.part}_{self.side}',
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.control_size,
            control_shape=self.control_shape,
            direction="y",
            color_type=self.control_color
        )

        module_space(control=self.arch_ctrl, space_list=self.control_space)

        #joints

        self.arch_joint = create_joint(name=f'def_{self.part}_{self.side}', transform=self.arch_ctrl.ctrl, connect=True, parent=self.joint_parent)

        constraint(drivers=[self.arch_ctrl.ctrl], driven=self.arch_joint, constraint_type='parent', parent=self.guts)

        arch_info = module_info(control =self.arch_ctrl, joint=self.arch_joint)
        return arch_info"""