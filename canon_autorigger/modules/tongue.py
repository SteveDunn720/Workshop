from dataclasses import dataclass

from Workshop.canon_autorigger.module_schema import ModuleCurveGuide, ModuleRelationship, ModuleSetting

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.core import GuideInfo, create_guide_from_position
from Workshop.skin.split.tag import tag_for_weight_split

from .module_shared import module_prep, module_space

import maya.cmds as cmds


@dataclass
class module_info:
    control:Control
    joint:str

class Tongue:
    MODULE_NAME = "tongue"
    DISPLAY_NAME = "Tongue"
    GUIDES = (ModuleCurveGuide(name="tongue"),)
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="divisions", setting_type="int", default=7),
        ModuleSetting(name="control_shape", setting_type="control_shape", default="circle"),
        ModuleSetting(name="control_size", setting_type="float", default=0.01),
        ModuleSetting(name="control_direction", setting_type="string", default="y"),
        ModuleSetting(name="control_color", setting_type="string", default="Middle"),
        ModuleSetting(name="guide_parent", setting_type="string", default="guides"),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
        ModuleRelationship(name="control_space", relationship_type="control_space", default="auto"),
    )

    def __init__(
        self,
        part: str = "tongue",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list | None = None,
        joint_parent:str = 'skel',
        control_space:list | None = None,
        control_shape:str = 'circle',
        divisions:int= 7,
        control_size: float = 0.01,
        control_direction: str = "y",
        control_color: str = "Middle",
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
        self.main_M_color = control_color
        self.sub_M_color = 'SubMiddle'
        self.control_shape = control_shape
        self.divisions = divisions
        self.control_size = control_size
        self.control_direction = control_direction
        self.guide_parent = guide_parent

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

    def build(self):

        if self.divisions < 1:
            raise ValueError("Tongue divisions must be at least 1")

        #module prep work
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
            g = create_guide_from_position(guide_name=f'{self.part}_0{i}_{self.side}', pos=pos, parent=self.guide_parent)
            guides.append(g)

            if i == 0:
                pass
            else:
                self.align_guides(guide_01=g, guide_02=guides[i-1])
            
            ctrl = create_control(
                name=g.descriptor,
                parent=ctrl_par,
                transform=g.name,
                size=self.rig_size * self.control_size,
                control_shape=self.control_shape,
                direction=self.control_direction,
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
