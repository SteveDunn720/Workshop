from dataclasses import dataclass
import maya.cmds as cmds
from Workshop.control.core import Control
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.core import GuideInfo
from Workshop.maya_api.node import BlendColorsNode, MultiplyDivideNode, SumNode
from Workshop.nurbs.curve import get_nurbs_curve_radius
from Workshop.transform.matrix import matrix_constraint
from Workshop.maya_api.attribute_utils import create_attribute

from ..module_shared import module_prep
from .eyelid import Eyelid
from .eyeball import Eyeball
from .socket import Socket

@dataclass
class module_info:
    master:Control
    master_joint:str
    path_pins:dict
    corner_controls:dict
    macro:dict

class Eye:
    def __init__(
        self,
        muppet,
        guides: dict[str, GuideInfo],
        jaw:Control,
        part: str = "mouth",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        joint_parent:str = 'skel',
        control_space:list = [],
        divisions:int = 11,
        look_parent: str = "Look_M_ctrl",
        main_control_shape: str = "round_square",
        main_control_direction: str = "z",
        main_control_offset_factor: float = 2.0,
        main_control_depth_factor: float = 1.0,
        eyelid_follow_default: float = 0.1,
        eyelid_sub_divisions: int = 11,
        socket_divisions: int = 11,
        blink_extension: float = 2.0,
        collision_push: float = 0.5,
        socket_follow_default: float = 0.1,
        root_rig_size:float = 1/40,

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.rig_size: float = rig_size
        self.guides: dict[str, GuideInfo] = guides
        self.joint_parent = joint_parent
        self.control_space = control_space
        self.jaw = jaw
        self.divisions = divisions
        self.muppet = muppet
        self.look_parent: str = look_parent
        self.main_control_shape = main_control_shape
        self.main_control_direction = main_control_direction
        self.main_control_offset_factor = main_control_offset_factor
        self.main_control_depth_factor = main_control_depth_factor
        self.eyelid_follow_default = eyelid_follow_default
        self.eyelid_sub_divisions = eyelid_sub_divisions
        self.socket_divisions = socket_divisions
        self.blink_extension = blink_extension
        self.collision_push = collision_push
        self.socket_follow_default = socket_follow_default
        self.root_rig_size = root_rig_size
        if self.side == 'L':
            self.main_color = 'Left'
            self.sub_color = 'SubLeft'
        elif self.side == 'R':
            self.main_color = 'Right'
            self.sub_color = 'SubRight'
        else:
            self.main_color = 'Middle'
            self.sub_color = 'SubMiddle'

    def build(self):
    
        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        eye_radius=get_nurbs_curve_radius(curve=self.guides["eye_diam"].name)
        offset_pos = (
            eye_radius * self.main_control_offset_factor,
            0,
            eye_radius * self.main_control_depth_factor,
        )

        #root control & joint


        self.main_ctrl = create_control(
            name=f'{self.part}_root_{self.side}',
            parent=self.control_grp,
            transform=self.guides["center"].name,
            size=self.rig_size * self.root_rig_size,
            control_shape=self.main_control_shape,
            direction=self.main_control_direction, #type:ignore
            shape_position_offset=offset_pos,
            color_type=self.main_color
        )

        self.main_jnt = create_joint(
            name=self.main_ctrl.name,
            parent=self.joint_parent,
            transform=self.main_ctrl.ctrl,
        )


        self.eyelid = Eyelid(
            side=self.side,
            guides=self.guides,
            rig_size=self.rig_size,
            main_ctrl=self.main_ctrl,
            parent=self.main_grp,
            joint_parent=self.main_jnt,
            component_grp=self.guts,
            control_grp=self.control_grp,
            guts=self.guts,
            main_color = self.main_color,
            sub_color = self.sub_color,

        )
        self.eyelid.build(
            sub_divisions=self.eyelid_sub_divisions,
            blink_extension=self.blink_extension,
            collision_push=self.collision_push,
        )

        self.socket = Socket(
            side=self.side,
            guts=self.guts,
            guides=self.guides,
            rig_size=self.rig_size,
            main_ctrl=self.main_ctrl,
            parent=self.main_grp,
            joint_parent=self.main_jnt,
            component_grp=self.guts,
            control_grp=self.control_grp,
            divisions=self.socket_divisions,
            follow_default=self.socket_follow_default,
            main_color = self.main_color,
            sub_color = self.sub_color,
        )

        self.socket.build()

        self.eyeball = Eyeball(
            side=self.side,
            guides=self.guides,
            rig_size=self.rig_size,
            main_ctrl=self.main_ctrl,
            parent=self.main_grp,
            joint_parent=self.main_jnt,
            component_grp=self.guts,
            control_grp=self.control_grp,
            main_color = self.main_color,
        )

        self.eyeball.build_eyeball()

        self.eye_look_offset_node = BlendColorsNode(name=f"look_blend_{self.side}_BC")

        if self.side == "R":
            mirroraim = MultiplyDivideNode(name=f"{self.side}_aim_mirror_MD")
            mirroraim.input2.set((-1, -1, -1))
            mirroraim.input1.connect_from(f"{self.eyeball.look_root}.rotate")
            # add_node.input[0].connect_from(f"{self.eyeball.look_root}.rotate{axes}")
        for axes in ["X", "Y", "Z"]:
            add_node = SumNode(name=f"look_{axes}_{self.side}_ADL")
            if self.side == "R":
                add_node.input[0].connect_from(f"{mirroraim.output}{axes}")
            else:
                add_node.input[0].connect_from(f"{self.eyeball.look_root}.rotate{axes}")
            add_node.input[1].connect_from(f"{self.eyeball.eye_ctrl}.rotate{axes}")
            if axes == "X":
                color = "R"
            elif axes == "Y":
                color = "G"
            else:
                color = "B"
            add_node.output.connect_to(f"{self.eye_look_offset_node.color1}{color}")

        eyelid_follow_attr = create_attribute(
            primary_object=self.main_ctrl.ctrl,
            attr_name="eyelidFollow",
            attr_type="double",
            default=self.eyelid_follow_default,
            min=0.0,
            max=1.0,
            keyable=True,
        )

        self.eye_look_offset_node.color2.set((0, 0, 0))
        self.eye_look_offset_node.output.connect_to(
            f"{self.eyelid.look_offset}.rotate"
        )
        self.eye_look_offset_node.blender.connect_from(eyelid_follow_attr)

        matrix_constraint(
            source_transform=self.look_parent,
            constrain_transform=self.eyeball.look_ctrl.top,
            keep_offset=True,
        )