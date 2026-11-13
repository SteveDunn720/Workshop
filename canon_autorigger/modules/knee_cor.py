from Workshop.canon_autorigger.module_schema import (
    ModuleGuideArray,
    ModuleRelationship,
    ModuleSetting,
)
from Workshop.transform.utils import create_transform

from .correctives.blend import Blend
from .correctives.pull import Pull


class Knee_Cor:
    MODULE_NAME = "knee_cor"
    DISPLAY_NAME = "Knee Correctives"
    GUIDES = (ModuleGuideArray(name="knee_cor", default_count=3, minimum_count=3),)
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="hamstring_name", setting_type="string", default="hamstring"),
        ModuleSetting(name="hamstring_driver_axis", setting_type="string", default="X"),
        ModuleSetting(name="hamstring_rotation_range", setting_type="vector2", default=(0, -120)),
        ModuleSetting(name="hamstring_amount_scale", setting_type="float", default=0.3333333333333333),
        ModuleSetting(name="hamstring_pull_axis", setting_type="string", default="Y"),
        ModuleSetting(name="kneecap_name", setting_type="string", default="kneecap"),
        ModuleSetting(name="kneecap_driver_axis", setting_type="string", default="X"),
        ModuleSetting(name="kneecap_rotation_range", setting_type="vector2", default=(0, -80)),
        ModuleSetting(name="kneecap_amount_scale", setting_type="float", default=0.14285714285714285),
        ModuleSetting(name="kneecap_mult_range", setting_type="vector2", default=(0.5, 0.8)),
        ModuleSetting(name="kneecap_pop_axis", setting_type="string", default="Y"),
        ModuleSetting(name="calf_name", setting_type="string", default="calf"),
        ModuleSetting(name="calf_driver_axis", setting_type="string", default="X"),
        ModuleSetting(name="calf_rotation_range", setting_type="vector2", default=(0, -120)),
        ModuleSetting(name="calf_amount_scale", setting_type="float", default=0.1),
        ModuleSetting(name="calf_pull_axis", setting_type="string", default="Y"),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="driver", relationship_type="joint", default="auto"),
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
    )

    def __init__(
        self,
        driver: str,
        part: str = "knee_cor",
        side: str = "M",
        parent: str = "rig",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list | None = None,
        joint_parent: str = "skel",
        hamstring_name: str = "hamstring",
        hamstring_driver_axis: str = "X",
        hamstring_rotation_range: tuple[float, float] = (0, -120),
        hamstring_amount_scale: float = 0.3333333333333333,
        hamstring_pull_axis: str = "Y",
        kneecap_name: str = "kneecap",
        kneecap_driver_axis: str = "X",
        kneecap_rotation_range: tuple[float, float] = (0, -80),
        kneecap_amount_scale: float = 0.14285714285714285,
        kneecap_mult_range: tuple[float, float] = (0.5, 0.8),
        kneecap_pop_axis: str = "Y",
        calf_name: str = "calf",
        calf_driver_axis: str = "X",
        calf_rotation_range: tuple[float, float] = (0, -120),
        calf_amount_scale: float = 0.1,
        calf_pull_axis: str = "Y",
    ):
        self.driver = driver
        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.rig_size = rig_size
        self.guides = guides if guides is not None else []
        self.joint_parent = joint_parent
        self.hamstring_name = hamstring_name
        self.hamstring_driver_axis = hamstring_driver_axis
        self.hamstring_rotation_range = hamstring_rotation_range
        self.hamstring_amount_scale = hamstring_amount_scale
        self.hamstring_pull_axis = hamstring_pull_axis
        self.kneecap_name = kneecap_name
        self.kneecap_driver_axis = kneecap_driver_axis
        self.kneecap_rotation_range = kneecap_rotation_range
        self.kneecap_amount_scale = kneecap_amount_scale
        self.kneecap_mult_range = kneecap_mult_range
        self.kneecap_pop_axis = kneecap_pop_axis
        self.calf_name = calf_name
        self.calf_driver_axis = calf_driver_axis
        self.calf_rotation_range = calf_rotation_range
        self.calf_amount_scale = calf_amount_scale
        self.calf_pull_axis = calf_pull_axis

    def build(self) -> None:
        self.main_grp = create_transform(
            name=f"{self.part}_{self.side}_cor", parent=self.parent
        )

        hamstring = Pull(
            part=self.hamstring_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.joint_parent,
            guides=[self.guides[1]],
            driver=self.driver,
            rig_size=self.rig_size,
            range=self.hamstring_rotation_range,
            pull_amount=self.rig_size * self.hamstring_amount_scale,
            driver_axis=self.hamstring_driver_axis,
            pull_axis=self.hamstring_pull_axis,
        )
        hamstring.build()

        kneecap = Blend(
            part=self.kneecap_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.joint_parent,
            guides=[self.guides[0]],
            driver=self.driver,
            driver_rot_range=self.kneecap_rotation_range,
            mult_range=self.kneecap_mult_range,
            driver_axis=self.kneecap_driver_axis,
            pop_amount=self.rig_size * self.kneecap_amount_scale,
            pop_axis=self.kneecap_pop_axis,
        )
        kneecap.build()

        calf = Pull(
            part=self.calf_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.driver,
            guides=[self.guides[2]],
            driver=self.driver,
            range=self.calf_rotation_range,
            pull_amount=self.rig_size * self.calf_amount_scale,
            driver_axis=self.calf_driver_axis,
            pull_axis=self.calf_pull_axis,
        )
        calf.build()
