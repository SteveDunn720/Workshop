from Workshop.canon_autorigger.module_schema import (
    ModuleGuideArray,
    ModuleRelationship,
    ModuleSetting,
)
from Workshop.transform.utils import create_transform

from .correctives.blend import Blend
from .correctives.pull import Pull


class Elbow_Cor:
    MODULE_NAME = "elbow_cor"
    DISPLAY_NAME = "Elbow Correctives"
    GUIDES = (ModuleGuideArray(name="elbow_cor", default_count=4, minimum_count=4),)
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="lowerbicep_name", setting_type="string", default="lowerbicep"),
        ModuleSetting(name="lowerbicep_driver_axis", setting_type="string", default="X"),
        ModuleSetting(name="lowerbicep_rotation_range", setting_type="vector2", default=(0, 120)),
        ModuleSetting(name="lowerbicep_amount_scale", setting_type="float", default=0.06666666666666667),
        ModuleSetting(name="lowerbicep_pull_axis", setting_type="string", default="Y"),
        ModuleSetting(name="lowertricep_name", setting_type="string", default="lowertricep"),
        ModuleSetting(name="lowertricep_driver_axis", setting_type="string", default="X"),
        ModuleSetting(name="lowertricep_rotation_range", setting_type="vector2", default=(0, 120)),
        ModuleSetting(name="lowertricep_amount_scale", setting_type="float", default=0.06666666666666667),
        ModuleSetting(name="lowertricep_pull_axis", setting_type="string", default="Y"),
        ModuleSetting(name="elbowin_name", setting_type="string", default="elbowin"),
        ModuleSetting(name="elbowin_driver_axis", setting_type="string", default="X"),
        ModuleSetting(name="elbowin_rotation_range", setting_type="vector2", default=(0, 80)),
        ModuleSetting(name="elbowin_amount_scale", setting_type="float", default=0.1),
        ModuleSetting(name="elbowin_mult_range", setting_type="vector2", default=(0.5, 0.5)),
        ModuleSetting(name="elbowin_pop_axis", setting_type="string", default="Y"),
        ModuleSetting(name="pronator_name", setting_type="string", default="pronator"),
        ModuleSetting(name="pronator_driver_axis", setting_type="string", default="X"),
        ModuleSetting(name="pronator_rotation_range", setting_type="vector2", default=(0, 120)),
        ModuleSetting(name="pronator_amount_scale", setting_type="float", default=0.1),
        ModuleSetting(name="pronator_pull_axis", setting_type="string", default="Y"),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="driver", relationship_type="joint", default="auto"),
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
    )

    def __init__(
        self,
        driver: str,
        part: str = "elbow_cor",
        side: str = "M",
        parent: str = "rig",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list | None = None,
        joint_parent: str = "skel",
        lowerbicep_name: str = "lowerbicep",
        lowerbicep_driver_axis: str = "X",
        lowerbicep_rotation_range: tuple[float, float] = (0, 120),
        lowerbicep_amount_scale: float = 0.06666666666666667,
        lowerbicep_pull_axis: str = "Y",
        lowertricep_name: str = "lowertricep",
        lowertricep_driver_axis: str = "X",
        lowertricep_rotation_range: tuple[float, float] = (0, 120),
        lowertricep_amount_scale: float = 0.06666666666666667,
        lowertricep_pull_axis: str = "Y",
        elbowin_name: str = "elbowin",
        elbowin_driver_axis: str = "X",
        elbowin_rotation_range: tuple[float, float] = (0, 80),
        elbowin_amount_scale: float = 0.1,
        elbowin_mult_range: tuple[float, float] = (0.5, 0.5),
        elbowin_pop_axis: str = "Y",
        pronator_name: str = "pronator",
        pronator_driver_axis: str = "X",
        pronator_rotation_range: tuple[float, float] = (0, 120),
        pronator_amount_scale: float = 0.1,
        pronator_pull_axis: str = "Y",
    ):
        self.driver = driver
        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.rig_size = rig_size
        self.guides = guides if guides is not None else []
        self.joint_parent = joint_parent
        self.lowerbicep_name = lowerbicep_name
        self.lowerbicep_driver_axis = lowerbicep_driver_axis
        self.lowerbicep_rotation_range = lowerbicep_rotation_range
        self.lowerbicep_amount_scale = lowerbicep_amount_scale
        self.lowerbicep_pull_axis = lowerbicep_pull_axis
        self.lowertricep_name = lowertricep_name
        self.lowertricep_driver_axis = lowertricep_driver_axis
        self.lowertricep_rotation_range = lowertricep_rotation_range
        self.lowertricep_amount_scale = lowertricep_amount_scale
        self.lowertricep_pull_axis = lowertricep_pull_axis
        self.elbowin_name = elbowin_name
        self.elbowin_driver_axis = elbowin_driver_axis
        self.elbowin_rotation_range = elbowin_rotation_range
        self.elbowin_amount_scale = elbowin_amount_scale
        self.elbowin_mult_range = elbowin_mult_range
        self.elbowin_pop_axis = elbowin_pop_axis
        self.pronator_name = pronator_name
        self.pronator_driver_axis = pronator_driver_axis
        self.pronator_rotation_range = pronator_rotation_range
        self.pronator_amount_scale = pronator_amount_scale
        self.pronator_pull_axis = pronator_pull_axis

    def build(self) -> None:
        self.main_grp = create_transform(
            name=f"{self.part}_{self.side}_cor", parent=self.parent
        )

        lowerbicep = Pull(
            part=self.lowerbicep_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.joint_parent,
            guides=[self.guides[1]],
            driver=self.driver,
            rig_size=self.rig_size,
            range=self.lowerbicep_rotation_range,
            pull_amount=self.rig_size * self.lowerbicep_amount_scale,
            driver_axis=self.lowerbicep_driver_axis,
            pull_axis=self.lowerbicep_pull_axis,
        )
        lowerbicep.build()

        lowertricep = Pull(
            part=self.lowertricep_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.joint_parent,
            guides=[self.guides[2]],
            driver=self.driver,
            rig_size=self.rig_size,
            range=self.lowertricep_rotation_range,
            pull_amount=self.rig_size * self.lowertricep_amount_scale,
            driver_axis=self.lowertricep_driver_axis,
            pull_axis=self.lowertricep_pull_axis,
        )
        lowertricep.build()

        elbowin = Blend(
            part=self.elbowin_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.joint_parent,
            guides=[self.guides[0]],
            driver=self.driver,
            driver_rot_range=self.elbowin_rotation_range,
            mult_range=self.elbowin_mult_range,
            driver_axis=self.elbowin_driver_axis,
            pop_amount=self.rig_size * self.elbowin_amount_scale,
            pop_axis=self.elbowin_pop_axis,
        )
        elbowin.build()

        pronator = Pull(
            part=self.pronator_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.driver,
            guides=[self.guides[3]],
            driver=self.driver,
            rig_size=self.rig_size,
            range=self.pronator_rotation_range,
            pull_amount=self.rig_size * self.pronator_amount_scale,
            driver_axis=self.pronator_driver_axis,
            pull_axis=self.pronator_pull_axis,
        )
        pronator.build()
