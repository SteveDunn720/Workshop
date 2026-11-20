
from Workshop.canon_autorigger.module_schema import (
    ModuleGuideArray,
    ModuleRelationship,
    ModuleSetting,
)
from Workshop.transform.utils import create_transform
from Workshop.guide.core import GuideInfo
from .correctives.blend import Blend

from .correctives.ik_correctives import Ik_correctives


class Chest_Cor:
    MODULE_NAME = "chest_cor"
    DISPLAY_NAME = "Chest Correctives"

    GUIDES = (
        ModuleGuideArray(
            name="chest",
            default_count=3,
            minimum_count=3,
        ),
    )

    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="divisions", setting_type="int", default=1),
        ModuleSetting(name="control_shape", setting_type="control_shape", default="circle"),
        ModuleSetting(name="control_color", setting_type="string", default="MISC"),
        ModuleSetting(name="pec_name", setting_type="string", default="pec"),
        ModuleSetting(name="trap_name", setting_type="string", default="trap"),
        ModuleSetting(name="necktrap_name", setting_type="string", default="necktrap"),
    )

    RELATIONSHIPS = (
        ModuleRelationship(
            name="driver",
            relationship_type="joint",
            default="auto",
        ),
        ModuleRelationship(
            name="clav_driver",
            relationship_type="joint",
            default="auto",
        ),
        ModuleRelationship(
            name="parent_space",
            relationship_type="control_space",
            default="auto",
        ),
        ModuleRelationship(
            name="joint_parent",
            relationship_type="joint",
            default="auto",
        ),
    )

    def __init__(
        self,
        driver: str,
        parent_space: str,
        blend:GuideInfo,
        blend_parent:str,
        blend_driver:str,
        clav_driver: str | None = None,
        part: str = "chest_cor",
        side: str = "M",
        parent: str = "rig",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list | None = None,
        joint_parent: str = "skel",
        divisions: int = 1,
        control_shape: str = "circle",
        control_color: str = "MISC",
        pec_name: str = "pec",
        trap_name: str = "trap",
        necktrap_name: str = "necktrap",
    ):
        self.driver = driver
        self.clav_driver = clav_driver
        self.parent_space = parent_space
        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.rig_size = rig_size
        self.guides = guides if guides is not None else []
        self.joint_parent = joint_parent
        self.divisions = divisions
        self.control_shape = control_shape
        self.control_color = control_color
        self.blend = blend
        self.blend_parent = blend_parent
        self.blend_driver = blend_driver

        self.corrective_names = (
            pec_name,
            trap_name,
            necktrap_name,
        )

    def build(self) -> None:
        self.main_grp = create_transform(
            name=f"{self.part}_{self.side}_cor",
            parent=self.parent,
        )

        for guide_index, part in enumerate(self.corrective_names):

            # Necktrap follows the clavicle instead of the arm.
            driver = (
                self.clav_driver
                if guide_index == 2 and self.clav_driver is not None
                else self.driver
            )

            corrective = Ik_correctives(
                part=part,
                rig_size=self.rig_size,
                joint_parent=self.joint_parent,
                parent=self.main_grp,
                side=self.side,
                guides=self.guides[guide_index],
                end_ik_space=[driver],
                root_ik_space=[self.parent_space],
                divisions=self.divisions,
                control_shape=self.control_shape,
                control_color=self.control_color,
            )

            corrective.build()

        bicep = Blend(
            part="bicep",
            side=self.side,
            parent=self.main_grp,
            joint_parent=self.blend_parent,
            guides=[self.blend],
            driver=self.blend_driver, #type:ignore

            blend=0.5,
            translate_blend=1.0,

            driver_axis="z",
            driver_rot_range=(0, 90),
            mult_range=(1, 1),

            pop_amount=self.rig_size * 1/10 ,
            pop_axis="y",
        )
        bicep.build()