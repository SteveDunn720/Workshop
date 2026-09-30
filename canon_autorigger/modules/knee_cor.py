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

class Knee_Cor:

    def __init__(
        self,
        driver:str ,
        part: str = "knee_cor",
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


        hamstring = Pull(part = 'hamstring', control_size=self.control_size, side=self.side, parent=self.main_grp, joint_parent=self.joint_parent, guides=[self.guides[1]], driver =  self.driver, range=(0,-120 * mod), pull_amount=self.control_size/3)
        hamstringinfo = hamstring.build()
        kneecap = Blend(part = 'kneecap', side=self.side, parent=self.main_grp, joint_parent= self.joint_parent, guides=[self.guides[0]], driver = self.driver, driver_rot_range=(0, -80* mod), mult_range=(.5,.8), driver_axis='X', pop_amount=(self.control_size/7))
        kneecapinfo = kneecap.build()
        calf = Pull(part = 'calf', side=self.side, parent=self.main_grp, joint_parent= self.driver, guides=[self.guides[2]], driver = self.driver, range=(0,-120 * mod), pull_amount=self.control_size/10)
        calfinfo = calf.build()
        """glutesup = Pull(part = 'glutesup', side=self.side, parent=self.main_grp, joint_parent= self.joint_parent, guides=[self.guides[4]], driver = self.driver, range=(0,-90 * mod), pull_amount=self.control_size/3) #trochanter
        glutesupinfo = glutesup.build()
        trochanter = Blend(part = 'trochanter', side=self.side, parent=self.main_grp, joint_parent= self.joint_parent, guides=[self.guides[5]], driver = self.driver, mult_range=(.5,.5),driver_rot_range=(0, 90* mod), driver_axis='Z', pop_amount=(self.control_size/8)) #trochanter
        trochanterinfo = trochanter.build()"""

        #joints

        #hip_info = module_info(control =self.hip_ctrl, joint=self.hip_joint)
        #return hip_info