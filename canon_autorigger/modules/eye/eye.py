from .workshop_bridge import add_attribute, connect_attr, set_attr
from maya import cmds

from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.maya_api.node import BlendColorsNode, MultiplyDivideNode, SumNode
from Workshop.transform.utils import create_transform
from .workshop_bridge import matrix_constraint

from .eyelid import Eyelid
from .eyeball import Eyeball
from .socket import Socket
from Workshop.canon_autorigger.module_schema import ModuleRelationship, ModuleSetting


class Eye:
    """Workshop Eye module. Build in the same order as the source YRig module."""

    MODULE_NAME = "eye"
    DISPLAY_NAME = "Eye"
    GUIDES = ()  # Guides are resolved using side-suffixed names below.
    SETTINGS = (
        ModuleSetting(name="control_size", setting_type="float", default=1.0),
        ModuleSetting(name="main_control_shape", setting_type="control_shape", default="round_square"),
        ModuleSetting(name="main_control_direction", setting_type="string", default="z"),
        ModuleSetting(name="main_control_offset_factor", setting_type="float", default=2.0),
        ModuleSetting(name="main_control_depth_factor", setting_type="float", default=1.0),
        ModuleSetting(name="eyelid_follow_default", setting_type="float", default=0.1),
        ModuleSetting(name="eyelid_sub_divisions", setting_type="int", default=11),
        ModuleSetting(name="socket_divisions", setting_type="int", default=11),
        ModuleSetting(name="blink_extension", setting_type="float", default=2.0),
        ModuleSetting(name="collision_push", setting_type="float", default=0.5),
        ModuleSetting(name="socket_follow_default", setting_type="float", default=0.1),
    )
    RELATIONSHIPS = (
        ModuleRelationship(name="parent", relationship_type="transform", default="face_grp"),
        ModuleRelationship(name="control_parent", relationship_type="control", default="neck_M0_head_ctl"),
        ModuleRelationship(name="parent_jnt", relationship_type="joint", default="face_jnt"),
        ModuleRelationship(name="look_parent", relationship_type="control", default="Look_M_ctrl"),
    )

    def __init__(
        self,
        part: str = "eye",
        side: str = "L",
        parent: str = "face_grp",
        control_parent: str = "neck_M0_head_ctl",
        control_size: float = 1.0,
        parent_jnt: str = "face_jnt",
        look_parent: str = "Look_M_ctrl",
        guides: dict | None = None,
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
    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str = control_parent
        self.control_size: float = control_size
        self.parent_jnt: str = parent_jnt
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
        default_guides: dict = {
            #"root_name": f"eye_center_{side}",
            "center_piv": f"eye_center_{self.side}_guide",
            "aim": f"look_{self.side}_guide",
            "eyelid_upblink": f"eyelid_upblink_{self.side}_guide",
            "eyelid_upper_rest": f"eyelid_upper_{self.side}_guide",
            "eyelid_blink": f"eyelid_blink_{self.side}_guide",
            "eyelid_lower_rest": f"eyelid_lower_{self.side}_guide",
            "eyelid_downblink": f"eyelid_lowblink_{self.side}_guide",
            "socket_upper_curve": f"socket_upper_{self.side}_guide",
            "socket_lower_curve": f"socket_lower_{self.side}_guide",
            "eye_diam": f"eye_{self.side}_guide",
            "iris_diam": f"iris_{self.side}_guide",
            "pupil_diam": f"pupil_{self.side}_guide",
        }
        self.guides = {**default_guides, **(guides or {})}

    # -------------------
    # Build steps
    # -------------------

    def get_nurbs_surface_radius(self, obj: str) -> float:
        """
        Returns the radius of a NURBS circle.

        Args:
            obj (str): Transform of the NURBS circle

        Returns:
            float: radius
        """

        bbox: list[int | float] = cmds.exactWorldBoundingBox(obj)

        x: int | float = bbox[3] - bbox[0]
        y: int | float = bbox[4] - bbox[1]
        z: int | float = bbox[5] - bbox[2]

        return max(x, y, z) * 0.5

    def setup_structure(self) -> None:
        self.component_grp = create_transform(
        self.main_grp = create_transform(name=f"eye_{self.side}", parent=self.parent)
            name=f"eye_component_{self.side}", parent=self.main_grp
        )
        cmds.hide(self.component_grp)
        self.control_grp = create_transform(
            name=f"eye_control_{self.side}", parent=self.control_parent
        )

    def create_controls(self) -> None:

        eye_radius: float = self.get_nurbs_surface_radius(obj=self.guides["eye_diam"])
        offset_pos = (
            eye_radius * self.main_control_offset_factor,
            0,
            eye_radius * self.main_control_depth_factor,
        )
        self.main_ctrl = create_control(
            name=self.guides["root_name"],
            parent=self.control_grp,
            transform=self.guides["center_piv"],
            size=self.control_size,
            control_shape=self.main_control_shape,
            direction=self.main_control_direction,
            position_offset=offset_pos,
        )

    def create_joints(self) -> None:
        self.main_jnt = create_joint(
            name=self.guides["root_name"],
            parent=self.parent_jnt,
            transform=self.main_ctrl.ctrl,
        )

    def build(self) -> None:
        self.setup_structure()
        self.create_controls()
        self.create_joints()

        add_attribute(
            self.main_ctrl.ctrl,
            longName="Socket",
            attributeType="enum",
            enumName="-------------",
            keyable=True,
        )

        for vis_attr in ["sub_socket"]:
            add_attribute(
                self.main_ctrl.ctrl,
                longName=vis_attr,
                attributeType="bool",
                defaultValue=False,
                keyable=True,
            )

        add_attribute(
            self.main_ctrl.ctrl,
            longName="Eyelid_Controls",
            attributeType="enum",
            enumName="-------------",
            keyable=True,
        )

        add_attribute(
            self.main_ctrl.ctrl,
            longName="eyelidFollow",
            attributeType="double",
            minValue=0.0,
            maxValue=1.0,
            defaultValue=self.eyelid_follow_default,
            keyable=True,
        )

        """self.eyelid = Eyelid(
            side=self.side,
            guides=self.guides,
            control_size=self.control_size,
            main_ctrl=self.main_ctrl.ctrl,
            parent=self.main_grp,
            joint_parent=self.main_jnt,
            component_grp=self.component_grp,
            control_grp=self.control_grp,
        )

        self.eyelid.build_blink()"""

        self.eyelid = Eyelid(
            side=self.side,
            guides=self.guides,
            control_size=self.control_size,
            main_ctrl=self.main_ctrl.ctrl,
            parent=self.main_grp,
            joint_parent=self.main_jnt,
            component_grp=self.component_grp,
            control_grp=self.control_grp,
        )
        self.eyelid.build(
            sub_divisions=self.eyelid_sub_divisions,
            blink_extension=self.blink_extension,
            collision_push=self.collision_push,
        )

        self.socket = Socket(
            side=self.side,
            guides=self.guides,
            control_size=self.control_size,
            main_ctrl=self.main_ctrl.ctrl,
            parent=self.main_grp,
            joint_parent=self.main_jnt,
            component_grp=self.component_grp,
            control_grp=self.control_grp,
            divisions=self.socket_divisions,
            follow_default=self.socket_follow_default,
        )

        self.socket.build_socket()

        self.eyeball = Eyeball(
            side=self.side,
            guides=self.guides,
            control_size=self.control_size,
            main_ctrl=self.main_ctrl.ctrl,
            parent=self.main_grp,
            joint_parent=self.main_jnt,
            component_grp=self.component_grp,
            control_grp=self.control_grp,
        )

        self.eyeball.build_eyeball()

        self.eye_look_offset_node = BlendColorsNode.create(name=f"look_blend_{self.side}_BC")

        if self.side == "R":
            mirroraim = MultiplyDivideNode.create(name=f"{self.side}_aim_mirror_MD")
            mirroraim.input2.set((-1, -1, -1))
            mirroraim.input1.connect_from(f"{self.eyeball.look_root}.rotate")
            # add_node.input[0].connect_from(f"{self.eyeball.look_root}.rotate{axes}")
        for axes in ["X", "Y", "Z"]:
            add_node = SumNode.create(name=f"look_{axes}_{self.side}_ADL")
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

        self.eye_look_offset_node.blender.set(0.1)
        self.eye_look_offset_node.color2.set((0, 0, 0))
        self.eye_look_offset_node.output.connect_to(f"{self.eyelid.look_offset}.rotate")
        self.eye_look_offset_node.blender.connect_from(f"{self.main_ctrl.ctrl}.eyelidFollow")

        matrix_constraint(
            source_transform=self.look_parent,
            constrain_transform=self.eyeball.look_ctrl.offset,
            keep_offset=True,
        )
