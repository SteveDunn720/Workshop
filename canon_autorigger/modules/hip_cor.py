from Workshop.canon_autorigger.module_schema import (
    ModuleGuideArray,
    ModuleRelationship,
    ModuleSetting,
)
from Workshop.transform.utils import create_transform

from .correctives.blend import Blend
from .correctives.pull import Pull


class Hip_Cor:
    MODULE_NAME = "hip_cor"
    DISPLAY_NAME = "Hip Correctives"
    GUIDES = (ModuleGuideArray(name="hip_cor", default_count=6, minimum_count=6),)
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="psosaup_name", setting_type="string", default="psosaup"),
        ModuleSetting(name="psosaup_driver_axis", setting_type="string", default="X"),
        ModuleSetting(name="psosaup_rotation_range", setting_type="vector2", default=(0, 120)),
        ModuleSetting(name="psosaup_amount_scale", setting_type="float", default=0.3333333333333333),
        ModuleSetting(name="psosaup_pull_axis", setting_type="string", default="Y"),
        ModuleSetting(name="psosadown_name", setting_type="string", default="psosadown"),
        ModuleSetting(name="psosadown_driver_axis", setting_type="string", default="X"),
        ModuleSetting(name="psosadown_rotation_range", setting_type="vector2", default=(0, 120)),
        ModuleSetting(name="psosadown_amount_scale", setting_type="float", default=0.3333333333333333),
        ModuleSetting(name="psosadown_pull_axis", setting_type="string", default="Y"),
        ModuleSetting(name="gluteslow_name", setting_type="string", default="gluteslow"),
        ModuleSetting(name="gluteslow_driver_axis", setting_type="string", default="X"),
        ModuleSetting(name="gluteslow_rotation_range", setting_type="vector2", default=(0, -90)),
        ModuleSetting(name="gluteslow_amount_scale", setting_type="float", default=0.3333333333333333),
        ModuleSetting(name="gluteslow_pull_axis", setting_type="string", default="Y"),
        ModuleSetting(name="glutesmid_name", setting_type="string", default="glutesmid"),
        ModuleSetting(name="glutesmid_driver_axis", setting_type="string", default="X"),
        ModuleSetting(name="glutesmid_rotation_range", setting_type="vector2", default=(0, -80)),
        ModuleSetting(name="glutesmid_amount_scale", setting_type="float", default=0.16666666666666666),
        ModuleSetting(name="glutesmid_mult_range", setting_type="vector2", default=(0.2, 0.4)),
        ModuleSetting(name="glutesmid_pop_axis", setting_type="string", default="Y"),
        ModuleSetting(name="glutesup_name", setting_type="string", default="glutesup"),
        ModuleSetting(name="glutesup_driver_axis", setting_type="string", default="X"),
        ModuleSetting(name="glutesup_rotation_range", setting_type="vector2", default=(0, -90)),
        ModuleSetting(name="glutesup_amount_scale", setting_type="float", default=0.3333333333333333),
        ModuleSetting(name="glutesup_pull_axis", setting_type="string", default="Y"),
        ModuleSetting(name="trochanter_name", setting_type="string", default="trochanter"),
        ModuleSetting(name="trochanter_driver_axis", setting_type="string", default="Z"),
        ModuleSetting(name="trochanter_rotation_range", setting_type="vector2", default=(0, 90)),
        ModuleSetting(name="trochanter_amount_scale", setting_type="float", default=0.125),
        ModuleSetting(name="trochanter_mult_range", setting_type="vector2", default=(0.5, 0.5)),
        ModuleSetting(name="trochanter_pop_axis", setting_type="string", default="Y"),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="driver", relationship_type="joint", default="auto"),
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
    )

    def __init__(
        self,
        driver: str,
        part: str = "hip_cor",
        side: str = "M",
        parent: str = "rig",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list | None = None,
        joint_parent: str = "skel",
        psosaup_name: str = "psosaup",
        psosaup_driver_axis: str = "X",
        psosaup_rotation_range: tuple[float, float] = (0, 120),
        psosaup_amount_scale: float = 0.3333333333333333,
        psosaup_pull_axis: str = "Y",
        psosadown_name: str = "psosadown",
        psosadown_driver_axis: str = "X",
        psosadown_rotation_range: tuple[float, float] = (0, 120),
        psosadown_amount_scale: float = 0.3333333333333333,
        psosadown_pull_axis: str = "Y",
        gluteslow_name: str = "gluteslow",
        gluteslow_driver_axis: str = "X",
        gluteslow_rotation_range: tuple[float, float] = (0, -90),
        gluteslow_amount_scale: float = 0.3333333333333333,
        gluteslow_pull_axis: str = "Y",
        glutesmid_name: str = "glutesmid",
        glutesmid_driver_axis: str = "X",
        glutesmid_rotation_range: tuple[float, float] = (0, -80),
        glutesmid_amount_scale: float = 0.16666666666666666,
        glutesmid_mult_range: tuple[float, float] = (0.2, 0.4),
        glutesmid_pop_axis: str = "Y",
        glutesup_name: str = "glutesup",
        glutesup_driver_axis: str = "X",
        glutesup_rotation_range: tuple[float, float] = (0, -90),
        glutesup_amount_scale: float = 0.3333333333333333,
        glutesup_pull_axis: str = "Y",
        trochanter_name: str = "trochanter",
        trochanter_driver_axis: str = "Z",
        trochanter_rotation_range: tuple[float, float] = (0, 90),
        trochanter_amount_scale: float = 0.125,
        trochanter_mult_range: tuple[float, float] = (0.5, 0.5),
        trochanter_pop_axis: str = "Y",
    ):
        self.driver = driver
        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.rig_size = rig_size
        self.guides = guides if guides is not None else []
        self.joint_parent = joint_parent
        self.psosaup_name = psosaup_name
        self.psosaup_driver_axis = psosaup_driver_axis
        self.psosaup_rotation_range = psosaup_rotation_range
        self.psosaup_amount_scale = psosaup_amount_scale
        self.psosaup_pull_axis = psosaup_pull_axis
        self.psosadown_name = psosadown_name
        self.psosadown_driver_axis = psosadown_driver_axis
        self.psosadown_rotation_range = psosadown_rotation_range
        self.psosadown_amount_scale = psosadown_amount_scale
        self.psosadown_pull_axis = psosadown_pull_axis
        self.gluteslow_name = gluteslow_name
        self.gluteslow_driver_axis = gluteslow_driver_axis
        self.gluteslow_rotation_range = gluteslow_rotation_range
        self.gluteslow_amount_scale = gluteslow_amount_scale
        self.gluteslow_pull_axis = gluteslow_pull_axis
        self.glutesmid_name = glutesmid_name
        self.glutesmid_driver_axis = glutesmid_driver_axis
        self.glutesmid_rotation_range = glutesmid_rotation_range
        self.glutesmid_amount_scale = glutesmid_amount_scale
        self.glutesmid_mult_range = glutesmid_mult_range
        self.glutesmid_pop_axis = glutesmid_pop_axis
        self.glutesup_name = glutesup_name
        self.glutesup_driver_axis = glutesup_driver_axis
        self.glutesup_rotation_range = glutesup_rotation_range
        self.glutesup_amount_scale = glutesup_amount_scale
        self.glutesup_pull_axis = glutesup_pull_axis
        self.trochanter_name = trochanter_name
        self.trochanter_driver_axis = trochanter_driver_axis
        self.trochanter_rotation_range = trochanter_rotation_range
        self.trochanter_amount_scale = trochanter_amount_scale
        self.trochanter_mult_range = trochanter_mult_range
        self.trochanter_pop_axis = trochanter_pop_axis

    def build(self) -> None:
        self.main_grp = create_transform(
            name=f"{self.part}_{self.side}_cor", parent=self.parent
        )

        psosaup = Pull(
            part=self.psosaup_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.joint_parent,
            guides=[self.guides[0]],
            driver=self.driver,
            rig_size=self.rig_size,
            range=self.psosaup_rotation_range,
            pull_amount=self.rig_size * self.psosaup_amount_scale,
            driver_axis=self.psosaup_driver_axis,
            pull_axis=self.psosaup_pull_axis,
        )
        psosaup.build()

        psosadown = Pull(
            part=self.psosadown_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.driver,
            guides=[self.guides[1]],
            driver=self.driver,
            rig_size=self.rig_size,
            range=self.psosadown_rotation_range,
            pull_amount=self.rig_size * self.psosadown_amount_scale,
            driver_axis=self.psosadown_driver_axis,
            pull_axis=self.psosadown_pull_axis,
        )
        psosadown.build()

        gluteslow = Pull(
            part=self.gluteslow_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.driver,
            guides=[self.guides[2]],
            driver=self.driver,
            range=self.gluteslow_rotation_range,
            pull_amount=self.rig_size * self.gluteslow_amount_scale,
            driver_axis=self.gluteslow_driver_axis,
            pull_axis=self.gluteslow_pull_axis,
        )
        gluteslow.build()

        glutesmid = Blend(
            part=self.glutesmid_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.joint_parent,
            guides=[self.guides[3]],
            driver=self.driver,
            driver_rot_range=self.glutesmid_rotation_range,
            mult_range=self.glutesmid_mult_range,
            driver_axis=self.glutesmid_driver_axis,
            pop_amount=self.rig_size * self.glutesmid_amount_scale,
            pop_axis=self.glutesmid_pop_axis,
        )
        glutesmid.build()

        glutesup = Pull(
            part=self.glutesup_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.joint_parent,
            guides=[self.guides[4]],
            driver=self.driver,
            range=self.glutesup_rotation_range,
            pull_amount=self.rig_size * self.glutesup_amount_scale,
            driver_axis=self.glutesup_driver_axis,
            pull_axis=self.glutesup_pull_axis,
        )
        glutesup.build()

        trochanter = Blend(
            part=self.trochanter_name,
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.joint_parent,
            guides=[self.guides[5]],
            driver=self.driver,
            driver_rot_range=self.trochanter_rotation_range,
            mult_range=self.trochanter_mult_range,
            driver_axis=self.trochanter_driver_axis,
            pop_amount=self.rig_size * self.trochanter_amount_scale,
            pop_axis=self.trochanter_pop_axis,
        )
        trochanter.build()
