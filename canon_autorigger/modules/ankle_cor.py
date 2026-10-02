from Workshop.transform.utils import create_transform

from .correctives.blend import Blend



class Ankle_Cor:
    pass

    def __init__(
        self,
        driver:str ,
        part: str = "ankle_cor",
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


        
        lateral = Blend(part = 'lateral', side=self.side, parent=self.main_grp, joint_parent= self.driver, guides=[self.guides[3]], driver = self.driver, )
        lateralinfo = lateral.build()
        medial = Blend(part = 'medial', side=self.side, parent=self.main_grp, joint_parent= self.driver, guides=[self.guides[2]], driver = self.driver, )
        medialinfo = medial.build()
        achilles = Blend(part = 'achilles', side=self.side, parent=self.main_grp, joint_parent= self.driver, guides=[self.guides[1]], driver = self.driver, )
        achillesinfo = achilles.build()
        tibialis = Blend(part = 'tibialis', side=self.side, parent=self.main_grp, joint_parent= self.driver, guides=[self.guides[0]], driver = self.driver, )
        tibialisinfo = tibialis.build()