from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint

from .module_shared import create_blend_driver_offset, create_driver_offset
from .module_initialize import module_prep, module_space


@dataclass
class module_info:
    control:Control
    joint:str

class Cheek:
    def __init__(
        self,
        puff_space,
        cheekbone_space,
        driver,
        head_space,
        part: str = "cheek",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list = [],
        joint_parent:str = 'skel',
        cheekbone_shape:str = 'triangle',
        puff_shape:str = 'sphere'


    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.puff_shape = puff_shape
        self.cheekbone_shape = cheekbone_shape
        if self.side == 'L':
            self.main_color = 'Left'
            self.sub_color = 'SubLeft'
        else:
            self.main_color = 'Right'
            self.sub_color = 'SubRight'
        self.puff_space = puff_space
        self.cheekbone_space = cheekbone_space
        self.driver = driver
        self.head_space = head_space

    # -------------------
    # Build steps
    # -------------------

    def cheek_build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        #controls
        self.puff_ctrl = create_control(
            name=self.guides[0].descriptor,
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.control_size/100,
            control_shape=self.puff_shape,
            direction="y",
            color_type=self.main_color,
            sdk_offset=True
        )

        module_space(control=self.puff_ctrl, space_list=self.puff_space)
        create_blend_driver_offset(default_mult=.5, control=self.puff_ctrl, driver=self.driver, parent_space=self.puff_space[0].ctrl,)
        #create_driver_offset(control=self.nose_ctrl, driver=self.jaw, x_range=(-90,0), rot_mult=.8, trans_mult=.25, y_range=(0,0), z_range=(-5,5))

        #joints

        self.puff_joint = create_joint(name=f'def_{self.guides[0].descriptor}', transform=self.puff_ctrl.ctrl, connect=True, parent=self.joint_parent)

        #constraint(drivers=[self.puff_ctrl.ctrl], driven=self.puff_joint, constraint_type='parent', parent=self.guts)

        #controls
        self.cheekbone_ctrl = create_control(
            name=self.guides[1].descriptor,
            parent=self.control_grp,
            transform=self.guides[1].name,
            size=self.control_size/100,
            control_shape=self.cheekbone_shape,
            direction="y",
            color_type=self.main_color,
            sdk_offset=True
        )

        module_space(control=self.cheekbone_ctrl, space_list=self.cheekbone_space)

        #joints

        self.cheekbone_joint = create_joint(name=f'def_{self.guides[1].descriptor}', transform=self.cheekbone_ctrl.ctrl, connect=True, parent=self.joint_parent)
        create_driver_offset(control=self.cheekbone_ctrl, driver=self.driver, x_range=(-90,0), rot_mult=.1, trans_mult=0, y_range=(0,0), z_range=(-5,5))

        #constraint(drivers=[self.cheekbone_ctrl.ctrl], driven=self.cheekbone_joint, constraint_type='parent', parent=self.guts)

        cheek_info = module_info(control =self.cheekbone_ctrl, joint=self.puff_joint)
        return cheek_info