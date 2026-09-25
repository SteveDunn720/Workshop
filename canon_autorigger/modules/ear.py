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

class Ear:
    def __init__(
        self,
        main_space,
        driver,
        head_space,
        part: str = "ear",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: dict = {},
        joint_parent:str = 'skel',
        shape:str = 'sphere',
        main_shape:str = 'round_square'


    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides= guides
        self.joint_parent = joint_parent
        self.main_shape = main_shape
        self.shape = shape
        if self.side == 'L':
            self.main_color = 'Left'
            self.sub_color = 'SubLeft'
        else:
            self.main_color = 'Right'
            self.sub_color = 'SubRight'
        self.main_space = main_space
        self.driver = driver
        self.head_space = head_space

    # -------------------
    # Build steps
    # -------------------

    def ear_build(self)->module_info:

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        #controls
        self.main_ctrl = create_control(
            name=self.guides[f'{self.side}_root'].descriptor,
            parent=self.control_grp,
            transform=self.guides[f'{self.side}_root'].name,
            size=self.control_size/100,
            control_shape=self.main_shape,
            direction="y",
            color_type=self.main_color,
            sdk_offset=True,
            shape_position_offset=((self.control_size * .03), self.control_size*.03, 0),
            shape_rotation_offset=(90,0,0)
        )

        module_space(control=self.main_ctrl, space_list=self.main_space)
        self.main_joint = create_joint(name=f"def_{self.guides[f'{self.side}_root'].descriptor}", transform=self.main_ctrl.ctrl, connect=True, parent=self.joint_parent)

        for mod in ['lower', 'upper', 'outer']:
            ctrl = create_control(
                name=self.guides[f'{self.side}_{mod}'].descriptor,
                parent=self.main_ctrl.ctrl,
                transform=self.guides[f'{self.side}_{mod}'].name,
                size=self.control_size/150,
                control_shape=self.shape,
                direction="y",
                color_type=self.main_color,
                sdk_offset=True
            )
            #joints

            joint = create_joint(name=f"def_{self.guides[f'{self.side}_{mod}'].descriptor}", transform=ctrl.ctrl, connect=True, parent=self.joint_parent)
            if mod == 'lower':
                create_blend_driver_offset(default_mult=.5, control=ctrl, driver=self.driver, parent_space=self.main_space[0].ctrl,)
        #joints

        ear_info = module_info(control =self.main_ctrl, joint=self.main_joint)
        return ear_info