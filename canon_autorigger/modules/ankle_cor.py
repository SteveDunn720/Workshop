from Workshop.canon_autorigger.module_schema import ModuleGuideArray, ModuleRelationship, ModuleSetting
from Workshop.transform.utils import create_transform

from .correctives.blend import Blend


class Ankle_Cor:
    MODULE_NAME = "ankle_cor"
    DISPLAY_NAME = "Ankle Correctives"
    GUIDES = (ModuleGuideArray(name="ankle", default_count=4, minimum_count=4),)
    SETTINGS = (
        ModuleSetting(name="rig_size", setting_type="float", default=1.0),
        ModuleSetting(name="blend", setting_type="float", default=0.5),
        ModuleSetting(name="translate_blend", setting_type="float", default=1.0),
        ModuleSetting(name="lateral_name", setting_type="string", default="lateral"),
        ModuleSetting(name="medial_name", setting_type="string", default="medial"),
        ModuleSetting(name="achilles_name", setting_type="string", default="achilles"),
        ModuleSetting(name="tibialis_name", setting_type="string", default="tibialis"),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="driver", relationship_type="joint", default="auto"),
        ModuleRelationship(name="joint_parent", relationship_type="joint", default="auto"),
    )

    def __init__(
        self,
        driver: str,
        part: str = "ankle_cor",
        side: str = "M",
        parent: str = "rig",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list | None = None,
        joint_parent: str = "skel",
        blend: float = 0.5,
        translate_blend: float = 1.0,
        lateral_name: str = "lateral",
        medial_name: str = "medial",
        achilles_name: str = "achilles",
        tibialis_name: str = "tibialis",
    ):
        self.driver = driver
        self.part = part
        self.side = side
        self.parent = parent
        self.control_parent = control_parent
        self.rig_size = rig_size
        self.guides = guides if guides is not None else []
        self.joint_parent = joint_parent
        self.blend = blend
        self.translate_blend = translate_blend
        self.corrective_names = (lateral_name, medial_name, achilles_name, tibialis_name)

    def build(self) -> None:
        self.main_grp = create_transform(name=f"{self.part}_{self.side}_cor", parent=self.parent)
        # Maintain the original guide-to-corrective assignments and build order.
        for part, guide_index in zip(self.corrective_names, (3, 2, 1, 0)):
            corrective = Blend(
                parent_part=self.part,
                part=part,
                side=self.side,
                parent=self.main_grp,
                joint_parent=self.joint_parent,
                guides=[self.guides[guide_index]],
                driver=self.driver,
                blend=self.blend,
                translate_blend=self.translate_blend,
            )
            corrective.build()
