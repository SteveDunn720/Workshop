from dataclasses import dataclass
from Workshop.control.core import Control
from Workshop.maya_api.attribute_utils import create_attribute

from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.tag.core import lock_tag
from Workshop.joint import create_joint
from Workshop.canon_autorigger.module_schema import ModuleGuide, ModuleRelationship, ModuleSetting
from Workshop.canon_autorigger.build_management.dev import create_dev_control
from .module_shared import module_prep


@dataclass
class module_info:
    root_control:Control
    local_control:Control
    offset_control:Control
    joint:str

class Root:

    MODULE_NAME = "root"
    DISPLAY_NAME = "Root"

    GUIDES = (
        ModuleGuide(
            name="root",
        ),
    )

    SETTINGS = (
        ModuleSetting(
            name="rig_size",
            setting_type="float",
            default=1.0,
        ),
        ModuleSetting(
            name="root_control_color",
            setting_type="string",
            default="Root",
        ),
        ModuleSetting(
            name="control_color",
            setting_type="string",
            default="MISC",
        ),
        ModuleSetting(
            name="settings_control_color",
            setting_type="string",
            default="MISC",
        ),
        ModuleSetting(
            name="root_control_shape",
            setting_type="control_shape",
            default="Character_base",
        ),
        ModuleSetting(
            name="control_shape",
            setting_type="control_shape",
            default="circle",
        ),
        ModuleSetting(
            name="settings_control_shape",
            setting_type="control_shape",
            default="gear",
        ),
        ModuleSetting(
            name="local_name",
            setting_type="string",
            default="local",
        ),
        ModuleSetting(name="offset_name", setting_type="string", default="offset"),
        ModuleSetting(name="local_size_scale", setting_type="float", default=0.56),
        ModuleSetting(name="offset_size_scale", setting_type="float", default=0.4),
        ModuleSetting(name="settings_size_scale", setting_type="float", default=0.05),
        ModuleSetting(name="settings_offset_character", setting_type="float", default=0.88),
        ModuleSetting(name="settings_offset_other", setting_type="float", default=0.71),
        ModuleSetting(name="visibility_control_name", setting_type="string", default="visibility_options"),
        ModuleSetting(name="color_control_name", setting_type="string", default="color_options"),
        ModuleSetting(name="dev_size_scale", setting_type="float", default=0.25),
        ModuleSetting(name="dev_offset_scale", setting_type="float", default=1.0),
    )

    RELATIONSHIPS = ()

    def __init__(
        self,
        part: str = "root",
        side: str = "M",
        parent: str = "rig",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list | None = None,
        joint_parent:str = 'skel',
        root_control_shape:str = "Character_base",
        root_control_color:str = "Root",
        settings_control_shape:str = "gear",
        settings_control_color:str = "MISC",
        control_shape:str = "circle",
        control_color:str = "MISC",
        local_name:str = "local",
        offset_name:str = "offset",
        local_size_scale: float = 0.56,
        offset_size_scale: float = 0.4,
        settings_size_scale: float = 0.05,
        settings_offset_character: float = 0.88,
        settings_offset_other: float = 0.71,
        visibility_control_name: str = "visibility_options",
        color_control_name: str = "color_options",
        dev_size_scale: float = 0.25,
        dev_offset_scale: float = 1.0,


    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.rig_size: float = rig_size
        self.guides: list = guides if guides is not None else []
        self.joint_parent = joint_parent
        self.root_control_shape = root_control_shape
        self.root_control_color = root_control_color
        self.settings_control_shape = settings_control_shape
        self.settings_control_color = settings_control_color
        self.control_shape = control_shape
        self.control_color = control_color
        self.local_name = local_name
        self.offset_name = offset_name
        self.local_size_scale = local_size_scale
        self.offset_size_scale = offset_size_scale
        self.settings_size_scale = settings_size_scale
        self.settings_offset_character = settings_offset_character
        self.settings_offset_other = settings_offset_other
        self.visibility_control_name = visibility_control_name
        self.color_control_name = color_control_name
        self.dev_size_scale = dev_size_scale
        self.dev_offset_scale = dev_offset_scale
    # -------------------
    # Build steps
    # -------------------

    @classmethod
    def preview(
        cls,
        part: str,
        side: str,
        guides: list[str],
        settings: dict,
    ) -> dict:

        if not guides:
            return {
                "controls": [],
                "joints": [],
                "output_control": None,
                "output_joint": None,
            }

        local_name = settings.get(
            "local_name",
            "local",
        )

        offset_name = settings.get(
            "offset_name",
            "offset",
        )

        root_control = f"{part}_{side}_ctrl"
        local_control = f"{local_name}_{side}_ctrl"
        offset_control = f"{offset_name}_{side}_ctrl"

        visibility_control = f'{settings.get("visibility_control_name", "visibility_options")}_ctrl'
        color_control = f'{settings.get("color_control_name", "color_options")}_ctrl' 

        root_joint = f"def_{part}_{side}_jnt"

        return {
            "controls": [
                root_control,
                local_control,
                offset_control,
                visibility_control,
                color_control,
            ],
            "joints": [
                root_joint,
            ],
            "output_control": offset_control,
            "output_joint": root_joint,
        }

    def build(self)->module_info:

        #modeule prop work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        #controls
        self.root_ctrl = create_control(
            name=f'{self.part}_{self.side}',
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.rig_size,
            control_shape=self.root_control_shape,
            direction="y",
            color_type=self.root_control_color
        )

        self.local_ctrl = create_control(
            name=f'{self.local_name}_{self.side}',
            parent=self.root_ctrl.ctrl,
            transform=self.guides[0].name,
            size=self.rig_size * self.local_size_scale,
            control_shape=self.control_shape,
            direction="y",
            color_type=self.control_color
        )

        self.offset_ctrl = create_control(
            name=f'{self.offset_name}_{self.side}',
            parent=self.local_ctrl.ctrl,
            transform=self.guides[0].name,
            size=self.rig_size * self.offset_size_scale,
            control_shape=self.control_shape,
            direction="y",
            color_type=self.control_color
        )

        #rig option controls

        settings_offset = (self.settings_offset_character if self.root_control_shape == 'Character_base' else self.settings_offset_other)
        self.vis_control = create_control(
            name=self.visibility_control_name,
            parent=self.root_ctrl.ctrl,
            transform=self.guides[0].name,
            size=self.rig_size * self.settings_size_scale,
            control_shape=self.settings_control_shape,
            direction="y",
            shape_position_offset=(self.rig_size * settings_offset, 0, 0 ),
            color_type=self.settings_control_color
        )

        self.color_control = create_control(
            name=self.color_control_name,
            parent=self.root_ctrl.ctrl,
            transform=self.guides[0].name,
            size=self.rig_size * self.settings_size_scale,
            control_shape=self.settings_control_shape,
            direction="y",
            shape_position_offset=(self.rig_size * -settings_offset, 0, 0 ),
            color_type=self.settings_control_color
        )
        lock_tag(self.color_control.ctrl, hide_tag=True)
        lock_tag(self.vis_control.ctrl, hide_tag=True)

        #root joint

        self.root_joint = create_joint(name=f'def_{self.part}_{self.side}', transform=self.root_ctrl.ctrl, connect=True, parent=self.joint_parent)

        constraint(drivers=[self.root_ctrl.ctrl], driven=self.root_joint, constraint_type='parent', parent=self.guts)

        #default attr
        for rig_vis_type in ['skel', 'geo', 'rig', 'controls']:
            create_attribute(
                primary_object=self.vis_control.ctrl,
                attr_name=f"{rig_vis_type}_vis",
                default=1,
                min=0,
                max=1,
                attr_type="bool",
            )

        create_dev_control(parent=self.root_ctrl.ctrl, size=self.rig_size * self.dev_size_scale, offset=(self.rig_size * self.dev_offset_scale, self.rig_size * self.dev_offset_scale, 0))

        root_info = module_info(root_control =self.root_ctrl, local_control=self.local_ctrl, offset_control=self.offset_ctrl, joint=self.root_joint)
        return root_info