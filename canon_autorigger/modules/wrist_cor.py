from Workshop.canon_autorigger.module_schema import (
    ModuleGuideArray,
    ModuleRelationship,
    ModuleSetting,
)
from Workshop.transform.utils import create_transform

from .correctives.blend import Blend
from .correctives.pull import Pull


class Wrist_Cor:
    MODULE_NAME = "wrist_cor"
    DISPLAY_NAME = "Wrist Correctives"
    GUIDES = (ModuleGuideArray(name="wrist_cor", default_count=4, minimum_count=4),)
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="wristup_name", setting_type="string", default="wristup"),
        ModuleSetting(name="wristup_driver_axis", setting_type="string", default="Z"),
        ModuleSetting(name="wristup_rotation_range", setting_type="vector2", default=(0, 90)),
        ModuleSetting(name="wristup_amount_scale", setting_type="float", default=0.06666666666666667),
        ModuleSetting(name="wristup_pull_axis", setting_type="string", default="Y"),
        ModuleSetting(name="wristdown_name", setting_type="string", default="wristdown"),
        ModuleSetting(name="wristdown_driver_axis", setting_type="string", default="Z"),
        ModuleSetting(name="wristdown_rotation_range", setting_type="vector2", default=(0, -90)),
        ModuleSetting(name="wristdown_amount_scale", setting_type="float", default=0.06666666666666667),
        ModuleSetting(name="wristdown_pull_axis", setting_type="string", default="Y"),
        ModuleSetting(name="wristin_name", setting_type="string", default="wristin"),
        ModuleSetting(name="wristin_driver_axis", setting_type="string", default="X"),
        ModuleSetting(name="wristin_rotation_range", setting_type="vector2", default=(0, 90)),
        ModuleSetting(name="wristin_amount_scale", setting_type="float", default=0.06666666666666667),
        ModuleSetting(name="wristin_mult_range", setting_type="vector2", default=(0.5, 0.5)),
        ModuleSetting(name="wristin_pop_axis", setting_type="string", default="Y"),
        ModuleSetting(name="wristout_name", setting_type="string", default="wristout"),
        ModuleSetting(name="wristout_driver_axis", setting_type="string", default="X"),
        ModuleSetting(name="wristout_rotation_range", setting_type="vector2", default=(0, -90)),
        ModuleSetting(name="wristout_amount_scale", setting_type="float", default=0.06666666666666667),
        ModuleSetting(name="wristout_mult_range", setting_type="vector2", default=(0.5, 0.5)),
        ModuleSetting(name="wristout_pop_axis", setting_type="string", default="Y"),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="driver", relationship_type="joint", default="auto"),
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
    )

    def __init__(
        self,
        driver: str,
        part: str = "wrist_cor",
        side: str = "M",
        parent: str = "rig",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list | None = None,
        joint_parent: str = "skel",
        wristup_name: str = "wristup",
        wristup_driver_axis: str = "Z",
        wristup_rotation_range: tuple[float, float] = (0, 90),
        wristup_amount_scale: float = 0.06666666666666667,
        wristup_pull_axis: str = "Y",
        wristdown_name: str = "wristdown",
        wristdown_driver_axis: str = "Z",
        wristdown_rotation_range: tuple[float, float] = (0, -90),
        wristdown_amount_scale: float = 0.06666666666666667,
        wristdown_pull_axis: str = "Y",
        wristin_name: str = "wristin",
        wristin_driver_axis: str = "X",
        wristin_rotation_range: tuple[float, float] = (0, 90),
        wristin_amount_scale: float = 0.06666666666666667,
        wristin_mult_range: tuple[float, float] = (0.5, 0.5),
        wristin_pop_axis: str = "Y",
        wristout_name: str = "wristout",
        wristout_driver_axis: str = "X",
        wristout_rotation_range: tuple[float, float] = (0, -90),
        wristout_amount_scale: float = 0.06666666666666667,
        wristout_mult_range: tuple[float, float] = (0.5, 0.5),
        wristout_pop_axis: str = "Y",
    ):
        self.driver = driver
        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.rig_size = rig_size
        self.guides = guides if guides is not None else []
        self.joint_parent = joint_parent
        self.wristup_name = wristup_name
        self.wristup_driver_axis = wristup_driver_axis
        self.wristup_rotation_range = wristup_rotation_range
        self.wristup_amount_scale = wristup_amount_scale
        self.wristup_pull_axis = wristup_pull_axis
        self.wristdown_name = wristdown_name
        self.wristdown_driver_axis = wristdown_driver_axis
        self.wristdown_rotation_range = wristdown_rotation_range
        self.wristdown_amount_scale = wristdown_amount_scale
        self.wristdown_pull_axis = wristdown_pull_axis
        self.wristin_name = wristin_name
        self.wristin_driver_axis = wristin_driver_axis
        self.wristin_rotation_range = wristin_rotation_range
        self.wristin_amount_scale = wristin_amount_scale
        self.wristin_mult_range = wristin_mult_range
        self.wristin_pop_axis = wristin_pop_axis
        self.wristout_name = wristout_name
        self.wristout_driver_axis = wristout_driver_axis
        self.wristout_rotation_range = wristout_rotation_range
        self.wristout_amount_scale = wristout_amount_scale
        self.wristout_mult_range = wristout_mult_range
        self.wristout_pop_axis = wristout_pop_axis

    def build(self) -> None:
        self.main_grp = create_transform(
            name=f"{self.part}_{self.side}_cor", parent=self.parent
        )

        wristup = Pull(
            part=self.wristup_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.joint_parent,
            guides=[self.guides[2]],
            driver=self.driver,
            rig_size=self.rig_size,
            range=self.wristup_rotation_range,
            pull_amount=self.rig_size * self.wristup_amount_scale,
            driver_axis=self.wristup_driver_axis,
            pull_axis=self.wristup_pull_axis,
        )
        wristup.build()

        wristdown = Pull(
            part=self.wristdown_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.joint_parent,
            guides=[self.guides[3]],
            driver=self.driver,
            rig_size=self.rig_size,
            range=self.wristdown_rotation_range,
            pull_amount=self.rig_size * self.wristdown_amount_scale,
            driver_axis=self.wristdown_driver_axis,
            pull_axis=self.wristdown_pull_axis,
        )
        wristdown.build()

        wristin = Blend(
            part=self.wristin_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.joint_parent,
            guides=[self.guides[0]],
            driver=self.driver,
            driver_rot_range=self.wristin_rotation_range,
            mult_range=self.wristin_mult_range,
            driver_axis=self.wristin_driver_axis,
            pop_amount=self.rig_size * self.wristin_amount_scale,
            pop_axis=self.wristin_pop_axis,
        )
        wristin.build()

        wristout = Blend(
            part=self.wristout_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.joint_parent,
            guides=[self.guides[1]],
            driver=self.driver,
            driver_rot_range=self.wristout_rotation_range,
            mult_range=self.wristout_mult_range,
            driver_axis=self.wristout_driver_axis,
            pop_amount=self.rig_size * self.wristout_amount_scale,
            pop_axis=self.wristout_pop_axis,
        )
        wristout.build()
