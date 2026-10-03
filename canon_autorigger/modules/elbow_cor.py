from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.utils import create_transform

from .module_initialize import module_prep, module_space

from .correctives.pull import Pull
from .correctives.blend import Blend



@dataclass
class module_info:
    control:Control
    joint:str

class Elbow_Cor:

    def __init__(
        self,
        driver:str ,
        part: str = "elbow_cor",
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

    # -------------------
    # Build steps
    # -------------------

    def build(self):

        #modeule prep work
        self.main_grp = create_transform(name=f'{self.part}_{self.side}_cor', parent=self.parent)

        mod = 1 #if self.side == 'R' else 1


        lowerbicep = Pull(part = 'lowerbicep', control_size=self.control_size, side=self.side, parent=self.main_grp, joint_parent=self.joint_parent, guides=[self.guides[1]], driver =  self.driver, range=(0,120 * mod), pull_amount=self.control_size/15,)
        lowerbicepinfo = lowerbicep.build()
        lowertricep = Pull(part = 'lowertricep', control_size=self.control_size, side=self.side, parent=self.main_grp, joint_parent=self.joint_parent, guides=[self.guides[2]], driver =  self.driver, range=(0,120 * mod), pull_amount=self.control_size/15)
        lowertricepinfo = lowertricep.build()
        elbowcorner = Blend(part = 'elbowcorner', side=self.side, parent=self.main_grp, joint_parent= self.joint_parent, guides=[self.guides[0]], driver = self.driver, driver_rot_range=(0, 80* mod), mult_range=(.5,.5), driver_axis='X', pop_amount=(self.control_size/15))
        elbowcornerinfo = elbowcorner.build()


        #joints

        #hip_info = module_info(control =self.hip_ctrl, joint=self.hip_joint)
        #return hip_info