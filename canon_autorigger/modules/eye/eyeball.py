import math

from maya import cmds

from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.maya_api.node import (
    BlendColorsNode,
    EulerToQuatNode,
    MultiplyDivideNode,
    SumNode,
)
from Workshop.transform.utils import create_transform, match_location
from Workshop.transform.utils import get_position
from Workshop.nurbs.curve import get_nurbs_curve_radius
from Workshop.control.core import Control
from Workshop.maya_api.attribute_utils import connect_attributes, create_attribute, add_attribute_header, set_attribute
from Workshop.skin.split.tag import tag_for_weight_split
from Workshop.transform.matrix import matrix_constraint


class Eyeball:
    def __init__(
        self,
        main_ctrl:Control,
        guides: dict,
        side: str = "L",
        rig_size: float = 1.0,
        parent: str = "",
        joint_parent: str = "",
        component_grp: str = "",
        control_grp: str = "",
        divisions:int = 10
    ) -> None:
        if guides is None:
            guides = {}
        self.side = side
        self.guides = guides
        self.main_ctrl = main_ctrl
        self.rig_size = rig_size
        self.parent = parent
        self.joint_parent = joint_parent
        self.component_grp = component_grp
        self.control_grp = control_grp
        self.divisions = divisions

    # -------------------
    # Helper Functions
    # -------------------

    def compare_radius_and_angle(self, obj_a: str, obj_b: str) -> float:
        """
        Compares two NURBS surfaces and returns:
        - percentage difference (based on radius)
        - estimated angle (based on cosine relationship)

        Args:
            obj_a (str): reference object (true size)
            obj_b (str): compared object (projected/tilted)

        Returns:
            (percent, angle_degrees)
        """

        r1: float =  get_nurbs_curve_radius(obj_a)
        r2: float =  get_nurbs_curve_radius(obj_b)

        if r1 == 0:
            raise RuntimeError(f"{obj_a} has zero radius")

        ratio: float = r2 / r1

        # Clamp for safety (floating point issues)
        ratio = max(min(ratio, 1.0), -1.0)

        angle_rad: float = math.acos(ratio)
        angle_deg: float = math.degrees(angle_rad)

        percent: float = ratio * 100.0

        return angle_deg

    def sphere_edge_loop_offsets(self, radius: float, num_loops: int) -> list:
        """
        Returns Y offsets from center loop (equator) to pole on a sphere.
        """
        offsets = []

        for i in range(num_loops + 1):
            t = i / float(num_loops)  # 0 → 1
            theta = t * (math.pi / 2)  # equator → pole
            y = radius * math.sin(theta)
            offsets.append(y)

        return offsets

    def create_eye_preview_circle(self, name_suffix: str, parent: str) -> str:
        eye_radius: float =  get_nurbs_curve_radius(self.guides["eye_diam"])

        eye_center_pos = get_position(self.guides["center_piv"])

        crv: str = cmds.circle(  # type:ignore
            name=f"preview_{name_suffix}_crv",
            radius=eye_radius,
            normal=[0, 0, 1],  # type:ignore
            sections=16,
            degree=3,
        )[0]

        cmds.parent(crv, parent)
        match_location(transform=crv, target_transform=self.guides["center_piv"])

        return crv

    def dilation_nodes(
        self,
        circle_type: str,
        obj: str,
        eye_radius: float,
        dilation_attr: str,
        new_attr: bool,
        new_attr_tgt: str | None,
        offset_x_attr: str,
        offset_y_attr: str,
        offset_z_attr: str,
        scale_x_attr: str,
        scale_y_attr: str,
    ) -> None:

        if new_attr:
            dilation_attr = create_attribute(
                primary_object=new_attr_tgt, #type:ignore
                attr_name=f"{circle_type}_{obj}_dilation",
            )  # type:ignore

        dilation_mult = MultiplyDivideNode(
            name=f"{circle_type}_dilation_mult_{self.side}_MD"
        )

        # Fixed dilation angle instead of DEV attribute
        dilation_mult.input2.x.set(18)

        dilation_mult.input1.x.connect_from(dilation_attr)

        etq_node = EulerToQuatNode(
            name=f"{circle_type}_dilation_mult_{self.side}_ETQ",
        )
        etq_node.input_rotate.x.connect_from(dilation_mult.output.x)

        radius_adjust = MultiplyDivideNode(
            name=f"{circle_type}_radius_adjust_{self.side}_MD"
        )
        radius_adjust.input1.x.connect_from(etq_node.output_quat.x)

        z_trans_adl = SumNode(
            name=f"{circle_type}_translateZ_{self.side}_ADL"
        )

        radius_adjust.output.x.connect_to(z_trans_adl.input[0])
        z_trans_adl.output.connect_to(f"{obj}.translateZ")

        etq_node.output_quat.w.connect_to(f"{obj}.scaleZ")

        # Fixed eye radius instead of DEV parameter
        radius_adjust.input2.x.set(eye_radius)

        # Scale adjustments
        radius_adjust.input1.y.connect_from(etq_node.output_quat.w)
        radius_adjust.input1.z.connect_from(etq_node.output_quat.w)

        radius_adjust.input2.z.connect_from(scale_x_attr)
        radius_adjust.input2.y.connect_from(scale_y_attr)

        radius_adjust.output.y.connect_to(f"{obj}.scaleY")
        radius_adjust.output.z.connect_to(f"{obj}.scaleX")

        z_trans_adl.input[1].connect_from(offset_z_attr)
        connect_attributes(offset_y_attr, [f"{obj}.translateY"])
        connect_attributes(offset_x_attr, [f"{obj}.translateX"])

    def build_eyeball(self) -> None:
        eye_radius: float =  get_nurbs_curve_radius(self.guides["eye_diam"])
        add_attribute_header(target=self.main_ctrl.ctrl, name="dilation_controls")

        self.eye_ctrl = create_control(
            name=f"eye_{self.side}",
            parent=self.main_ctrl,
            transform=self.guides["center"].name,
            control_shape="circle",
            direction="z",
            size=eye_radius / 4,
            shape_position_offset=(0, 0, eye_radius),
        )
        self.eye_jnt = create_joint(
            transform=self.eye_ctrl.ctrl, name=f"eye_{self.side}", parent=self.joint_parent
        )

        self.look_ctrl = create_control(
            name=f"look_{self.side}",
            parent=self.control_grp,
            transform=self.guides["aim"].name,
            control_shape="circle",
            direction="z",
            size=eye_radius / 2,
        )

        self.look_root = create_joint(
            transform=self.eye_ctrl.ctrl,
            name=f"look_root_{self.side}",
            parent=self.component_grp,
            connect=False,
        )

        self.look_end = create_joint(
            transform=self.look_ctrl.ctrl,
            name=f"look_end_{self.side}",
            parent=self.look_root,
            connect=False,
        )

        self.ik_handle, self.effector = cmds.ikHandle(
            name=f"aim_sc_{self.side}_ikh",
            startJoint=self.look_root,
            endEffector=self.look_end,
            solver="ikSCsolver",
        )  # type: ignore

        cmds.parent(self.ik_handle, self.component_grp)

        matrix_constraint(self.look_ctrl.ctrl, self.ik_handle)
        cmds.pointConstraint(self.main_ctrl.ctrl, self.look_root, maintainOffset=True)
        cmds.orientConstraint(self.look_root, self.eye_ctrl.top, maintainOffset=True)

        pupil_degree: float = round(
            self.compare_radius_and_angle(self.guides["eye_diam"], self.guides["pupil_diam"])
        )

        iris_degree: float = round(
            self.compare_radius_and_angle(self.guides["eye_diam"], self.guides["iris_diam"])
        )

        pupil_percent = pupil_degree / 90
        iris_percent = iris_degree / 90

        eye_center_pos = self.guides["center"].pos

        percents = [0, iris_percent, pupil_percent, 1]

        create_attribute(primary_object=self.main_ctrl.ctrl, attr_name="pupil_dilation", min=0 - (pupil_percent * 10), max=10 - (pupil_percent * 10), proxy_objects=[self.eye_ctrl.ctrl, self.look_ctrl.ctrl], default=0)
        create_attribute(primary_object=self.main_ctrl.ctrl, attr_name="iris_dilation", min=0 - (iris_percent * 10), max=10 - (iris_percent * 10), proxy_objects=[self.eye_ctrl.ctrl, self.look_ctrl.ctrl], default=0)
        create_attribute(primary_object=self.main_ctrl.ctrl, attr_name="end_dilation", min=0 , max=10, keyable=False, hidden=True, default=10)
        create_attribute(primary_object=self.main_ctrl.ctrl, attr_name="center_dilation", min=0, max=10, keyable=False, hidden=True, default=0)

        dilation_offset = create_transform(
            name=f"dilation_{self.side}_Offset",
            parent=self.eye_ctrl.ctrl,
            transform=self.guides["center"].name,
        )

        cmds.hide(dilation_offset)

        self.preview_circles = {}

        for i, circle_type in enumerate(["center", "iris", "pupil", "end"]):
            circle = self.create_eye_preview_circle(
                name_suffix=f"{circle_type}_{self.side}", parent=f"{dilation_offset}"
            )
            self.preview_circles[f"{circle_type}"] = circle
            create_attribute(primary_object=circle, attr_name="dilation_amount",)
            key = circle_type in ["iris", "pupil"]

            if key:
                add_attribute_header(target=self.main_ctrl.ctrl, name=f"{circle_type}_adjustments", proxy=[self.eye_ctrl.ctrl, self.look_ctrl.ctrl], sub=True)
            create_attribute(primary_object=self.main_ctrl.ctrl, attr_name=f"{circle_type}_scaleX", proxy_objects=[self.eye_ctrl.ctrl, self.look_ctrl.ctrl], keyable=key,)
            create_attribute(primary_object=self.main_ctrl.ctrl, attr_name=f"{circle_type}_scaleY", proxy_objects=[self.eye_ctrl.ctrl, self.look_ctrl.ctrl], keyable=key,)
            create_attribute(primary_object=self.main_ctrl.ctrl, attr_name=f"{circle_type}_offsetY", proxy_objects=[self.eye_ctrl.ctrl, self.look_ctrl.ctrl], keyable=key,)
            create_attribute(primary_object=self.main_ctrl.ctrl, attr_name=f"{circle_type}_offsetX", proxy_objects=[self.eye_ctrl.ctrl, self.look_ctrl.ctrl], keyable=key,)
            create_attribute(primary_object=self.main_ctrl.ctrl, attr_name=f"{circle_type}_offsetZ", proxy_objects=[self.eye_ctrl.ctrl, self.look_ctrl.ctrl], keyable=key,)



            if circle_type == "center":
                pass
            else:
                # percents[i]
                dilation_offset_node = SumNode(
                    name=f"{circle_type}_dilation_mult_{self.side}_ADL"
                )
                dilation_offset_node.input[1].connect_from(f"{self.main_ctrl}.{circle_type}_dilation")
                dilation_offset_node.input[0].set(percents[i] * 10)
                dilation_offset_node.output.connect_to(f"{circle}.dilation_amount")
                
                self.dilation_nodes(
                    circle_type=circle_type,
                    obj=circle,
                    eye_radius=eye_radius,
                    dilation_attr=f"{dilation_offset_node.output}",
                    new_attr=False,
                    new_attr_tgt=None,
                    scale_x_attr=f"{self.main_ctrl}.{circle_type}_scaleX",
                    scale_y_attr=f"{self.main_ctrl}.{circle_type}_scaleY",
                    offset_x_attr=f"{self.main_ctrl}.{circle_type}_offsetX",
                    offset_y_attr=f"{self.main_ctrl}.{circle_type}_offsetY",
                    offset_z_attr=f"{self.main_ctrl}.{circle_type}_offsetZ",
                )

        # joints
        loops_list = self.sphere_edge_loop_offsets(radius=eye_radius, num_loops=self.divisions)

        self.dilation_joints = []

        for i, loop in enumerate(loops_list):
            parent = self.eye_jnt

            jnt = create_joint(
                name=f"eye_dilation_{i:02d}_{self.side}",
                parent=parent,
                transform=self.guides["center_piv"].name,
                connect=False,
            )
            self.dilation_joints.append(jnt)
            set_attribute(attr=f"{jnt}.translateZ", value=loop)
            x = i / 10.0
            if x < iris_percent:
                blend = ["iris", "center"]
                blend_num = x / iris_percent

            elif x < pupil_percent:
                blend = ["pupil", "iris"]
                blend_num = (x - iris_percent) / (pupil_percent - iris_percent)

            else:
                blend = ["pupil", "pupil"]
                blend_num = (x - pupil_percent) / (1.0 - pupil_percent)

            blendnode = BlendColorsNode(name=f"blend_dilation_{i:02d}_{self.side}_BC")
            blendnode2 = BlendColorsNode(name=f"blend_offset_{i:02d}_{self.side}_BC")
            blendnode.color1.r.connect_from(
                source_attr=f"{self.preview_circles[blend[0]]}.dilation_amount"
            )
            blendnode.color2.r.connect_from(
                source_attr=f"{self.preview_circles[blend[1]]}.dilation_amount"
            )
            blendnode.blender.set(blend_num)

            blendnode.color1.g.connect_from(source_attr=f"{self.main_ctrl}.{blend[0]}_scaleY")
            blendnode.color1.b.connect_from(source_attr=f"{self.main_ctrl}.{blend[0]}_scaleX")
            blendnode.color2.g.connect_from(source_attr=f"{self.main_ctrl}.{blend[1]}_scaleY")
            blendnode.color2.b.connect_from(source_attr=f"{self.main_ctrl}.{blend[1]}_scaleX")

            blendnode2.blender.set(blend_num)

            blendnode2.color1.g.connect_from(source_attr=f"{self.main_ctrl}.{blend[0]}_offsetY")
            blendnode2.color1.b.connect_from(source_attr=f"{self.main_ctrl}.{blend[0]}_offsetX")
            blendnode2.color2.g.connect_from(source_attr=f"{self.main_ctrl}.{blend[1]}_offsetY")
            blendnode2.color2.b.connect_from(source_attr=f"{self.main_ctrl}.{blend[1]}_offsetX")
            blendnode2.color1.r.connect_from(source_attr=f"{self.main_ctrl}.{blend[0]}_offsetZ")
            blendnode2.color2.r.connect_from(source_attr=f"{self.main_ctrl}.{blend[1]}_offsetZ")

            self.dilation_nodes(
                circle_type=f"loop{i:02d}",
                obj=jnt,
                eye_radius=eye_radius,
                dilation_attr=f"{blendnode.output.r}",
                new_attr=False,
                new_attr_tgt=None,
                scale_x_attr=f"{blendnode.output.b}",
                scale_y_attr=f"{blendnode.output.g}",
                offset_x_attr=f"{blendnode2.output.b}",
                offset_y_attr=f"{blendnode2.output.g}",
                offset_z_attr=f"{blendnode2.output.r}",
            )
        tag_for_weight_split(
            influence=self.dilation_joints[0],
            split_influences=self.dilation_joints,
        )

