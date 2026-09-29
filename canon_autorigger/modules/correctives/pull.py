from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.core import read_guide
from Workshop.maya_api.node import RemapValueNode

from ..module_initialize import module_prep, module_space

from Workshop.canon_autorigger.module_schema import (
    ModuleSetting,
    ModuleRelationship,
    ModuleGuide,
)


@dataclass
class module_info:
    control:Control
    joint:str

class Pull:

    def __init__(
        self,
        driver:str ,
        part: str = "pull",
        side: str = "M",
        parent: str = "rig",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel',
        range:tuple = (-90,90),
        driver_axis:str = 'X',
        pull_axis:str = 'Y',
        pull_amount:float = 1 

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.pull_axis = pull_axis
        self.driver_axis = driver_axis
        self.range = range
        self.pull_amount = pull_amount
        self.driver=driver

    # -------------------
    # Build steps
    # -------------------

    def build(self):

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        #joints

        #root_joint = create_joint(name=f'def_{self.guides[0].descriptor}', transform=self.guides[0].name, connect=True, parent=self.joint_parent)
        root_switch_joint = create_joint(name=f'switch_root_{self.guides[0].descriptor}', transform=self.guides[0].name, connect=False, parent=self.guts, bind_set=False, ue_set=False)
        switch_joint = create_joint(name=f'switch_{self.guides[0].descriptor}', transform=self.guides[0].name, connect=False, parent=root_switch_joint, bind_set=False, ue_set=False )

        #self.pull_joint = create_joint(name=f'def_{self.guides[0].descriptor}', transform=self.pull_ctrl.ctrl, connect=True, parent=self.joint_parent)

        constraint(drivers=[self.joint_parent], driven=root_switch_joint, parent=self.guts)
        pull_remap = RemapValueNode(name=f'{self.guides[0].descriptor}_remap')
        pull_remap.input_max.set(self.range[1])
        pull_remap.input_min.set(self.range[0])
        pull_remap.output_max.set(self.pull_amount)
        pull_remap.input_value.connect_from(f'{self.driver}.rotate{self.driver_axis}')
        pull_remap.output.connect_to(f'{switch_joint}.translate{self.pull_axis}')

        self.pull_joint = create_joint(name=f'def_{self.guides[0].descriptor}', transform=switch_joint, connect=True, parent=self.joint_parent)


        #pull_info = module_info(control =self.pull_ctrl, joint=self.pull_joint)
        #return pull_info