from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.utils import create_transform

from .module_initialize import module_prep, module_space

from .correctives.ik_correctives import Ik_correctives



@dataclass
class module_info:
    control:Control
    joint:str

class Chest_Cor:

    def __init__(
        self,
        driver:str ,
        parent_space:str ,
        part: str = "chest_cor",
        side: str = "M",
        parent: str = "rig",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel',


    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.driver = driver
        self.parent_space = parent_space

    # -------------------
    # Build steps
    # -------------------

    def build(self):

        #modeule prep work
        self.main_grp = create_transform(name=f'{self.part}_{self.side}_cor', parent=self.parent)

        mod = 1 #if self.side == 'R' else 1 ///// spineinfo.bind_joints[-1] /// arm_info.switch_joints[0] //// spineinfo.chest_off.ctrl ///pec_correctives, trap_correctives, necktrap_correctives

        pec = Ik_correctives(part="pec", control_size=self.control_size, joint_parent=self.joint_parent, parent=self.main_grp, side=self.side, guides=self.guides[0], end_ik_space=[self.driver], root_ik_space=[self.parent_space], divisions=1) #type:ignore
        pec.build()
        trap = Ik_correctives(part="trap", control_size=self.control_size, joint_parent=self.joint_parent, parent=self.main_grp, side=self.side, guides=self.guides[1], end_ik_space=[self.driver], root_ik_space=[self.parent_space], divisions=1) #type:ignore
        trap.build()
        necktrap = Ik_correctives(part="necktrap", control_size=self.control_size, joint_parent=self.joint_parent, parent=self.main_grp, side=self.side, guides=self.guides[2], end_ik_space=[self.driver], root_ik_space=[self.parent_space], divisions=1) #type:ignore
        necktrap.build()




        #joints

        #hip_info = module_info(control =self.hip_ctrl, joint=self.hip_joint)
        #return hip_info











