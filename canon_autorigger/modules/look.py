
from Workshop.control import create_control
from Workshop.transform.utils import create_space_switch, get_position
from Workshop.guide.core import GuideInfo, create_midpoint_guide
from .module_shared import module_prep


class Look:
    def __init__(
        self,
        guides:list[GuideInfo],
        part: str = "look",
        side: str = "M",
        parent: str = "face_grp",
        control_parent: str = "neck_M0_head_ctl",
        rig_size: float = 1.0,
        parent_jnt: str = "face_jnt",
        parent_spaces:list = [],
        control_size = 1/30,
        control_shape = "round_square",
        dimensions = (3, 1, 1),
        control_color:str | None = None
    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str = control_parent
        self.rig_size: float = rig_size
        self.parent_jnt: str = parent_jnt
        self.guides = guides
        self.parent_list = parent_spaces
        self.control_size = control_size
        self.control_shape = control_shape
        self.dimensions = dimensions
        self.main_control_color = control_color or {
            "M": "Middle", "L": "Left", "R": "Right"
        }.get(side, "Right")

    def build(self) -> None:
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        mid_guide = create_midpoint_guide(guide_a=self.guides[0], guide_b=self.guides[1], name=f'{self.part}_{self.side}', parent='guides', create=True)

        self.main_ctrl = create_control(
            name=mid_guide.descriptor,
            parent=self.control_grp,
            transform=mid_guide.name,
            size=self.rig_size * self.control_size,
            control_shape=self.control_shape,
            direction="z",
            dimensions=self.dimensions,
            color_type=self.main_control_color
        )
        if self.parent_list:
            create_space_switch(
                target_transform=self.main_ctrl.top,
                parents=self.parent_list,
                target_control=self.main_ctrl.ctrl,
            )

